#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
script="$script_dir/run.sh"

"$script" --help | grep -q 'Usage:'

dry_run_output="$("$script" \
  --type chore \
  --subject "작업 단위 커밋 스킬 추가" \
  --intent "커밋 단위의 판단 근거를 body에 남기기 위함" \
  --scope ".codex/skills/task-commit" \
  --change "topic commit 메시지 생성 스킬을 추가" \
  --approach "정책 reference를 실행형 wrapper로 감싸고 dry-run을 제공" \
  --verification "run.test.sh dry-run 경로 확인" \
  --risk "기존 커밋에는 소급 적용하지 않음" \
  --follow-up "없음" \
  --dry-run)"

grep -q '^chore: 작업 단위 커밋 스킬 추가$' <<<"$dry_run_output"
grep -q '^의도:$' <<<"$dry_run_output"
grep -q '^범위:$' <<<"$dry_run_output"
grep -q '^변경:$' <<<"$dry_run_output"
grep -q '^방식:$' <<<"$dry_run_output"
grep -q '^검증:$' <<<"$dry_run_output"
grep -q '^리스크:$' <<<"$dry_run_output"
grep -q '^후속:$' <<<"$dry_run_output"
grep -q 'task-commit dry run passed' <<<"$dry_run_output"

if "$script" \
  --type chore \
  --subject "작업 단위 커밋 스킬 추가" \
  --intent "커밋 단위의 판단 근거를 body에 남기기 위함" \
  --scope ".codex/skills/task-commit" \
  --change "topic commit 메시지 생성 스킬을 추가" \
  --approach "정책 reference를 실행형 wrapper로 감싸고 dry-run을 제공" \
  --verification "run.test.sh mutation guard 확인" \
  --risk "기존 커밋에는 소급 적용하지 않음" \
  --follow-up "없음" >/dev/null 2>&1; then
  echo "task-commit mutation without --yes unexpectedly passed" >&2
  exit 1
fi

if "$script" \
  --type chore \
  --subject "english subject" \
  --intent "한국어 본문" \
  --scope ".codex/skills/task-commit" \
  --change "변경" \
  --approach "방식" \
  --verification "검증" \
  --risk "리스크" \
  --follow-up "없음" \
  --dry-run >/dev/null 2>&1; then
  echo "task-commit accepted non-Korean subject" >&2
  exit 1
fi

echo "task-commit run tests passed"
