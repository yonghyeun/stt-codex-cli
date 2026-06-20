import {
  clipboardReadCommand,
  clipboardWriteCommand,
  parseClipboardBackend,
  resolveClipboardBackend,
} from "@/features/clipboard";
import { runCommand } from "@/shared/process";

import { isDirectRun } from "./shared/direct-run";

interface ParsedArgs {
  backend: "auto" | "xclip" | "wl-copy";
  verify: boolean;
  textParts: string[];
}

export async function main(argv = process.argv.slice(2)): Promise<number> {
  const parsed = parseArgs(argv);
  if (parsed.kind === "help") {
    process.stdout.write(`${usage()}\n`);
    return 0;
  }
  if (parsed.kind === "error") {
    process.stderr.write(`error: ${parsed.message}\n${usage()}\n`);
    return 2;
  }

  try {
    const text = await inputText(parsed.args.textParts);
    if (text === "") {
      throw new Error("text must not be empty");
    }
    const backend = await resolveClipboardBackend(parsed.args.backend, {
      waylandDisplay: process.env.WAYLAND_DISPLAY,
      hasCommand: commandExists,
    });
    const write = clipboardWriteCommand(backend);
    const writeResult = await runCommand(write.command, write.args, {
      input: text,
    });
    if (writeResult.code !== 0) {
      throw new Error(
        writeResult.stderr.trim() || `${backend} failed to copy text`,
      );
    }

    if (parsed.args.verify) {
      const read = clipboardReadCommand(backend);
      const readResult = await runCommand(read.command, read.args);
      if (readResult.code !== 0) {
        throw new Error(
          readResult.stderr.trim() || `${backend} readback failed`,
        );
      }
      if (readResult.stdout !== text) {
        throw new Error("clipboard verification failed");
      }
    }

    process.stdout.write(`${text}\n`);
    process.stderr.write(
      `copied: backend=${backend} verified=${parsed.args.verify ? "true" : "false"} chars=${text.length}\n`,
    );
    return 0;
  } catch (error) {
    process.stderr.write(
      `error: ${error instanceof Error ? error.message : String(error)}\n`,
    );
    return 1;
  }
}

type ParseResult =
  | { kind: "ok"; args: ParsedArgs }
  | { kind: "help" }
  | { kind: "error"; message: string };

function parseArgs(argv: string[]): ParseResult {
  const args: ParsedArgs = {
    backend: parseClipboardBackend(process.env.STT_CLIPBOARD_BACKEND ?? "auto"),
    verify: true,
    textParts: [],
  };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index] ?? "";
    if (arg === "-h" || arg === "--help") {
      return { kind: "help" };
    }
    if (arg === "--no-verify") {
      args.verify = false;
      continue;
    }
    if (arg === "--backend") {
      const value = argv[index + 1];
      if (!value) {
        return { kind: "error", message: "--backend requires a value" };
      }
      index += 1;
      try {
        args.backend = parseClipboardBackend(value);
      } catch (error) {
        return { kind: "error", message: formatError(error) };
      }
      continue;
    }
    if (arg.startsWith("--backend=")) {
      try {
        args.backend = parseClipboardBackend(arg.slice("--backend=".length));
      } catch (error) {
        return { kind: "error", message: formatError(error) };
      }
      continue;
    }
    if (arg === "--") {
      args.textParts.push(...argv.slice(index + 1));
      break;
    }
    if (arg.startsWith("-")) {
      return { kind: "error", message: `unknown option: ${arg}` };
    }
    args.textParts.push(arg);
  }

  return { kind: "ok", args };
}

async function inputText(parts: string[]): Promise<string> {
  if (parts.length > 0) {
    return parts.join(" ");
  }
  if (process.stdin.isTTY) {
    throw new Error("text is required when stdin is empty");
  }
  return await new Promise<string>((resolve) => {
    let text = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk: string) => {
      text += chunk;
    });
    process.stdin.on("end", () => resolve(text));
  });
}

async function commandExists(command: string): Promise<boolean> {
  const result = await runCommand("which", [command]);
  return result.code === 0;
}

function usage(): string {
  return "Usage: npm run copy-text -- [--backend auto|xclip|wl-copy] [--no-verify] [text ...]";
}

function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

if (isDirectRun(import.meta.url)) {
  process.exitCode = await main();
}
