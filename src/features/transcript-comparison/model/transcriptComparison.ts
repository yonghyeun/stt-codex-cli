export type TranscriptComparisonMode = "exact" | "normalized";

export interface CompareTranscriptsInput {
  expected: string;
  actual: string;
  exact?: boolean;
}

export interface TranscriptComparisonResult {
  ok: boolean;
  mode: TranscriptComparisonMode;
  expected: string;
  actual: string;
  normalizedExpected?: string;
  normalizedActual?: string;
}

const ASCII_PUNCTUATION = "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~";
const KOREAN_PUNCTUATION = "，。！？、…·“”‘’「」『』《》〈〉";
const PUNCTUATION = new Set(
  Array.from(`${ASCII_PUNCTUATION}${KOREAN_PUNCTUATION}`),
);

export function normalizeTranscript(text: string): string {
  return Array.from(text.trim().toLowerCase())
    .filter((character) => !PUNCTUATION.has(character))
    .join("")
    .replace(/\s+/gu, "");
}

export function compareTranscripts(
  input: CompareTranscriptsInput,
): TranscriptComparisonResult {
  const expected = input.expected.trim();
  const actual = input.actual.trim();

  if (input.exact === true) {
    return {
      ok: expected === actual,
      mode: "exact",
      expected,
      actual,
    };
  }

  const normalizedExpected = normalizeTranscript(expected);
  const normalizedActual = normalizeTranscript(actual);

  return {
    ok: normalizedExpected === normalizedActual,
    mode: "normalized",
    expected,
    actual,
    normalizedExpected,
    normalizedActual,
  };
}
