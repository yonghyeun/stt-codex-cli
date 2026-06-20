#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
script="$script_dir/run.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

fake_bin="$tmp/bin"
mkdir -p "$fake_bin"
cat >"$fake_bin/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == *"/comments"* ]]; then
  cat <<'JSON'
{"url":"https://example.test/risk/1","body":"## Risk Capture\n\nSource slice: #65\nRisk inbox: #77\nDate: 2026-06-11\nType: bottleneck\nSeverity: high\nStatus: captured\n\n### Observation\n\n- found\n\n### Evidence\n\n- evidence\n\n### Slice Impact\n\n- affects-future-slice\n\n### Proposed Handling\n\n- create-resolution-issue"}
JSON
  exit 0
fi
printf '%s\n' "kind:risk-management"
EOF
chmod +x "$fake_bin/gh"

output="$(PATH="$fake_bin:$PATH" "$script" --risk-issue 77)"
grep -q 'Captured risk count: 1' <<<"$output"

echo "risk-intake run tests passed"
