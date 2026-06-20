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

PATH="$fake_bin:$PATH" "$script" \
  --risk-issue 77 \
  --source-slice 65 \
  --type bottleneck \
  --severity medium \
  --impact slows-current-slice \
  --handling defer \
  --observation "found risk" \
  --evidence "test evidence" \
  --dry-run |
  grep -q 'risk-capture dry run passed'

echo "risk-capture run tests passed"
