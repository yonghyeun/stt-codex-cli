import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { copyFile, mkdir, rename, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import * as pty from "node-pty";

import {
  childArgv,
  parseKeySequence,
  runIdFromDate,
  splitByTrigger,
  type InjectMode,
} from "@/features/codex-pty";
import { transcribeAudio } from "@/features/stt-adapter";
import { repoRoot } from "@/shared/repo";
import { hasMeaningfulText } from "@/shared/text";

import { isDirectRun } from "./shared/direct-run";

const DEFAULT_CMD = "codex";
const DEFAULT_INJECT_MODE = "stt";
const DEFAULT_FIXED_INJECT_KEY = "ctrl+t";
const DEFAULT_STT_INJECT_KEY = "ctrl+t";
const DEFAULT_INJECT_TEXT = "hello from stt wrapper";
const DEFAULT_RELEASE_GAP = 0.75;
const DEFAULT_MAX_DURATION = 60;
const DEFAULT_MIN_DURATION = 0.15;
const DEFAULT_RUN_OUTPUT_DIR = "output/runs";
const PARENT_PREFIX = "[stt-parent]";

interface Args {
  cmd: string;
  cwd?: string;
  quietParent: boolean;
  noColor: boolean;
  codexAltScreen: boolean;
  injectMode: InjectMode;
  injectKey: string;
  injectKeyBytes: Buffer;
  injectText: string;
  disableInjectKey: boolean;
  releaseGap: number;
  maxDuration: number;
  minDuration: number;
  tempDir?: string;
  keepAudio: boolean;
  saveRun: boolean;
  runOutputDir: string;
  sttModel: string;
  sttLanguage: string;
  sttDevice: "auto" | "cpu" | "cuda";
  sttComputeType: string;
  sttBeamSize: number;
  sttInitialPrompt?: string;
  sttNoVadFilter: boolean;
  cmdArgs: string[];
}

interface RecordingState {
  process?: ChildProcessWithoutNullStreams;
  audioFile?: string;
  startedAt?: number;
  startedWallAt?: Date;
  lastTriggerAt?: number;
}

export async function main(argv = process.argv.slice(2)): Promise<number> {
  const parsed = parseArgs(argv);
  if (parsed.kind === "help") {
    process.stdout.write(`${usage()}\n`);
    return 0;
  }
  if (parsed.kind === "error") {
    process.stderr.write(`error: ${parsed.message}\n${usage()}\n`);
    return 2;
  }

  const args = parsed.args;
  try {
    const child = childArgv({
      command: args.cmd,
      args: args.cmdArgs,
      codexAltScreen: args.codexAltScreen,
    });
    parentBanner(args, child);
    const exitCode = await runWrapper(args, child);
    parentStatus(args, `child exited: ${exitCode}`);
    return exitCode;
  } catch (error) {
    process.stderr.write(
      `error: ${error instanceof Error ? error.message : String(error)}\n`,
    );
    return 1;
  }
}

type ParseResult =
  | { kind: "ok"; args: Args }
  | { kind: "help" }
  | { kind: "error"; message: string };

function parseArgs(argv: string[]): ParseResult {
  const args: Args = {
    cmd: process.env.STT_CODEX_CMD ?? DEFAULT_CMD,
    quietParent: false,
    noColor: false,
    codexAltScreen: false,
    injectMode: (process.env.STT_INJECT_MODE ??
      DEFAULT_INJECT_MODE) as InjectMode,
    injectKey: "",
    injectKeyBytes: Buffer.alloc(0),
    injectText: process.env.STT_INJECT_TEXT ?? DEFAULT_INJECT_TEXT,
    disableInjectKey: false,
    releaseGap: numberEnv("STT_PTT_RELEASE_GAP", DEFAULT_RELEASE_GAP),
    maxDuration: numberEnv("STT_PTT_MAX_DURATION", DEFAULT_MAX_DURATION),
    minDuration: numberEnv("STT_PTT_MIN_DURATION", DEFAULT_MIN_DURATION),
    tempDir: process.env.STT_TEMP_DIR,
    keepAudio: false,
    saveRun: false,
    runOutputDir: process.env.STT_RUN_OUTPUT_DIR ?? DEFAULT_RUN_OUTPUT_DIR,
    sttModel: process.env.STT_MODEL ?? "large-v3",
    sttLanguage: process.env.STT_LANGUAGE ?? "ko",
    sttDevice: (process.env.STT_DEVICE ?? "auto") as "auto" | "cpu" | "cuda",
    sttComputeType: process.env.STT_COMPUTE_TYPE ?? "auto",
    sttBeamSize: Number(process.env.STT_BEAM_SIZE ?? "5"),
    sttInitialPrompt: process.env.STT_INITIAL_PROMPT,
    sttNoVadFilter: false,
    cmdArgs: [],
  };
  args.injectKey =
    process.env.STT_INJECT_KEY ??
    (args.injectMode === "stt"
      ? DEFAULT_STT_INJECT_KEY
      : DEFAULT_FIXED_INJECT_KEY);

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index] ?? "";
    if (arg === "-h" || arg === "--help") {
      return { kind: "help" };
    }
    if (arg === "--quiet-parent") {
      args.quietParent = true;
      continue;
    }
    if (arg === "--no-color") {
      args.noColor = true;
      continue;
    }
    if (arg === "--codex-alt-screen") {
      args.codexAltScreen = true;
      continue;
    }
    if (arg === "--disable-inject-key") {
      args.disableInjectKey = true;
      continue;
    }
    if (arg === "--keep-audio") {
      args.keepAudio = true;
      continue;
    }
    if (arg === "--save-run") {
      args.saveRun = true;
      continue;
    }
    if (arg === "--stt-no-vad-filter") {
      args.sttNoVadFilter = true;
      continue;
    }
    if (arg === "--") {
      args.cmdArgs = argv.slice(index + 1);
      break;
    }
    const valueOptions = new Set([
      "--cmd",
      "--cwd",
      "--inject-mode",
      "--inject-key",
      "--inject-text",
      "--release-gap",
      "--max-duration",
      "--min-duration",
      "--temp-dir",
      "--run-output-dir",
      "--stt-model",
      "--stt-language",
      "--stt-device",
      "--stt-compute-type",
      "--stt-beam-size",
      "--stt-initial-prompt",
    ]);
    if (valueOptions.has(arg)) {
      const value = argv[index + 1];
      if (value === undefined) {
        return { kind: "error", message: `${arg} requires a value` };
      }
      index += 1;
      const error = assignOption(args, arg, value);
      if (error) {
        return { kind: "error", message: error };
      }
      continue;
    }
    return { kind: "error", message: `unknown option: ${arg}` };
  }

  if (args.injectMode !== "stt" && args.injectMode !== "fixed-text") {
    return {
      kind: "error",
      message: "--inject-mode must be one of: stt, fixed-text",
    };
  }
  if (args.injectText === "") {
    return { kind: "error", message: "--inject-text must not be empty" };
  }
  try {
    args.injectKeyBytes = parseKeySequence(args.injectKey);
  } catch (error) {
    return {
      kind: "error",
      message: error instanceof Error ? error.message : String(error),
    };
  }
  return { kind: "ok", args };
}

