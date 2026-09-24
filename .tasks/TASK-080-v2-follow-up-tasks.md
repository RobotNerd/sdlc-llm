---
id: TASK-080
title: "implement-task-v2: autonomous follow-up tasks with a creation limit"
type: feature
status: todo
epic: EPIC-005
created: 2026-09-23
branch: task-080-v2-follow-up-tasks
pr: null
merge_commit: null
blocked_by: [TASK-076]
blocks: [TASK-081]
---

# TASK-080: implement-task-v2: autonomous follow-up tasks with a creation limit

## Description

Add `references/follow-up-tasks.md` (SPEC-005), and make follow-up creation work at any point
in a batch.

- **When**: the current task is too large to finish, or out-of-scope work is discovered.
- **How**: use the `add-task` skill with every answer pre-supplied, so it never asks.
  `priority_mode` is `"end"`; `epic` is `null` unless the task clearly fits an existing epic.
  The new task is created on the current task branch, so it lands in that task's squash commit.
- **Splits**: move the out-of-scope criteria to the new task and note the split.
- **Limit**: `autonomous_new_task_limit` caps creation per batch (`null` = no cap, `0` = never).
  Past the cap, record a recommendation instead.
- Everything is recorded in the batch state's `follow_ups` and shown in both reports.

## Acceptance criteria

- [ ] `references/follow-up-tasks.md` covers when, how, splitting, the limit, and the fact that creation is fully autonomous.
- [ ] A follow-up is created without any question to the human, at the bottom of TODO, with `epic: null` unless it clearly fits one. It's included in the parent task's squash commit.
- [ ] At the limit, nothing is created, a `created: false` recommendation is recorded, and the batch keeps going.
- [ ] The per-task and batch reports list created tasks (with id, title, why, parent) and recommendations not created.
- [ ] `test_command` and `sync check` pass.

## Testing strategy

1. Manual, in a scratch repo: `init-project --target <tmp>`, a local bare repo as `origin`, a few dummy `todo` tasks, and `.claude/skills/implement-task-v2/` copied in: a dummy task that states an out-of-scope need produces a new task at the bottom of TODO, inside the parent's squash commit.
2. Manual: with `autonomous_new_task_limit: 1` and two needs, one task is created and one is recommended. Check both reports.
3. Manual: with `autonomous_new_task_limit: 0`, only recommendations appear.
4. `.venv/bin/pytest` and `python3 .tasks/bin/sync check` pass.

## Worklog

_(empty — appended during implementation)_

## Notes

- v1 did this with `scaffold.py create-follow-up`. v2 drives `add-task` directly, since it's prose-only.
