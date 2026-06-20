import { describe, expect, it } from "vitest";

import {
  childArgv,
  parseKeySequence,
  runIdFromDate,
  splitByTrigger,
} from "./codexPty";

describe("codex pty", () => {
  it("parses ctrl key sequences", () => {
    expect(parseKeySequence("ctrl+t")).toEqual(Buffer.from([20]));
  });

  it("adds --no-alt-screen to codex by default", () => {
    expect(
      childArgv({
        command: "codex",
        args: [],
        codexAltScreen: false,
      }),
    ).toEqual(["codex", "--no-alt-screen"]);
  });

  it("does not duplicate --no-alt-screen", () => {
    expect(
      childArgv({
        command: "codex",
        args: ["--no-alt-screen"],
        codexAltScreen: false,
      }),
    ).toEqual(["codex", "--no-alt-screen"]);
  });

  it("formats run ids with millisecond precision", () => {
    expect(runIdFromDate(new Date(2026, 5, 20, 1, 2, 3, 4))).toBe(
      "20260620-010203-004-stt-codex",
    );
  });

  it("splits stdin chunks by trigger", () => {
    expect(splitByTrigger(Buffer.from("abTcdT"), Buffer.from("T"))).toEqual([
      Buffer.from("ab"),
      Buffer.from("cd"),
      Buffer.from(""),
    ]);
  });
});
