---
id: TASK-039
title: Batch selection + deterministic validation script
type: feature
status: todo
epic: EPIC-003
created: 2026-09-14
branch: task-039-batch-selection-validation
pr: null
merge_commit: null
blocked_by: [TASK-032, TASK-033, TASK-034, TASK-035, TASK-036, TASK-037, TASK-038]
blocks: [TASK-041]
---

# TASK-039: Batch selection + deterministic validation script

## Description

Foundational slice for EPIC-003 (see SPEC-003). Blocked on all seven EPIC-002 tasks, per this
epic's placement decision (planned to run after EPIC-002 completes in full).

A dedicated stdlib script under `.claude/skills/implement-task/` (not a new `sync` subcommand —
`sync` stays generic/skill-agnostic) that imports `sync`'s existing graph/blocked-status functions
(same `SourceFileLoader` pattern already used in `tests/`) to validate a batch selection
deterministically, before any work starts. Offloads this decision from model judgment, per the
epic's whole premise.

Four selection modes:
1. **Epic** — every non-`done`/`wont-do` task under the given `EPIC-NNN`.
2. **Numeric task-ID range** — e.g. `TASK-032..TASK-038`, inclusive. Tasks in the range that are
   already `done`/`wont-do` are silently skipped, not errors.
3. **Explicit task list** — arbitrary ids, in the order given, which may not match TODO order.
4. **Stopping task** — TODO top-to-bottom, in board order, through and including the named task.

Validation must confirm, for the resolved set: every task exists and is `todo` (or already
`in-progress`/`in-review` if resuming); every `blocked_by` dependency is either inside the set (and
ordered before its dependent) or already `done`/`wont-do` outside it — otherwise the selection is
invalid and the script refuses with a clear message naming the offending task and blocker. On
success it emits the concrete execution order (respecting a real intra-set dependency, and
otherwise preserving the mode's natural order — board order for epic/stopping-task, given order
for the explicit list, ID order for the range).

## Acceptance criteria

- [ ] All four selection modes resolve to a concrete, ordered task-id list from real `.tasks/`
      state.
- [ ] A selection containing a task blocked by something outside the set and not yet
      `done`/`wont-do` is refused with a clear message.
- [ ] A selection whose members have a real ordering conflict (a task before a blocker also in the
      set) is refused with a clear message.
- [ ] Tasks in a range/epic that are already `done`/`wont-do` are silently excluded, not errors.
- [ ] The script writes nothing and exits non-zero on any invalid selection.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests per selection mode against fixture `.tasks/` trees (mirroring `tests/fixtures/`
   conventions already in the repo).
2. Unit tests for each invalid-selection case (external unresolved blocker, intra-set ordering
   conflict, nonexistent task id, task already `done`).
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- Every other task in this epic depends on this one (directly or transitively) except TASK-040
  (TDD mode), which is independent.
