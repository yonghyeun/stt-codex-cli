import { describe, expect, it } from "vitest";

import {
  buildArecordArgs,
  defaultRecordingConfig,
  parsePositiveInteger,
  recordingFileName,
} from "./audioRecording";

describe("audio recording", () => {
  it("builds the arecord command arguments", () => {
    expect(
      buildArecordArgs({
        duration: 3,
        outputFile: "output/recordings/sample.wav",
        config: {
          device: "default",
          format: "S16_LE",
          rate: "16000",
          channels: "1",
        },
      }),
    ).toEqual([
      "-D",
      "default",
      "-f",
      "S16_LE",
      "-r",
      "16000",
      "-c",
      "1",
      "-d",
      "3",
      "output/recordings/sample.wav",
    ]);
  });

  it("reads recording config from env with defaults", () => {
    expect(
      defaultRecordingConfig({
        STT_RECORD_DEVICE: "hw:1,0",
        STT_RECORD_RATE: "48000",
      }),
    ).toEqual({
      device: "hw:1,0",
      format: "S16_LE",
      rate: "48000",
      channels: "1",
    });
  });

  it("formats recording file names", () => {
    expect(recordingFileName(new Date(2026, 5, 20, 1, 2, 3))).toBe(
      "recording-20260620-010203.wav",
    );
  });

  it("rejects invalid durations", () => {
    expect(() => parsePositiveInteger("0", "duration_seconds")).toThrow(
      "duration_seconds must be a positive integer: 0",
    );
  });
});