function assignOption(
  args: Args,
  name: string,
  value: string,
): string | undefined {
  if (name === "--cmd") args.cmd = value;
  else if (name === "--cwd") args.cwd = value;
  else if (name === "--inject-mode") args.injectMode = value as InjectMode;
  else if (name === "--inject-key") args.injectKey = value;
  else if (name === "--inject-text") args.injectText = value;
  else if (name === "--release-gap")
    args.releaseGap = positiveNumber(value, name);
  else if (name === "--max-duration")
    args.maxDuration = positiveNumber(value, name);
  else if (name === "--min-duration")
    args.minDuration = positiveNumber(value, name);
  else if (name === "--temp-dir") args.tempDir = value;
  else if (name === "--run-output-dir") args.runOutputDir = value;
  else if (name === "--stt-model") args.sttModel = value;
  else if (name === "--stt-language") args.sttLanguage = value;
  else if (name === "--stt-device") {
    if (value !== "auto" && value !== "cpu" && value !== "cuda") {
      return "--stt-device must be one of: auto, cpu, cuda";
    }
    args.sttDevice = value;
  } else if (name === "--stt-compute-type") args.sttComputeType = value;
  else if (name === "--stt-beam-size") {
    const beamSize = Number(value);
    if (!Number.isInteger(beamSize) || beamSize <= 0) {
      return `invalid --stt-beam-size: ${value}`;
    }
    args.sttBeamSize = beamSize;
  } else if (name === "--stt-initial-prompt") args.sttInitialPrompt = value;
  return undefined;
}

