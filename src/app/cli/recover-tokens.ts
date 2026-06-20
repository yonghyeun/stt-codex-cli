import { readFile } from "node:fs/promises";
import { isAbsolute, relative, resolve } from "node:path";

import { parseMemoryEntries, recoverText } from "@/features/token-recovery";
import { readJsonFile } from "@/shared/json";
import { repoRoot } from "@/shared/repo";

import { isDirectRun } from "./shared/direct-run";

const DEFAULT_MEMORY = "memory/manual-aliases.json";
const FALLBACK_MEMORY = "memory/manual-aliases.example.json";
const DEFAULT_MIN_CONFIDENCE = 0.8;

interface ParsedArgs {
  text: string[];
  memory?: string;
  minConfidence: number;
  json: boolean;
  fixture?: string;
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
    if (parsed.args.fixture) {
      return await runFixture(parsed.args);
    }

    const memoryPath = await resolveMemoryPath(parsed.args);
    const entries = parseMemoryEntries(await readJsonFile(memoryPath));
    const original = await inputText(parsed.args.text);
    const result = recoverText(original, entries, parsed.args.minConfidence);

    if (parsed.args.json) {
      process.stdout.write(
        `${JSON.stringify({ ...result, memory: displayPath(memoryPath) }, null, 2)}\n`,
      );
    } else {
      process.stdout.write(`${result.recovered}\n`);
    }

    return 0;
  } catch (error) {
    process.stderr.write(`error: ${formatError(error)}\n`);
    return 2;
  }
}

type ParseResult =
  | { kind: "ok"; args: ParsedArgs }
  | { kind: "help" }
  | { kind: "error"; message: string };

function parseArgs(argv: string[]): ParseResult {
  const args: ParsedArgs = {
    text: [],
    minConfidence: DEFAULT_MIN_CONFIDENCE,
    json: false,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index] ?? "";
    if (arg === "-h" || arg === "--help") {
      return { kind: "help" };
    }
    if (arg === "--json") {
      args.json = true;
      continue;
    }
    if (
      arg === "--memory" ||
      arg === "--fixture" ||
      arg === "--min-confidence"
    ) {
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
    if (
      arg.startsWith("--memory=") ||
      arg.startsWith("--fixture=") ||
      arg.startsWith("--min-confidence=")
    ) {
      const [name, value = ""] = arg.split("=", 2);
      const error = assignOption(args, name, value);
      if (error) {
        return { kind: "error", message: error };
      }
      continue;
    }
    if (arg.startsWith("-")) {
      return { kind: "error", message: `unknown option: ${arg}` };
    }
    args.text.push(arg);
  }

  return { kind: "ok", args };
}

function assignOption(
  args: ParsedArgs,
  name: string,
  value: string,
): string | undefined {
  if (name === "--memory") {
    args.memory = value;
    return undefined;
  }
  if (name === "--fixture") {
    args.fixture = value;
    return undefined;
  }
  const minConfidence = Number(value);
  if (!Number.isFinite(minConfidence)) {
    return `invalid --min-confidence: ${value}`;
  }
  args.minConfidence = minConfidence;
  return undefined;
}

async function runFixture(args: ParsedArgs): Promise<number> {
  if (!args.fixture) {
    throw new Error("--fixture is required");
  }
  const fixturePath = repoRelative(args.fixture);
  const fixture = await readJsonFile(fixturePath);
  if (
    typeof fixture !== "object" ||
    fixture === null ||
    Array.isArray(fixture)
  ) {
    throw new Error("fixture file must contain a JSON object");
  }
  const fixtureRecord = fixture as Record<string, unknown>;
  if (!Array.isArray(fixtureRecord.cases)) {
    throw new Error("fixture file field 'cases' must be a list");
  }
  const memoryPath = await resolveMemoryPath(args, fixtureRecord.memory);
  const entries = parseMemoryEntries(await readJsonFile(memoryPath));
  const results = fixtureRecord.cases.map((rawCase, index) => {
    if (
      typeof rawCase !== "object" ||
      rawCase === null ||
      Array.isArray(rawCase)
    ) {
      throw new Error(`fixture case ${index} must be an object`);
    }
    const testCase = rawCase as Record<string, unknown>;
    const input = requireString(testCase.input, "input", index);
    const expected = requireString(testCase.expected, "expected", index);
    const result = recoverText(input, entries, args.minConfidence);
    const passed = result.recovered === expected;
    process.stdout.write(
      `${passed ? "PASS" : "FAIL"} ${String(testCase.label ?? `case-${index}`)}: ${input} -> ${result.recovered}\n`,
    );
    return {
      label: testCase.label ?? `case-${index}`,
      input,
      expected,
      actual: result.recovered,
      passed,
      applied: result.applied,
    };
  });
  const failed = results.filter((result) => !result.passed);
  const summary = {
    fixture: displayPath(fixturePath),
    memory: displayPath(memoryPath),
    total: results.length,
    passed: results.length - failed.length,
    failed: failed.length,
    results,
  };

  if (args.json) {
    process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
  } else {
    process.stdout.write(
      `summary: passed=${summary.passed}/${summary.total} memory=${summary.memory}\n`,
    );
  }

  return failed.length === 0 ? 0 : 1;
}

async function inputText(parts: string[]): Promise<string> {
  if (parts.length > 0) {
    return parts.join(" ").trim();
  }
  if (process.stdin.isTTY) {
    throw new Error("text is required when stdin is empty");
  }
  return await readStream(process.stdin);
}

function readStream(stream: NodeJS.ReadStream): Promise<string> {
  return new Promise((resolve) => {
    let value = "";
    stream.setEncoding("utf8");
    stream.on("data", (chunk: string) => {
      value += chunk;
    });
    stream.on("end", () => {
      resolve(value.trim());
    });
  });
}

async function resolveMemoryPath(
  args: ParsedArgs,
  fixtureMemory?: unknown,
): Promise<string> {
  if (args.memory) {
    return repoRelative(args.memory);
  }
  if (typeof fixtureMemory === "string" && fixtureMemory) {
    return repoRelative(fixtureMemory);
  }
  if (process.env.STT_TOKEN_MEMORY) {
    return repoRelative(process.env.STT_TOKEN_MEMORY);
  }

  const defaultPath = repoRelative(DEFAULT_MEMORY);
  try {
    await readFile(defaultPath, "utf8");
    return defaultPath;
  } catch {
    return repoRelative(FALLBACK_MEMORY);
  }
}

function repoRelative(path: string): string {
  return isAbsolute(path) ? path : resolve(repoRoot, path);
}

function displayPath(path: string): string {
  const relativePath = relative(repoRoot, path);
  return relativePath.startsWith("..") ? path : relativePath;
}

function requireString(value: unknown, field: string, index: number): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(
      `fixture case ${index} field '${field}' must be a non-empty string`,
    );
  }
  return value.trim();
}

function usage(): string {
  return [
    "Usage: npm run recover-tokens -- [--memory PATH] [--min-confidence N] [--json] [text ...]",
    "       npm run recover-tokens -- --fixture fixtures/token-recovery-v1.json",
  ].join("\n");
}

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

if (isDirectRun(import.meta.url)) {
  process.exitCode = await main();
}
