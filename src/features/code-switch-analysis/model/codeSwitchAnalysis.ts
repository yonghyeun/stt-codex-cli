export interface SuiteRow {
  row_idx: number;
  label: string;
  category?: unknown;
  cs_level?: unknown;
  expected: string;
  actual: string;
}

export interface CodeSwitchRowAnalysis {
  row_idx: number;
  label: string;
  category?: unknown;
  cs_level?: unknown;
  expected_tokens: string[];
  actual_tokens: string[];
  preserved_tokens: string[];
  missing_tokens: string[];
  preserved_count: number;
  expected_count: number;
  preservation_rate: number;
}

export interface CodeSwitchSuiteAnalysis {
  suite_id: unknown;
  model: unknown;
  language: unknown;
  device: unknown;
  compute_type: unknown;
  initial_prompt: unknown;
  rows: number;
  expected_latin_tokens: number;
  preserved_latin_tokens: number;
  preservation_rate: number;
  row_results: CodeSwitchRowAnalysis[];
}

const TOKEN_PATTERN = /[A-Za-z][A-Za-z0-9]*/g;

export function asciiTokens(text: string): string[] {
  return Array.from(text.matchAll(TOKEN_PATTERN), (match) =>
    match[0].toLowerCase(),
  );
}

export function analyzeCodeSwitchRow(row: SuiteRow): CodeSwitchRowAnalysis {
  const expectedTokens = asciiTokens(row.expected);
  const actualTokens = asciiTokens(row.actual);
  const actualTokenSet = new Set(actualTokens);
  const preservedTokens = expectedTokens.filter((token) =>
    actualTokenSet.has(token),
  );
  const missingTokens = expectedTokens.filter(
    (token) => !actualTokenSet.has(token),
  );
  const expectedCount = expectedTokens.length;
  const preservedCount = preservedTokens.length;

  return {
    row_idx: row.row_idx,
    label: row.label,
    category: row.category,
    cs_level: row.cs_level,
    expected_tokens: expectedTokens,
    actual_tokens: actualTokens,
    preserved_tokens: preservedTokens,
    missing_tokens: missingTokens,
    preserved_count: preservedCount,
    expected_count: expectedCount,
    preservation_rate: round4(
      expectedCount === 0 ? 1 : preservedCount / expectedCount,
    ),
  };
}

export function analyzeCodeSwitchSuite(
  suite: Record<string, unknown>,
): CodeSwitchSuiteAnalysis {
  if (!Array.isArray(suite.results)) {
    throw new Error("suite result field 'results' must be a list");
  }

  const rows = suite.results.map((row) =>
    analyzeCodeSwitchRow(parseSuiteRow(row)),
  );
  const expectedTotal = rows.reduce((sum, row) => sum + row.expected_count, 0);
  const preservedTotal = rows.reduce(
    (sum, row) => sum + row.preserved_count,
    0,
  );

  return {
    suite_id: suite.suite_id,
    model: suite.model,
    language: suite.language,
    device: suite.device,
    compute_type: suite.compute_type,
    initial_prompt: suite.initial_prompt,
    rows: rows.length,
    expected_latin_tokens: expectedTotal,
    preserved_latin_tokens: preservedTotal,
    preservation_rate: round4(
      expectedTotal === 0 ? 1 : preservedTotal / expectedTotal,
    ),
    row_results: rows,
  };
}

function parseSuiteRow(value: unknown): SuiteRow {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error("suite result row must be an object");
  }
  const row = value as Record<string, unknown>;
  if (typeof row.row_idx !== "number") {
    throw new Error("suite result row field 'row_idx' must be a number");
  }
  if (typeof row.label !== "string") {
    throw new Error("suite result row field 'label' must be a string");
  }
  if (typeof row.expected !== "string" || typeof row.actual !== "string") {
    throw new Error(
      "suite result row fields 'expected' and 'actual' must be strings",
    );
  }

  return {
    row_idx: row.row_idx,
    label: row.label,
    category: row.category,
    cs_level: row.cs_level,
    expected: row.expected,
    actual: row.actual,
  };
}

function round4(value: number): number {
  return Math.round(value * 10000) / 10000;
}
