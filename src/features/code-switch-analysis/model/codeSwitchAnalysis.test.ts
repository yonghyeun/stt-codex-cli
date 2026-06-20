import { describe, expect, it } from "vitest";

import {
  analyzeCodeSwitchRow,
  analyzeCodeSwitchSuite,
  asciiTokens,
} from "./codeSwitchAnalysis";

describe("code switch analysis", () => {
  it("extracts latin tokens case-insensitively", () => {
    expect(asciiTokens("Session bug README.md 세션")).toEqual([
      "session",
      "bug",
      "readme",
      "md",
    ]);
  });

  it("reports preserved and missing latin tokens", () => {
    expect(
      analyzeCodeSwitchRow({
        row_idx: 7,
        label: "sample",
        expected: "session bug README.md",
        actual: "session 리드미",
      }),
    ).toMatchObject({
      expected_tokens: ["session", "bug", "readme", "md"],
      actual_tokens: ["session"],
      preserved_tokens: ["session"],
      missing_tokens: ["bug", "readme", "md"],
      preserved_count: 1,
      expected_count: 4,
      preservation_rate: 0.25,
    });
  });

  it("summarizes suite-level preservation", () => {
    expect(
      analyzeCodeSwitchSuite({
        suite_id: "suite",
        model: "large-v3",
        language: "ko",
        device: "cuda",
        compute_type: "float16",
        results: [
          {
            row_idx: 1,
            label: "one",
            expected: "session bug",
            actual: "session bug",
          },
          {
            row_idx: 2,
            label: "two",
            expected: "README md",
            actual: "리드미",
          },
        ],
      }),
    ).toMatchObject({
      expected_latin_tokens: 4,
      preserved_latin_tokens: 2,
      preservation_rate: 0.5,
      rows: 2,
    });
  });
});
