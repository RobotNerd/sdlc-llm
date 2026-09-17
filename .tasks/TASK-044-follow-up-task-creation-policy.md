---
id: TASK-044
title: Follow-up task creation policy with a configurable per-batch limit
type: feature
status: todo
epic: EPIC-003
created: 2026-09-14
branch: task-044-follow-up-task-creation-policy
pr: null
merge_commit: null
blocked_by: [TASK-041]
blocks: [TASK-054, TASK-055]
---

# TASK-044: Follow-up task creation policy with a configurable per-batch limit

## Description

Blocked on TASK-041 (core autonomous loop).

When the LLM determines mid-batch that a task is too big and needs splitting (or a genuinely new
piece of follow-up work is discovered), it creates the new task(s) itself — following the same
mechanics `add-task` already uses (allocate id via `sync next-id task`, write from
`.tasks/templates/task.md`, run `sync`) — rather than stopping to ask, up to a limit.

New `.tasks/config.md` key: `autonomous_new_task_limit`, default `3`, `null` = unlimited. Once the
limit is reached within a batch run, stop creating further new tasks: flag the remaining
oversized/split-needing task(s) in the end-of-batch summary for the human to handle (e.g. via
`add-task` or `refine-backlog`), but keep working every other unaffected task in the batch — this
is an isolated condition (per TASK-042's taxonomy), not a reason to halt.

Every autonomously created task gets a `blocked_by`/priority placement consistent with why it was
created (e.g. a split-off piece of the original task is placed immediately after it in TODO), and
is recorded in the end-of-batch summary regardless of whether the limit was hit.

## Acceptance criteria

- [ ] `autonomous_new_task_limit` exists in `config.md`, default `3`.
- [ ] The LLM can create a follow-up task mid-batch without stopping to ask, up to the limit.
- [ ] Reaching the limit stops further autonomous task creation for the rest of the batch, flags
      the remaining need(s) in the summary, and does not halt the batch.
- [ ] `autonomous_new_task_limit: null` removes the cap entirely.
- [ ] Every task created this way appears correctly in `.tasks/BOARD.md` after `sync` (same
      mechanics as a human-run `add-task`).
- [ ] The end-of-batch summary lists every follow-up task created, with why.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the limiter: under the limit creates normally; at the limit refuses further
   creation and flags instead; `null` never refuses.
2. Integration test: a scratch batch where one task is deliberately oversized, confirming the
   resulting split-off task is written correctly and placed sensibly in TODO, then `sync` and
   `sync check` both succeed.
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- Reuses `add-task`'s own file-writing mechanics rather than reinventing them.
