---
id: TASK-017
title: "refine-backlog skill: periodic lightweight backlog pass"
type: feature
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-017-skill-refine-backlog
pr: null
merge_commit: null
blocked_by: [TASK-009]
blocks: []
---

# TASK-017: refine-backlog skill: periodic lightweight backlog pass

## Description

A short periodic pass (not a ceremony): confirm/reorder TODO priority with the user, recompute blocked status via `sync`, surface stale `todo` tasks as `wont-do` candidates, and flag under-specified tasks for another `add-task`-style pass (SPEC-001 §`refine-backlog`).

## Acceptance criteria

- [ ] Skill is a checklist with STOP markers; it proposes changes and waits for the user rather than acting unilaterally on priority.
- [ ] Runs `sync` to recompute `blocked` / `blocks` and epic status — does not hand-edit them.
- [ ] Lists `todo` tasks whose `created` date is old as `wont-do` candidates, with the user deciding.
- [ ] Flags tasks lacking concrete acceptance criteria or a testing strategy for re-refinement.
- [ ] Any TODO reordering is applied by editing the hand-maintained list, then `sync` — which must preserve the new order.

## Testing strategy

1. Run against the current board; confirm it reports the blocked chain (e.g. TASK-004 → TASK-006 → …) and proposes nothing destructive without confirmation.
2. Backdate a fixture task's `created`; confirm it shows up as a `wont-do` candidate.
3. Reorder two TODO lines through the skill; confirm `sync check` stays clean and the order holds.

## Worklog

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-009 (relies on the TODO-merge semantics being settled).
- Independent of the other skills.
