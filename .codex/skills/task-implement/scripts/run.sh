#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run.sh --mode checklist [--issue <number>] [--dry-run]

Prints the task-implement workflow checklist. This script does not mutate Git,
GitHub, or files.
USAGE
}

mode=""
issue=""
dry_run="0"

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --mode) mode="${2:-}"; shift 2 ;;
    --issue) issue="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$mode" in
  checklist) ;;
  "") echo "--mode is required" >&2; usage >&2; exit 2 ;;
  *) echo "--mode must be checklist" >&2; exit 2 ;;
esac

if [[ -n "$issue" && ! "$issue" =~ ^[0-9]+$ ]]; then
  echo "--issue must be a number" >&2
  exit 2
fi

cat <<EOF
## Task Implement Checklist

Issue: ${issue:+#}${issue:-none}

Workflow:
- task-intake -> phase plan -> phase loop -> final verification -> task-pr-create

Phase loop:
- phase 목표를 확인한다.
- 코드 동작 변경이면 failing test를 먼저 작성한다.
- 가장 작은 bounded change를 구현한다.
- focused verification을 실행한다.
- 시스템 리스크가 발견된 phase에서만 risk-capture를 실행한다.
- 각 atomic phase는 task-commit으로 닫는다.

Risk handling:
- none: 기록 후 계속
- affects-future-slice: 기록 후 계속
- slows-current-slice: 최소 복구 후 계속
- blocks-current-slice: 중단 후 risk-resolution 검토

Comment policy:
- task-update는 기본 phase loop에서 제외한다.
- phase 진행 기록은 task-commit body에 둔다.
- review 추적은 PR body에 둔다.
- 시스템 리스크 기록은 risk inbox의 Risk Capture comment에 둔다.

PR body:
- Phase commit hash와 focused verification을 요약한다.
- final verification 결과를 요약한다.
- captured risk link 또는 none을 명시한다.
EOF

if [[ "$dry_run" == "1" ]]; then
  echo "task-implement checklist dry run passed"
else
  echo "task-implement checklist complete"
fi
