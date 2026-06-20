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
cat <<'JSON'
[60,"open","chore: repo-local skill run.sh entrypoints","## Scope\n\n- scoped\n\n## Non-Scope\n\n- excluded\n\n## Acceptance Criteria\n\n- [ ] checked\n\n## Completion Signal\n\n- complete"]
JSON
EOF
cat >"$fake_bin/git" <<'EOF'
#!/usr/bin/env bash
if [[ "$*" == "rev-parse --show-toplevel" ]]; then
  pwd
  exit 0
fi
command git "$@"
EOF
chmod +x "$fake_bin/gh" "$fake_bin/git"

"$script" --help | grep -q 'Usage:'

PATH="$fake_bin:$PATH" "$script" --issue 60 --dry-run |
  grep -q 'task-intake dry run passed'

if PATH="$fake_bin:$PATH" "$script" --issue 60 >/dev/null 2>&1; then
  echo "task-intake mutation without --yes unexpectedly passed" >&2
  exit 1
fi

echo "task-intake run tests passed"
