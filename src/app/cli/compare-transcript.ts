import { readFile } from "node:fs/promises";

import { compareTranscripts } from "@/features/transcript-comparison";

import { isDirectRun } from "./shared/direct-run";

interface ParsedArgs {
  expectedFile: string;
  actualFile: string;
  exact: boolean;
}

interface CliIo {
  stderr: Pick<NodeJS.WriteStream, "write">;
  stdout: Pick<NodeJS.WriteStream, "write">;
}

export async function main(
  argv: string[] = process.argv.slice(2),
  io: CliIo = {
    stderr: process.stderr,
    stdout: process.stdout,
  },
): Promise<number> {
  const parsed = parseArgs(argv);

  if (parsed.kind === "help") {
    io.stdout.write(`${usage()}\n`);
    return 0;
  }

  if (parsed.kind === "error") {
    io.stderr.write(`${parsed.message}\n${usage()}\n`);
    return 2;
  }

  try {
    const expected = await readTranscriptFile(parsed.args.expectedFile);
    const actual = await readTranscriptFile(parsed.args.actualFile);
    const result = compareTranscripts({
      expected,
      actual,
      exact: parsed.args.exact,
    });

    if (result.ok) {
      io.stdout.write("transcript match\n");
      return 0;
    }

    io.stderr.write("transcript mismatch\n");
    io.stderr.write(`expected: ${result.expected}\n`);
    io.stderr.write(`actual:   ${result.actual}\n`);
    return 1;
  } catch (error) {
    io.stderr.write(`${formatError(error)}\n`);
    return 2;
  }
}

type ParseResult =
  | { kind: "ok"; args: ParsedArgs }
  | { kind: "help" }
  | { kind: "error"; message: string };

function parseArgs(argv: string[]): ParseResult {
  const files: string[] = [];
  let exact = false;

  for (const arg of argv) {
    if (arg === "--help" || arg === "-h") {
      return { kind: "help" };
    }

    if (arg === "--exact") {
      exact = true;
      continue;
    }

    if (arg.startsWith("-")) {
      return { kind: "error", message: `unknown option: ${arg}` };
    }

    files.push(arg);
  }

  if (files.length !== 2) {
    return {
      kind: "error",
      message: "expected exactly two transcript files",
    };
  }

  return {
    kind: "ok",
    args: {
      expectedFile: files[0] ?? "",
      actualFile: files[1] ?? "",
      exact,
    },
  };
}

async function readTranscriptFile(path: string): Promise<string> {
  return (await readFile(path, "utf8")).trim();
}

function usage(): string {
  return [
    "Usage: npm run compare-transcript -- [--exact] <expected_file> <actual_file>",
    "",
    "Compare expected and actual transcripts for fixture checks.",
  ].join("\n");
}

function formatError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return String(error);
}

if (isDirectRun(import.meta.url)) {
  process.exitCode = await main();
}
