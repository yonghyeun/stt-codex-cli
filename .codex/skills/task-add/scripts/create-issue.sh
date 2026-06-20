#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  create-issue.sh --kind <umbrella|leaf|standalone|risk-management|risk-resolution> --title <title> --body-file <path> --label <label>... [options]

Options:
  --parent <#number>              Required for --kind leaf.
  --parent-comment-file <path>    Comment on the parent after creation. Supports {{issue_number}} and {{issue_url}}.
  --dry-run                       Validate inputs and parent state without remote mutation.
  -h, --help                      Show this help.
USAGE
}

die() {
  local code="$1"
  shift
  printf '%s\n' "$*" >&2
  exit "$code"
}

contains() {
  local needle="$1"
  shift
  local item
  for item in "$@"; do
    [[ "$item" == "$needle" ]] && return 0
  done
  return 1
}

normalize_issue_number() {
  local raw="$1"
  raw="${raw#\#}"
  raw="${raw##*/issues/}"
  [[ "$raw" =~ ^[0-9]+$ ]] || die 2 "Invalid parent issue: $1"
  printf '%s\n' "$raw"
}

validate_parent() {
  local parent_issue="$1"
  local state labels
  state="$(gh api "repos/:owner/:repo/issues/${parent_issue}" --jq '.state')" ||
    die 1 "Parent issue #${parent_issue} could not be fetched."
  [[ "$state" == "open" ]] ||
    die 3 "Parent issue #${parent_issue} is not open."
  labels="$(gh api "repos/:owner/:repo/issues/${parent_issue}" --jq '.labels[].name')" ||
    die 1 "Parent issue #${parent_issue} labels could not be fetched."
  grep -qx 'kind:umbrella' <<<"$labels" ||
    die 3 "Parent issue #${parent_issue} is not labeled kind:umbrella."
}

validate_risk_management_singleton() {
  local existing
  existing="$(gh api --method GET repos/:owner/:repo/issues \
    -f state=open \
    -f labels=kind:risk-management \
    --jq '.[] | select(.pull_request | not) | "#\(.number) \(.title)"')" ||
    die 1 "Open risk-management inbox could not be checked."

  [[ -z "$existing" ]] ||
    die 3 "Open risk-management inbox already exists. Reuse it instead of creating another kind:risk-management inbox:
$existing"
}

validate_labels() {
  local kind="$1"
  local title="$2"
  shift 2
  local labels=("$@")
  local allowed_types=(type:feat type:fix type:docs type:test type:chore type:refactor type:design type:infra)
  local allowed_kinds=(kind:umbrella kind:leaf kind:standalone kind:risk-management kind:risk-resolution kind:decision kind:spike)
  local allowed_statuses=(status:idea status:intake status:ready status:in-progress status:blocked status:review status:done)
  local allowed_priorities=(priority:p0 priority:p1 priority:p2 priority:p3)
  local allowed_areas=(area:ops area:docs area:audio area:stt area:cli area:test area:ci area:design)
  local type_count=0 kind_count=0 status_count=0 priority_count=0 area_count=0
  local type_label="" kind_label="" status_label="" label

  [[ "${#labels[@]}" -gt 0 ]] || die 2 "Missing labels."

  for label in "${labels[@]}"; do
    case "$label" in
      type:*) contains "$label" "${allowed_types[@]}" || die 3 "Unsupported type label: $label"; type_count=$((type_count + 1)); type_label="$label" ;;
      kind:*) contains "$label" "${allowed_kinds[@]}" || die 3 "Unsupported kind label: $label"; kind_count=$((kind_count + 1)); kind_label="$label" ;;
      status:*) contains "$label" "${allowed_statuses[@]}" || die 3 "Unsupported status label: $label"; status_count=$((status_count + 1)); status_label="$label" ;;
      priority:*) contains "$label" "${allowed_priorities[@]}" || die 3 "Unsupported priority label: $label"; priority_count=$((priority_count + 1)) ;;
      area:*) contains "$label" "${allowed_areas[@]}" || die 3 "Unsupported area label: $label"; area_count=$((area_count + 1)) ;;
      *) die 3 "Unsupported label: $label" ;;
    esac
  done

  [[ "$type_count" -eq 1 ]] || die 3 "Expected exactly one type:* label."
  [[ "$kind_count" -eq 1 ]] || die 3 "Expected exactly one kind:* label."
  [[ "$status_count" -eq 1 ]] || die 3 "Expected exactly one status:* label."
  [[ "$priority_count" -eq 1 ]] || die 3 "Expected exactly one priority:* label."
  [[ "$area_count" -ge 1 ]] || die 3 "Expected at least one area:* label."
  [[ "$kind_label" == "kind:${kind}" ]] || die 3 "Kind label $kind_label does not match --kind $kind."
  [[ "$status_label" == "status:intake" ]] || die 3 "New issues must start with status:intake."
  [[ "$title" =~ ^[a-z]+: ]] || die 3 "Issue title must use '<type>: <summary>'."

  local title_type="${title%%:*}"
  [[ "$type_label" == "type:${title_type}" ]] ||
    die 3 "Type label $type_label does not match title prefix $title_type."
}

