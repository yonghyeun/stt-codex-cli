#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run.sh --issue <number> --body-file <path> [--umbrella <number>] [--dry-run] [--yes]

GitHub issue closeout only. Does not touch local branches, worktrees, or workspace files.
USAGE
}

issue=""
body_file=""
umbrella=""
dry_run="0"
yes="0"

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --issue) issue="${2:-}"; shift 2 ;;
    --body-file) body_file="${2:-}"; shift 2 ;;
    --umbrella) umbrella="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
    --yes) yes="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$issue" =~ ^[0-9]+$ ]] || { echo "--issue must be a number" >&2; exit 2; }
[[ -n "$body_file" && -f "$body_file" ]] || { echo "--body-file must point to an existing file" >&2; exit 2; }
if [[ -n "$umbrella" && ! "$umbrella" =~ ^[0-9]+$ ]]; then
  echo "--umbrella must be a number" >&2
  exit 2
fi

payload="$(gh api "repos/:owner/:repo/issues/${issue}" --jq '[.number, .state, .title] | @tsv')"
issue_number="$(cut -f1 <<<"$payload")"
issue_state="$(cut -f2 <<<"$payload")"
issue_title="$(cut -f3- <<<"$payload")"
status_labels="$(gh api "repos/:owner/:repo/issues/${issue}/labels" --jq '.[] | select(.name | startswith("status:")) | .name')"

echo "Issue: #$issue_number"
echo "Title: $issue_title"
echo "State: $issue_state"
echo "Body file: $body_file"
echo "Status labels:"
if [[ -n "$status_labels" ]]; then
  printf '%s\n' "$status_labels" | sed 's/^/- /'
else
  echo "- none"
fi
[[ -z "$umbrella" ]] || echo "Umbrella update: #$umbrella"

if [[ "$dry_run" == "1" ]]; then
  echo "task-remote-closeout dry run passed"
  exit 0
fi

[[ "$yes" == "1" ]] || { echo "--yes is required for remote closeout mutation" >&2; exit 2; }

gh api "repos/:owner/:repo/issues/${issue}/comments" \
  --method POST \
  -f "body=$(<"$body_file")" \
  --jq '.html_url'

while IFS= read -r label; do
  [[ -n "$label" && "$label" != "status:done" ]] || continue
  gh api "repos/:owner/:repo/issues/${issue}/labels/${label}" --method DELETE >/dev/null || true
done <<<"$status_labels"

gh api "repos/:owner/:repo/issues/${issue}/labels" \
  --method POST \
  -f "labels[]=status:done" >/dev/null

gh api "repos/:owner/:repo/issues/${issue}" \
  --method PATCH \
  -f state=closed \
  -f state_reason=completed \
  --jq '.html_url'

if [[ -n "$umbrella" ]]; then
  gh api "repos/:owner/:repo/issues/${umbrella}/comments" \
    --method POST \
    -f "body=Remote closeout completed for #${issue}." \
    --jq '.html_url'
fi

echo "task-remote-closeout complete"
