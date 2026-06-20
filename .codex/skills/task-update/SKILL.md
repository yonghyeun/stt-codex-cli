---
name: task-update
description: Post structured update comments to existing stt-codex-cli issues through REST gh api, with optional umbrella propagation when downstream leaves need shared context.
---

# Task Update

Use when an existing issue's plan, scope, dependency, risk, handoff, or closeout preparation changes.

Read `references/comment-template.md` when drafting the update.

Post with:

```bash
.codex/skills/task-update/scripts/run.sh --issue 55 --body-file /tmp/comment.md --dry-run
```

Use `--dry-run` before mutation. Use `--yes` for mutation.

`scripts/comment.sh` is the lower-level comment helper.

Umbrella propagation is needed when the update changes:

- leaf order
- shared context for multiple leaves
- dependency or risk policy
- future leaf non-scope or handoff

Use REST `gh api`; do not default to `gh issue comment`.
