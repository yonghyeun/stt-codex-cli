import { describe, expect, it } from "vitest";

import {
  clipboardReadCommand,
  clipboardWriteCommand,
  parseClipboardBackend,
  resolveClipboardBackend,
} from "./clipboard";

describe("clipboard", () => {
  it("prefers wl-copy on Wayland when both commands exist", async () => {
    await expect(
      resolveClipboardBackend("auto", {
        waylandDisplay: "wayland-0",
        hasCommand: (command) =>
          command === "wl-copy" || command === "wl-paste",
      }),
    ).resolves.toBe("wl-copy");
  });

  it("falls back to xclip", async () => {
    await expect(
      resolveClipboardBackend("auto", {
        hasCommand: (command) => command === "xclip",
      }),
    ).resolves.toBe("xclip");
  });

  it("rejects invalid backend names", () => {
    expect(() => parseClipboardBackend("pbcopy")).toThrow(
      "invalid backend: pbcopy",
    );
  });

  it("maps backend commands", () => {
    expect(clipboardWriteCommand("xclip")).toEqual({
      command: "xclip",
      args: ["-selection", "clipboard", "-in"],
    });
    expect(clipboardReadCommand("wl-copy")).toEqual({
      command: "wl-paste",
      args: ["--no-newline"],
    });
  });
});
