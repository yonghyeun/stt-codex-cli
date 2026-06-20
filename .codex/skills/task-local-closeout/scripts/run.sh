#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run.sh --branch <branch> [--pr <number>] [--dry-run] [--yes]

Local cleanup only. Does not mutate GitHub issues or PRs.
USAGE
}

branch=""
pr=""
dry_run="0"
yes="0"

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --branch) branch="${2:-}"; shift 2 ;;
    --pr) pr="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
    --yes) yes="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$branch" ]] || { echo "--branch is required" >&2; exit 2; }
if [[ -n "$pr" && ! "$pr" =~ ^[0-9]+$ ]]; then
  echo "--pr must be a number" >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel)"

git -C "$repo_root" fetch --prune >/dev/null 2>&1 || true

main_worktree="$(git -C "$repo_root" worktree list --porcelain | awk '/^worktree / { print substr($0, 10); exit }')"
[[ -n "$main_worktree" ]] || { echo "Could not determine main worktree" >&2; exit 3; }
control_root="$main_worktree"
workspace_updater="$control_root/.codex/skills/task-intake/scripts/update-vscode-workspace.mjs"

refresh_workspace() {
  [[ -f "$workspace_updater" ]] || {
    echo "Workspace updater not found: $workspace_updater" >&2
    exit 3
  }
  node "$workspace_updater"
}

record="$(
  git -C "$repo_root" worktree list --porcelain |
    awk -v branch="refs/heads/${branch}" '
      /^worktree / { path = substr($0, 10) }
      /^branch / {
        current = substr($0, 8)
        if (current == branch) {
          print path
        }
      }
    '
)"

if [[ -z "$record" ]]; then
  echo "No registered worktree is currently checking out $branch"
  if [[ "$dry_run" == "1" ]]; then
    echo "task-local-closeout dry run passed"
    exit 0
  fi
  [[ "$yes" == "1" ]] || { echo "--yes is required for local cleanup mutation" >&2; exit 2; }
  refresh_workspace
  exit 0
fi

status="$(git -C "$record" status --short)"
upstream="$(git -C "$record" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || true)"
unpushed="0"
remote_gone="0"
pr_merged="unknown"
pr_head_matches="unknown"
local_head="$(git -C "$record" rev-parse HEAD)"
if [[ -n "$upstream" ]]; then
  if git -C "$record" rev-parse --verify --quiet "$upstream" >/dev/null; then
    ahead="$(git -C "$record" rev-list --count "${upstream}..HEAD")"
    [[ "$ahead" == "0" ]] || unpushed="1"
    if [[ -n "$pr" ]]; then
      pr_payload="$(gh api "repos/:owner/:repo/pulls/${pr}" --jq '[.merged, .head.sha] | @tsv' 2>/dev/null || true)"
      pr_merged="$(cut -f1 <<<"$pr_payload")"
      pr_head="$(cut -f2 <<<"$pr_payload")"
      if [[ "$pr_merged" == "true" && "$local_head" == "$pr_head" ]]; then
        pr_head_matches="yes"
      else
        pr_head_matches="no"
      fi
    fi
  else
    remote_gone="1"
    if ! git -C "$record" merge-base --is-ancestor HEAD origin/main; then
      unpushed="1"
      if [[ -n "$pr" ]]; then
        pr_payload="$(gh api "repos/:owner/:repo/pulls/${pr}" --jq '[.merged, .head.sha] | @tsv' 2>/dev/null || true)"
        pr_merged="$(cut -f1 <<<"$pr_payload")"
        pr_head="$(cut -f2 <<<"$pr_payload")"
        if [[ "$pr_merged" == "true" && "$local_head" == "$pr_head" ]]; then
          pr_head_matches="yes"
          unpushed="0"
        else
          pr_head_matches="no"
        fi
      fi
    fi
  fi
else
  unpushed="1"
fi

echo "Branch: $branch"
echo "Worktree: $record"
echo "Main worktree: $main_worktree"
echo "Dirty: $([[ -n "$status" ]] && echo yes || echo no)"
echo "Remote gone: $([[ "$remote_gone" == "1" ]] && echo yes || echo no)"
[[ -z "$pr" ]] || echo "PR merged: $pr_merged"
[[ -z "$pr" ]] || echo "PR head matches local HEAD: $pr_head_matches"
echo "Unpushed: $([[ "$unpushed" == "1" ]] && echo yes || echo no)"

[[ "$record" != "$main_worktree" ]] || { echo "pending: target is main worktree" >&2; exit 3; }
[[ -z "$status" ]] || { echo "pending: worktree is dirty" >&2; exit 3; }
[[ "$unpushed" != "1" ]] || { echo "pending: branch has unpushed/local-only commits" >&2; exit 3; }

if [[ "$dry_run" == "1" ]]; then
  echo "task-local-closeout dry run passed"
  exit 0
fi

[[ "$yes" == "1" ]] || { echo "--yes is required for local cleanup mutation" >&2; exit 2; }

target_abs="$(cd "$record" && pwd -P)"
git -C "$control_root" worktree list --porcelain | awk '/^worktree / { print substr($0, 10) }' | grep -Fxq "$target_abs" ||
  { echo "Path is not a registered worktree: $target_abs" >&2; exit 3; }

git -C "$control_root" worktree remove "$target_abs"
refresh_workspace
if [[ "$pr_head_matches" == "yes" ]]; then
  git -C "$control_root" branch -D "$branch"
else
  git -C "$control_root" branch -d "$branch"
fi
refresh_workspace
git -C "$control_root" worktree prune
git -C "$control_root" branch -vv | grep -F "$branch" || true
echo "Worktree removed: $target_abs"
echo "Removed branch: $branch"
echo "Updated workspace: stt-codex-cli-worktrees.code-workspace"
echo "task-local-closeout complete"
