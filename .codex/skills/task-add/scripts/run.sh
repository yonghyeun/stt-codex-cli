#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run.sh --kind <umbrella|leaf|standalone|risk-management|risk-resolution> --title <title> --body-file <path> --label <label>... [options] [--dry-run] [--yes]

Creates one GitHub issue through the repo-local issue contract. Always dry-run before mutation.
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
  echo "--yes is required for task-add mutation" >&2
  exit 2
fi

if [[ "$dry_run" == "1" ]]; then
  "$script_dir/create-issue.sh" "${forward[@]}"
  exit 0
fi

"$script_dir/create-issue.sh" "${forward[@]}"
