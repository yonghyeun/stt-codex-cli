#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run.sh --mode issue-body --risk-issue <number> --captured-risk <text> --selection-criteria <text> --resolution-plan <text> --propagation-target <text> [--output <path>]
  run.sh --mode start --risk-issue <number> --resolution-issue <number> --captured-risk <text> --resolution-plan <text> [--dry-run] [--yes]
  run.sh --mode closeout --risk-issue <number> --resolution-issue <number> --resolved <text> --verification <text> [--remaining-risk <text>] [--dry-run] [--yes]
  run.sh --mode propagate --umbrella <number> --resolution-issue <number> --summary <text> --decision <text> [--remaining-risk <text>] [--dry-run] [--yes]

Prepares or records risk-resolution lifecycle transitions. Issue creation remains task-add responsibility.
USAGE
}

mode=""
risk_issue=""
resolution_issue=""
umbrella=""
captured_risk=""
selection_criteria=""
resolution_plan=""
propagation_target=""
resolved=""
verification=""
remaining_risk=""
summary=""
decision=""
output=""
dry_run="0"
yes="0"

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --mode) mode="${2:-}"; shift 2 ;;
    --risk-issue) risk_issue="${2:-}"; shift 2 ;;
    --resolution-issue) resolution_issue="${2:-}"; shift 2 ;;
    --umbrella) umbrella="${2:-}"; shift 2 ;;
    --captured-risk) captured_risk="${2:-}"; shift 2 ;;
    --selection-criteria) selection_criteria="${2:-}"; shift 2 ;;
    --resolution-plan) resolution_plan="${2:-}"; shift 2 ;;
    --propagation-target) propagation_target="${2:-}"; shift 2 ;;
    --resolved) resolved="${2:-}"; shift 2 ;;
    --verification) verification="${2:-}"; shift 2 ;;
    --remaining-risk) remaining_risk="${2:-}"; shift 2 ;;
    --summary) summary="${2:-}"; shift 2 ;;
    --decision) decision="${2:-}"; shift 2 ;;
    --output) output="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
    --yes) yes="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

case "$mode" in
  issue-body|start|closeout|propagate) ;;
  *) echo "--mode must be one of issue-body, start, closeout, propagate" >&2; exit 2 ;;
esac

validate_risk_issue() {
  local issue="$1"
  [[ "$issue" =~ ^[0-9]+$ ]] || { echo "--risk-issue must be a number" >&2; exit 2; }
  local labels
  labels="$(gh api "repos/:owner/:repo/issues/${issue}" --jq '.labels[].name')" ||
    { echo "risk inbox could not be fetched: #${issue}" >&2; exit 1; }
  grep -qx 'kind:risk-management' <<<"$labels" ||
    { echo "risk inbox #${issue} must be labeled kind:risk-management" >&2; exit 3; }
}

post_comment() {
  local issue="$1"
  local body_file="$2"
  if [[ "$dry_run" == "1" ]]; then
    echo "Would post comment to #${issue}"
    echo "Body file: ${body_file}"
    return 0
  fi
  [[ "$yes" == "1" ]] || { echo "--yes is required for risk-resolution mutation" >&2; exit 2; }
  gh api "repos/:owner/:repo/issues/${issue}/comments" \
    --method POST \
    -f "body=$(<"$body_file")" \
    --jq '.html_url'
}

write_or_print() {
  local body_file="$1"
  if [[ -n "$output" ]]; then
    cp "$body_file" "$output"
    echo "Wrote: $output"
  else
    cat "$body_file"
  fi
}

tmp_body="$(mktemp)"
cleanup() {
  rm -f "$tmp_body"
}
trap cleanup EXIT

case "$mode" in
  issue-body)
    validate_risk_issue "$risk_issue"
    [[ -n "$captured_risk" ]] || { echo "--captured-risk is required" >&2; exit 2; }
    [[ -n "$selection_criteria" ]] || { echo "--selection-criteria is required" >&2; exit 2; }
    [[ -n "$resolution_plan" ]] || { echo "--resolution-plan is required" >&2; exit 2; }
    [[ -n "$propagation_target" ]] || { echo "--propagation-target is required" >&2; exit 2; }
    cat >"$tmp_body" <<EOF
