---
id: TASK-037
title: "SessionStart board-context hook"
type: feature
status: todo
epic: EPIC-002
created: 2026-09-14
branch: task-037-sessionstart-board-context-hook
pr: null
merge_commit: null
blocked_by: [TASK-032]
blocks: []
---

# TASK-037: SessionStart board-context hook

## Description

Blocked on TASK-032 (hooks infrastructure).

On `SessionStart`, inject the current `BOARD.md` In Progress/In Review sections and, if a task is
`in-progress`/`in-review`, that task's id/title/status/`pr` as `additionalContext` — so
`implement-task`'s resume-detection starts from fact already in context rather than re-deriving it
via tool calls every session.

Not a guardrail — a convenience hook that reduces redundant board/task reads at the start of every
session.

## Acceptance criteria

- [ ] A session start with no in-flight task injects the board's open columns (In Progress, In
      Review) only.
- [ ] A session start with an in-flight task also includes that task's id/title/status/`pr`.
- [ ] Output is silent (the hook skips cleanly) if `.tasks/` doesn't exist, so this hook is
      harmless in a non-workflow repo.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the context-building function against fixture `BOARD.md`/task-file states: none
   in-flight, one in-progress, one in-review.
2. Hook-script test confirming the `additionalContext` field shape matches the documented
   `SessionStart` JSON schema.
3. A test confirming the hook exits cleanly with no output when `.tasks/` is absent.
4. `pytest` — full suite green.
5. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- Depends on TASK-032's hooks-infrastructure/wiring pattern only — no other guardrail
  dependencies.
