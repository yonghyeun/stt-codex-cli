#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run.sh --risk-issue <number>

Reads Risk Capture comments from the kind:risk-management inbox issue and prints a non-mutating intake summary.
USAGE
}

risk_issue=""
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --risk-issue) risk_issue="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$risk_issue" =~ ^[0-9]+$ ]] || { echo "--risk-issue must be a number" >&2; exit 2; }

labels="$(gh api "repos/:owner/:repo/issues/${risk_issue}" --jq '.labels[].name')" ||
  { echo "risk inbox could not be fetched: #${risk_issue}" >&2; exit 1; }
grep -qx 'kind:risk-management' <<<"$labels" ||
  { echo "risk inbox #${risk_issue} must be labeled kind:risk-management" >&2; exit 3; }

comments="$(gh api "repos/:owner/:repo/issues/${risk_issue}/comments" --paginate \
  --jq '.[] | select(.body | startswith("## Risk Capture")) | {url: .html_url, body: .body}')" || exit 1

echo "## Risk Intake Summary"
echo
echo "Risk inbox: #${risk_issue}"
echo "Generated: $(date +%F)"
echo

if [[ -z "$comments" ]]; then
  echo "No captured risks."
  exit 0
fi

count="$(printf '%s\n' "$comments" | jq -s 'length')"
echo "Captured risk count: ${count}"
echo
echo "| Source | Type | Severity | Status | Impact | Handling | URL |"
echo "| --- | --- | --- | --- | --- | --- | --- |"
printf '%s\n' "$comments" | while IFS= read -r item; do
  [[ -n "$item" ]] || continue
  body="$(jq -r '.body' <<<"$item")"
  url="$(jq -r '.url' <<<"$item")"
  source="$(awk -F': ' '/^Source slice:/ {print $2; exit}' <<<"$body")"
  type="$(awk -F': ' '/^Type:/ {print $2; exit}' <<<"$body")"
  severity="$(awk -F': ' '/^Severity:/ {print $2; exit}' <<<"$body")"
  status="$(awk -F': ' '/^Status:/ {print $2; exit}' <<<"$body")"
  impact="$(awk '/^### Slice Impact/ {getline; getline; sub(/^- /, ""); print; exit}' <<<"$body")"
  handling="$(awk '/^### Proposed Handling/ {getline; getline; sub(/^- /, ""); print; exit}' <<<"$body")"
  printf '| %s | %s | %s | %s | %s | %s | %s |\n' \
    "${source:-unknown}" "${type:-unknown}" "${severity:-unknown}" "${status:-unknown}" \
    "${impact:-unknown}" "${handling:-unknown}" "$url"
done

echo
echo "Selection guidance:"
echo "- Select blocking, high severity, duplicate, multi-leaf, contract, architecture, or verification-surface risks."
echo "- Use risk-resolution to prepare a kind:risk-resolution issue body for selected risks."
