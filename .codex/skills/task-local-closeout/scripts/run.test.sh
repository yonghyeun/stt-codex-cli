#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
script="$script_dir/run.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

fake_bin="$tmp/bin"
fake_main="$tmp/main-worktree"
fake_target="$tmp/issue-worktree"
git_log="$tmp/git.log"
node_log="$tmp/node.log"
output="$tmp/output.txt"
branch="chore/144-local-closeout-stable-path"
mkdir -p "$fake_bin" "$fake_main/.codex/skills/task-intake/scripts" "$fake_target"
touch "$fake_main/.codex/skills/task-intake/scripts/update-vscode-workspace.mjs"

cat >"$fake_bin/git" <<EOF
#!/usr/bin/env bash
cwd=""
if [[ "\${1:-}" == "-C" ]]; then
  cwd="\$2"
  shift 2
fi
printf '%s|%s\n' "\$cwd" "\$*" >> "$git_log"

if [[ "\${1:-}" == "worktree" && "\${2:-}" == "remove" && "\${3:-}" == "$fake_target" ]]; then
  rm -rf "$fake_target"
  exit 0
fi

if [[ "\${1:-}" == "branch" && "\${2:-}" == "-d" && "\${3:-}" == "$branch" ]]; then
  exit 0
fi

case "\$*" in
  "rev-parse --show-toplevel")
    printf '%s\n' "$fake_target"
    ;;
  "fetch --prune")
    exit 0
    ;;
  "worktree list --porcelain")
    if [[ "\${NO_RECORD:-0}" == "1" ]]; then
      cat <<'WORKTREES'
worktree $fake_main
HEAD mainhead
branch refs/heads/main
WORKTREES
    else
      cat <<'WORKTREES'
worktree $fake_main
HEAD mainhead
branch refs/heads/main

worktree $fake_target
HEAD targethead
branch refs/heads/$branch
WORKTREES
    fi
    ;;
  "status --short")
    exit 0
    ;;
  "rev-parse --abbrev-ref --symbolic-full-name @{u}")
    printf '%s\n' "origin/$branch"
    ;;
  "rev-parse --verify --quiet origin/$branch")
    exit 0
    ;;
  "rev-list --count origin/$branch..HEAD")
    printf '%s\n' "0"
    ;;
  "rev-parse HEAD")
    printf '%s\n' "targethead"
    ;;
  "worktree prune")
    exit 0
    ;;
  "branch -vv")
    exit 0
    ;;
  *)
    echo "unexpected git args: \$*" >&2
    exit 1
    ;;
esac
EOF
chmod +x "$fake_bin/git"

cat >"$fake_bin/node" <<EOF
#!/usr/bin/env bash
printf '%s\n' "\$*" >> "$node_log"
exit 0
EOF
chmod +x "$fake_bin/node"

"$script" --help | grep -q 'Usage:'

PATH="$fake_bin:$PATH" "$script" --branch "$branch" --yes >"$output"

grep -q 'task-local-closeout complete' "$output"
grep -q "$fake_main/.codex/skills/task-intake/scripts/update-vscode-workspace.mjs" "$node_log"
if grep -q "$fake_target/.codex" "$node_log"; then
  echo "task-local-closeout used deleted worktree helper path" >&2
  exit 1
fi
grep -q "^$fake_main|worktree remove $fake_target$" "$git_log"
grep -q "^$fake_main|branch -d $branch$" "$git_log"
grep -q "^$fake_main|worktree prune$" "$git_log"

: >"$node_log"
NO_RECORD=1 PATH="$fake_bin:$PATH" "$script" --branch missing-branch --dry-run >"$output"
grep -q 'task-local-closeout dry run passed' "$output"
if [[ -s "$node_log" ]]; then
  echo "task-local-closeout dry-run refreshed workspace for missing branch" >&2
  exit 1
fi

if NO_RECORD=1 PATH="$fake_bin:$PATH" "$script" --branch missing-branch >"$output" 2>&1; then
  echo "task-local-closeout refreshed workspace without --yes for missing branch" >&2
  exit 1
fi
grep -q -- '--yes is required for local cleanup mutation' "$output"

echo "task-local-closeout run tests passed"
