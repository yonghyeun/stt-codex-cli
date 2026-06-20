import { basename } from "node:path";

export type InjectMode = "stt" | "fixed-text";

export interface ChildCommandInput {
  command: string;
  args: string[];
  codexAltScreen: boolean;
}

export function parseKeySequence(value: string): Buffer {
  const normalized = value.trim().toLowerCase();
  if (normalized === "") {
    throw new Error("--inject-key must not be empty");
  }

  const namedKeys: Record<string, string> = {
    tab: "\t",
    esc: "\u001b",
    escape: "\u001b",
    space: " ",
    enter: "\r",
  };
  if (namedKeys[normalized] !== undefined) {
    return Buffer.from(namedKeys[normalized]);
  }

  if (normalized.startsWith("ctrl+")) {
    const key = normalized.slice("ctrl+".length);
    if (!/^[a-z]$/u.test(key)) {
      throw new Error("ctrl key syntax must be ctrl+<a-z>, for example ctrl+t");
    }
    return Buffer.from([key.charCodeAt(0) - "a".charCodeAt(0) + 1]);
  }

  if (value.length === 1) {
    return Buffer.from(value);
  }

  throw new Error(
    "inject key must be a single character, named key, or ctrl+<a-z>",
  );
}

export function isCodexCommand(command: string): boolean {
  return basename(command) === "codex";
}

export function shouldAddCodexNoAltScreen(input: ChildCommandInput): boolean {
  return (
    isCodexCommand(input.command) &&
    !input.codexAltScreen &&
    !input.args.includes("--no-alt-screen")
  );
}

export function childArgv(input: ChildCommandInput): string[] {
  const args = [...input.args];
  if (shouldAddCodexNoAltScreen(input)) {
    args.unshift("--no-alt-screen");
  }
  return [input.command, ...args];
}

export function runIdFromDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const hour = String(date.getHours()).padStart(2, "0");
  const minute = String(date.getMinutes()).padStart(2, "0");
  const second = String(date.getSeconds()).padStart(2, "0");
  const milliseconds = String(date.getMilliseconds()).padStart(3, "0");
  return `${year}${month}${day}-${hour}${minute}${second}-${milliseconds}-stt-codex`;
}

export function splitByTrigger(data: Buffer, trigger: Buffer): Buffer[] {
  if (trigger.length === 0) {
    return [data];
  }

  const parts: Buffer[] = [];
  let start = 0;
  while (start <= data.length) {
    const index = data.indexOf(trigger, start);
    if (index < 0) {
      parts.push(data.subarray(start));
      return parts;
    }
    parts.push(data.subarray(start, index));
    start = index + trigger.length;
  }

  return parts;
}
