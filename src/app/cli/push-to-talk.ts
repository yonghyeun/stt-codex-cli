import { spawn, type ChildProcessWithoutNullStreams } from "node:child_process";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";

import {
  defaultRecordingConfig,
  recordingFileName,
} from "@/features/audio-recording";

import { main as sttClipboardMain } from "./stt-clipboard";
import { isDirectRun } from "./shared/direct-run";

interface Args {
  backend: "stdin-repeat" | "xinput";
  triggerKey: string;
  releaseGap: number;
  outputDir: string;
  recordOnly: boolean;
  sttArgs: string[];
}

interface RecordingState {
  process?: ChildProcessWithoutNullStreams;
  outputFile?: string;
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

  try {
    if (parsed.args.backend !== "stdin-repeat") {
      throw new Error(
        "TS push-to-talk currently supports --backend stdin-repeat",
      );
    }
    process.stderr.write(
      `waiting: backend=stdin-repeat trigger-key=${parsed.args.triggerKey} release-gap=${parsed.args.releaseGap}s\n`,
    );
    const recording = await recordOnceWithStdinRepeat(parsed.args);
    if (parsed.args.recordOnly) {
      process.stdout.write(`${recording}\n`);
      return 0;
    }
    return await sttClipboardMain([recording, ...parsed.args.sttArgs]);
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
    backend: (process.env.STT_PTT_BACKEND ?? "stdin-repeat") as
      | "stdin-repeat"
      | "xinput",
    triggerKey: "t",
    releaseGap: 0.75,
    outputDir: process.env.STT_OUTPUT_DIR ?? "output/recordings",
    recordOnly: false,
    sttArgs: [],
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index] ?? "";
    if (arg === "-h" || arg === "--help") {
      return { kind: "help" };
    }
    if (arg === "--record-only") {
      args.recordOnly = true;
      continue;
    }
    if (arg === "--") {
      args.sttArgs = argv.slice(index + 1);
      break;
    }
    if (
      ["--backend", "--trigger-key", "--release-gap", "--output-dir"].includes(
        arg,
      )
    ) {
      const value = argv[index + 1];
      if (!value) {
        return { kind: "error", message: `${arg} requires a value` };
      }
      index += 1;
      const error = assignOption(args, arg, value);
      if (error) {
        return { kind: "error", message: error };
      }
      continue;
    }
    if (
      arg === "--keycode" ||
      arg === "--modifier-keycodes" ||
      arg === "--listen-timeout"
    ) {
      index += 1;
      continue;
    }
    if (arg === "--no-modifier" || arg === "--require-modifier") {
      continue;
    }
    if (arg.startsWith("-")) {
      return { kind: "error", message: `unknown option: ${arg}` };
    }
    return { kind: "error", message: `unexpected argument before --: ${arg}` };
  }

  if (args.triggerKey.length !== 1) {
    return { kind: "error", message: "trigger key must be a single character" };
  }
  return { kind: "ok", args };
}

function assignOption(
  args: Args,
  name: string,
  value: string,
): string | undefined {
  if (name === "--backend") {
    if (value !== "stdin-repeat" && value !== "xinput") {
      return "--backend must be one of: stdin-repeat, xinput";
    }
    args.backend = value;
  } else if (name === "--trigger-key") {
    args.triggerKey = value;
  } else if (name === "--release-gap") {
    const releaseGap = Number(value);
    if (!Number.isFinite(releaseGap) || releaseGap <= 0) {
      return `invalid --release-gap: ${value}`;
    }
    args.releaseGap = releaseGap;
  } else if (name === "--output-dir") {
    args.outputDir = value;
  }
  return undefined;
}

async function recordOnceWithStdinRepeat(args: Args): Promise<string> {
  if (!process.stdin.isTTY) {
    throw new Error("stdin-repeat backend requires a TTY");
  }
  const restoreRaw = enableRawMode();
  const state: RecordingState = {};
  let lastTriggerAt = 0;
  try {
    return await new Promise((resolvePromise, reject) => {
      const interval = setInterval(() => {
        if (
          state.process &&
          performance.now() - lastTriggerAt >= args.releaseGap * 1000
        ) {
          clearInterval(interval);
          restoreRaw();
          void stopRecording(state).then(resolvePromise, reject);
        }
      }, 50);
      process.stdin.on("data", (data: Buffer) => {
        if (!data.includes(Buffer.from(args.triggerKey))) {
          return;
        }
        lastTriggerAt = performance.now();
        if (!state.process) {
          process.stderr.write("recording started\n");
          void startRecording(args, state).catch(reject);
        }
      });
    });
  } finally {
    restoreRaw();
  }
}

async function startRecording(
  args: Args,
  state: RecordingState,
): Promise<void> {
  await mkdir(args.outputDir, { recursive: true });
  const outputFile = join(args.outputDir, recordingFileName());
  const config = defaultRecordingConfig();
  state.process = spawn("arecord", [
    "-D",
    config.device,
    "-f",
    config.format,
    "-r",
    config.rate,
    "-c",
    config.channels,
    outputFile,
  ]);
  state.outputFile = outputFile;
}

function stopRecording(state: RecordingState): Promise<string> {
  return new Promise((resolvePromise, reject) => {
    if (!state.process || !state.outputFile) {
      reject(new Error("recording is not running"));
      return;
    }
    const processToStop = state.process;
    const outputFile = state.outputFile;
    processToStop.once("exit", () => {
      state.process = undefined;
      state.outputFile = undefined;
      resolvePromise(outputFile);
    });
    processToStop.kill("SIGINT");
  });
}

function enableRawMode(): () => void {
  const wasRaw = process.stdin.isRaw;
  process.stdin.setRawMode(true);
  process.stdin.resume();
  return () => process.stdin.setRawMode(wasRaw);
}

function usage(): string {
  return "Usage: npm run push-to-talk -- [--record-only] [--trigger-key t] [-- --model tiny]";
}

if (isDirectRun(import.meta.url)) {
  process.exitCode = await main();
}
