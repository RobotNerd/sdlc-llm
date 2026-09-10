---
id: TASK-007
title: "sync: epic children and spec epics region renderers"
type: feature
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-007-sync-epic-spec-renderers
pr: null
merge_commit: null
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

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-005 (region engine) and TASK-006 (derived status).
- Blocks TASK-012 (`sync check` diffs these regions).
