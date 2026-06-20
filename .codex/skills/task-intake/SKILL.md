---
name: task-intake
description: Intake a stt-codex-cli issue before implementation by checking issue readiness, preparing an isolated worktree, and updating the generated VS Code workspace.
---

# Task Intake

Use before non-trivial repo edits.

Preferred flow:

1. Fetch the issue with REST `gh api`.
2. Confirm the issue has scope, non-scope, acceptance criteria, and completion signal.
3. Choose branch and worktree.
4. Run `scripts/run.sh`.
5. Post an intake receipt with `task-update` when remote mutation is needed.

Always dry-run first:

```bash
.codex/skills/task-intake/scripts/run.sh \
  --issue 55 \
  --path ../stt-codex-cli-issue-55-task-skill-system-bootstrap \
  --branch feat/55-task-skill-system-bootstrap \
  --base origin/main \
  --no-code-add \
  --dry-run
```

Mutation requires explicit confirmation:

```bash
.codex/skills/task-intake/scripts/run.sh \
  --issue 55 \
  --path ../stt-codex-cli-issue-55-task-skill-system-bootstrap \
  --branch feat/55-task-skill-system-bootstrap \
  --base origin/main \
  --no-code-add \
  --yes
```

`scripts/worktree-add.sh` and `scripts/update-vscode-workspace.mjs` are lower-level helpers.

Do not edit in the main worktree for issue implementation.
