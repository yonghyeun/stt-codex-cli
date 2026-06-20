import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

import { asRecord, readJsonFile, writeJsonFile } from "@/shared/json";

interface FixtureFetchConfig {
  dataset: string;
  config: string;
  split: string;
  sourcePage: string;
  license: string;
  defaultPrefix: string;
  expectedField: string;
  displayField?: string;
  metadataFields: string[];
}

interface ParsedArgs {
  rowIdx: number;
  manifest?: string;
  outputDir?: string;
}

export async function fetchFixtureCli(
  config: FixtureFetchConfig,
): Promise<number> {
  const parsed = parseArgs(process.argv.slice(2));
  if (parsed.kind === "help") {
    process.stdout.write(`${usage(config.defaultPrefix)}\n`);
    return 0;
  }
  if (parsed.kind === "error") {
    process.stderr.write(
      `error: ${parsed.message}\n${usage(config.defaultPrefix)}\n`,
    );
    return 2;
  }

  try {
    if (parsed.args.manifest) {
      const manifest = asRecord(
        await readJsonFile(parsed.args.manifest),
        "manifest must contain a JSON object",
      );
      if (!Array.isArray(manifest.fixtures)) {
        throw new Error("manifest field 'fixtures' must be a list");
      }
      const manifestId = requireString(manifest.id, "manifest id");
      const prefix =
        typeof manifest.fixture_dir_prefix === "string"
          ? manifest.fixture_dir_prefix
          : config.defaultPrefix;
      const root =
        parsed.args.outputDir ?? join("fixtures/generated", manifestId);
      for (const rawFixture of manifest.fixtures) {
        const fixture = asRecord(rawFixture, "fixture must be an object");
        const rowIdx = requireNumber(fixture.row_idx, "row_idx");
        const outputDir = join(
          root,
          `${prefix}-${String(rowIdx).padStart(5, "0")}`,
        );
        const result = await fetchFixture(
          config,
          rowIdx,
          outputDir,
          fixture.expected,
        );
        process.stdout.write(
          `row_idx=${rowIdx} audio_file=${result.audio_file} expected=${result.expected}\n`,
        );
      }
      return 0;
    }

    const outputDir =
      parsed.args.outputDir ??
      join(
        "fixtures/generated",
        `${config.defaultPrefix}-${String(parsed.args.rowIdx).padStart(5, "0")}`,
      );
    const result = await fetchFixture(config, parsed.args.rowIdx, outputDir);
    process.stdout.write(`audio_file=${result.audio_file}\n`);
    process.stdout.write(`expected_file=${result.expected_file}\n`);
    process.stdout.write(`metadata_file=${result.metadata_file}\n`);
    process.stdout.write(`expected=${result.expected}\n`);
    return 0;
  } catch (error) {
    process.stderr.write(
      `error: ${error instanceof Error ? error.message : String(error)}\n`,
    );
    return 1;
  }
}

