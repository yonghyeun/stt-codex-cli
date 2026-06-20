#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
script="$script_dir/comment.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

body="$tmp/comment.md"
printf '## Task Update\n\n- test\n' >"$body"
fake_bin="$tmp/bin"
mkdir -p "$fake_bin"
cat >"$fake_bin/gh" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == *"/comments"* ]]; then
  echo "unexpected mutation in dry-run" >&2
  exit 1
fi
echo "55"
EOF
chmod +x "$fake_bin/gh"

PATH="$fake_bin:$PATH" "$script" --issue 55 --body-file "$body" --dry-run | grep -q 'task-update dry run passed'
echo "comment tests passed"
