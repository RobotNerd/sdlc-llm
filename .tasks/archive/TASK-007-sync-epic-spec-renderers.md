---
id: TASK-007
title: "sync: epic children and spec epics region renderers"
type: feature
status: done
epic: EPIC-001
created: 2026-09-10
branch: task-007-sync-epic-spec-renderers
pr: https://github.com/RobotNerd/sdlc-llm/pull/7
merge_commit: 346f2acfd4c6edb64b540cd1984e3ee3fb42d022
blocked_by: [TASK-005, TASK-006]
blocks: [TASK-012]
---

# TASK-007: sync: epic children and spec epics region renderers

## Description

Render the two non-board regions: the `children` table + `Progress: n/m done` line in each `EPIC-*.md`, and the `epics` table (id, derived status) in each `SPEC-*.md`. Rows ordered by ID ascending (SPEC-001 §'Generated regions', §'Rendering details').

## Acceptance criteria

- [ ] Epic `children` region: `| Task | Status | Title |` header, one row per child ordered by ID, then a blank line, then `Progress: <done>/<total> done` where `done` counts `done`+`wont-do`.
- [ ] Spec `epics` region: `| Epic | Status | Progress |` header, one row per epic linked via `spec:`, ordered by ID, status from TASK-006's derivation.
- [ ] An epic with no children / a spec with no epics renders `_(none)_`.
- [ ] Renderers call TASK-005's `replace_region`; running twice produces no diff.
- [ ] Unit tests assert exact bytes for a zero-child, one-child, and many-child epic.

## Testing strategy

1. Render EPIC-001's `children` region and diff against the hand-written region committed in this epic — must be identical (the bootstrap no-op check).
2. Render SPEC-001's `epics` region and diff against its hand-written region.
3. Run the renderer twice; confirm idempotent.

## Worklog

- 2026-09-11: Testing strategy step 2 (render SPEC-001's `epics` region, diff against hand-written)
  surfaced a real defect in TASK-005's `find_region`: it has no concept of markdown fenced code
  blocks, so SPEC-001's own illustrative examples of the marker syntax (§'Generated regions',
  §'Epics panel') were misread as live regions. Fixed `_find_marker`/`find_region` to skip matches
  inside ` ``` ` fences, with regression tests added to `test_region_engine.py` (TASK-005's test
  file — the right home for tests of that code, even though the fix ships in this task's commit).
  Chose to fix rather than work around: the bug would have corrupted SPEC-001 the first time
  `sync` actually processed it, and it was found executing this task's own mandated testing step,
  not an unrelated drive-by change.
- Also added the real `epics` region to SPEC-001 (replacing the stale "Proposed epic breakdown"
  six-epic table, superseded when the epic decomposition became a single `EPIC-001: MVP`) — this
  was needed to have something real to diff against for step 2, and completes SPEC-001's own
  Data model promise that spec files carry an `epics` region.

## Notes

- Blocked by TASK-005 (region engine) and TASK-006 (derived status).
- Blocks TASK-012 (`sync check` diffs these regions).
