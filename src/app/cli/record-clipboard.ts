import { parsePositiveInteger, recordAudio } from "@/features/audio-recording";

import { main as sttClipboardMain } from "./stt-clipboard";
import { isDirectRun } from "./shared/direct-run";

interface ParsedArgs {
  duration: number;
  recordOnly: boolean;
  sttArgs: string[];
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
    process.stderr.write(`step=record duration=${parsed.args.duration}s\n`);
    const recording = await recordAudio(
      parsed.args.duration,
      process.env.STT_OUTPUT_DIR ?? "output/recordings",
    );
    process.stderr.write(`recording=${recording}\n`);
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
  | { kind: "ok"; args: ParsedArgs }
  | { kind: "help" }
  | { kind: "error"; message: string };

function parseArgs(argv: string[]): ParseResult {
  let duration = parsePositiveInteger(
    process.env.STT_RECORD_DURATION ?? "5",
    "duration_seconds",
  );
  let durationSet = false;
  let recordOnly = false;
  const sttArgs: string[] = [];

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index] ?? "";
    if (arg === "-h" || arg === "--help") {
      return { kind: "help" };
    }
    if (arg === "--record-only") {
      recordOnly = true;
      continue;
    }
    if (arg === "--duration") {
      const value = argv[index + 1];
      if (!value) {
        return {
          kind: "error",
          message: "--duration requires a positive integer",
        };
      }
      index += 1;
      try {
        duration = parsePositiveInteger(value, "duration_seconds");
      } catch (error) {
        return { kind: "error", message: formatError(error) };
      }
      durationSet = true;
      continue;
    }
    if (arg.startsWith("--duration=")) {
      try {
        duration = parsePositiveInteger(
          arg.slice("--duration=".length),
          "duration_seconds",
        );
      } catch (error) {
        return { kind: "error", message: formatError(error) };
      }
      durationSet = true;
      continue;
    }
    if (arg === "--") {
      sttArgs.push(...argv.slice(index + 1));
      break;
    }
    if (arg.startsWith("-")) {
      sttArgs.push(arg, ...argv.slice(index + 1));
      break;
    }
    if (durationSet) {
      return {
        kind: "error",
        message: `unexpected argument before --: ${arg}`,
      };
    }
    try {
      duration = parsePositiveInteger(arg, "duration_seconds");
    } catch (error) {
      return { kind: "error", message: formatError(error) };
    }
    durationSet = true;
  }

  return { kind: "ok", args: { duration, recordOnly, sttArgs } };
}

function usage(): string {
  return "Usage: npm run record-clipboard -- [--duration SECONDS] [--record-only] [-- transcribe options...]";
}

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

if (isDirectRun(import.meta.url)) {
  process.exitCode = await main();
}
