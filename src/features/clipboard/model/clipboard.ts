export type ClipboardBackend = "auto" | "xclip" | "wl-copy";
export type ResolvedClipboardBackend = "xclip" | "wl-copy";

export interface ClipboardEnvironment {
  waylandDisplay?: string;
  hasCommand: (command: string) => boolean | Promise<boolean>;
}

export async function resolveClipboardBackend(
  requested: ClipboardBackend,
  env: ClipboardEnvironment,
): Promise<ResolvedClipboardBackend> {
  if (requested === "xclip" || requested === "wl-copy") {
    return requested;
  }

  const hasWlCopy = await env.hasCommand("wl-copy");
  const hasWlPaste = await env.hasCommand("wl-paste");
  if (env.waylandDisplay && hasWlCopy && hasWlPaste) {
    return "wl-copy";
  }

  if (await env.hasCommand("xclip")) {
    return "xclip";
  }

  if (hasWlCopy && hasWlPaste) {
    return "wl-copy";
  }

  throw new Error(
    "no supported clipboard backend found. Install xclip or wl-clipboard.",
  );
}

export function parseClipboardBackend(value: string): ClipboardBackend {
  if (value === "auto" || value === "xclip" || value === "wl-copy") {
    return value;
  }
  throw new Error(`invalid backend: ${value}`);
}

export function clipboardWriteCommand(backend: ResolvedClipboardBackend): {
  command: string;
  args: string[];
} {
  if (backend === "xclip") {
    return { command: "xclip", args: ["-selection", "clipboard", "-in"] };
  }
  return { command: "wl-copy", args: [] };
}

export function clipboardReadCommand(backend: ResolvedClipboardBackend): {
  command: string;
  args: string[];
} {
  if (backend === "xclip") {
    return { command: "xclip", args: ["-selection", "clipboard", "-out"] };
  }
  return { command: "wl-paste", args: ["--no-newline"] };
}
