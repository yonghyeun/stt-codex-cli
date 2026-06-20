#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  comment.sh --issue <risk-issue-number> --body-file <path> [--dry-run]
USAGE
}

issue=""
body_file=""
dry_run="0"

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --issue) issue="${2:-}"; shift 2 ;;
    --body-file) body_file="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$issue" =~ ^[0-9]+$ ]] || { echo "--issue must be a number" >&2; exit 2; }
[[ -n "$body_file" && -f "$body_file" ]] || { echo "--body-file must point to an existing file" >&2; exit 2; }
grep -q '^## Risk Capture' "$body_file" || { echo "risk comment must start with ## Risk Capture" >&2; exit 3; }

gh api "repos/:owner/:repo/issues/${issue}" --jq '.number' >/dev/null

if [[ "$dry_run" == "1" ]]; then
  echo "risk-capture dry run passed"
  echo "issue: #$issue"
  echo "body-file: $body_file"
  exit 0
fi

gh api "repos/:owner/:repo/issues/${issue}/comments" --method POST -f "body=$(<"$body_file")" --jq '.html_url'
