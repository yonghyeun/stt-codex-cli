#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
script="$script_dir/run.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

fake_bin="$tmp/bin"
fake_repo="$tmp/repo"
captured_body="$tmp/pr-body.md"
captured_existing_body="$tmp/existing-pr-body.md"
mkdir -p "$fake_bin" "$fake_repo"

cat >"$fake_bin/git" <<EOF
#!/usr/bin/env bash
if [[ "\$1" == "-C" ]]; then
  shift 2
fi
case "\$*" in
  "rev-parse --show-toplevel") printf '%s\n' "$fake_repo" ;;
  "branch --show-current") printf '%s\n' "chore/109-task-pr-create-korean-pr-body" ;;
  "status --short") exit 0 ;;
  "fetch origin") exit 0 ;;
  "rev-parse --verify --quiet chore/109-task-pr-create-korean-pr-body") exit 0 ;;
  "rev-parse --verify --quiet origin/main") exit 0 ;;
  "diff --name-only origin/main..HEAD") printf '%s\n' ".codex/skills/task-pr-create/SKILL.md" ".codex/skills/task-pr-create/scripts/run.sh" ;;
  "diff --stat origin/main..HEAD") printf '%s\n' " 2 files changed, 20 insertions(+), 10 deletions(-)" ;;
  "push -u origin chore/109-task-pr-create-korean-pr-body") exit 0 ;;
  *) echo "unexpected git args: \$*" >&2; exit 1 ;;
esac
EOF
chmod +x "$fake_bin/git"

cat >"$fake_bin/gh" <<EOF
#!/usr/bin/env bash
if [[ "\$1" == "api" && "\$2" == "repos/:owner/:repo/pulls/77" ]]; then
  body_arg=""
  while [[ "\$#" -gt 0 ]]; do
    if [[ "\$1" == "--raw-field" && "\${2:-}" == body=* ]]; then
      body_arg="\${2#body=}"
      break
    fi
    shift
  done
  [[ -n "\$body_arg" ]] || { echo "missing patch body" >&2; exit 1; }
  printf '%s' "\$body_arg" > "$captured_existing_body"
  exit 0
fi
case "\$*" in
  "api repos/:owner/:repo/issues/109 --jq [."*)
    printf '%s\t%s\t%s\n' "109" "open" "chore: task-pr-create PR 본문 한국어 계약 보강"
    ;;
  "pr list --head chore/109-task-pr-create-korean-pr-body --state open --json number,url --jq .[0] // empty")
    if [[ "\${EXISTING_PR:-0}" == "1" ]]; then
      printf '%s\n' '{"number":77,"url":"https://github.com/yonghyeun/stt-codex-cli/pull/77"}'
      exit 0
    fi
    exit 0
    ;;
  pr\ create*)
    body_file=""
    while [[ "\$#" -gt 0 ]]; do
      if [[ "\$1" == "--body-file" ]]; then
        body_file="\$2"
        break
      fi
      shift
    done
    [[ -n "\$body_file" ]] || { echo "missing body file" >&2; exit 1; }
    cp "\$body_file" "$captured_body"
    printf '%s\n' "https://github.com/yonghyeun/stt-codex-cli/pull/110"
    ;;
  "pr view https://github.com/yonghyeun/stt-codex-cli/pull/110 --json number --jq .number")
    printf '%s\n' "110"
    ;;
  "api repos/:owner/:repo/issues/109/labels --jq .[] | select(.name | startswith(\"status:\")) | .name")
    printf '%s\n' "status:intake"
    ;;
  "api repos/:owner/:repo/issues/109/labels/status:intake --method DELETE")
    exit 0
    ;;
  "api repos/:owner/:repo/issues/109/labels --method POST -f labels[]=status:review")
    exit 0
    ;;
  "api repos/:owner/:repo/issues/109/comments --method POST -f body=PR created for review: https://github.com/yonghyeun/stt-codex-cli/pull/110 --jq .html_url")
    printf '%s\n' "https://github.com/yonghyeun/stt-codex-cli/issues/109#issuecomment-test"
    ;;
  *) echo "unexpected gh args: \$*" >&2; exit 1 ;;
esac
EOF
chmod +x "$fake_bin/gh"

PATH="$fake_bin:$PATH" "$script" \
  --issue 109 \
  --branch chore/109-task-pr-create-korean-pr-body \
  --base main \
  --yes |
  grep -q 'task-pr-create complete'

grep -q '^## 요약' "$captured_body"
grep -q '^## 변경 파일 트리' "$captured_body"
grep -q '^## 변경 파일 맵' "$captured_body"
grep -q '^Closes #109' "$captured_body"
if grep -q '^## Summary' "$captured_body"; then
  echo "generated PR body still uses English headings" >&2
  exit 1
fi

EXISTING_PR=1 PATH="$fake_bin:$PATH" "$script" \
  --issue 109 \
  --branch chore/109-task-pr-create-korean-pr-body \
  --base main \
  --yes |
  grep -q 'task-pr-create reused existing PR'

grep -q '^## 요약' "$captured_existing_body"
grep -q '^## 변경 파일 트리' "$captured_existing_body"
if grep -q '^## Summary' "$captured_existing_body"; then
  echo "reused PR body still uses English headings" >&2
  exit 1
fi

echo "task-pr-create run tests passed"
