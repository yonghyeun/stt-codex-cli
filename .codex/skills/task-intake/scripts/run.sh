#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run.sh --issue <number> [--path <path>] [--branch <branch>] [--base <start-point>] [--no-code-add] [--dry-run] [--yes]

Checks issue readiness, prepares an isolated worktree, and refreshes stt-codex-cli-worktrees.code-workspace.
Dry-run performs live read checks only and does not create branches, worktrees, or files.
USAGE
}

die() {
  local code="$1"
  shift
  printf '%s\n' "$*" >&2
  exit "$code"
}

slugify() {
  printf '%s' "$1" |
    tr '[:upper:]' '[:lower:]' |
    sed -E 's/^[a-z]+:[[:space:]]*//; s/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g'
}

issue=""
target_path=""
branch=""
base="origin/main"
skip_code_add="0"
dry_run="0"
yes="0"

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --issue) issue="${2:-}"; shift 2 ;;
    --path) target_path="${2:-}"; shift 2 ;;
    --branch) branch="${2:-}"; shift 2 ;;
    --base) base="${2:-}"; shift 2 ;;
    --no-code-add) skip_code_add="1"; shift ;;
    --dry-run) dry_run="1"; shift ;;
    --yes) yes="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$issue" =~ ^[0-9]+$ ]] || die 2 "--issue must be a number"

repo_root="$(git rev-parse --show-toplevel)"
payload="$(gh api "repos/:owner/:repo/issues/${issue}" --jq '[.number, .state, .title, (.body // "")] | @json')" ||
  die 1 "Issue #${issue} could not be fetched."
issue_state="$(jq -r '.[1]' <<<"$payload")"
issue_title="$(jq -r '.[2]' <<<"$payload")"
issue_body="$(jq -r '.[3]' <<<"$payload")"

[[ "$issue_state" == "open" ]] || die 3 "Issue #${issue} is not open."

missing=()
for section in "## Scope" "## Non-Scope" "## Acceptance Criteria" "## Completion Signal"; do
  if ! grep -qF "$section" <<<"$issue_body"; then
    missing+=("$section")
  fi
done

if [[ "${#missing[@]}" -gt 0 ]]; then
  printf 'Issue #%s is missing required intake sections:\n' "$issue" >&2
  printf -- '- %s\n' "${missing[@]}" >&2
  exit 3
fi

slug="$(slugify "$issue_title")"
[[ -n "$slug" ]] || slug="task"
[[ -n "$branch" ]] || branch="feat/${issue}-${slug}"
[[ -n "$target_path" ]] || target_path="../stt-codex-cli-issue-${issue}-${slug}"

echo "Issue: #$issue"
echo "Issue state: $issue_state"
echo "Issue title: $issue_title"
echo "Branch: $branch"
echo "Path: $target_path"
echo "Base: $base"
echo "Skip VS Code add: $([[ "$skip_code_add" == "1" ]] && echo yes || echo no)"
echo "Required sections: present"

if [[ "$dry_run" == "1" ]]; then
  echo "Would run worktree-add.sh"
  echo "Would refresh stt-codex-cli-worktrees.code-workspace through worktree-add.sh"
  echo "task-intake dry run passed"
  exit 0
fi

[[ "$yes" == "1" ]] || die 2 "--yes is required for task-intake mutation"

args=(--path "$target_path" --branch "$branch" --base "$base")
[[ "$skip_code_add" != "1" ]] || args+=(--no-code-add)

"$repo_root/.codex/skills/task-intake/scripts/worktree-add.sh" "${args[@]}"