validate_body_language() {
  local body_file="$1"

  grep -Pq '\p{Hangul}' "$body_file" ||
    die 3 "Issue body must include Korean prose. Keep contract headings in English if needed, but do not create a fully English body."
}

kind=""
title=""
body_file=""
parent=""
parent_comment_file=""
dry_run="0"
labels=()

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --kind) kind="${2:-}"; shift 2 ;;
    --title) title="${2:-}"; shift 2 ;;
    --body-file) body_file="${2:-}"; shift 2 ;;
    --label) labels+=("${2:-}"); shift 2 ;;
    --parent) parent="$(normalize_issue_number "${2:-}")"; shift 2 ;;
    --parent-comment-file) parent_comment_file="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die 2 "Unknown argument: $1" ;;
  esac
done

case "$kind" in
  umbrella|leaf|standalone|risk-management|risk-resolution) ;;
  "") die 2 "Missing --kind." ;;
  *) die 2 "Unsupported --kind: $kind." ;;
esac

[[ -n "$title" ]] || die 2 "Missing --title."
[[ -n "$body_file" ]] || die 2 "Missing --body-file."
[[ -f "$body_file" ]] || die 2 "Issue body file not found: $body_file."
[[ -z "$parent_comment_file" || -f "$parent_comment_file" ]] || die 2 "Parent comment file not found: $parent_comment_file."

if [[ "$kind" == "leaf" ]]; then
  [[ -n "$parent" ]] || die 2 "Missing --parent for leaf issue."
else
  [[ -z "$parent" ]] || die 2 "--parent is only valid for leaf issues."
  [[ -z "$parent_comment_file" ]] || die 2 "--parent-comment-file requires --kind leaf."
fi

validate_labels "$kind" "$title" "${labels[@]}"
validate_body_language "$body_file"
[[ "$kind" != "leaf" ]] || validate_parent "$parent"
[[ "$kind" != "risk-management" ]] || validate_risk_management_singleton

if [[ "$dry_run" == "1" ]]; then
  printf 'task-add dry run passed\n'
  printf 'kind: %s\n' "$kind"
  printf 'title: %s\n' "$title"
  printf 'body-file: %s\n' "$body_file"
  printf 'labels:\n'
  printf -- '- %s\n' "${labels[@]}"
  [[ -z "$parent" ]] || printf 'parent: #%s\n' "$parent"
  exit 0
fi

command -v jq >/dev/null 2>&1 || die 1 "jq is required for REST payload construction."

payload="$(mktemp)"
cleanup() {
  rm -f "$payload" "${rendered_comment:-}"
}
trap cleanup EXIT

printf '%s\n' "${labels[@]}" | jq -R . | jq -s --arg title "$title" --rawfile body "$body_file" \
  '{title: $title, body: $body, labels: .}' >"$payload"

issue_url="$(gh api repos/:owner/:repo/issues --method POST --input "$payload" --jq '.html_url')" ||
  die 1 "GitHub issue creation failed."
issue_number="${issue_url##*/}"
[[ "$issue_number" =~ ^[0-9]+$ ]] || die 1 "Created issue number could not be parsed from $issue_url."

if [[ "$kind" == "leaf" ]]; then
  issue_id="$(gh api "repos/:owner/:repo/issues/${issue_number}" --jq '.id')" ||
    die 1 "Created issue id could not be fetched."
  gh api "repos/:owner/:repo/issues/${parent}/sub_issues" --method POST -F "sub_issue_id=${issue_id}" >/dev/null ||
    die 1 "Sub-issue registration failed."

  if [[ -n "$parent_comment_file" ]]; then
    rendered_comment="$(mktemp)"
    sed -e "s|{{issue_number}}|${issue_number}|g" -e "s|{{issue_url}}|${issue_url}|g" "$parent_comment_file" >"$rendered_comment"
    gh api "repos/:owner/:repo/issues/${parent}/comments" --method POST -f "body=$(<"$rendered_comment")" >/dev/null ||
      die 1 "Parent comment creation failed."
  fi
fi

printf 'Created issue: %s\n' "$issue_url"
[[ "$kind" != "leaf" ]] || printf 'Registered sub-issue: #%s -> #%s\n' "$issue_number" "$parent"
