import { describe, expect, it } from "vitest";

import {
  buildWhisperCliArgs,
  DEFAULT_TRANSCRIBE_OPTIONS,
  modelFileName,
  parseWhisperStdout,
  resolveWhisperModel,
  transcribeAudio,
} from "./sttEngine";

describe("stt engine", () => {
  it("builds whisper.cpp cli arguments", () => {
    expect(
      buildWhisperCliArgs("/tmp/audio.wav", "/tmp/ggml-large-v3.bin", {
        model: "large-v3",
        language: "ko",
        device: "cpu",
        computeType: "auto",
        beamSize: 3,
        initialPrompt: "README.md",
        vadFilter: false,
      }),
    ).toEqual([
      "-m",
      "/tmp/ggml-large-v3.bin",
      "-f",
      "/tmp/audio.wav",
      "-l",
      "ko",
      "-bs",
      "3",
      "-np",
      "-nt",
      "--prompt",
      "README.md",
      "-ng",
    ]);
  });

  it("supports large-v3 model file names", () => {
    expect(modelFileName("large-v3")).toBe("ggml-large-v3.bin");
  });

  it("rejects unsupported model names before download", () => {
    expect(() => resolveWhisperModel("unknown-model", "/models")).toThrow(
      "unsupported STT model",
    );
  });

  it("normalizes whisper.cpp stdout to transcript text", () => {
    expect(
      parseWhisperStdout(`
whisper_init_from_file_with_params_no_state: loading model

[00:00:00.000 --> 00:00:01.000] 안녕하세요.
[00:00:01.000 --> 00:00:02.000] README.md 수정해줘.

whisper_print_timings: total time = 100 ms
`),
    ).toBe("안녕하세요. README.md 수정해줘.");
  });

  it("fails before model work when the audio file is missing", async () => {
    await expect(
      transcribeAudio("/tmp/stt-codex-missing-audio.wav", {
        ...DEFAULT_TRANSCRIBE_OPTIONS,
        model: "tiny",
      }),
    ).rejects.toThrow("audio file not found");
  });
});
