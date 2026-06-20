import { existsSync } from "node:fs";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";

import { compareTranscripts } from "@/features/transcript-comparison";
import { transcribeAudio } from "@/features/stt-adapter";
import { asRecord, readJsonFile } from "@/shared/json";

import { isDirectRun } from "./shared/direct-run";
import { parseArgs as parseTranscribeArgs } from "./transcribe";

interface ParsedArgs {
  manifest: string;
  fixtureRoot?: string;
  output?: string;
  require: "exact" | "normalized" | "none";
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
    const manifest = asRecord(
      await readJsonFile(parsed.args.manifest),
      "manifest must contain a JSON object",
    );
    const suiteId = requireString(manifest.id, "manifest id");
    const fixtures = requireArray(manifest.fixtures, "fixtures");
    const prefix =
      typeof manifest.fixture_dir_prefix === "string"
        ? manifest.fixture_dir_prefix
        : "kss-row";
    const fixtureRoot =
      parsed.args.fixtureRoot ?? join("fixtures/generated", suiteId);
    const output =
      parsed.args.output ??
      join("output/suite", `${suiteId}-typescript-adapter.json`);
    const results = [];
    const startedAt = performance.now();

    for (const rawFixture of fixtures) {
      const fixture = asRecord(rawFixture, "fixture must be an object");
      const rowIdx = requireNumber(fixture.row_idx, "row_idx");
      const directory = join(
        fixtureRoot,
        `${prefix}-${String(rowIdx).padStart(5, "0")}`,
      );
      const audioFile = join(directory, "audio.wav");
      const expectedFile = join(directory, "expected.txt");
      if (!existsSync(audioFile) || !existsSync(expectedFile)) {
        throw new Error(`missing generated fixture for row ${rowIdx}`);
      }

      const expected = (await readFile(expectedFile, "utf8")).trim();
      const transcribeParsed = parseTranscribeArgs([
        audioFile,
        ...parsed.args.transcribeArgs,
      ]);
      if (transcribeParsed.kind !== "ok") {
        throw new Error(
          transcribeParsed.kind === "error"
            ? transcribeParsed.message
            : "invalid transcribe args",
        );
      }
      const rowStartedAt = performance.now();
      const actual = await transcribeAudio(
        transcribeParsed.audioFile,
        transcribeParsed.options,
      );
      const exact = compareTranscripts({ expected, actual, exact: true }).ok;
      const normalized = compareTranscripts({ expected, actual }).ok;
      const result = {
        row_idx: rowIdx,
        label: fixture.label,
        category: fixture.category,
        cs_level: fixture.cs_level,
        expected,
        actual,
        exact_match: exact,
        normalized_match: normalized,
        elapsed: round3((performance.now() - rowStartedAt) / 1000),
      };
      results.push(result);
      const status = rowStatus(result, parsed.args.require);
      process.stdout.write(
        `${status} row=${String(rowIdx).padStart(5, "0")} exact=${exact} normalized=${normalized} elapsed=${result.elapsed.toFixed(2)}s\n`,
      );
    }

    const summary = {
      suite_id: suiteId,
      manifest: parsed.args.manifest,
      required_match: parsed.args.require,
      elapsed: round3((performance.now() - startedAt) / 1000),
      total: results.length,
      exact_pass: results.filter((result) => result.exact_match).length,
      normalized_pass: results.filter((result) => result.normalized_match)
        .length,
      results,
    };
    await mkdir(join(output, ".."), { recursive: true });
    await writeFile(output, `${JSON.stringify(summary, null, 2)}\n`, "utf8");
    process.stdout.write(`output=${output}\n`);
    return results.some((result) => !rowOk(result, parsed.args.require))
      ? 1
      : 0;
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
  let manifest = "";
  let fixtureRoot: string | undefined;
  let output: string | undefined;
  let require: ParsedArgs["require"] = "normalized";
  const transcribeArgs: string[] = [];

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index] ?? "";
    if (arg === "-h" || arg === "--help") return { kind: "help" };
    if (arg === "--fixture-root" || arg === "--output" || arg === "--require") {
      const value = argv[index + 1];
      if (!value) return { kind: "error", message: `${arg} requires a value` };
      index += 1;
      if (arg === "--fixture-root") fixtureRoot = value;
      else if (arg === "--output") output = value;
      else {
        if (value !== "exact" && value !== "normalized" && value !== "none") {
          return {
            kind: "error",
            message: "--require must be exact, normalized, or none",
          };
        }
        require = value;
      }
      continue;
    }
    if (arg.startsWith("-")) {
      transcribeArgs.push(arg, ...argv.slice(index + 1));
      break;
    }
    if (!manifest) {
      manifest = arg;
      continue;
    }
    transcribeArgs.push(arg, ...argv.slice(index + 1));
    break;
  }

  if (!manifest) return { kind: "error", message: "manifest is required" };
  return {
    kind: "ok",
    args: { manifest, fixtureRoot, output, require, transcribeArgs },
  };
}

function rowOk(
  result: { exact_match: boolean; normalized_match: boolean },
  required: ParsedArgs["require"],
): boolean {
  if (required === "none") return true;
  return required === "exact" ? result.exact_match : result.normalized_match;
}

function rowStatus(
  result: { exact_match: boolean; normalized_match: boolean },
  required: ParsedArgs["require"],
): string {
  if (required === "none") return "MEASURE";
  return rowOk(result, required) ? "PASS" : "FAIL";
}

function requireString(value: unknown, field: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(`field '${field}' must be a non-empty string`);
  }
  return value;
}

function requireNumber(value: unknown, field: string): number {
  if (typeof value !== "number") {
    throw new Error(`field '${field}' must be a number`);
  }
  return value;
}

function requireArray(value: unknown, field: string): unknown[] {
  if (!Array.isArray(value)) {
    throw new Error(`field '${field}' must be a list`);
  }
  return value;
}

function round3(value: number): number {
  return Math.round(value * 1000) / 1000;
}

function usage(): string {
  return "Usage: npm run run-fixture-suite -- manifest.json [--model MODEL] [--device auto|cpu|cuda]";
}

if (isDirectRun(import.meta.url)) {
  process.exitCode = await main();
}
