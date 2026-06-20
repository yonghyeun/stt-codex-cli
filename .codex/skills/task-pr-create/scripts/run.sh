#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  run.sh --issue <number> --branch <branch> [--base <branch>] [--title <title>] [--body-file <path>] [--draft] [--refs-only] [--dry-run] [--yes]

Creates or reuses a PR and moves the linked issue to review. Does not merge or clean up local worktrees.
USAGE
}

issue=""
branch=""
base="main"
title=""
body_file=""
draft="0"
refs_only="0"
dry_run="0"
yes="0"

while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --issue) issue="${2:-}"; shift 2 ;;
    --branch) branch="${2:-}"; shift 2 ;;
    --base) base="${2:-}"; shift 2 ;;
    --title) title="${2:-}"; shift 2 ;;
    --body-file) body_file="${2:-}"; shift 2 ;;
    --draft) draft="1"; shift ;;
    --refs-only) refs_only="1"; shift ;;
    --dry-run) dry_run="1"; shift ;;
    --yes) yes="1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$issue" =~ ^[0-9]+$ ]] || { echo "--issue must be a number" >&2; exit 2; }
[[ -n "$branch" ]] || { echo "--branch is required" >&2; exit 2; }
[[ -z "$body_file" || -f "$body_file" ]] || { echo "--body-file must point to an existing file" >&2; exit 2; }

repo_root="$(git rev-parse --show-toplevel)"
current_branch="$(git -C "$repo_root" branch --show-current)"
[[ "$current_branch" == "$branch" ]] || {
  echo "Current branch is $current_branch, expected $branch" >&2
  exit 3
}

status="$(git -C "$repo_root" status --short)"
[[ -z "$status" ]] || {
  echo "pending: worktree is dirty" >&2
  printf '%s\n' "$status" >&2
  exit 3
}

git -C "$repo_root" fetch origin >/dev/null 2>&1 || true
git -C "$repo_root" rev-parse --verify --quiet "$branch" >/dev/null || {
  echo "Branch does not exist: $branch" >&2
  exit 3
}
git -C "$repo_root" rev-parse --verify --quiet "origin/${base}" >/dev/null || {
  echo "Base branch does not exist on origin: $base" >&2
  exit 3
}

issue_payload="$(gh api "repos/:owner/:repo/issues/${issue}" --jq '[.number, .state, .title] | @tsv')"
issue_number="$(cut -f1 <<<"$issue_payload")"
issue_state="$(cut -f2 <<<"$issue_payload")"
issue_title="$(cut -f3- <<<"$issue_payload")"
[[ -n "$title" ]] || title="$issue_title"

link_keyword="Closes"
[[ "$refs_only" != "1" ]] || link_keyword="Refs"
changed_files="$(git -C "$repo_root" diff --name-only "origin/${base}..HEAD")"
diff_stat="$(git -C "$repo_root" diff --stat "origin/${base}..HEAD")"
if [[ -n "$changed_files" ]]; then
  changed_file_tree="$(
    printf '%s\n' "$changed_files" |
      sort |
      awk '
        {
          path = ""
          depth = split($0, parts, "/")
          for (i = 1; i <= depth; i++) {
            key = path "/" parts[i]
            if (!(key in seen)) {
              indent = ""
              for (j = 1; j < i; j++) {
                indent = indent "  "
              }
              suffix = i < depth ? "/" : ""
              print indent parts[i] suffix
              seen[key] = 1
            }
            path = key
          }
        }
      '
  )"
else
  changed_file_tree="_none_"
fi

generated_body=""
tmp_body=""
if [[ -n "$body_file" ]]; then
  generated_body="$body_file"
