#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
script="$script_dir/run.sh"

"$script" --help | grep -q 'Usage:'

checklist_output="$("$script" --mode checklist --issue 146 --dry-run)"

grep -q '^## Task Implement Checklist' <<<"$checklist_output"
grep -q 'task-intake -> phase plan -> phase loop -> final verification -> task-pr-create' <<<"$checklist_output"
grep -q '각 atomic phase는 task-commit으로 닫는다' <<<"$checklist_output"
grep -q '시스템 리스크가 발견된 phase에서만 risk-capture를 실행한다' <<<"$checklist_output"
grep -q 'task-update는 기본 phase loop에서 제외한다' <<<"$checklist_output"
grep -q 'task-implement checklist dry run passed' <<<"$checklist_output"

if "$script" --mode unsupported --dry-run >/dev/null 2>&1; then
  echo "task-implement accepted unsupported mode" >&2
  exit 1
fi

echo "task-implement run tests passed"
