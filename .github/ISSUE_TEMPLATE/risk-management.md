---
name: Risk Management
about: Singleton inbox for structured risk capture comments
title: "chore: repository risk inbox"
labels: "kind:risk-management,status:intake"
---

## Context

- This issue is the repository-level inbox for `## Risk Capture` comments from any task.
- Keep at most one open `kind:risk-management` issue in the backlog.

## Inbox Scope

- Capture bottlenecks, dependencies, test gaps, runtime uncertainty, scope pressure, tooling gaps, and architecture risks discovered during task execution.
- Do not scope this issue to one captured risk, umbrella, or slice.

## Capture Policy

- Capture discovered bottlenecks as `## Risk Capture` comments.
- Do not use this issue as executable implementation work.
- Keep implementation discussion on the source task or a selected risk-resolution issue.

## Intake Cadence

- Review before selecting risk-resolution work.
- Review before umbrella closeout when captured risks affect shared sequencing or acceptance criteria.

## Resolution Routing

- Selected risks become `kind:risk-resolution` issues through `task-add`.
- Resolution work starts through `task-intake`.

## Acceptance Criteria

- [ ] Captured risks can be reviewed from comments.
- [ ] Selected risks can be routed to issue-backed resolution work.

## Closeout Signal
