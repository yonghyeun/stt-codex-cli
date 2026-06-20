import { describe, expect, it } from "vitest";

import { buildTranscribeArgs } from "./sttAdapter";

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