else
  tmp_body="$(mktemp)"
  generated_body="$tmp_body"
  {
    cat <<EOF
## 요약

- #${issue}의 review-ready slice를 구현한다.
- 아래 변경 파일에 대한 repo-local task lifecycle 동작을 보강한다.
- merge, remote closeout, local cleanup은 별도 lifecycle 단계로 유지한다.

## 연결 이슈

${link_keyword} #${issue}

## 변경 파일 트리

\`\`\`
${changed_file_tree}
\`\`\`

## 변경 파일 맵

| 경로 | 변경 | 이유 | 리스크 |
| --- | --- | --- | --- |
EOF
    if [[ -n "$changed_files" ]]; then
      while IFS= read -r path; do
        [[ -n "$path" ]] || continue
        printf '| `%s` | diff 확인 필요. | #%s 범위 지원. | 계약 drift 또는 누락된 guard 확인 필요. |\n' "$path" "$issue"
      done <<<"$changed_files"
    else
      printf '| _none_ | 파일 변경 없음. | N/A | N/A |\n'
    fi
    cat <<EOF

## 검증

- [ ] review 요청 전 실행한 명령과 결과를 기록한다.

생략:

- 없음.

## 리뷰 초점

- Lifecycle 경계가 올바른지.
- Mutation guard와 dry-run 동작이 유지되는지.
- 재실행/idempotency 동작이 안전한지.

## 제외 범위

- Merge 실행.
- merge 후 GitHub auto-close 외 issue closeout.
- local branch/worktree cleanup.

## 후속 작업 / 리스크

- 생성된 파일 맵 행을 검토하고 필요한 경우 변경, 이유, 리스크를 구체화한다.

## Diff Stat

\`\`\`
${diff_stat}
\`\`\`
EOF
  } >"$generated_body"
fi

existing_pr="$(gh pr list --head "$branch" --state open --json number,url --jq '.[0] // empty')"
if [[ -n "$existing_pr" ]]; then
  existing_url="$(jq -r '.url' <<<"$existing_pr")"
  existing_number="$(jq -r '.number' <<<"$existing_pr")"
  echo "Existing PR: #$existing_number"
  echo "$existing_url"
  echo "Body file: $generated_body"
  if [[ "$dry_run" == "1" ]]; then
    echo "Would update existing PR body with Korean review surface"
    echo "task-pr-create dry run passed"
    [[ -z "$tmp_body" ]] || rm -f "$tmp_body"
    exit 0
  fi
  [[ "$yes" == "1" ]] || {
    [[ -z "$tmp_body" ]] || rm -f "$tmp_body"
    echo "--yes is required for PR reuse mutation" >&2
    exit 2
  }
  gh api "repos/:owner/:repo/pulls/${existing_number}" \
    --method PATCH \
    --raw-field "body=$(<"$generated_body")" >/dev/null
  [[ -z "$tmp_body" ]] || rm -f "$tmp_body"
  echo "task-pr-create reused existing PR"
  exit 0
fi

echo "Issue: #$issue_number"
echo "Issue state: $issue_state"
echo "Branch: $branch"
echo "Base: $base"
echo "Title: $title"
echo "Body file: $generated_body"
echo "Link keyword: $link_keyword"
echo "Draft: $([[ "$draft" == "1" ]] && echo yes || echo no)"
echo "Changed files:"
if [[ -n "$changed_files" ]]; then
  printf '%s\n' "$changed_files" | sed 's/^/- /'
else
  echo "- none"
fi

if [[ "$dry_run" == "1" ]]; then
  echo "Would push branch: $branch"
  echo "Would create PR against: $base"
  echo "Would sync issue #$issue to status:review"
  echo "Would post PR creation receipt"
  echo "task-pr-create dry run passed"
  [[ -z "$tmp_body" ]] || rm -f "$tmp_body"
  exit 0
fi

[[ "$yes" == "1" ]] || {
  [[ -z "$tmp_body" ]] || rm -f "$tmp_body"
  echo "--yes is required for PR creation mutation" >&2
  exit 2
}

git -C "$repo_root" push -u origin "$branch"

create_args=(--base "$base" --head "$branch" --title "$title" --body-file "$generated_body")
[[ "$draft" != "1" ]] || create_args+=(--draft)
pr_url="$(gh pr create "${create_args[@]}")"
pr_number="$(gh pr view "$pr_url" --json number --jq '.number')"

status_labels="$(gh api "repos/:owner/:repo/issues/${issue}/labels" --jq '.[] | select(.name | startswith("status:")) | .name')"
while IFS= read -r label; do
  [[ -n "$label" && "$label" != "status:review" ]] || continue
  gh api "repos/:owner/:repo/issues/${issue}/labels/${label}" --method DELETE >/dev/null || true
done <<<"$status_labels"
gh api "repos/:owner/:repo/issues/${issue}/labels" --method POST -f "labels[]=status:review" >/dev/null

gh api "repos/:owner/:repo/issues/${issue}/comments" \
  --method POST \
  -f "body=PR created for review: ${pr_url}" \
  --jq '.html_url' >/dev/null

[[ -z "$tmp_body" ]] || rm -f "$tmp_body"
echo "$pr_url"
echo "task-pr-create complete"
