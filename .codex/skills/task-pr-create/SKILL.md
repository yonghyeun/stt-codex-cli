---
name: task-pr-create
description: Push a stt-codex-cli task branch, create or reuse a PR, generate a review-focused PR body, and move the linked issue to review.
---

# Task PR Create

Use when implementation is ready for review and the user asks to create a PR.

This skill creates the review surface only. It must not merge PRs, close issues
directly, delete branches, remove worktrees, or edit
`stt-codex-cli-worktrees.code-workspace`.

PR title and PR body must be written in Korean by default for this repository.
When `--body-file` is not supplied, generate the PR body in Korean. When an open
PR is reused, refresh the PR body in Korean instead of leaving stale generated
text untouched.

By default, the generated PR body uses `Closes #<issue>` so GitHub closes the
issue automatically after merge. Use `--refs-only` when the issue must stay open
after merge.

Always dry-run first:

```bash
.codex/skills/task-pr-create/scripts/run.sh \
  --issue 55 \
  --branch feat/55-task-skill-system-bootstrap \
  --dry-run
```

Mutation requires explicit confirmation:

```bash
.codex/skills/task-pr-create/scripts/run.sh \
  --issue 55 \
  --branch feat/55-task-skill-system-bootstrap \
  --yes
```

PR creation does:

- verify the current branch matches `--branch`
- verify the worktree is clean
- fetch `origin`
- create or reuse an open PR for the branch
- push the branch before creating a PR
- generate a review-focused PR body when `--body-file` is not supplied
- set the issue status label to `status:review`
- post a PR creation receipt comment on the issue

Generated PR bodies include:

- 요약
- 연결 이슈
- 변경 파일 트리
- 변경 파일 맵 with path, change, reason, and risk columns
- 검증
- 리뷰 초점
- 제외 범위
- 후속 작업 / 리스크

Use `task-merge` after review approval.
