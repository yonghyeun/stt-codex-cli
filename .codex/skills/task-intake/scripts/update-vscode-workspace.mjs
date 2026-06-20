#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = execFileSync(
  "git",
  ["-C", scriptDir, "rev-parse", "--show-toplevel"],
  {
    encoding: "utf8",
  },
).trim();

const workspacePath = join(repoRoot, "stt-codex-cli-worktrees.code-workspace");
const raw = execFileSync(
  "git",
  ["-C", repoRoot, "worktree", "list", "--porcelain"],
  {
    encoding: "utf8",
  },
);

const records = raw
  .trim()
  .split(/\n\n+/)
  .filter(Boolean)
  .map((record) => {
    const fields = new Map();
    for (const line of record.split("\n")) {
      const [key, ...valueParts] = line.split(" ");
      fields.set(key, valueParts.join(" "));
    }
    return {
      path: fields.get("worktree"),
      branch: fields.get("branch")?.replace(/^refs\/heads\//, "") ?? "detached",
    };
  })
  .filter((record) => record.path);

const counts = new Map();
for (const record of records) {
  const basename = record.path.split("/").filter(Boolean).at(-1) ?? record.path;
  counts.set(basename, (counts.get(basename) ?? 0) + 1);
}

const folders = records.map((record) => {
  const basename = record.path.split("/").filter(Boolean).at(-1) ?? record.path;
  return {
    name:
      counts.get(basename) === 1 ? basename : `${basename} (${record.branch})`,
    path: record.path,
  };
});

const excludes = {
  "**/node_modules/**": true,
  "**/.next/**": true,
  "**/dist/**": true,
  "**/build/**": true,
  "**/out/**": true,
};

writeFileSync(
  workspacePath,
  `${JSON.stringify({ folders, settings: { "files.watcherExclude": excludes, "search.exclude": excludes } }, null, 2)}\n`,
);

console.log(
  `Updated ${relative(process.cwd(), workspacePath) || workspacePath}`,
);
console.log(`Folders: ${folders.length}`);
