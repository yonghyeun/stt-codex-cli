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
  echo "unexpected mutation in dry-run" >&2
  exit 1
fi
printf '%s\n' "kind:risk-management"
EOF
chmod +x "$fake_bin/gh"

body="$tmp/risk-resolution-body.md"
PATH="$fake_bin:$PATH" "$script" \
  --mode issue-body \
  --risk-issue 77 \
  --captured-risk "https://example.test/risk/1" \
  --selection-criteria "high severity" \
  --resolution-plan "resolve the gap" \
  --propagation-target "none" \
  --output "$body" |
  grep -q "Wrote: $body"

grep -q '^## Captured Risks' "$body"
grep -q '선택된 risk' "$body"

PATH="$fake_bin:$PATH" "$script" \
  --mode start \
  --risk-issue 77 \
  --resolution-issue 88 \
  --captured-risk "https://example.test/risk/1" \
  --resolution-plan "resolve the gap" \
  --dry-run |
  grep -q 'risk-resolution start dry run passed'

PATH="$fake_bin:$PATH" "$script" \
  --mode closeout \
  --risk-issue 77 \
  --resolution-issue 88 \
  --resolved "resolved the gap" \
  --verification "test evidence" \
  --dry-run |
  grep -q 'risk-resolution closeout dry run passed'

echo "risk-resolution run tests passed"
