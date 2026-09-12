---
id: TASK-008
title: "sync: BOARD.md epics panel and status columns"
type: feature
status: in-review
epic: EPIC-001
created: 2026-09-10
branch: task-008-sync-board-columns
pr: https://github.com/RobotNerd/sdlc-llm/pull/8
merge_commit: null
blocked_by: [TASK-005, TASK-006]
blocks: [TASK-009, TASK-011, TASK-012]
---

# TASK-008: sync: BOARD.md epics panel and status columns

## Description

Regenerate the fully-derived parts of `BOARD.md`: the `epics` roll-up panel (one row per epic not `done`/`wont-do`) and the `in-progress` / `in-review` / `blocked` / `done` column regions (SPEC-001 §'BOARD.md contract').

## Acceptance criteria

- [ ] `epics` panel: `| Epic | Status | Progress |`, one row per epic whose derived status is not `done` and not `wont-do`, ordered by ID, `Progress` as `n/m done`.
- [ ] Each column region uses the `| Task | Title | Epic | Ref |` header from §'Rendering details'; `Ref` = branch for `in-progress`, PR URL for `in-review`/`done`; no epic → `—`.
- [ ] `done` column is capped at the most recent 20 rows.
- [ ] Every empty region renders `_(none)_`.
- [ ] All five regions written via TASK-005's engine; a second run is a no-op.
- [ ] Unit tests cover an empty board and a board with a task in each status.

## Testing strategy

1. Run against the hand-written `BOARD.md` from this epic — the `epics` panel must come back as `| EPIC-001 | todo | 0/20 done |` and all four columns as `_(none)_`, i.e. no diff.
2. Move a fixture task to each status in turn and confirm it lands in the right column with the right `Ref`.
3. Run twice; confirm idempotent.

## Worklog

- 2026-09-12: Testing strategy step 1 was written when this epic was still all-`todo` ("epics
  panel must come back as `| EPIC-001 | todo | 0/20 done |`, all four columns `_(none)_`"). Real
  progress has moved on since (5 tasks done by the time this started). Ran the equivalent check
  against current reality instead: all five real board regions (epics panel + 4 columns) came back
  as true no-ops against the hand-written `BOARD.md` — same intent, current data.
- Clarified a genuine ambiguity in SPEC-001 while implementing the `blocked` column: "a blocked
  task stays in TODO" (§TODO) and "Blocked" being one of the four generated columns (§BOARD.md
  contract) sound contradictory. Resolved: a `todo` task with unmet `blocked_by` stays in TODO
  with the ⛔ marker (status is still `todo`); a task whose `status` field is literally `blocked`
  has left `todo` and gets the column. Added one disambiguating sentence to SPEC-001.

## Notes

- Blocked by TASK-005 and TASK-006.
- Blocks TASK-009 (TODO merge runs after columns), TASK-011, TASK-012.
