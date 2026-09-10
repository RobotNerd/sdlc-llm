---
id: TASK-018
title: "plan-feature skill: spec -> epics -> vertical-slice tasks"
type: feature
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-018-skill-plan-feature
pr: null
merge_commit: null
blocked_by: [TASK-015]
blocks: []
---

# TASK-018: plan-feature skill: spec -> epics -> vertical-slice tasks

## Description

Requirements-gathering skill. Interviews for the 'why', writes a `SPEC-*.md` in `.tasks/specs/` (problem, alternatives, non-goals), decomposes the feature into vertical slices capturing `blocked_by`/`blocks`, groups slices under one or more epics linked to the spec, then fans out to `add-task` per slice (SPEC-001 §`plan-feature`).

## Acceptance criteria

- [ ] Skill is a checklist with STOP markers, including a checkpoint on the spec draft before any tasks are created.
- [ ] Produces a `SPEC-*.md` from the template via `sync next-id spec`, with Problem / Goals / Non-goals / alternatives sections.
- [ ] Decomposes into vertical slices — each independently shippable and testable — not horizontal phases; records `blocked_by`/`blocks` between slices.
- [ ] Creates one or more `EPIC-*.md` (via `sync next-id epic`) with `spec:` set, then calls `add-task` for each slice with the epic pre-selected.
- [ ] Ends with `sync` and a clean `sync check`; the new epic appears in the board `epics` panel.

## Testing strategy

1. Run `plan-feature` on a sample feature; confirm a spec file, at least one epic, and several linked tasks are created, and the dependency graph among the new tasks is acyclic.
2. Confirm the spec checkpoint STOP halts before tasks are generated.
3. Confirm the new epic's `children` region and the board `epics` panel populate after `sync`.

## Worklog

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-015 (`add-task` is the fan-out target).
- This skill is how future work (beyond MVP) enters the system.