async function runWrapper(args: Args, argv: string[]): Promise<number> {
  const child = pty.spawn(argv[0] ?? args.cmd, argv.slice(1), {
    cwd: args.cwd ? resolve(args.cwd) : process.cwd(),
    env: process.env,
    cols: process.stdout.columns || 80,
    rows: process.stdout.rows || 24,
    name: "xterm-color",
  });
  parentStatus(args, `child pid: ${child.pid}`);

  const state: RecordingState = {};
  const interval = setInterval(() => {
    void maybeFinishSttRecording(args, child, state);
  }, 100);
  const restoreRaw = enableRawMode();

  process.stdout.on("resize", () => {
    child.resize(process.stdout.columns || 80, process.stdout.rows || 24);
  });
  child.onData((data) => process.stdout.write(data));
  process.stdin.on("data", (data: Buffer) => {
    void handleStdinData(args, child, data, state);
  });

  return await new Promise((resolvePromise) => {
    child.onExit(({ exitCode }) => {
      clearInterval(interval);
      restoreRaw();
      if (state.process) {
        void stopRecording(args, state).then(({ audioFile }) =>
          cleanupAudio(args, audioFile),
        );
      }
      resolvePromise(exitCode);
    });
  });
}

function enableRawMode(): () => void {
  if (!process.stdin.isTTY) {
    return () => undefined;
  }
  const wasRaw = process.stdin.isRaw;
  process.stdin.setRawMode(true);
  process.stdin.resume();
  return () => {
    process.stdin.setRawMode(wasRaw);
  };
}

async function handleStdinData(
  args: Args,
  child: pty.IPty,
  data: Buffer,
  state: RecordingState,
): Promise<void> {
  if (args.disableInjectKey) {
    child.write(data.toString("utf8"));
    return;
  }

  if (args.injectMode === "fixed-text") {
    const parts = splitByTrigger(data, args.injectKeyBytes);
    for (let index = 0; index < parts.length; index += 1) {
      const part = parts[index];
      if (part && part.length > 0) {
        child.write(part.toString("utf8"));
      }
      if (index < parts.length - 1) {
        child.write(args.injectText);
        parentStatus(
          args,
          `injected ${args.injectText.length} chars; review text, then press Enter to send`,
        );
      }
    }
    return;
  }

  const parts = splitByTrigger(data, args.injectKeyBytes);
  for (let index = 0; index < parts.length; index += 1) {
    const part = parts[index];
    if (part && part.length > 0) {
      child.write(part.toString("utf8"));
    }
    if (index < parts.length - 1) {
      await startRecording(args, state);
      state.lastTriggerAt = performance.now();
    }
  }
}

async function startRecording(
  args: Args,
  state: RecordingState,
): Promise<void> {
  if (state.process) {
    return;
  }
  const audioFile = join(
    args.tempDir ?? tmpdir(),
    `stt-codex-${process.pid}-${Date.now()}.wav`,
  );
  const config = {
    device: process.env.STT_RECORD_DEVICE ?? "default",
    format: process.env.STT_RECORD_FORMAT ?? "S16_LE",
    rate: process.env.STT_RECORD_RATE ?? "16000",
    channels: process.env.STT_RECORD_CHANNELS ?? "1",
  };
  state.process = spawn("arecord", [
    "-D",
    config.device,
    "-f",
    config.format,
    "-r",
    config.rate,
    "-c",
    config.channels,
    audioFile,
  ]);
  state.audioFile = audioFile;
  state.startedAt = performance.now();
  state.startedWallAt = new Date();
  state.lastTriggerAt = state.startedAt;
  parentStatus(args, `recording started: ${audioFile}`);
}

