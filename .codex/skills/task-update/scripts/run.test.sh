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
printf '%s\n' "55"
EOF
chmod +x "$fake_bin/gh"

body="$tmp/comment.md"
printf '%s\n' "## Task Update" "" "- test" >"$body"

"$script" --help | grep -q 'Usage:'

PATH="$fake_bin:$PATH" "$script" --issue 55 --body-file "$body" --dry-run |
  grep -q 'task-update dry run passed'

if PATH="$fake_bin:$PATH" "$script" --issue 55 --body-file "$body" >/dev/null 2>&1; then
  echo "task-update mutation without --yes unexpectedly passed" >&2
  exit 1
fi

echo "task-update run tests passed"
