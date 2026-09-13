---
id: TASK-019
title: "Dogfood: bring this repo's .tasks/ fully under the toolkit"
type: chore
status: in-review
epic: EPIC-001
created: 2026-09-10
branch: task-019-dogfood-migrate
pr: https://github.com/RobotNerd/sdlc-llm/pull/17
merge_commit: null
blocked_by: [TASK-012, TASK-013]
blocks: []
---

# TASK-019: Dogfood: bring this repo's .tasks/ fully under the toolkit

## Description

Switch this repo from hand-written tracking to the real `sync`. Run `sync` for the first time, confirm it produces no diff against the files hand-written in this epic, then wire `sync` into the workflow so all further board/epic/spec updates go through it (SPEC-001 §'Success criteria').

## Acceptance criteria

- [x] First `sync` run on this repo produces an empty diff — the hand-written generated regions in `EPIC-001`, `BOARD.md`, and `SPEC-001` already match `sync` output. Any mismatch is filed as a `sync` or SPEC-001 defect and fixed.
- [x] `sync check` exits 0 on a clean checkout of `main`.
- [x] `guidelines.md` / `CLAUDE.md` updated to instruct future sessions to run `sync` rather than hand-edit generated regions.
- [x] `README.md` updated to describe the now-working toolkit instead of 'design stage'.
- [x] The `.tasks/archive/` directory exists (created by the first archive run, even if empty).

## Testing strategy

1. On a fresh clone, run `sync` and `git diff` — expect no changes.
2. Run `sync check` — expect exit 0.
3. Move TASK-001 through to `done` end-to-end via `implement-task` and confirm the board, the epic `children` progress count, and archiving all update through `sync` alone.

## Worklog

- 2026-09-12: After phase-1 frontmatter/board/epic edits for this task itself, ran bare
  `python3 .tasks/bin/sync` for the first time ever on this real repo. Output: "Already up to
  date." — a true no-op (`git status`/`git diff` showed only the phase-1 edits I'd just made by
  hand, nothing extra from `sync`). This is AC #1's proof: the 13 hand-written-to-match-spec
  regions across `BOARD.md`, `EPIC-001-mvp.md`, and `SPEC-001` were byte-accurate all along. No
  `sync` or SPEC-001 defect to file.
- `python3 .tasks/bin/sync check` → exit 0, both before and after the bare run.
- `.tasks/archive/` already existed (13 entries) — every prior task's phase-4 bookkeeping has
  been hand-archiving into it since TASK-001, mirroring what `sync archive` does. AC #5 satisfied
  by that history, not new work here.
- Updated `.tasks/guidelines.md` and `CLAUDE.md`: replaced every "until `sync` exists, hand-edit
  the region" / "planned" framing with "run `sync`" — phases 1/3/4 of the per-task loop now call
  `sync` instead of hand-updating `BOARD.md`/epic children. Also updated `.tmp/workflow-plan.md`
  (in `config.md`'s `docs_paths`, and squarely touched by this change) — closed its "sync's write
  mode not yet run for real" Gap row and updated the per-task loop's phase descriptions the same
  way.
- Rewrote `README.md` end to end: dropped the "split off from another repo, design stage" framing
  and the old two-value Type enum / hand-authored task-file example, replaced with the actual data
  model, `sync`'s CLI, and the five skills' status.
- Testing strategy step 3 (move a task to `done` via `sync` alone): deferred to this task's *own*
  phase-4 close-out — once merged, recording `merge_commit`/`status: done`/archiving via bare
  `sync` for TASK-019 itself is a more faithful instance of this proof than a separate synthetic
  example would be.
- `pytest` (209 passed) and `sync check` (exit 0) reconfirmed after all doc edits; `git diff
  --name-only` stayed within `.tasks/BOARD.md`, `.tasks/EPIC-001-mvp.md`,
  `.tasks/TASK-019-dogfood-migrate.md`, `.tasks/guidelines.md`, `.tmp/workflow-plan.md`,
  `CLAUDE.md`, `README.md` — all in `docs_paths` or this task's own file.

## Notes

- Blocked by TASK-012 (`sync check`) and TASK-013 (green suite).
- This is the bootstrap payoff: proves the hand-written regions were spec-accurate.