async function maybeFinishSttRecording(
  args: Args,
  child: pty.IPty,
  state: RecordingState,
): Promise<void> {
  if (
    !state.process ||
    state.lastTriggerAt === undefined ||
    state.startedAt === undefined
  ) {
    return;
  }
  const now = performance.now();
  const elapsed = (now - state.startedAt) / 1000;
  const elapsedSinceTrigger = (now - state.lastTriggerAt) / 1000;
  if (elapsed >= args.maxDuration) {
    parentStatus(args, `max duration reached: ${args.maxDuration}s`);
    await finishRecordingAndInject(args, child, state);
    return;
  }
  if (elapsedSinceTrigger >= args.releaseGap) {
    await finishRecordingAndInject(args, child, state);
  }
}

async function finishRecordingAndInject(
  args: Args,
  child: pty.IPty,
  state: RecordingState,
): Promise<void> {
  const { audioFile, elapsed, startedAt } = await stopRecording(args, state);
  let transcript = "";
  let injected = false;
  let outcome = "unknown";
  let errorMessage: string | undefined;
  try {
    if (elapsed < args.minDuration) {
      parentStatus(
        args,
        `recording too short: ${elapsed.toFixed(2)}s < ${args.minDuration}s; skipped STT`,
      );
      outcome = "skipped_short_recording";
      return;
    }
    parentStatus(args, "transcribing...");
    transcript = await transcribeAudio(audioFile, {
      model: args.sttModel,
      language: args.sttLanguage,
      device: args.sttDevice,
      computeType: args.sttComputeType,
      beamSize: args.sttBeamSize,
      initialPrompt: args.sttInitialPrompt,
      vadFilter: !args.sttNoVadFilter,
    });
    if (!hasMeaningfulText(transcript)) {
      parentStatus(args, "empty transcript; nothing injected");
      outcome = "empty_transcript";
      return;
    }
    child.write(transcript);
    injected = true;
    outcome = "injected";
    parentStatus(
      args,
      `injected transcript ${transcript.length} chars; review text, then press Enter to send`,
    );
  } catch (error) {
    outcome = "stt_error";
    errorMessage = error instanceof Error ? error.message : String(error);
    parentStatus(args, `stt error: ${errorMessage}`);
  } finally {
    await saveRunArtifacts(args, {
      audioFile,
      transcript,
      startedAt,
      elapsed,
      injected,
      outcome,
      error: errorMessage,
    });
    await cleanupAudio(args, audioFile);
  }
}

async function stopRecording(
  args: Args,
  state: RecordingState,
): Promise<{ audioFile: string; elapsed: number; startedAt: Date }> {
  if (!state.process || !state.audioFile || !state.startedAt) {
    throw new Error("recording is not running");
  }
  const processToStop = state.process;
  const audioFile = state.audioFile;
  const startedAt = state.startedWallAt ?? new Date();
  const elapsed = (performance.now() - state.startedAt) / 1000;
  processToStop.kill("SIGINT");
  await waitForExit(processToStop, 5000);
  state.process = undefined;
  state.audioFile = undefined;
  state.startedAt = undefined;
  state.startedWallAt = undefined;
  state.lastTriggerAt = undefined;
  parentStatus(args, `recording stopped: elapsed=${elapsed.toFixed(2)}s`);
  return { audioFile, elapsed, startedAt };
}

function waitForExit(
  child: ChildProcessWithoutNullStreams,
  timeoutMs: number,
): Promise<void> {
  return new Promise((resolvePromise) => {
    const timeout = setTimeout(() => {
      child.kill("SIGTERM");
      resolvePromise();
    }, timeoutMs);
    child.once("exit", () => {
      clearTimeout(timeout);
      resolvePromise();
    });
  });
}

