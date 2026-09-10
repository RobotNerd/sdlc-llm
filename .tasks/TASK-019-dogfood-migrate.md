---
id: TASK-019
title: "Dogfood: bring this repo's .tasks/ fully under the toolkit"
type: chore
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-019-dogfood-migrate
pr: null
merge_commit: null
blocked_by: [TASK-012, TASK-013]
blocks: []
---

# TASK-019: Dogfood: bring this repo's .tasks/ fully under the toolkit

## Description

Switch this repo from hand-written tracking to the real `sync`. Run `sync` for the first time, confirm it produces no diff against the files hand-written in this epic, then wire `sync` into the workflow so all further board/epic/spec updates go through it (SPEC-001 §'Success criteria').

## Acceptance criteria

- [ ] First `sync` run on this repo produces an empty diff — the hand-written generated regions in `EPIC-001`, `BOARD.md`, and `SPEC-001` already match `sync` output. Any mismatch is filed as a `sync` or SPEC-001 defect and fixed.
- [ ] `sync check` exits 0 on a clean checkout of `main`.
- [ ] `guidelines.md` / `CLAUDE.md` updated to instruct future sessions to run `sync` rather than hand-edit generated regions.
- [ ] `README.md` updated to describe the now-working toolkit instead of 'design stage'.
- [ ] The `.tasks/archive/` directory exists (created by the first archive run, even if empty).

## Testing strategy

1. On a fresh clone, run `sync` and `git diff` — expect no changes.
2. Run `sync check` — expect exit 0.
3. Move TASK-001 through to `done` end-to-end via `implement-task` and confirm the board, the epic `children` progress count, and archiving all update through `sync` alone.

## Worklog

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-012 (`sync check`) and TASK-013 (green suite).
- This is the bootstrap payoff: proves the hand-written regions were spec-accurate.
