---
id: TASK-037
title: SessionStart board-context hook
type: feature
status: todo
epic: EPIC-002
created: 2026-09-14
branch: task-037-sessionstart-board-context-hook
pr: null
merge_commit: null
blocked_by: [TASK-032, TASK-052]
blocks: [TASK-039, TASK-040]
---

# TASK-037: SessionStart board-context hook

## Description

Blocked on TASK-032 (hooks infrastructure) and TASK-052 (guidelines.md trim — see amendment
below).

On `SessionStart`, inject the current `BOARD.md` In Progress/In Review sections and, if a task is
`in-progress`/`in-review`, that task's id/title/status/`pr` as `additionalContext` — so
`implement-task`'s resume-detection starts from fact already in context rather than re-deriving it
via tool calls every session.

Also inject `.tasks/guidelines.md`'s contents as `additionalContext`, read verbatim (never a
copy embedded in the hook script) — so the shared workflow model (the artifact model, what `sync`
owns, which skill to reach for) is in context from turn one in every scaffolded project, with no
`CLAUDE.md` edit required in the target repo. This only became worth doing once TASK-052 trimmed
the file to something small enough to inject on every session; injecting the pre-trim 91-line file
would defeat that task's whole point.

Not a guardrail — a convenience hook that reduces redundant board/task reads and puts the workflow
model in context at the start of every session.

## Acceptance criteria

- [ ] A session start with no in-flight task injects the board's open columns (In Progress, In
      Review) only.
- [ ] A session start with an in-flight task also includes that task's id/title/status/`pr`.
- [ ] `.tasks/guidelines.md`'s contents appear in the injected `additionalContext` alongside the
      board state.
- [ ] Output is silent (the hook skips cleanly) if `.tasks/` doesn't exist, so this hook is
      harmless in a non-workflow repo.
- [ ] The hook still exits cleanly if `.tasks/` exists but `.tasks/guidelines.md` specifically is
      absent — it injects the board context it does have and simply omits the guidelines section,
      the same tolerant posture as the "`.tasks/` doesn't exist" case.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the context-building function against fixture `BOARD.md`/task-file states: none
   in-flight, one in-progress, one in-review.
2. Unit tests on the same function with `guidelines.md` present vs. absent, confirming its content
   is included/omitted respectively without affecting the board-context portion.
3. Hook-script test confirming the `additionalContext` field shape matches the documented
   `SessionStart` JSON schema.
4. A test confirming the hook exits cleanly with no output when `.tasks/` is absent.
5. `pytest` — full suite green.
6. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- Depends on TASK-032's hooks-infrastructure/wiring pattern, and now also on TASK-052's trimmed
  `guidelines.md` (see Description).
- Amended 2026-09-16 (before implementation started) to also inject `guidelines.md`'s contents,
  closing a gap found during a `guidelines.md`-scoping review: nothing in a scaffolded project
  ever loaded that file today. Added `TASK-052` to `blocked_by` accordingly. No other behavior
  change to this task's original board-context scope.
