import { execFile } from "node:child_process";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";
import { describe, expect, it } from "vitest";

import {
  compareTranscripts,
  normalizeTranscript,
} from "./transcriptComparison";

const execFileAsync = promisify(execFile);

describe("normalizeTranscript", () => {
  it("lowercases and removes whitespace plus ASCII/Korean punctuation", () => {
    expect(normalizeTranscript("  Session, 세션！\n파일명.py  ")).toBe(
      "session세션파일명py",
    );
  });
});

describe("compareTranscripts", () => {
  it("uses normalized comparison by default", () => {
    const result = compareTranscripts({
      expected: "Session, 세션！",
      actual: "session 세션",
    });

    expect(result).toMatchObject({
      ok: true,
      mode: "normalized",
      expected: "Session, 세션！",
      actual: "session 세션",
    });
  });

  it("can require exact comparison", () => {
    const result = compareTranscripts({
      expected: "Session",
      actual: "session",
      exact: true,
    });

    expect(result).toMatchObject({
      ok: false,
      mode: "exact",
    });
  });
});

describe("compare-transcript CLI", () => {
  it("prints match and exits 0 for normalized matches", async () => {
    const tempDir = await mkdtemp(join(tmpdir(), "stt-codex-cli-"));
    const expectedFile = join(tempDir, "expected.txt");
    const actualFile = join(tempDir, "actual.txt");

    await writeFile(expectedFile, "Session, 세션！\n", "utf8");
    await writeFile(actualFile, "session 세션\n", "utf8");

    const result = await execFileAsync(process.execPath, [
      "--import",
      "tsx",
      "src/app/cli/compare-transcript.ts",
      expectedFile,
      actualFile,
    ]);

    expect(result.stdout.trim()).toBe("transcript match");
    expect(result.stderr).toBe("");
  });

  it("prints mismatch details and exits 1 for exact mismatches", async () => {
    const tempDir = await mkdtemp(join(tmpdir(), "stt-codex-cli-"));
    const expectedFile = join(tempDir, "expected.txt");
    const actualFile = join(tempDir, "actual.txt");

    await writeFile(expectedFile, "Session\n", "utf8");
    await writeFile(actualFile, "session\n", "utf8");

    await expect(
      execFileAsync(process.execPath, [
        "--import",
        "tsx",
        "src/app/cli/compare-transcript.ts",
        expectedFile,
        actualFile,
        "--exact",
      ]),
    ).rejects.toMatchObject({
      code: 1,
      stdout: "",
      stderr: "transcript mismatch\nexpected: Session\nactual:   session\n",
    });
  });
});
