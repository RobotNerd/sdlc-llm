---
id: TASK-044
title: Follow-up task creation policy with a configurable per-batch limit
type: feature
status: in-progress
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

- [x] `autonomous_new_task_limit` exists in `config.md`, default `3`.
- [x] The LLM can create a follow-up task mid-batch without stopping to ask, up to the limit.
- [x] Reaching the limit stops further autonomous task creation for the rest of the batch, flags
      the remaining need(s) in the summary, and does not halt the batch.
- [x] `autonomous_new_task_limit: null` removes the cap entirely.
- [x] Every task created this way appears correctly in `.tasks/BOARD.md` after `sync` (same
      mechanics as a human-run `add-task`).
- [x] The end-of-batch summary lists every follow-up task created, with why.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the limiter: under the limit creates normally; at the limit refuses further
   creation and flags instead; `null` never refuses.
2. Integration test: a scratch batch where one task is deliberately oversized, confirming the
   resulting split-off task is written correctly and placed sensibly in TODO, then `sync` and
   `sync check` both succeed.
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

- Tests first (31 failing for the expected reasons: helpers/subcommands/`follow_ups` key absent), then implemented; all green. Full suite 745 passed, `sync check` exit 0.
- Limiter: `check_follow_up_limit(created, limit)` -- `None` never refuses, `0` disables, a non-integer/negative/bool limit raises `ValueError` (a mistyped config value fails loudly rather than silently uncapping). Missing key defaults to 3 (`DEFAULT_FOLLOW_UP_LIMIT`).
- Ledger: optional `follow_ups` list in `.tmp/batch-state.json` (so the count survives a lost session); files written before the key existed read back with `[]`. `batch_progress` and `batch-update`'s completion result carry it, since the file is deleted at the end and the summary still needs it.
- `create-follow-up` reuses `add-task`'s own `run` as a subprocess (resolved at the same fixed relative offset `guardrails.py` uses), finding the new file via `sync next-id task` beforehand -- no add-task changes, no output parsing. Refuses (exit 2) outside an active batch; an add-task failure is surfaced and records nothing. At the limit: nothing created, a `created: false` entry recorded, exit 0 -- isolated, the batch continues.
- Human decisions at plan approval: placement defaults to the **bottom** of TODO (`priority_mode: "end"`) and the epic defaults to **unassigned** unless the work clearly fits an existing one (the human prioritizes after the batch) -- instead of the task text's "immediately after the original", which add-task can't do while the parent is in-progress (not in TODO). The new task file stays on the current task's branch and goes into that task's `wrap-up` `paths`/PR (documented in SKILL.md's new "Follow-up tasks" section).
- Summary: `render_follow_up_summary` / `render-follow-up-summary` (created table with why + origin; flagged list under "needs a human"), wired into SKILL.md's batch-end step and the systemic-halt path.
- Config: `autonomous_new_task_limit: 3` added to `templates/config.md` and this repo's `.tasks/config.md` with Key notes; `init-project`'s generic `migrate-config` picks it up for existing projects. `test_init_project_upgrade.py`: `_CURRENT_CONFIG` updated, two position assertions shifted, new migration test.
- Testing strategy step 2's "scratch batch with an oversized task" is covered by the `repo`-fixture CLI tests (batch-init -> create-follow-up -> board placement, `sync check` clean, limit/flag/null/absent-key cases).

## Notes

- Reuses `add-task`'s own file-writing mechanics rather than reinventing them.
