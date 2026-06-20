#!/usr/bin/env node

import { existsSync, readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { join } from "node:path";

const script = new URL("./update-vscode-workspace.mjs", import.meta.url)
  .pathname;
const result = spawnSync(process.execPath, [script], { encoding: "utf8" });

if (result.status !== 0) {
  process.stderr.write(result.stderr);
  process.exit(result.status ?? 1);
}

const repoRoot = spawnSync("git", ["rev-parse", "--show-toplevel"], {
  encoding: "utf8",
}).stdout.trim();
const workspacePath = join(repoRoot, "stt-codex-cli-worktrees.code-workspace");

if (!existsSync(workspacePath)) {
  throw new Error("workspace file was not created");
}

const parsed = JSON.parse(readFileSync(workspacePath, "utf8"));
if (!Array.isArray(parsed.folders) || parsed.folders.length === 0) {
  throw new Error("workspace folders are missing");
}

console.log("update-vscode-workspace tests passed");
