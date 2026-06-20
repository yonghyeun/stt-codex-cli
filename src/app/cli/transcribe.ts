import {
  DEFAULT_TRANSCRIBE_OPTIONS,
  transcribeAudio,
} from "@/features/stt-adapter";
import type { TranscribeOptions } from "@/features/stt-adapter";

import { isDirectRun } from "./shared/direct-run";

type TranscribeCliOptions = TranscribeOptions & {
  modelDir?: string;
  output?: string;
};

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
    const transcript = await transcribeAudio(parsed.audioFile, parsed.options);
    process.stdout.write(`${transcript}\n`);
    return 0;
  } catch (error) {
    process.stderr.write(
      `error: ${error instanceof Error ? error.message : String(error)}\n`,
    );
    return 1;
  }
}

type ParseResult =
  | {
      kind: "ok";
      audioFile: string;
      options: TranscribeCliOptions;
    }
  | { kind: "help" }
  | { kind: "error"; message: string };

export function parseArgs(argv: string[]): ParseResult {
  const positional: string[] = [];
  const options = {
    ...DEFAULT_TRANSCRIBE_OPTIONS,
    model: process.env.STT_MODEL ?? DEFAULT_TRANSCRIBE_OPTIONS.model,
    language: process.env.STT_LANGUAGE ?? DEFAULT_TRANSCRIBE_OPTIONS.language,
    device: (process.env.STT_DEVICE ?? DEFAULT_TRANSCRIBE_OPTIONS.device) as
      | "auto"
      | "cpu"
      | "cuda",
    computeType:
      process.env.STT_COMPUTE_TYPE ?? DEFAULT_TRANSCRIBE_OPTIONS.computeType,
    beamSize: Number(
      process.env.STT_BEAM_SIZE ?? DEFAULT_TRANSCRIBE_OPTIONS.beamSize,
    ),
    initialPrompt: process.env.STT_INITIAL_PROMPT,
    modelDir: process.env.STT_MODEL_DIR,
    vadFilter: envFlag("STT_VAD_FILTER", true),
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index] ?? "";
    if (arg === "-h" || arg === "--help") {
      return { kind: "help" };
    }
    if (arg === "--vad-filter") {
      options.vadFilter = true;
      continue;
    }
    if (arg === "--no-vad-filter") {
      options.vadFilter = false;
      continue;
    }
    if (
      [
        "--model",
        "--language",
        "--device",
        "--compute-type",
        "--beam-size",
        "--initial-prompt",
        "--model-dir",
        "--output",
      ].includes(arg)
    ) {
      const value = argv[index + 1];
      if (value === undefined) {
        return { kind: "error", message: `${arg} requires a value` };
      }
      index += 1;
      const error = assignOption(options, arg, value);
      if (error) {
        return { kind: "error", message: error };
      }
      continue;
    }
    if (arg.startsWith("-")) {
      return { kind: "error", message: `unknown option: ${arg}` };
    }
    positional.push(arg);
  }

  if (positional.length !== 1) {
    return { kind: "error", message: "audio_file is required" };
  }

  return { kind: "ok", audioFile: positional[0] ?? "", options };
}

function assignOption(
  options: TranscribeCliOptions,
  name: string,
  value: string,
): string | undefined {
  if (name === "--model") {
    options.model = value;
  } else if (name === "--language") {
    options.language = value;
  } else if (name === "--device") {
    if (value !== "auto" && value !== "cpu" && value !== "cuda") {
      return "--device must be one of: auto, cpu, cuda";
    }
    options.device = value;
  } else if (name === "--compute-type") {
    options.computeType = value;
  } else if (name === "--beam-size") {
    const beamSize = Number(value);
    if (!Number.isInteger(beamSize) || beamSize <= 0) {
      return `invalid --beam-size: ${value}`;
    }
    options.beamSize = beamSize;
  } else if (name === "--initial-prompt") {
    options.initialPrompt = value;
  } else if (name === "--model-dir") {
    options.modelDir = value;
  } else if (name === "--output") {
    options.output = value;
  }
  return undefined;
}

function envFlag(name: string, defaultValue: boolean): boolean {
  const value = process.env[name];
  if (value === undefined) {
    return defaultValue;
  }
  return ["1", "true", "yes", "on"].includes(value.toLowerCase());
}

function usage(): string {
  return "Usage: npm run transcribe -- audio_file [--model MODEL] [--device auto|cpu|cuda] [--compute-type TYPE]";
}

if (isDirectRun(import.meta.url)) {
  process.exitCode = await main();
}
