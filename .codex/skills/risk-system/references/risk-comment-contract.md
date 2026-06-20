# Risk Comment Contract

## Capture Template

```md
## Risk Capture

Source slice: #<slice-issue>
Risk inbox: #<risk-management-issue>
Date: <YYYY-MM-DD>
Type: <bottleneck|dependency|test-gap|runtime-uncertainty|scope-pressure|tooling-gap|architecture-risk>
Severity: <low|medium|high|blocking>
Status: captured

### Observation

- <what was found>

### Evidence

- <file, command, error, or issue link>

### Slice Impact

- <none|slows-current-slice|blocks-current-slice|affects-future-slice>

### Proposed Handling

- <defer|monitor|create-resolution-issue|resolve-now>

### Notes

- <optional>
```

## Selection Template

```md
## Risk Selection

Risk inbox: #<risk-management-issue>
Date: <YYYY-MM-DD>
Status: selected

### Selected Risks

- <risk comment URL or short id>

### Selection Criteria

- <blocking|multi-leaf|contract-change|verification-gap|architecture-risk>

### Resolution Target

- <new-risk-resolution-issue|existing-issue|defer|monitor>
```

## Resolution Issue Body Template

```md
## Context

- Selected from risk management inbox issue #<risk-management-issue>.

## Captured Risks

- <risk comment URL or summary>

## Selection Criteria

- <why this risk should become issue-backed work>

## Resolution Plan

- <bounded plan>

## Propagation Target

- <none|umbrella #N|issue #N>

## Scope

- <included work>

## Non-Scope

- <excluded work>

## Acceptance Criteria

- [ ] <observable result>

## Completion Signal

- <how the risk is considered resolved>
```

## Resolution Start Template

```md
## Risk Resolution Start

Risk inbox: #<risk-management-issue>
Resolution issue: #<risk-resolution-issue>
Date: <YYYY-MM-DD>
Status: resolution-started

### Selected Risks

- <risk comment URL or summary>

### Resolution Plan

- <bounded plan>
```

## Resolution Closeout Template

```md
## Risk Resolution Closeout

Risk inbox: #<risk-management-issue>
Resolution issue: #<risk-resolution-issue>
Date: <YYYY-MM-DD>
Status: resolved

### Resolved

- <what changed>

### Verification

- <commands or evidence>

### Remaining Risk

- <none or follow-up>
```

## Propagation Template

```md
## Task Update

Type: risk-update
Source issue: #<risk-resolution-issue>
Related umbrella: #<umbrella-or-none>
Date: <YYYY-MM-DD>

### What Changed

- <risk resolution summary>

### Current Decision

- <shared decision>

### Risk / Follow-up

- <remaining plan-level risk>
```

## Intake Rules

- Read the singleton risk-management inbox comments by REST `gh api`.
- Extract comments beginning with `## Risk Capture`.
- Group by type, severity, source slice, and status.
- Identify duplicates.
- Identify multi-leaf or umbrella-level risks.
- Do not mutate GitHub during intake unless explicitly requested.

## Resolution Rules

- Resolve selected risks only.
- Prefer separate issue-backed work for contract, architecture, workflow, or verification changes.
- Post resolution start and closeout comments to the risk-management inbox issue.
- Propagate summary to umbrella when multiple leaves or shared plan context are affected.
