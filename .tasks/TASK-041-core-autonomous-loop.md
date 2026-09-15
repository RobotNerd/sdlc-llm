---
id: TASK-041
title: "Core autonomous loop: iterate a validated batch without manual re-invocation"
type: feature
status: todo
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
      real human action — polling detects it, nothing bypasses it).
- [ ] Phase 1's plan is printed for every task in the batch without a blocking STOP.
- [ ] The loop uses `ScheduleWakeup` (not a tight polling loop) to wait for each merge.
- [ ] A basic per-task outcome table (id, title, status, PR/merge-commit link) is produced once the
      batch ends.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the outcome-accumulation and per-task announce-not-block logic.
2. Scratch-branch dry run (throwaway branches off `origin/main`, deleted — not merged — when
   done): a batch of 2-3 trivial scratch tasks run end-to-end, confirming the loop advances after
   each merge without a fresh invocation and the final outcome table is accurate. Human-run —
   record in the Worklog, since real merges and real polling can't be meaningfully mocked.
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- TASK-042 (interrupts), TASK-043 (context/token safety-valve), TASK-044 (follow-up tasks), and
  TASK-045 (critic + auto-merge) all build on this loop.
