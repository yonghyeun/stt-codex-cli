#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
script="$script_dir/run.sh"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

fake_bin="$tmp/bin"
body_file="$tmp/closeout.md"
captured_merge="$tmp/merge-args.txt"
captured_landing_body="$tmp/landing-body.md"
dry_run_output="$tmp/dry-run-output.txt"
merge_output="$tmp/merge-output.txt"
mkdir -p "$fake_bin"

cat >"$body_file" <<'EOF'
## 완료

- PR/landing commit 규약을 반영했다.
EOF

cat >"$fake_bin/gh" <<EOF
#!/usr/bin/env bash
if [[ "\$1" == "api" && "\$2" == "repos/:owner/:repo/pulls/130" ]]; then
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "130" "open" "false" "abc123" "feat/129-pr-landing-commit-convention" "chore: PR commit convention 계약 정리"
  exit 0
fi

case "\$*" in
  "pr checks 130 --required")
    exit 0
    ;;
  pr\ merge\ 130*)
    printf '%s\n' "\$*" > "$captured_merge"
    body_file_arg=""
    while [[ "\$#" -gt 0 ]]; do
      if [[ "\$1" == "--body-file" ]]; then
        body_file_arg="\$2"
        break
      fi
      shift
    done
    [[ -n "\$body_file_arg" ]] || { echo "missing landing body file" >&2; exit 1; }
    cp "\$body_file_arg" "$captured_landing_body"
    exit 0
    ;;
  "api repos/:owner/:repo/issues/129 --jq [."*)
    printf '%s\t%s\t%s\n' "129" "open" "chore: PR commit convention 계약 정리"
    ;;
  "api repos/:owner/:repo/issues/129/labels --jq .[] | select(.name | startswith(\"status:\")) | .name")
    printf '%s\n' "status:review"
    ;;
  "api repos/:owner/:repo/issues/129/comments --method POST -f body=## 완료"*)
    printf '%s\n' "https://github.com/yonghyeun/stt-codex-cli/issues/129#issuecomment-test"
    ;;
  "api repos/:owner/:repo/issues/129/labels/status:review --method DELETE")
    exit 0
    ;;
  "api repos/:owner/:repo/issues/129/labels --method POST -f labels[]=status:done")
    exit 0
    ;;
  "api repos/:owner/:repo/issues/129 --method PATCH -f state=closed -f state_reason=completed --jq .html_url")
    printf '%s\n' "https://github.com/yonghyeun/stt-codex-cli/issues/129"
    ;;
  *) echo "unexpected gh args: \$*" >&2; exit 1 ;;
esac
EOF
chmod +x "$fake_bin/gh"

"$script" --help | grep -q 'Usage:'

PATH="$fake_bin:$PATH" "$script" \
  --pr 130 \
  --issue 129 \
  --branch feat/129-pr-landing-commit-convention \
  --body-file "$body_file" \
  --dry-run >"$dry_run_output"
grep -q 'Landing subject: land(chore): PR commit convention 계약 정리 (#130)' "$dry_run_output"

PATH="$fake_bin:$PATH" "$script" \
  --pr 130 \
  --issue 129 \
  --branch feat/129-pr-landing-commit-convention \
  --body-file "$body_file" \
  --skip-local \
  --yes >"$merge_output"
grep -q 'task-merge complete' "$merge_output"

grep -q -- '--subject land(chore): PR commit convention 계약 정리 (#130)' "$captured_merge"
grep -q '^Closes #129$' "$captured_landing_body"
grep -q '^PR #130$' "$captured_landing_body"
grep -q '^## 완료$' "$captured_landing_body"

echo "task-merge run tests passed"
