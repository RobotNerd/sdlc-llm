---
id: TASK-040
title: "TDD mode for implement-task phase 2"
type: feature
status: todo
epic: EPIC-003
created: 2026-09-14
branch: task-040-tdd-mode
pr: null
merge_commit: null
blocked_by: [TASK-032, TASK-033, TASK-034, TASK-035, TASK-036, TASK-037, TASK-038]
blocks: []
---

# TASK-040: TDD mode for implement-task phase 2

## Description

Blocked on all seven EPIC-002 tasks, per this epic's placement decision. Independent of every
other task in this epic — it's a project-wide `implement-task` behavior change, not batch-specific,
and applies identically to a single-task run or a batch run.

New `.tasks/config.md` key, `tdd_enforced`, default `true`. When `true`, `implement-task` phase 2
changes: write the test(s) for a Testing strategy step (or acceptance criterion) first, run them
and confirm they fail for the expected reason (not an unrelated error), then implement until they
pass. When `false`, phase 2 keeps today's behavior (write code and its tests together).

## Acceptance criteria

- [ ] `init-project/templates/config.md` (and this repo's own `.tasks/config.md`) include
      `tdd_enforced: true`, documented under "Key notes" alongside the other boolean flags.
- [ ] `scaffold.py`'s `REQUIRED_KEYS`/interview gains `tdd_enforced` (asked, with `true` proposed
      as the default, confirmable/overridable like every other interview value).
- [ ] With `tdd_enforced: true`, `implement-task` phase 2 writes a failing test before any
      implementation code, runs it to confirm it fails for the right reason, then implements and
      re-runs until green — documented as an explicit sub-step, not left to model discretion.
- [ ] With `tdd_enforced: false`, phase 2's behavior is unchanged from today.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Extend `tests/test_init_project_scaffold.py`: a scaffolded `config.md` contains
   `tdd_enforced: true` by default, and a `false` answer round-trips correctly.
2. Whatever test module the (by-then-existing) `implement-task` script uses gains cases: with
   `tdd_enforced: true`, the phase-2 step order writes/fails/implements/passes in that sequence; a
   test that doesn't fail as expected before implementation surfaces as a stop condition rather
   than silently continuing.
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.
5. Scratch-branch dry run (throwaway branch off `origin/main`, deleted — not merged — when done):
   run `implement-task` on a trivial scratch task with `tdd_enforced: true` and confirm the test
   file exists and was run (and failed) before the implementation file was written. Human-run —
   record in the Worklog.

## Worklog

_(empty — appended during implementation)_

## Notes

- Independent of the batch/autonomy mechanism (TASK-039, 041-045) — could be implemented in any
  order relative to them once EPIC-002 is done.
