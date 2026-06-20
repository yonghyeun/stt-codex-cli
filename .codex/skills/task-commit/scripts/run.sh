#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run.sh --type <type> --subject <korean subject> --intent <text> --scope <text> --change <text> --approach <text> --verification <text> --risk <text> --follow-up <text> [--dry-run] [--yes]

Creates one Korean topic commit message from the repo commit convention. Dry-run prints the message without mutating Git. --yes commits staged changes with git commit -F.
USAGE
}

die() {
  local code="$1"
  shift
  printf '%s\n' "$*" >&2
  exit "$code"
}

has_hangul() {
  grep -Pq '\p{Hangul}' <<<"$1"
}

type=""
subject=""
intent=""
scope=""
change=""
approach=""
verification=""
risk=""
follow_up=""
dry_run="0"
yes="0"

allowed_types=(feat fix docs test chore refactor design infra)

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --type) type="${2:-}"; shift 2 ;;
    --subject) subject="${2:-}"; shift 2 ;;
    --intent) intent="${2:-}"; shift 2 ;;
    --scope) scope="${2:-}"; shift 2 ;;
    --change) change="${2:-}"; shift 2 ;;
    --approach) approach="${2:-}"; shift 2 ;;
    --verification) verification="${2:-}"; shift 2 ;;
    --risk) risk="${2:-}"; shift 2 ;;
    --follow-up) follow_up="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
    --yes) yes="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$type" ]] || die 2 "--type is required"
valid_type="0"
for allowed in "${allowed_types[@]}"; do
  if [[ "$type" == "$allowed" ]]; then
    valid_type="1"
    break
  fi
done
[[ "$valid_type" == "1" ]] || die 2 "--type must be one of: ${allowed_types[*]}"

[[ -n "$subject" ]] || die 2 "--subject is required"
[[ -n "$intent" ]] || die 2 "--intent is required"
[[ -n "$scope" ]] || die 2 "--scope is required"
[[ -n "$change" ]] || die 2 "--change is required"
[[ -n "$approach" ]] || die 2 "--approach is required"
[[ -n "$verification" ]] || die 2 "--verification is required"
[[ -n "$risk" ]] || die 2 "--risk is required"
[[ -n "$follow_up" ]] || die 2 "--follow-up is required"

has_hangul "$subject" || die 3 "--subject must include Korean prose"
combined_body="${intent}
${scope}
${change}
${approach}
${verification}
${risk}
${follow_up}"
has_hangul "$combined_body" || die 3 "commit body fields must include Korean prose"

message_file="$(mktemp)"
cleanup() {
  rm -f "$message_file"
}
trap cleanup EXIT

{
  printf '%s: %s\n\n' "$type" "$subject"
  printf '의도:\n- %s\n\n' "$intent"
  printf '범위:\n- %s\n\n' "$scope"
  printf '변경:\n- %s\n\n' "$change"
  printf '방식:\n- %s\n\n' "$approach"
  printf '검증:\n- %s\n\n' "$verification"
  printf '리스크:\n- %s\n\n' "$risk"
  printf '후속:\n- %s\n' "$follow_up"
} >"$message_file"

if [[ "$dry_run" == "1" ]]; then
  echo "Commit message:"
  sed -n '1,200p' "$message_file"
  echo "task-commit dry run passed"
  exit 0
fi

[[ "$yes" == "1" ]] || die 2 "--yes is required for git commit mutation"

if git diff --cached --quiet; then
  die 3 "No staged changes to commit"
fi

git commit -F "$message_file"
echo "task-commit complete"
