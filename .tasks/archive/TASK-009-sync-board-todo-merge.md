---
id: TASK-009
title: "sync: BOARD.md TODO merge (preserve order, drop, append, annotate)"
type: feature
status: done
epic: EPIC-001
created: 2026-09-10
branch: task-009-sync-board-todo-merge
pr: https://github.com/RobotNerd/sdlc-llm/pull/9
merge_commit: d0df4ac1f41ea0f17da363633df5f77fcb79527a
blocked_by: [TASK-008]
blocks: [TASK-012, TASK-013, TASK-017]
---

# TASK-009: sync: BOARD.md TODO merge (preserve order, drop, append, annotate)

## Description

The one place `sync` merges instead of regenerating. Reconcile the hand-ordered TODO list with reality: keep existing line order, drop lines whose task left `todo`, append new `todo` tasks at the end, and re-annotate every line with its epic tag and blocked marker. Never reorder (SPEC-001 §'TODO — hand-maintained').

## Acceptance criteria

- [ ] Existing TODO line order is preserved exactly — no sort, ever.
- [ ] A line whose task is no longer `todo` is removed.
- [ ] A `todo` task absent from the list is appended after the last existing line, in ID order among the newly-added.
- [ ] Each line matches the SPEC-001 §'TODO' format: dash, task ID, em-dash, title, two spaces, the epic tag in backticks (omitted when the task has no epic), then a ' ⛔ blocked_by ' clause listing blocker IDs ascending when `blocked_by` is non-empty.
- [ ] Round-trip is stable: parsing the rendered line back yields the same task ID.
- [ ] Unit tests: reorder attempt (must not reorder), status departure, new-task append, blocked-annotation add and remove.

## Testing strategy

1. Run against the hand-written `BOARD.md` — all 20 lines come back in the same order with identical annotations: no diff (bootstrap no-op check).
2. Hand-scramble two TODO lines, run `sync`, confirm the scramble is preserved (proves no reordering) and annotations are refreshed.
3. Flip a fixture task out of `todo`; confirm its line disappears.
4. Run twice; confirm idempotent.

## Worklog

- 2026-09-12: Testing strategy step 1 (no-op against the hand-written `BOARD.md`) failed on first
  run against the real repo — `render_todo_line` rendered `blocked_by` verbatim, but that field is
  a static historical list (nothing prunes it as blockers complete; only `blocks` is derived from
  it). TASK-012/010/011's `blocked_by` still list already-done blockers from when they were
  created, so the raw field disagreed with the hand-maintained board, which has always shown only
  outstanding blockers. Fixed: `render_todo_line` now takes the full task map and filters to
  blockers whose status isn't `done`/`wont-do` at render time. Added a clarifying sentence to
  SPEC-001 §'Relationships' since this was genuinely ambiguous before. No task files needed
  correcting — the bug was in the new code, not in any prior hand-maintenance.
- Also found a smaller idempotency edge case (TODO as the very last section, no next heading):
  fixed the trailing-blank-line logic to not force one when there's nothing after to separate from.

## Notes

- Blocked by TASK-008 (columns regenerate first so 'left todo' is unambiguous).
- Blocks TASK-012, TASK-013, TASK-017.
- SPEC-001 calls this the hardest thing in `sync` to get right — hence its own task.
