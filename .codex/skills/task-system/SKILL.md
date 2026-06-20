---
name: task-system
description: Use for this STT experiment repo task operating rules: issue graph, labels, commit conventions, and README/AGENTS boundaries.
---

# Task System

This skill routes repo task work to the local operating contracts.

Read only the reference needed for the current task:

- Issue graph and issue body contract: `references/issue-system.md`
- Label taxonomy: `references/label-taxonomy.md`
- Future worktree and VS Code workspace rules: `references/worktree-vscode-workspace.md`
- Commit body convention: `references/commit-convention.md`
- README and AGENTS boundary: `references/readme-agents-boundary.md`
- Existing skill reuse decision: `references/reuse-decision.md`

Available sibling skill:

- `task-commit`: create Korean topic commits that follow the commit convention.
- `task-add`: create GitHub issues through the repo issue contract.
- `task-update`: post structured task comments.
- `task-intake`: prepare isolated issue worktrees.
- `task-implement`: run issue-backed implementation phases.
- `task-pr-create`: create or reuse PR review surfaces.
- `task-remote-closeout`: close GitHub issues after completion.
- `task-local-closeout`: clean up local branches and worktrees.
- `task-not-implemented`: close intentionally unimplemented issues.
- `task-merge`: orchestrate PR merge, remote closeout, and local cleanup.
- `risk-*`: capture, intake, and resolve task risks.

Do not put these contracts under `docs/operations`.
