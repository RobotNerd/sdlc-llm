---
id: TASK-039
title: Batch selection + deterministic validation script
type: feature
status: in-review
epic: EPIC-003
created: 2026-09-14
branch: task-039-batch-selection-validation
pr: "https://github.com/RobotNerd/sdlc-llm/pull/74"
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

- [x] All four selection modes resolve to a concrete, ordered task-id list from real `.tasks/`
      state.
- [x] A selection containing a task blocked by something outside the set and not yet
      `done`/`wont-do` is refused with a clear message.
- [x] A selection whose members have a real ordering conflict (a task before a blocker also in the
      set) is refused with a clear message.
- [x] Tasks in a range/epic that are already `done`/`wont-do` are silently excluded, not errors.
- [x] The script writes nothing and exits non-zero on any invalid selection.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests per selection mode against fixture `.tasks/` trees (mirroring `tests/fixtures/`
   conventions already in the repo).
2. Unit tests for each invalid-selection case (external unresolved blocker, intra-set ordering
   conflict, nonexistent task id, task already `done`).
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

- 2026-09-17: Added `.claude/skills/implement-task/batch_select.py` -- a standalone stdlib
  script (not a new `sync` subcommand, not folded into `scaffold.py`, per the task description)
  implementing the four selection modes (`epic`, `range`, `list`, `stopping`) plus a shared
  `validate_and_order` step that reuses `sync.discover()`/`sync._outstanding_blockers()`. Design
  choice worth recording: the "natural order" for each mode is validated, not resorted --
  `validate_and_order` refuses a selection whose given order doesn't already respect a real
  intra-set `blocked_by` edge, rather than silently reordering it, matching the task description's
  "refused with a clear message" wording for that case. "Board order" for `epic` mode is defined
  as ascending task-id order (the same order `sync.render_epic_children` renders in that epic's
  own file); `stopping` mode's natural order is literally `.tasks/BOARD.md`'s hand-ordered TODO
  section text.
- 2026-09-17: Step 1/2 — added 37 unit tests to `tests/test_batch_select.py`: one per selection
  mode's happy path plus its invalid-input cases (no such epic, malformed/backwards range,
  stopping task absent from TODO), `validate_and_order`'s full matrix (nonexistent task,
  ineligible status, satisfied/inside-set/outside-set/missing blockers, ordering violation, empty
  selection), `select_batch`'s mode dispatch, and 3 real-subprocess CLI tests against a
  hand-authored `.tasks/` tree in a scratch git repo (list-mode happy path, an external-blocker
  refusal, and epic mode end to end).
- 2026-09-17: Step 3 — `.venv/bin/pytest` (this repo's `test_command`): 616 passed, 0 failed.
- 2026-09-17: Step 4 — `python3 .tasks/bin/sync check` exits 0.
- 2026-09-17: A first pass leaked this task's own id (and `EPIC-003`/`SPEC-003`/`TASK-041`) into
  `batch_select.py`'s module docstring, caught by the existing portable-surface test suite
  (`test_check_portable_references.py`/`test_portable_surface.py`/
  `test_strip_project_references_scaffold.py`) since this script lives under the portable skills
  surface — reworded to stay id-free before re-running the suite.

## Notes

- Every other task in this epic depends on this one (directly or transitively) except TASK-040
  (TDD mode), which is independent.