async function saveRunArtifacts(
  args: Args,
  input: {
    audioFile: string;
    transcript: string;
    startedAt: Date;
    elapsed: number;
    injected: boolean;
    outcome: string;
    error?: string;
  },
): Promise<void> {
  if (!args.saveRun) {
    return;
  }
  const runDir = await createRunDir(args, input.startedAt);
  const audioOutput = join(runDir, "audio.wav");
  if (args.keepAudio) {
    await copyFile(input.audioFile, audioOutput);
  } else {
    await rename(input.audioFile, audioOutput);
  }
  await writeFile(
    join(runDir, "transcript.txt"),
    `${input.transcript}\n`,
    "utf8",
  );
  await writeFile(
    join(runDir, "metadata.json"),
    `${JSON.stringify(
      {
        schema_version: 1,
        run_id: runDir.split("/").at(-1),
        created_at: new Date().toISOString(),
        recording_started_at: input.startedAt.toISOString(),
        elapsed_seconds: Math.round(input.elapsed * 1000) / 1000,
        outcome: input.outcome,
        injected: input.injected,
        transcript_chars: input.transcript.length,
        transcript_has_text: hasMeaningfulText(input.transcript),
        audio_file: "audio.wav",
        transcript_file: "transcript.txt",
        error: input.error ?? null,
        stt: {
          model: args.sttModel,
          language: args.sttLanguage,
          device: args.sttDevice,
          compute_type: args.sttComputeType,
          beam_size: args.sttBeamSize,
          vad_filter: !args.sttNoVadFilter,
          initial_prompt: args.sttInitialPrompt,
        },
      },
      null,
      2,
    )}\n`,
    "utf8",
  );
  parentStatus(args, `saved run artifacts: ${runDir}`);
}

async function createRunDir(args: Args, timestamp: Date): Promise<string> {
  const outputDir = resolve(repoRoot, args.runOutputDir);
  await mkdir(outputDir, { recursive: true });
  const base = runIdFromDate(timestamp);
  for (let suffix = 0; suffix < 1000; suffix += 1) {
    const name =
      suffix === 0 ? base : `${base}-${String(suffix).padStart(3, "0")}`;
    const path = join(outputDir, name);
    try {
      await mkdir(path);
      return path;
    } catch {
      continue;
    }
  }
  throw new Error(`could not create unique run directory under ${outputDir}`);
}

async function cleanupAudio(args: Args, audioFile: string): Promise<void> {
  if (args.keepAudio) {
    parentStatus(args, `kept audio: ${audioFile}`);
    return;
  }
  try {
    await unlink(audioFile);
    parentStatus(args, "deleted temporary audio");
  } catch {
    return;
  }
}

function parentBanner(args: Args, argv: string[]): void {
  parentStatus(args, `starting child: ${argv.join(" ")}`);
  parentStatus(args, `cwd: ${args.cwd ?? process.cwd()}`);
  if (args.disableInjectKey) {
    parentStatus(args, "injection key disabled");
  } else if (args.injectMode === "fixed-text") {
    parentStatus(
      args,
      `inject key: ${args.injectKey} -> ${args.injectText.length} chars; Enter still manual`,
    );
  } else {
    parentStatus(
      args,
      `ptt key: ${args.injectKey}; release gap ${args.releaseGap}s; Enter still manual`,
    );
  }
  parentStatus(args, "child output follows");
}

function parentStatus(args: Args, message: string): void {
  if (args.quietParent) {
    return;
  }
  const prefix =
    process.stderr.isTTY && !args.noColor
      ? `\u001b[36m${PARENT_PREFIX}\u001b[0m`
      : PARENT_PREFIX;
  process.stderr.write(`${prefix} ${message}\n`);
}

function numberEnv(name: string, fallback: number): number {
  const value = process.env[name];
  return value === undefined ? fallback : positiveNumber(value, name);
}

function positiveNumber(value: string, label: string): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`${label} must be positive: ${value}`);
  }
  return parsed;
}

function usage(): string {
  return "Usage: npm run stt-codex -- [options] [-- child args...]";
}

if (isDirectRun(import.meta.url)) {
  process.exitCode = await main();
}
