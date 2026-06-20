---
name: risk-system
description: Use for stt-codex-cli risk operating rules: capture bottlenecks during slice work, intake accumulated risk comments, and route selected risks to resolution issues.
---

# Risk System

This skill routes risk work.

Read only the reference needed for the current task:

- Lifecycle and issue roles: `references/risk-lifecycle.md`
- Comment and body templates: `references/risk-comment-contract.md`

Use sibling skills:

- `risk-capture`: post a structured risk comment.
- `risk-intake`: read and summarize captured risks.
- `risk-resolution`: select and resolve risks through issue-backed work.

Risk comments are separate from task progress comments.
The risk-management issue is a singleton repo-level inbox; risk-resolution issues are executable tasks.
