---
id: TASK-015
title: "add-task skill: interview, epic prompt, size check, priority placement"
type: feature
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-015-skill-add-task
pr: null
merge_commit: null
blocked_by: [TASK-002, TASK-010]
blocks: [TASK-018]
---

# TASK-015: add-task skill: interview, epic prompt, size check, priority placement

## Description

A skill that turns a rough description into a well-formed `TASK-*.md`: interviews for concrete acceptance criteria and a testing strategy, allocates the ID via `sync next-id`, prompts for epic assignment, size-checks against one-PR, and asks where the task ranks in TODO (SPEC-001 §`add-task`).

## Acceptance criteria

- [ ] Skill is a checklist with STOP markers; if the description yields no concrete acceptance criteria or testing strategy, it asks follow-ups before writing anything.
- [ ] Allocates the ID with `sync next-id task` — never by counting files itself.
- [ ] Epic prompt offers: attach to an existing open epic (lists them), create a new epic now, or leave unassigned.
- [ ] Size check: if the work looks larger than one PR / one sitting, it proposes a split and stops.
- [ ] Asks for TODO rank rather than always appending; inserts the line at that position.
- [ ] Writes the file from `.tasks/templates/task.md`, then runs `sync`.

## Testing strategy

1. Feed a vague one-liner; confirm the skill asks follow-ups and does not create a file until criteria exist.
2. Feed a well-specified task with an epic; confirm ID allocation, epic link, TODO insertion at the requested rank, and a clean `sync check` after.
3. Feed an oversized task; confirm the split proposal.

## Worklog

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-002 (task template) and TASK-010 (`next-id`).
- Blocks TASK-018 (`plan-feature` fans out to `add-task`).
