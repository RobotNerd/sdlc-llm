---
id: TASK-070
title: "Persistent batch state: recover batch progress from repo state after a lost session"
type: feature
status: in-review
epic: EPIC-003
created: 2026-09-19
branch: task-070-persistent-batch-state-recover-batch-progress-from-repo-state-after-a-lost-session
pr: "https://github.com/RobotNerd/sdlc-llm/pull/84"
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-070: Persistent batch state: recover batch progress from repo state after a lost session

## Description

Closes the gap TASK-041's own Worklog named and deliberately deferred:

> No persistent batch-state file: `ScheduleWakeup` resumes the same session/conversation rather
> than starting a fresh process, so the remaining task order and the outcomes accumulator survive
> in context across a wait. Recovering batch progress from repo state alone after a lost session
> is an open gap, not required by this task and not claimed by any of TASK-042/043/044/045 either.

Today, a batch's `order` (from `batch_select.py`) and its outcomes accumulator (`record-outcome`)
exist only in the running session's own conversation context. If that session is lost — closed,
crashed, or simply not the one that comes back — a fresh `/implement-task` invocation has no way to
know a batch was in flight at all: `resume-state` only ever looks for a single in-progress/in-review
task, never "a batch with N more tasks queued after this one."

Add a small, local, git-ignored batch-state file (e.g. `.tmp/batch-state.json` — not `.tasks/`,
since this is pure runtime state, never meant to be committed or reviewed, unlike everything else
this toolkit tracks) that the batch loop writes/updates at each step: the original batch selection,
the resolved `order`, which of those tasks are already accounted for, and the outcomes accumulator
so far. Wire a batch-aware check into (or alongside) `resume-state` — when this file exists and
names an active batch, a fresh session resumes the batch (continuing at the right task in `order`,
in the right phase) instead of `resume-state`'s existing single-task-only view, and instead of
`start`'s auto-pick-top-of-TODO default. Clean the file up once the batch completes or halts, so a
finished run never confuses a later plain single-task invocation.

This only fixes the "lost conversation, same working directory" case (which is the actual scope of
"a lost session" in this harness) — it does not attempt cross-machine/cross-checkout recovery,
since the state file is intentionally local and untracked.

## Acceptance criteria

- [x] A batch-state file records the original batch selection, the resolved `order`, per-task
      completion state, and the accumulated outcomes — updated at each step of the batch loop
      (`SKILL.md`'s "Batch mode"), not only at the end.
- [x] The file is git-ignored / never committed, and never counts as a dirty-tree blocker for
      `start`'s phase-1 check (same posture as `ignored_paths` already gives `.tmp/prompts.md`).
- [x] A fresh session invoking `/implement-task` with no parameters, when this file names an active
      batch, resumes that batch — at the correct task and phase — instead of auto-picking the top
      of TODO or reporting single-task `resume-state`'s narrower view.
- [x] The file is removed once the batch completes (every task in `order` accounted for) or halts
      (a systemic interrupt fires) — a later plain invocation never sees stale batch state.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the batch-state file's read/write/update functions (pure functions given a path,
   no real batch loop needed) — round-trips, in-place updates as tasks complete, correct shape.
2. Unit tests on the batch-aware resume check: given a present, active batch-state file, returns
   the right "resume here" info; given none, falls through to today's unchanged single-task
   `resume-state`/`start` behavior.
3. Unit test confirming the file is deleted on batch completion and on a systemic-halt path.
4. `pytest` — full suite green.
5. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

- Tests first (18 failing for the expected reason: helpers/subcommands absent), then implemented; full suite 676 passed, `sync check` exit 0.
- State file: `.tmp/batch-state.json` = `{selection, order, accounted, outcomes}`. New `scaffold.py` helpers (`new_batch_state`/`read_batch_state`/`write_batch_state`/`advance_batch_state`/`batch_progress`/`batch_is_complete`/`clear_batch_state`) and subcommands `batch-init`/`batch-update`/`batch-clear`. `batch-update` deletes the file itself when the last task is accounted for; `batch-clear` handles a systemic halt.
- `resume-state` adds a `batch` key (`next_task_id`, `remaining`, `outcomes`, ...) whenever the file is valid; phase detection itself is unchanged. A corrupt/incomplete file reads as "no batch".
- Never-dirty posture: the path is added to `.gitignore` *and* always appended to the dirty-tree ignore list (`effective_ignored_paths`) in `resume-state`/`start`/`wrap-up`, so it holds even in a vendored project whose `.gitignore` lacks it.
- A task's provisional `in-review` outcome is replaced in place by its final `done` row rather than duplicated.
- Design note: a systemic halt clears the file (per the ACs), so the rest of `order` isn't remembered after one -- the interrupted task resumes as a plain single-task `resume-state`.
- Testing strategy steps 1-5 all automated; nothing needed the human's hands.

## Notes

- Directly closes the open gap named in `TASK-041`'s own Worklog (see `.tasks/archive/`).
- Scope is deliberately narrower than general context-window/session-management strategy (that
  remains a future spec/epic, per `SPEC-003`'s own Non-goals) — this is just enough state to
  survive losing the conversation, not a general checkpoint/resume framework.
