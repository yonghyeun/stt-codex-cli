# Risk Lifecycle

## Issue Roles

- `kind:risk-management`: singleton repo-level risk capture inbox. It stores structured risk comments from any task and is not executable through `task-intake`.
- `kind:risk-resolution`: executable issue for a selected captured risk. It starts through `task-intake`.
- task issue: normal executable issue where implementation work happens.
- umbrella issue: optional propagation target when the risk changes shared sequencing, dependency, or plan context.

## Lifecycle

1. `captured`: `risk-capture` posts a `## Risk Capture` comment to the open `kind:risk-management` inbox issue.
2. `intaked`: `risk-intake` reads capture comments and prints a non-mutating summary.
3. `selected`: `risk-resolution` records why one or more captured risks should become issue-backed work.
4. `resolution-issued`: `risk-resolution` prepares a risk-resolution issue body, then `task-add --kind risk-resolution` creates the issue.
5. `resolution-started`: `risk-resolution` posts a start comment to the risk-management inbox linking the resolution issue.
6. `resolved`: after the resolution issue is done, `risk-resolution` posts a closeout comment to the risk-management inbox.
7. `propagated`: when the risk affects an umbrella or multiple leaves, `task-update` posts the propagated summary.

## Secondary States

- `deferred`: selected for later review, with reason and review condition.
- `superseded`: replaced by another risk, issue, or decision.
- `monitoring`: tracked without immediate issue-backed work.

## Routing Rules

- Capture goes only to the open `kind:risk-management` inbox issue.
- Keep at most one open `kind:risk-management` issue in the repository backlog.
- Reuse the existing inbox for all task, leaf, umbrella, and standalone risks.
- Intake never mutates GitHub.
- Selected risks become `kind:risk-resolution` issues only through `task-add`.
- Resolution implementation starts only through `task-intake`.
- Risk comments do not replace task progress comments.
- Do not silently fold unrelated risk work into the current slice.

## Normal Flow

```text
task-add --kind risk-management  # bootstrap only when no inbox exists
-> risk-capture
-> risk-intake
-> risk-resolution issue-body
-> task-add --kind risk-resolution
-> risk-resolution start
-> task-intake
-> task-pr-create / task-merge
-> risk-resolution closeout
```
