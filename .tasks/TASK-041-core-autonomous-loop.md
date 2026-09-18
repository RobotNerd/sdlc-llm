---
id: TASK-041
title: "Core autonomous loop: iterate a validated batch without manual re-invocation"
type: feature
status: in-progress
epic: EPIC-003
created: 2026-09-14
branch: task-041-core-autonomous-loop
pr: null
merge_commit: null
blocked_by: [TASK-039]
blocks: [TASK-042, TASK-043, TASK-044, TASK-045]
---

# TASK-041: Core autonomous loop: iterate a validated batch without manual re-invocation

## Description

Blocked on TASK-039 (batch selection + validation — needs a concrete, ordered, validated task
list to iterate).

For each task in the validated batch, in order:

1. Run `implement-task` phases 1-2 as today, except phase 1's plan/acceptance-criteria restatement
   is **announced, not blocking** — printed for the visible record, but the batch itself was the
   approval, so work proceeds without waiting on a fresh STOP.
2. Phase 3 (wrap up, open PR) proceeds as today.
3. Instead of ending the run and requiring manual re-invocation once the PR is open (today's
   phase-4 "event-driven, don't loop" behavior), **self-schedule** via this harness's
   `ScheduleWakeup` to poll `gh pr view --json state,mergeCommit` and resume automatically once
   merged — still never auto-merging by default; a human still reviews and merges every PR unless
   TASK-045's opt-in critic-gated auto-merge is enabled and configured.
4. Once merged, run phase 4's existing bookkeeping, then move to the next task in the batch.
5. Accumulate a basic per-task outcome record (id, title, final status, PR/merge-commit link) as
   the batch progresses.

At the end of the batch (all tasks done, or the batch halts — see TASK-042), print the
accumulated per-task outcome table. This is the summary's first version; TASK-043 and TASK-045
extend it with more sections.

## Acceptance criteria

- [ ] The batch loop runs phases 1-4 for each task in the validated order with no required human
      input between a PR opening and the next task starting (verified by the merge still being a
      real human action — polling detects it, nothing bypasses it). *(implemented; live
      verification is the deferred scratch-branch dry run below)*
- [x] Phase 1's plan is printed for every task in the batch without a blocking STOP.
- [x] The loop uses `ScheduleWakeup` (not a tight polling loop) to wait for each merge.
- [x] A basic per-task outcome table (id, title, status, PR/merge-commit link) is produced once the
      batch ends.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the outcome-accumulation and per-task announce-not-block logic.
2. Scratch-branch dry run (throwaway branches off `origin/main`, deleted — not merged — when
   done): a batch of 2-3 trivial scratch tasks run end-to-end, confirming the loop advances after
   each merge without a fresh invocation and the final outcome table is accurate. Human-run —
   record in the Worklog, since real merges and real polling can't be meaningfully mocked.
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

- 2026-09-18: Added `stop_required_for_phase1`/`record_outcome`/`render_outcome_table` to
  `.claude/skills/implement-task/scaffold.py` -- pure functions, wired into `cmd_start` (a new
  optional `batch_mode` answer, surfaced as `stop_required` in `start`'s output) and two new thin
  CLI subcommands, `record-outcome`/`render-outcome-table`. Rewrote `SKILL.md`: a batch-parameter
  alternative to the single-task-id parameter, a batch-mode carve-out on the STOP-semantics list,
  and a new "Batch mode" section describing the per-task loop -- `batch_select.py select` up
  front (refuse-and-STOP on an invalid selection), phase 1 announced instead of blocked, phase 3
  unchanged through PR-open, then `ScheduleWakeup` in place of phase 3's hard STOP (re-running
  `finish-merge` on each wake, rescheduling on `merged: false`, advancing to the next task on
  `merged: true`), and every other single-task STOP (phase 2 decision, rebase conflict,
  `phase4_closed_not_merged`, `ambiguous`) still halting the whole batch. Deliberately did not add
  a persistent batch-state file: `ScheduleWakeup` resumes the same session/conversation rather
  than starting a fresh process, so the remaining `order` and the outcomes accumulator survive in
  context across a wait; recovering batch progress from repo state alone after a lost session is
  an open gap, not required by this task's acceptance criteria, and not claimed by any of
  TASK-042/043/044/045 either.
- 2026-09-18: Step 1 -- TDD per `tdd_enforced: true`: added failing tests for the three new pure
  functions plus `cmd_start`'s new `stop_required` output and the two new CLI subcommands to
  `tests/test_implement_task_scaffold.py`, confirmed each failed for the expected reason
  (`AttributeError` for the not-yet-defined functions, `KeyError` for the missing `stop_required`
  key, argparse's "invalid choice" for the two unregistered subcommands), then implemented until
  green.
- 2026-09-18: A first pass leaked this task's own id into two new docstrings in `scaffold.py`,
  caught by the same portable-surface test suite TASK-039's Worklog flagged -- reworded both
  before re-running the suite (same class of mistake, same fix).
- 2026-09-18: Step 2 (scratch-branch dry run) is genuinely human-run and real (live PRs/merges
  against `origin`) -- deferred to the human to run separately rather than in this session; not
  checked off below pending that run.
- 2026-09-18: Step 3 -- `.venv/bin/pytest`: 634 passed, 0 failed.
- 2026-09-18: Step 4 -- `python3 .tasks/bin/sync check` exits 0.

## Notes

- TASK-042 (interrupts), TASK-043 (context/token safety-valve), TASK-044 (follow-up tasks), and
  TASK-045 (critic + auto-merge) all build on this loop.
