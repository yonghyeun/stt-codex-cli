#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
script="$script_dir/create-issue.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

mock_bin="$tmp/bin"
mkdir -p "$mock_bin"
cat >"$mock_bin/gh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != "api" ]]; then
  echo "unexpected gh command" >&2
  exit 1
fi

if [[ "${MOCK_OPEN_RISK_MANAGEMENT:-0}" == "1" ]]; then
  printf '%s\n' '#78 chore: repo risk inbox'
fi
EOF
chmod +x "$mock_bin/gh"
export PATH="$mock_bin:$PATH"

body="$tmp/body.md"
cat >"$body" <<'EOF'
## Context

테스트 본문
EOF

english_body="$tmp/english-body.md"
cat >"$english_body" <<'EOF'
## Context

English only body
EOF

"$script" --kind standalone --title "chore: test issue" --body-file "$body" \
  --label type:chore --label kind:standalone --label status:intake --label priority:p2 --label area:ops --dry-run |
  grep -q 'task-add dry run passed'

"$script" --kind risk-management --title "chore: risk inbox" --body-file "$body" \
  --label type:chore --label kind:risk-management --label status:intake --label priority:p2 --label area:ops --dry-run |
  grep -q 'kind: risk-management'

if MOCK_OPEN_RISK_MANAGEMENT=1 "$script" --kind risk-management --title "chore: risk inbox" --body-file "$body" \
  --label type:chore --label kind:risk-management --label status:intake --label priority:p2 --label area:ops --dry-run >/dev/null 2>&1; then
  echo "expected duplicate risk-management inbox to fail" >&2
  exit 1
fi

if "$script" --kind standalone --title "feat: mismatch" --body-file "$body" \
  --label type:chore --label kind:standalone --label status:intake --label priority:p2 --label area:ops --dry-run >/dev/null 2>&1; then
  echo "expected title/type mismatch to fail" >&2
  exit 1
fi

if "$script" --kind standalone --title "chore: english body" --body-file "$english_body" \
  --label type:chore --label kind:standalone --label status:intake --label priority:p2 --label area:ops --dry-run >/dev/null 2>&1; then
  echo "expected English-only issue body to fail" >&2
  exit 1
fi

echo "create-issue tests passed"