## Context

- Selected from risk management inbox issue #${risk_issue}.

## Captured Risks

- ${captured_risk}

## Selection Criteria

- ${selection_criteria}

## Resolution Plan

- ${resolution_plan}

## Propagation Target

- ${propagation_target}

## Scope

- 선택된 risk를 위 resolution plan 범위 안에서 해결한다.

## Non-Scope

- 선택되지 않은 risk 정리 없음.
- 관련 없는 STT wrapper 동작 변경 없음.
- 기존 issue 본문 일괄 migration 없음.

## Acceptance Criteria

- [ ] 선택된 risk가 issue-backed 작업으로 해결된다.
- [ ] 검증 근거가 기록된다.
- [ ] risk management issue에 closeout comment가 남는다.

## Completion Signal

- 선택된 risk가 해결되거나, 남은 follow-up과 함께 명시적으로 종료된다.
EOF
    write_or_print "$tmp_body"
    ;;
  start)
    validate_risk_issue "$risk_issue"
    [[ "$resolution_issue" =~ ^[0-9]+$ ]] || { echo "--resolution-issue must be a number" >&2; exit 2; }
    [[ -n "$captured_risk" ]] || { echo "--captured-risk is required" >&2; exit 2; }
    [[ -n "$resolution_plan" ]] || { echo "--resolution-plan is required" >&2; exit 2; }
    cat >"$tmp_body" <<EOF
## Risk Resolution Start

Risk inbox: #${risk_issue}
Resolution issue: #${resolution_issue}
Date: $(date +%F)
Status: resolution-started

### Selected Risks

- ${captured_risk}

### Resolution Plan

- ${resolution_plan}
EOF
    post_comment "$risk_issue" "$tmp_body"
    [[ "$dry_run" != "1" ]] || echo "risk-resolution start dry run passed"
    ;;
  closeout)
    validate_risk_issue "$risk_issue"
    [[ "$resolution_issue" =~ ^[0-9]+$ ]] || { echo "--resolution-issue must be a number" >&2; exit 2; }
    [[ -n "$resolved" ]] || { echo "--resolved is required" >&2; exit 2; }
    [[ -n "$verification" ]] || { echo "--verification is required" >&2; exit 2; }
    cat >"$tmp_body" <<EOF
## Risk Resolution Closeout

Risk inbox: #${risk_issue}
Resolution issue: #${resolution_issue}
Date: $(date +%F)
Status: resolved

### Resolved

- ${resolved}

### Verification

- ${verification}

### Remaining Risk

- ${remaining_risk:-none}
EOF
    post_comment "$risk_issue" "$tmp_body"
    [[ "$dry_run" != "1" ]] || echo "risk-resolution closeout dry run passed"
    ;;
  propagate)
    [[ "$umbrella" =~ ^[0-9]+$ ]] || { echo "--umbrella must be a number" >&2; exit 2; }
    [[ "$resolution_issue" =~ ^[0-9]+$ ]] || { echo "--resolution-issue must be a number" >&2; exit 2; }
    [[ -n "$summary" ]] || { echo "--summary is required" >&2; exit 2; }
    [[ -n "$decision" ]] || { echo "--decision is required" >&2; exit 2; }
    cat >"$tmp_body" <<EOF
## Task Update

Type: risk-update
Source issue: #${resolution_issue}
Related umbrella: #${umbrella}
Date: $(date +%F)

### What Changed

- ${summary}

### Current Decision

- ${decision}

### Risk / Follow-up

- ${remaining_risk:-none}
EOF
    post_comment "$umbrella" "$tmp_body"
    [[ "$dry_run" != "1" ]] || echo "risk-resolution propagation dry run passed"
    ;;
esac
