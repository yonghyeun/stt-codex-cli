#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
script="$script_dir/run.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

body="$tmp/body.md"
printf '%s\n' "## Context" "" "- 한국어 테스트 본문" >"$body"

"$script" --help | grep -q 'Usage:'

"$script" --kind standalone --title "chore: example" --body-file "$body" \
  --label type:chore --label kind:standalone --label status:intake --label priority:p2 --label area:ops --dry-run |
  grep -q 'task-add dry run passed'

if "$script" --kind standalone --title "chore: example" --body-file "$body" \
  --label type:chore --label kind:standalone --label status:intake --label priority:p2 --label area:ops >/dev/null 2>&1; then
  echo "task-add mutation without --yes unexpectedly passed" >&2
  exit 1
fi

echo "task-add run tests passed"
