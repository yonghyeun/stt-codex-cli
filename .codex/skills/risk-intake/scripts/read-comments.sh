#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  read-comments.sh --issue <risk-issue-number>
USAGE
}

issue=""
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --issue) issue="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$issue" =~ ^[0-9]+$ ]] || { echo "--issue must be a number" >&2; exit 2; }

gh api "repos/:owner/:repo/issues/${issue}/comments" --paginate \
  --jq '.[] | select(.body | startswith("## Risk Capture")) | {url: .html_url, body: .body}'
