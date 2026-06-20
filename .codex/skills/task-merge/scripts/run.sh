#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run.sh --pr <number> --issue <number> --branch <branch> --body-file <path> [--umbrella <number>] [--skip-checks] [--skip-local] [--dry-run] [--yes]

Orchestrates PR squash merge, remote issue closeout, and local cleanup.
USAGE
}

pr=""
issue=""
branch=""
body_file=""
umbrella=""
skip_checks="0"
skip_local="0"
dry_run="0"
yes="0"

allowed_landing_types=(feat fix docs test chore refactor design infra)

build_landing_subject() {
  local pr_number="$1"
  local pr_title="$2"
  local landing_type="chore"
  local landing_summary="$pr_title"
  local title_prefix=""
  local candidate=""

  if [[ "$pr_title" == *:* ]]; then
    title_prefix="${pr_title%%:*}"
    landing_summary="${pr_title#*:}"
    landing_summary="${landing_summary#"${landing_summary%%[![:space:]]*}"}"
    for candidate in "${allowed_landing_types[@]}"; do
      if [[ "$title_prefix" == "$candidate" || "$title_prefix" == "$candidate!" || "$title_prefix" == "$candidate("* ]]; then
        landing_type="$candidate"
        break
      fi
    done
  fi

  landing_summary="$(sed -E 's/[[:space:]]+\(#[0-9]+\)$//' <<<"$landing_summary")"
  printf 'land(%s): %s (#%s)\n' "$landing_type" "$landing_summary" "$pr_number"
}

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --pr) pr="${2:-}"; shift 2 ;;
    --issue) issue="${2:-}"; shift 2 ;;
    --branch) branch="${2:-}"; shift 2 ;;
    --body-file) body_file="${2:-}"; shift 2 ;;
    --umbrella) umbrella="${2:-}"; shift 2 ;;
    --skip-checks) skip_checks="1"; shift ;;
    --skip-local) skip_local="1"; shift ;;
    --dry-run) dry_run="1"; shift ;;
    --yes) yes="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$pr" =~ ^[0-9]+$ ]] || { echo "--pr must be a number" >&2; exit 2; }
[[ "$issue" =~ ^[0-9]+$ ]] || { echo "--issue must be a number" >&2; exit 2; }
[[ -n "$branch" ]] || { echo "--branch is required" >&2; exit 2; }
[[ -n "$body_file" && -f "$body_file" ]] || { echo "--body-file must point to an existing file" >&2; exit 2; }
if [[ -n "$umbrella" && ! "$umbrella" =~ ^[0-9]+$ ]]; then
  echo "--umbrella must be a number" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
remote_args=(--issue "$issue" --body-file "$body_file")
[[ -z "$umbrella" ]] || remote_args+=(--umbrella "$umbrella")

pr_payload="$(gh api "repos/:owner/:repo/pulls/${pr}" --jq '[.number, .state, .merged, .head.sha, .head.ref, .title] | @tsv')"
pr_number="$(cut -f1 <<<"$pr_payload")"
pr_state="$(cut -f2 <<<"$pr_payload")"
pr_merged="$(cut -f3 <<<"$pr_payload")"
pr_head_sha="$(cut -f4 <<<"$pr_payload")"
pr_head_ref="$(cut -f5 <<<"$pr_payload")"
pr_title="$(cut -f6- <<<"$pr_payload")"
landing_subject="$(build_landing_subject "$pr_number" "$pr_title")"
landing_body_file="$(mktemp)"
trap 'rm -f "$landing_body_file"' EXIT
{
  printf 'Closes #%s\n' "$issue"
  [[ -z "$umbrella" ]] || printf 'Refs #%s\n' "$umbrella"
  printf 'PR #%s\n\n' "$pr_number"
  cat "$body_file"
} >"$landing_body_file"

echo "PR: #$pr_number"
echo "Title: $pr_title"
echo "Landing subject: $landing_subject"
echo "State: $pr_state"
echo "Merged: $pr_merged"
echo "Head ref: $pr_head_ref"
echo "Head SHA: $pr_head_sha"
echo "Issue: #$issue"
echo "Branch: $branch"
echo "Body file: $body_file"
echo "Landing body file: $landing_body_file"
[[ -z "$umbrella" ]] || echo "Umbrella: #$umbrella"
echo "Skip checks: $([[ "$skip_checks" == "1" ]] && echo yes || echo no)"
echo "Skip local cleanup: $([[ "$skip_local" == "1" ]] && echo yes || echo no)"

if [[ "$pr_merged" == "true" ]]; then
  echo "Required checks: skipped because PR is already merged"
elif [[ "$skip_checks" != "1" ]]; then
  echo "Required checks:"
  if ! gh pr checks "$pr" --required; then
    echo "pending: required checks are not passing or no required checks are reported" >&2
    echo "Use --skip-checks only after checks have been verified another way." >&2
    exit 3
  fi
else
  echo "Required checks: skipped"
fi

if [[ "$dry_run" == "1" ]]; then
  echo "Would squash merge PR #$pr with landing subject."
  echo "Would run task-remote-closeout for issue #$issue."
  if [[ "$skip_local" == "1" ]]; then
    echo "Would skip task-local-closeout."
  else
    echo "Would run task-local-closeout for branch $branch."
  fi
  echo "task-merge dry run passed"
  exit 0
fi

[[ "$yes" == "1" ]] || { echo "--yes is required for merge orchestration mutation" >&2; exit 2; }

if [[ "$pr_merged" == "true" ]]; then
  echo "PR already merged; skipping merge step"
elif [[ "$pr_state" == "open" ]]; then
  gh pr merge "$pr" --squash --match-head-commit "$pr_head_sha" --subject "$landing_subject" --body-file "$landing_body_file"
else
  echo "pending: PR is closed but not merged" >&2
  exit 3
fi

"$script_dir/../../task-remote-closeout/scripts/run.sh" "${remote_args[@]}" --yes

if [[ "$skip_local" == "1" ]]; then
  echo "task-local-closeout skipped"
else
  "$script_dir/../../task-local-closeout/scripts/run.sh" --branch "$branch" --pr "$pr" --yes
fi

echo "task-merge complete"
