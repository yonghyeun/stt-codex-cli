import { describe, expect, it } from "vitest";

import { buildTranscribeArgs, pythonRuntimeCandidates } from "./sttAdapter";

describe("stt adapter", () => {
  it("builds transcribe.py arguments", () => {
    expect(
      buildTranscribeArgs("audio.wav", {
        model: "tiny",
        language: "ko",
        device: "cpu",
        computeType: "int8",
        beamSize: 3,
        initialPrompt: "README.md",
        vadFilter: false,
      }),
    ).toEqual([
      expect.stringContaining("scripts/transcribe.py"),
      "audio.wav",
      "--model",
      "tiny",
      "--language",
      "ko",
      "--device",
      "cpu",
      "--compute-type",
      "int8",
      "--beam-size",
      "3",
      "--initial-prompt",
      "README.md",
      "--no-vad-filter",
    ]);
  });
});

describe("python runtime resolution", () => {
  it("prefers STT_PYTHON and then worktree/main venv candidates", () => {
    expect(
      pythonRuntimeCandidates(
        "/repo/worktree",
        { STT_PYTHON: "/custom/python" },
        "/repo/main/.git",
      ),
    ).toEqual([
      { pythonPath: "/custom/python" },
      {
        pythonPath: "/repo/worktree/.venv/bin/python",
        venvRoot: "/repo/worktree/.venv",
      },
      {
        pythonPath: "/repo/main/.venv/bin/python",
        venvRoot: "/repo/main/.venv",
      },
      { pythonPath: "python3" },
    ]);
  });
});
