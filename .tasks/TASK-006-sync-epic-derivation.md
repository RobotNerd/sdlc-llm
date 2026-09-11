---
id: TASK-006
title: "sync: epic-status derivation and blocked_by/blocks reconciliation"
type: feature
status: in-progress
epic: EPIC-001
created: 2026-09-10
branch: task-006-sync-epic-derivation
pr: null
merge_commit: null
blocked_by: [TASK-004]
blocks: [TASK-007, TASK-008]
---

# TASK-006: sync: epic-status derivation and blocked_by/blocks reconciliation

## Description

Two pure computations over the loaded records: (a) each epic's `status` from its children via the seven ordered rules in SPEC-001 §'Epic status derivation', and (b) reconciling `blocks` as the exact reverse of every `blocked_by` edge, with `blocked_by` winning on conflict.

## Acceptance criteria

- [ ] `derive_epic_status(epic, children)` implements rules 1–7 in order, first match wins; a human-set `wont-do` is preserved (rule 1).
- [ ] Function is total — a test drives every row of the §derivation worked-cases table (empty, all-todo, todo+in-progress, all-blocked, all-wont-do, done+wont-do, todo+done, hand-set wont-do) and asserts the documented result and rule number.
- [ ] `reconcile_blocks(tasks)` rewrites every task's `blocks` list to match inbound `blocked_by` edges; pre-existing `blocks` that disagree are overwritten.
- [ ] Neither function writes files — they return updated records for the caller to persist.
- [ ] A `blocked_by` pointing at a missing task ID is reported as an error, not silently dropped.

## Testing strategy

1. Build a fixture epic per worked-case row; run `derive_epic_status` and assert result + rule.
2. Build a task set with intentionally wrong `blocks` mirrors; run `reconcile_blocks` and confirm the output matches the `blocked_by` graph.
3. Add a dangling `blocked_by` and confirm the error fires.

## Worklog

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-004 (needs loaded records).
- Blocks TASK-007, TASK-008 (both render derived status).
