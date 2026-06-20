#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run.sh --issue <number> --body-file <path> [--dry-run] [--yes]

Posts a structured Task Update comment through REST gh api. Always dry-run before mutation.
USAGE
}

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
dry_run="0"
yes="0"
forward=()

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --dry-run) dry_run="1"; forward+=("$1"); shift ;;
    --yes) yes="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) forward+=("$1"); shift ;;
  esac
done

if [[ "$dry_run" != "1" && "$yes" != "1" ]]; then
  echo "--yes is required for task-update mutation" >&2
  exit 2
fi

if [[ "$dry_run" == "1" ]]; then
  "$script_dir/comment.sh" "${forward[@]}"
  exit 0
fi

"$script_dir/comment.sh" "${forward[@]}"
