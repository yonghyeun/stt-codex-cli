#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  worktree-add.sh --path <path> --branch <branch> [--base <start-point>] [--no-code-add]
  worktree-add.sh <path> <branch> [start-point]
USAGE
}

target_path=""
branch=""
start_point="HEAD"
skip_code_add="${STT_CODEX_CLI_SKIP_CODE_ADD:-0}"
positional=()

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --path) target_path="${2:-}"; shift 2 ;;
    --branch) branch="${2:-}"; shift 2 ;;
    --base) start_point="${2:-}"; shift 2 ;;
    --no-code-add) skip_code_add="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    --*) echo "Unknown option: $1" >&2; usage >&2; exit 2 ;;
    *) positional+=("$1"); shift ;;
  esac
done

if [[ "${#positional[@]}" -gt 0 ]]; then
  [[ -z "$target_path" && -z "$branch" && "$start_point" == "HEAD" ]] || {
    echo "Do not mix positional arguments with named options" >&2
    exit 2
  }
  [[ "${#positional[@]}" -ge 2 && "${#positional[@]}" -le 3 ]] || { usage >&2; exit 2; }
  target_path="${positional[0]}"
  branch="${positional[1]}"
  start_point="${positional[2]:-HEAD}"
fi

[[ -n "$target_path" && -n "$branch" ]] || { echo "Both path and branch are required" >&2; exit 2; }

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
repo_root="$(git rev-parse --show-toplevel)"
target_parent="$(dirname "$target_path")"
target_name="$(basename "$target_path")"

[[ -d "$target_parent" ]] || { echo "Target parent directory does not exist: $target_parent" >&2; exit 1; }
target_abs="$(cd "$target_parent" && pwd -P)/$target_name"

if git -C "$repo_root" worktree list --porcelain | awk '/^worktree / { print substr($0, 10) }' | grep -Fxq "$target_abs"; then
  echo "Worktree already registered: $target_abs"
else
  if git -C "$repo_root" show-ref --verify --quiet "refs/heads/$branch"; then
    git -C "$repo_root" worktree add "$target_abs" "$branch"
  else
    git -C "$repo_root" worktree add -b "$branch" "$target_abs" "$start_point"
  fi
fi

node "$script_dir/update-vscode-workspace.mjs"

if [[ "$skip_code_add" != "1" ]]; then
  if command -v code >/dev/null 2>&1; then
    code --add "$target_abs" || echo "VS Code CLI failed; workspace file was still updated." >&2
  else
    echo "VS Code CLI 'code' not found; workspace file was still updated." >&2
  fi
fi

echo "Worktree ready: $target_abs"
