import { mkdir, writeFile } from "node:fs/promises";
import { dirname } from "node:path";

import { parseClipboardBackend } from "@/features/clipboard";
import { transcribeAudio } from "@/features/stt-engine";
import { parseMemoryEntries, recoverText } from "@/features/token-recovery";
import { readJsonFile } from "@/shared/json";
import { repoPath } from "@/shared/repo";
import { hasMeaningfulText } from "@/shared/text";

import { main as copyTextMain } from "./copy-text";
import { isDirectRun } from "./shared/direct-run";
import { parseArgs as parseTranscribeArgs } from "./transcribe";

interface ParsedArgs {
  recovery: boolean;
  memory?: string;
  minConfidence: number;
  clipboardBackend: "auto" | "xclip" | "wl-copy";
  copyVerify: boolean;
  outputTranscript?: string;
  outputRecovered?: string;
  audioFile: string;
  transcribeArgs: string[];
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
    process.stderr.write(`step=transcribe audio=${parsed.args.audioFile}\n`);
    const transcribeParsed = parseTranscribeArgs([
      parsed.args.audioFile,
      ...parsed.args.transcribeArgs,
    ]);
    if (transcribeParsed.kind !== "ok") {
      throw new Error(
        transcribeParsed.kind === "error"
          ? transcribeParsed.message
          : "invalid transcribe args",
      );
    }
    const transcript = await transcribeAudio(
      transcribeParsed.audioFile,
      transcribeParsed.options,
    );
    validateMeaningfulText("transcript", transcript);
    if (parsed.args.outputTranscript) {
      await writeTextFile(parsed.args.outputTranscript, transcript);
    }

    let finalText = transcript;
    if (parsed.args.recovery) {
      process.stderr.write("step=recover_tokens enabled=true\n");
      const memoryPath =
        parsed.args.memory ?? repoPath("memory/manual-aliases.example.json");
      const entries = parseMemoryEntries(await readJsonFile(memoryPath));
      finalText = recoverText(
        transcript,
        entries,
        parsed.args.minConfidence,
      ).recovered;
    } else {
      process.stderr.write("step=recover_tokens enabled=false\n");
    }
    validateMeaningfulText("final text", finalText);
    if (parsed.args.outputRecovered) {
      await writeTextFile(parsed.args.outputRecovered, finalText);
    }

    process.stderr.write(
      `step=copy_clipboard backend=${parsed.args.clipboardBackend} verify=${parsed.args.copyVerify ? "true" : "false"}\n`,
    );
    return await copyTextMain([
      "--backend",
      parsed.args.clipboardBackend,
      ...(parsed.args.copyVerify ? [] : ["--no-verify"]),
      finalText,
    ]);
  } catch (error) {
    process.stderr.write(
      `error: ${error instanceof Error ? error.message : String(error)}\n`,
    );
    return 1;
  }
}

type ParseResult =
  | { kind: "ok"; args: ParsedArgs }
  | { kind: "help" }
  | { kind: "error"; message: string };

export function parseArgs(argv: string[]): ParseResult {
  const args: Partial<ParsedArgs> = {
    recovery: true,
    minConfidence: Number(process.env.STT_TOKEN_MIN_CONFIDENCE ?? "0.8"),
    clipboardBackend: parseClipboardBackend(
      process.env.STT_CLIPBOARD_BACKEND ?? "auto",
    ),
    copyVerify: true,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index] ?? "";
    if (arg === "-h" || arg === "--help") {
      return { kind: "help" };
    }
    if (arg === "--no-recovery") {
      args.recovery = false;
      continue;
    }
    if (arg === "--no-copy-verify") {
      args.copyVerify = false;
      continue;
    }
    if (
      [
        "--memory",
        "--min-confidence",
        "--clipboard-backend",
        "--output-transcript",
        "--output-recovered",
      ].includes(arg)
    ) {
      const value = argv[index + 1];
      if (!value) {
        return { kind: "error", message: `${arg} requires a value` };
      }
      index += 1;
      const error = assignWrapperOption(args, arg, value);
      if (error) {
        return { kind: "error", message: error };
      }
      continue;
    }
    if (arg === "--") {
      const audioFile = argv[index + 1];
      if (!audioFile) {
        return { kind: "error", message: "audio_file is required after --" };
      }
      args.audioFile = audioFile;
      args.transcribeArgs = argv.slice(index + 2);
      return finalize(args);
    }
    if (arg.startsWith("-")) {
      return {
        kind: "error",
        message: `unknown wrapper option before audio_file: ${arg}`,
      };
    }
    args.audioFile = arg;
    args.transcribeArgs = argv.slice(index + 1);
    return finalize(args);
  }

  return { kind: "error", message: "audio_file is required" };
}

function assignWrapperOption(
  args: Partial<ParsedArgs>,
  name: string,
  value: string,
): string | undefined {
  if (name === "--memory") {
    args.memory = value;
  } else if (name === "--min-confidence") {
    const minConfidence = Number(value);
    if (!Number.isFinite(minConfidence)) {
      return `invalid --min-confidence: ${value}`;
    }
    args.minConfidence = minConfidence;
  } else if (name === "--clipboard-backend") {
    try {
      args.clipboardBackend = parseClipboardBackend(value);
    } catch (error) {
      return error instanceof Error ? error.message : String(error);
    }
  } else if (name === "--output-transcript") {
    args.outputTranscript = value;
  } else if (name === "--output-recovered") {
    args.outputRecovered = value;
  }
  return undefined;
}

function finalize(args: Partial<ParsedArgs>): ParseResult {
  return {
    kind: "ok",
    args: {
      recovery: args.recovery ?? true,
      memory: args.memory,
      minConfidence: args.minConfidence ?? 0.8,
      clipboardBackend: args.clipboardBackend ?? "auto",
      copyVerify: args.copyVerify ?? true,
      outputTranscript: args.outputTranscript,
      outputRecovered: args.outputRecovered,
      audioFile: args.audioFile ?? "",
      transcribeArgs: args.transcribeArgs ?? [],
    },
  };
}

function validateMeaningfulText(label: string, text: string): void {
  if (text.trim() === "") {
    throw new Error(`${label} is empty`);
  }
  if (!hasMeaningfulText(text)) {
    throw new Error(`${label} has no meaningful text: ${text}`);
  }
}

async function writeTextFile(path: string, text: string): Promise<void> {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${text}\n`, "utf8");
}

function usage(): string {
  return "Usage: npm run stt-clipboard -- [options] audio_file [transcribe options...]";
}

if (isDirectRun(import.meta.url)) {
  process.exitCode = await main();
}
