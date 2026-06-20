import { describe, expect, it } from "vitest";

import { parseMemoryEntries, recoverText } from "./tokenRecovery";

describe("token recovery", () => {
  it("applies longer spoken aliases first and tolerates whitespace", () => {
    const entries = parseMemoryEntries({
      version: 1,
      entries: [
        {
          spoken: "리드 미",
          target: "README.md",
          scope: "workspace",
          confidence: 1,
          source: "manual",
        },
        {
          spoken: "리드",
          target: "lead",
          scope: "workspace",
          confidence: 1,
          source: "manual",
        },
      ],
    });

    expect(recoverText("리드   미 수정해", entries).recovered).toBe(
      "README.md 수정해",
    );
  });

  it("filters entries below min confidence", () => {
    const entries = parseMemoryEntries({
      version: 1,
      entries: [
        {
          spoken: "세션",
          target: "session",
          scope: "workspace",
          confidence: 0.7,
          source: "manual",
        },
      ],
    });

    expect(recoverText("세션 확인", entries, 0.8)).toMatchObject({
      recovered: "세션 확인",
      changed: false,
      applied: [],
    });
  });
});
