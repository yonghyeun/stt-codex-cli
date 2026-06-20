#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run.sh --risk-issue <number> --body-file <path> [--dry-run] [--yes]
  run.sh --risk-issue <number> --source-slice <number> --type <type> --severity <severity> --impact <impact> --handling <handling> --observation <text> --evidence <text> [--notes <text>] [--dry-run] [--yes]

Posts a Risk Capture comment to the kind:risk-management inbox issue.
USAGE
}

risk_issue=""
source_slice=""
risk_type=""
severity=""
impact=""
handling=""
observation=""
evidence=""
notes=""
body_file=""
dry_run="0"
yes="0"

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --risk-issue) risk_issue="${2:-}"; shift 2 ;;
    --source-slice) source_slice="${2:-}"; shift 2 ;;
    --type) risk_type="${2:-}"; shift 2 ;;
    --severity) severity="${2:-}"; shift 2 ;;
    --impact) impact="${2:-}"; shift 2 ;;
    --handling) handling="${2:-}"; shift 2 ;;
    --observation) observation="${2:-}"; shift 2 ;;
    --evidence) evidence="${2:-}"; shift 2 ;;
    --notes) notes="${2:-}"; shift 2 ;;
    --body-file) body_file="${2:-}"; shift 2 ;;
    --dry-run) dry_run="1"; shift ;;
    --yes) yes="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$risk_issue" =~ ^[0-9]+$ ]] || { echo "--risk-issue must be a number" >&2; exit 2; }
[[ -z "$body_file" || -f "$body_file" ]] || { echo "--body-file must point to an existing file" >&2; exit 2; }

labels="$(gh api "repos/:owner/:repo/issues/${risk_issue}" --jq '.labels[].name')" ||
  { echo "risk inbox could not be fetched: #${risk_issue}" >&2; exit 1; }
grep -qx 'kind:risk-management' <<<"$labels" ||
  { echo "risk inbox #${risk_issue} must be labeled kind:risk-management" >&2; exit 3; }

tmp_body=""
cleanup() {
  [[ -z "$tmp_body" ]] || rm -f "$tmp_body"
}
trap cleanup EXIT

if [[ -z "$body_file" ]]; then
  [[ "$source_slice" =~ ^[0-9]+$ ]] || { echo "--source-slice must be a number" >&2; exit 2; }
  [[ -n "$risk_type" ]] || { echo "--type is required" >&2; exit 2; }
  [[ -n "$severity" ]] || { echo "--severity is required" >&2; exit 2; }
  [[ -n "$impact" ]] || { echo "--impact is required" >&2; exit 2; }
  [[ -n "$handling" ]] || { echo "--handling is required" >&2; exit 2; }
  [[ -n "$observation" ]] || { echo "--observation is required" >&2; exit 2; }
  [[ -n "$evidence" ]] || { echo "--evidence is required" >&2; exit 2; }
  tmp_body="$(mktemp)"
  body_file="$tmp_body"
  {
    cat <<EOF
## Risk Capture

Source slice: #${source_slice}
Risk inbox: #${risk_issue}
Date: $(date +%F)
Type: ${risk_type}
Severity: ${severity}
Status: captured

### Observation

- ${observation}

### Evidence

- ${evidence}

### Slice Impact

- ${impact}

### Proposed Handling

- ${handling}

### Notes

- ${notes:-none}
EOF
  } >"$body_file"
fi

grep -q '^## Risk Capture' "$body_file" || { echo "risk comment must start with ## Risk Capture" >&2; exit 3; }

echo "Risk inbox: #$risk_issue"
echo "Body file: $body_file"

if [[ "$dry_run" == "1" ]]; then
  echo "Would post Risk Capture comment"
  echo "risk-capture dry run passed"
  exit 0
fi

[[ "$yes" == "1" ]] || { echo "--yes is required for risk-capture mutation" >&2; exit 2; }

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
"$script_dir/comment.sh" --issue "$risk_issue" --body-file "$body_file"
