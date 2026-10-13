# Review policy

What a pull request review checks before the developer merges. It applies to the developer's own review, and to any review Claude is asked to do. The reviewer reads this doc, the tasks the pull request covers, the diff, the checks' results, and `architecture.md`, `code-style.md`, and `documentation-style.md`.

## Checklist

An item that can't be verified counts as failed.

| Item | Passes when |
|------|-------------|
| Criteria met | The diff satisfies every acceptance criterion of every task in the pull request. |
| Checks passed | Tests, lint, format, and the reference check pass, in CI and locally. |
| Docs clean | Docs changed wherever behavior changed. The text is concise and accurate, follows `documentation-style.md`, and nothing stale is left behind. |
| Nothing alarming | No secrets, destructive or unrelated changes, or disabled tests. |
| Scope | Every changed file is within a task's scope. A follow-up task is always allowed. |
| Sorted order | Lists and structures whose order doesn't matter are sorted, per `code-style.md` (code) and `documentation-style.md` (docs). |
| Tests behavioral | Committed tests exercise behavior through the public surface, per `testing.md`. A committed unit test has its reason in a task comment. |

When a task changes a skill, the review also checks the rules in `skill-authoring.md`. A broken rule is a finding.

## Severity

Every finding has a severity:

* **`important`:** breaks behavior, leaks data or secrets, fails an acceptance criterion, or fails a checklist item.
* **`nit`:** anything else worth fixing: naming, wording, small style points.

Only an `important` finding blocks the merge. Nits never block.

**Nit cap:** report at most ten nits per review. Count the rest: "and 3 more nits".

## Excluded

A review doesn't comment on:

* generated files
* anything a check already enforces, such as formatting and lint
* the tasks' own requirements: whether a task was a good idea is out of scope

## Findings

List the findings with the `important` ones first, each with its file and line and what to change. Fixes go on the same branch, and each task they touch gets a comment saying what changed.