async function fetchFixture(
  config: FixtureFetchConfig,
  rowIdx: number,
  outputDir: string,
  expectedText?: unknown,
): Promise<Record<string, string>> {
  if (rowIdx < 0) {
    throw new Error("--row-idx must be >= 0");
  }
  const payload = asRecord(
    await fetchJson(rowsApiUrl(config, rowIdx)),
    "rows API response must be an object",
  );
  if (!Array.isArray(payload.rows) || payload.rows.length !== 1) {
    throw new Error(
      `expected one row, got ${Array.isArray(payload.rows) ? payload.rows.length : 0}`,
    );
  }
  const rowPayload = asRecord(payload.rows[0], "row payload must be an object");
  const row = asRecord(
    rowPayload.row,
    "row payload field 'row' must be an object",
  );
  const sourceExpected = requireString(
    row[config.expectedField],
    config.expectedField,
  ).trim();
  if (
    typeof expectedText === "string" &&
    expectedText.trim() !== sourceExpected
  ) {
    throw new Error(
      `manifest expected text does not match row ${rowIdx}: ${JSON.stringify(expectedText)} != ${JSON.stringify(sourceExpected)}`,
    );
  }

  await mkdir(outputDir, { recursive: true });
  const wavPath = join(outputDir, "audio.wav");
  const expectedPath = join(outputDir, "expected.txt");
  const metadataPath = join(outputDir, "metadata.local.json");
  await download(audioUrl(row), wavPath);
  await writeFile(expectedPath, `${sourceExpected}\n`, "utf8");

  const metadata: Record<string, unknown> = {
    dataset: config.dataset,
    source_page: config.sourcePage,
    license: config.license,
    config: config.config,
    split: config.split,
    row_idx: rowPayload.row_idx,
    retrieved_at: new Date().toISOString(),
    audio_file: wavPath,
    expected_file: expectedPath,
  };
  for (const field of config.metadataFields) {
    metadata[field] = row[field];
  }
  if (config.displayField) {
    const displayPath = join(outputDir, "expected.display.txt");
    await writeFile(
      displayPath,
      `${String(row[config.displayField]).trim()}\n`,
      "utf8",
    );
    metadata.display_file = displayPath;
  }
  await writeJsonFile(metadataPath, metadata);

  return {
    audio_file: wavPath,
    expected_file: expectedPath,
    metadata_file: metadataPath,
    expected: sourceExpected,
  };
}

function rowsApiUrl(config: FixtureFetchConfig, rowIdx: number): string {
  const query = new URLSearchParams({
    dataset: config.dataset,
    config: config.config,
    split: config.split,
    offset: String(rowIdx),
    length: "1",
  });
  return `https://datasets-server.huggingface.co/rows?${query}`;
}

async function fetchJson(url: string): Promise<unknown> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} fetching ${url}`);
  }
  return await response.json();
}

async function download(url: string, path: string): Promise<void> {
  await mkdir(dirname(path), { recursive: true });
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status} downloading ${url}`);
  }
  await writeFile(path, Buffer.from(await response.arrayBuffer()));
}

function audioUrl(row: Record<string, unknown>): string {
  const audio = row.audio;
  if (Array.isArray(audio) && audio.length > 0) {
    return requireString(
      asRecord(audio[0], "audio item must be an object").src,
      "audio src",
    );
  }
  if (typeof audio === "object" && audio !== null && !Array.isArray(audio)) {
    return requireString((audio as Record<string, unknown>).src, "audio src");
  }
  throw new Error("row does not contain a downloadable audio URL");
}

type ParseResult =
  | { kind: "ok"; args: ParsedArgs }
  | { kind: "help" }
  | { kind: "error"; message: string };

function parseArgs(argv: string[]): ParseResult {
  const args: ParsedArgs = { rowIdx: 0 };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index] ?? "";
    if (arg === "-h" || arg === "--help") {
      return { kind: "help" };
    }
    if (arg === "--row-idx" || arg === "--manifest" || arg === "--output-dir") {
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
      arg.startsWith("--row-idx=") ||
      arg.startsWith("--manifest=") ||
      arg.startsWith("--output-dir=")
    ) {
      const [name, value = ""] = arg.split("=", 2);
      const error = assignOption(args, name, value);
      if (error) {
        return { kind: "error", message: error };
      }
      continue;
    }
    return { kind: "error", message: `unknown option: ${arg}` };
  }
  return { kind: "ok", args };
}

function assignOption(
  args: ParsedArgs,
  name: string,
  value: string,
): string | undefined {
  if (name === "--manifest") {
    args.manifest = value;
    return undefined;
  }
  if (name === "--output-dir") {
    args.outputDir = value;
    return undefined;
  }
  const rowIdx = Number(value);
  if (!Number.isInteger(rowIdx)) {
    return `invalid --row-idx: ${value}`;
  }
  args.rowIdx = rowIdx;
  return undefined;
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

function usage(prefix: string): string {
  return [
    "Usage: npm run fetch-kss-fixture -- [--row-idx N] [--manifest PATH] [--output-dir PATH]",
    `Default output without manifest: fixtures/generated/${prefix}-00000`,
  ].join("\n");
}
