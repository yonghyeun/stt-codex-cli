import { analyzeCodeSwitchSuite } from "@/features/code-switch-analysis";
import { asRecord, readJsonFile, writeJsonFile } from "@/shared/json";

interface ParsedArgs {
  suiteResult: string;
  output?: string;
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

  const suite = asRecord(
    await readJsonFile(parsed.args.suiteResult),
    "suite result must contain a JSON object",
  );
  const summary = analyzeCodeSwitchSuite(suite);

  for (const row of summary.row_results) {
    process.stdout.write(
      `row=${String(row.row_idx).padStart(5, "0")} preserved=${row.preserved_count}/${row.expected_count} missing=${JSON.stringify(row.missing_tokens)}\n`,
    );
  }
  process.stdout.write(
    `latin_token_preservation=${summary.preserved_latin_tokens}/${summary.expected_latin_tokens} (${(summary.preservation_rate * 100).toFixed(2)}%)\n`,
  );

  if (parsed.args.output) {
    await writeJsonFile(parsed.args.output, summary);
    process.stdout.write(`output=${parsed.args.output}\n`);
  }

  return 0;
}

type ParseResult =
  | { kind: "ok"; args: ParsedArgs }
  | { kind: "help" }
  | { kind: "error"; message: string };

function parseArgs(argv: string[]): ParseResult {
  let output: string | undefined;
  const positional: string[] = [];

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index] ?? "";
    if (arg === "-h" || arg === "--help") {
      return { kind: "help" };
    }
    if (arg === "--output") {
      const value = argv[index + 1];
      if (!value) {
        return { kind: "error", message: "--output requires a value" };
      }
      output = value;
      index += 1;
      continue;
    }
    if (arg.startsWith("--output=")) {
      output = arg.slice("--output=".length);
      continue;
    }
    if (arg.startsWith("-")) {
      return { kind: "error", message: `unknown option: ${arg}` };
    }
    positional.push(arg);
  }

  if (positional.length !== 1) {
    return { kind: "error", message: "suite_result is required" };
  }

  return {
    kind: "ok",
    args: {
      suiteResult: positional[0] ?? "",
      output,
    },
  };
}

function usage(): string {
  return "Usage: npm run analyze-code-switch-suite -- [--output PATH] suite_result.json";
}

process.exitCode = await main();
