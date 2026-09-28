---
id: TASK-076
title: "implement-task-v2: build and validate batches from every argument form"
type: feature
status: todo
epic: EPIC-005
created: 2026-09-23
branch: task-076-v2-build-batch
pr: null
merge_commit: null
blocked_by: [TASK-074]
blocks: [TASK-077, TASK-080]
---

# TASK-076: implement-task-v2: build and validate batches from every argument form

## Description

Implement the optional `[tasks|range|stopping-task|epic]` argument and all of **build batch**:

- The agent parses the free-form argument. Ambiguous → ASK.
- Resolution uses the board's hand-ordered TODO list, in board order for every mode, including
  epic mode.
- Validation runs before any work (see the acceptance criteria).

Add the batch state file `.tmp/batch-state-v2.json` (gitignored) with SPEC-005's schema: order,
`active_task`, `step` (the human-readable step name), and per-task status. Steps 4–10 loop over
every task in the batch. `merge changes` marks each task merged. `batch complete` deletes the
state, and its report lists every task in the batch.

## Acceptance criteria

- [ ] Every argument form in SPEC-005 §Design "Parameter" resolves to the right tasks in board order: none, a list (ids or bare numbers), a range, a stopping task, an epic.
- [ ] An ambiguous or unparseable argument gets an ASK, never a guessed mode.
- [ ] Each validation failure stops before any change, with a clear reason: already implemented, task does not exist, task blocked (outside the batch, or ordered after the task it blocks), wrong order for range, no stopping task, no tasks found.
- [ ] `.tmp/batch-state-v2.json` is written after validation and is gitignored. `step` always holds the name of the step in progress.
- [ ] A multi-task batch runs steps 4–10 for each task in order, and the batch report lists them all.
- [ ] The batch state is deleted when the batch completes.
- [ ] `test_command` and `sync check` pass.

## Testing strategy

1. Manual, in a scratch repo: `init-project --target <tmp>`, a local bare repo as `origin`, a few dummy `todo` tasks, and `.claude/skills/implement-task-v2/` copied in with about 5 dummy tasks (some blocked, one in an epic): run each argument form and confirm the announced order.
2. Manual: trigger each of the six validation failures. Each stops with its reason and leaves `git status` clean.
3. Manual: while a 2-task batch runs, inspect `.tmp/batch-state-v2.json` between steps and confirm `step` matches the current step name.
4. `.venv/bin/pytest` and `python3 .tasks/bin/sync check` pass.

## Worklog

_(empty — appended during implementation)_

## Notes

- v1's `batch_select.py` shows the validation rules, but it isn't used here; v2 is prose-only. Epic mode deliberately changes from v1's id order to board order.
