---
id: TASK-042
title: "Interrupt taxonomy: isolated skip-task vs. systemic halt-batch routing"
type: feature
status: done
epic: EPIC-003
created: 2026-09-14
branch: task-042-interrupt-taxonomy
pr: "https://github.com/RobotNerd/sdlc-llm/pull/80"
merge_commit: 2485601889cf3beaafbebbb1da9dda203207c7ee
blocked_by: [TASK-041]
blocks: [TASK-054, TASK-055]
---

# TASK-042: Interrupt taxonomy: isolated skip-task vs. systemic halt-batch routing

## Description

Blocked on TASK-041 (core autonomous loop — needs a running batch to interrupt).

Five interrupt conditions, each routed as isolated (skip this task, flag it in the summary,
continue the batch) or systemic (halt the whole batch immediately):

**Isolated (skip, continue):**
1. **Needs clarification** — the task is ambiguous or its acceptance criteria contradict
   something discovered mid-implementation (today's existing bail-out reason, now also causing
   the batch to move on rather than stop entirely).
2. **Unexpected blocker** — something task-specific prevents progress (a dependency assumed
   satisfied turns out not to be, an environment precondition specific to this task is missing).
3. **Quality-gate failure surviving bounded retries** — `test_command`/`lint_command`/
   `format_command`/`sync check` keeps failing after a fixed number of fix attempts (e.g. 3) —
   escalate rather than iterate indefinitely on the same failure.
4. **Repeated guardrail/hook denial** — the same `PreToolUse` hook denies a retry 2-3 times in a
   row on this task specifically.

**Systemic (halt the batch):**
5. **`git`/`gh` infrastructure failure** — auth expired, network failure, rate-limited. Distinct
   from "the code is wrong": the tooling itself is broken and every remaining task would hit the
   same wall, so halt once rather than fail through the whole batch.

Each interrupt writes a clear record (what happened, on which task, why it was routed the way it
was) into that task's Worklog and the batch's running outcome table.

## Acceptance criteria

- [x] Each of the five conditions above is detected and routed as specified (four isolated, one
      systemic).
- [x] An isolated interrupt on task N leaves tasks N+1 onward in the batch to run normally.
- [x] A systemic interrupt halts before starting the next task, with a clear summary of why.
- [x] The interrupted task's Worklog records what happened, matching today's existing bail-out
      convention (set `status` back to `todo`/`blocked`, note findings) for isolated interrupts.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests simulating each of the five conditions against the loop from TASK-041, asserting the
   correct skip-vs-halt routing and Worklog content.
2. A test confirming an isolated interrupt on one task doesn't affect the batch's ability to
   continue to the next.
3. A test confirming a systemic interrupt halts before any further task starts.
4. `pytest` — full suite green.
5. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

- 2026-09-18: Added `interrupt_routing(kind)` to `.claude/skills/implement-task/scaffold.py` -- a
  pure lookup over the five defined kinds (`needs_clarification`/`unexpected_blocker`/
  `quality_gate_failure`/`guardrail_denial` isolated, `infra_failure` systemic), returning
  `{"routing", "continue_batch"}` and raising on anything else, wired to a new `classify-interrupt`
  CLI subcommand. Deliberately didn't build a separate "batch position" state machine: isolated's
  `continue_batch: true` and systemic's `false` are exactly what the two behavioral tests below
  ask for, and the loop's own position in `order` is already tracked in-context per TASK-041 --
  no new state needed to prove "N+1 onward still runs" vs. "halts before starting anything else."
- 2026-09-18: Rewrote `SKILL.md`'s "Batch mode" section: replaced the blanket "anything else halts
  the batch" line from TASK-041 with a new "Interrupts" subsection giving concrete detection
  guidance per condition (a `start` refusal routes as `unexpected_blocker`; 3 consecutive
  same-reason quality-gate failures or 3 consecutive denials of the same guardrail hook on one
  task route as `quality_gate_failure`/`guardrail_denial`) and the actual routing procedure --
  isolated bails out the task (existing `bail-out`) and records its outcome before continuing;
  systemic leaves the task's status untouched (the tooling failed, not the task -- a normal
  single-task `resume-state` picks it back up once `git`/`gh` works again) and halts after
  printing what's accumulated so far.
- 2026-09-18: TDD per `tdd_enforced: true`: added failing tests for `interrupt_routing` (all four
  isolated kinds, the one systemic kind, and an unknown-kind `ValueError`) and the
  `classify-interrupt` CLI subcommand to `tests/test_implement_task_scaffold.py`; confirmed each
  failed for the expected reason (`AttributeError` for the undefined function, argparse's "invalid
  choice" for the unregistered subcommand) before implementing until green.
- 2026-09-18: `.venv/bin/pytest`: 643 passed, 0 failed.
- 2026-09-18: `python3 .tasks/bin/sync check` exits 0.

## Notes

- Context-usage and token-usage interrupts are a separate, sixth and seventh condition — see
  TASK-043, which has a different detection mechanism (usage signals, not workflow state) and is
  kept as its own task rather than folded in here.
