# Existing Skill Reuse Decision

Source surface inspected: prior repo-local task skill set.

## Reuse

- `task-system` references: reuse as the initial task contract.
- `task-commit`: reuse because it only depends on local Git and Korean commit message rules.
- `.github/ISSUE_TEMPLATE` Markdown files: reuse as planning templates.
- `task-add`, `task-update`, `task-intake`, `task-pr-create`, `task-merge`,
  `task-remote-closeout`, `task-local-closeout`, `task-not-implemented`, and
  `task-implement`: reuse after remote `origin` and GitHub label taxonomy are
  configured for this repo.
- `risk-system`, `risk-capture`, `risk-intake`, and `risk-resolution`: reuse
  after adding the risk issue templates and remote risk labels.

## Modify

- Use repo root `.` in docs and command examples.
- Avoid assumptions about the parent directory name.
- Replace source repo names, worktree defaults, and generated workspace names
  with `stt-codex-cli` equivalents.
- Use STT-specific area labels instead of source repo product labels.
- Keep generated STT output local and ignored.

## Do Not Reuse

- Product-specific docs or runtime contracts from the source repo.
