# Issue System

## Kinds

- `kind:umbrella`: sequencing and shared context.
- `kind:leaf`: one executable slice under one umbrella.
- `kind:standalone`: one bounded executable issue without parent tracking.
- `kind:risk-management`: singleton repo-level risk capture inbox. Not executable through `task-intake`.
- `kind:risk-resolution`: resolves selected risks captured during slice work.

## Relationship Notation

- `Parent: #<umbrella>`: ownership by an umbrella.
- `Sub-issue of: #<umbrella>`: GitHub sub-issue relation.
- `Related: #<issue>`: informational context only.
- `Depends on: #<issue>`: planned order.
- `Blocked by: #<issue>`: actual current blocker.
- `Blocks: #<issue>`: this issue must finish first.

## Required Issue Body Sections

Every executable issue should include:

- Context
- Goal
- Scope
- Non-Scope
- Acceptance Criteria
- Completion Signal

## Issue Body Language

- Repo-local issue body prose is Korean-first.
- Keep section headings in the established contract form, such as `## Context`, `## Scope`, and `## Acceptance Criteria`.
- English is acceptable for code identifiers, paths, commands, labels, URLs, product names, and quoted source evidence.
- When an agent prepares an issue body, the body must include Korean prose outside the fixed headings and technical literals.
- Do not resolve language drift by translating old issues in bulk. Fix the issue creation path or the next issue body before mutation.

Umbrella issues additionally include:

- Leaf Sequence
- Shared Decisions
- Closeout Signal

Risk-management issues additionally include:

- Inbox Scope
- Capture Policy
- Intake Cadence
- Resolution Routing

Risk-resolution issues additionally include:

- Captured Risks
- Selection Criteria
- Resolution Plan
- Propagation Target

## Issue Creation

Use `task-add` for new issues.

New issues start with:

- one `type:*`
- one `kind:*`
- one `status:intake`
- one `priority:*`
- at least one `area:*`

GitHub writes should use REST `gh api` through repo-local scripts.

There should be at most one open `kind:risk-management` issue in the repository.
Use that issue as the shared inbox for captured risk comments from any task.
