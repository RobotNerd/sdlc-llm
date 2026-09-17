---
id: TASK-060
title: "Rework state: 3-strike cap, stale-report guard, second-opinion cap"
type: feature
status: todo
epic: EPIC-004
created: 2026-09-17
branch: task-060-rework-state
pr: null
merge_commit: null
blocked_by: [TASK-059]
blocks: [TASK-063]
---

# TASK-060: Rework state: 3-strike cap, stale-report guard, second-opinion cap

## Description

Blocked on TASK-059 (triage taxonomy) — this bounds the actions it defines.

Per-batch run state in `.tasks/.run/BATCH-<id>.json` tracking, per task: `rework_count` and the
`critic_sha` the most recent critic report was generated against. Three mechanisms:

1. **3-strike cap.** Three rework kickbacks on the *same task* halts the automation entirely and
   prompts the human for clarification — the guardrail you specified directly. This is distinct
   from TASK-042's per-task isolated interrupts: a repeated critic disagreement on one task is
   treated as systemic enough to halt, not skip-and-continue, because it signals the critic and
   worker are stuck in a loop neither can resolve alone.
2. **Stale-report guard.** If `HEAD` has moved past `critic_sha` (e.g. the worker made further
   changes, or a rebase happened) before the orchestrator acts on a report, discard that report
   rather than acting on out-of-date findings — re-run the critic instead.
3. **Second-opinion cap.** At most one second-opinion critic call (TASK-059's action 5) per task,
   ever — never a second second opinion.

## Acceptance criteria

- [ ] A task kicked back by the critic 3 times halts the batch automation and surfaces a clear
      message naming the task and its rework history, rather than attempting a 4th.
- [ ] A critic report whose recorded `critic_sha` doesn't match current `HEAD` is discarded, not
      acted on — the orchestrator re-requests a fresh review instead.
- [ ] A second second-opinion request on the same task is refused, falling through to another
      taxonomy action (e.g. halt-and-ask) instead of looping.
- [ ] State is scoped per batch run (`BATCH-<id>.json`), not global — two different batch runs don't
      share or corrupt each other's rework counts.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the rework counter: increments correctly per kickback, and the 3rd increment
   triggers the halt signal (not the 2nd or 4th — an off-by-one check).
2. Unit tests on the stale-report guard: a report with a `critic_sha` equal to current `HEAD`
   passes through; one with a stale sha is discarded and flagged for re-review.
3. Unit tests on the second-opinion cap: first request allowed, second request for the same task
   refused.
4. Unit test confirming state isolation between two different `BATCH-<id>` fixtures.
5. `python3 -m pytest -q` — full suite green.
6. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- Shares the `.tasks/.run/` state directory with TASK-058's usage tracking — both are ephemeral
  per-run bookkeeping and should be `.gitignore`d together.
- This is the concrete guardrail you asked for directly: "if the critic kicks back the same task 3
  times ... the orchestrator stops the automation and prompts the human user for clarification."
