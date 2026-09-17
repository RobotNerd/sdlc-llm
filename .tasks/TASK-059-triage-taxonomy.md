---
id: TASK-059
title: Critic-report triage taxonomy with a severity floor
type: feature
status: todo
epic: EPIC-004
created: 2026-09-17
branch: task-059-triage-taxonomy
pr: null
merge_commit: null
blocked_by: [TASK-056]
blocks: [TASK-060, TASK-063]
---

# TASK-059: Critic-report triage taxonomy with a severity floor

## Description

Blocked on TASK-056 (critic client) — this interprets its findings output.

Deterministic classification in `.tasks/bin/triage.py`: given a findings list (from TASK-056) and a
severity floor, only `blocker`-severity findings are eligible to trigger rework — `nit`-severity
findings become a follow-up task candidate instead (feeding TASK-044's limiter), which is what
prevents an infinite polish loop. `triage.py classify` is the deterministic half; the orchestrator's
judgment (which of the nine actions below actually applies) stays in the skill (TASK-063), per this
repo's script/judgment split.

Nine possible actions, decided by the orchestrator from `triage.py`'s classification plus context:

1. **Accept/complete** — no blocker findings; proceed.
2. **Rework** — blocker finding(s); send back to the worker with the finding as context.
3. **Rework with escalated effort/model** — a rework that already failed once; escalate one tier
   (via TASK-061's tiering) before trying again, rather than repeating the same attempt.
4. **Create follow-up task** — nit-severity findings, or a blocker judged out of this task's scope;
   routes through TASK-044's per-batch limiter.
5. **Second opinion** — findings conflict with green deterministic-gate results; one additional
   critic call on a different model, capped at 1 (TASK-060 enforces the cap).
6. **Reject the finding with recorded rationale** — the orchestrator judges a finding wrong; logged
   in the Worklog, distinct from silently ignoring it.
7. **Split the task** — findings reveal the task was oversized; hands off to `add-task`-style
   splitting (also under TASK-044's limiter).
8. **Bail out** — reuses `implement-task`'s existing `bail-out` subcommand.
9. **Halt and ask the human** — a genuinely ambiguous case, or a cap already hit.

## Acceptance criteria

- [ ] `triage.py classify` returns a distinct result for "no blocker findings" vs. "blocker findings
      present", and separately surfaces nit-severity findings for follow-up-task routing.
- [ ] The severity floor is configurable (not hardcoded to exactly "blocker"), defaulting to
      blocker-only-triggers-rework.
- [ ] All nine actions are represented as an explicit, named action type the orchestrator can act
      on — not a free-form judgment call with no fixed vocabulary.
- [ ] "Reject the finding with recorded rationale" writes to the task's Worklog, distinguishably
      from a normal accept (auditable, not silent).
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on `triage.py classify` against fixture findings lists: no findings, nit-only,
   blocker-only, mixed severities — confirming the floor is applied correctly in each case.
2. Unit tests confirming each of the nine action types is a distinct, named value the calling code
   can branch on (an enum or equivalent), not stringly-typed ad hoc text.
3. Unit test for the reject-with-rationale path writing a Worklog entry.
4. `python3 -m pytest -q` — full suite green.
5. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- Actions 3, 4, 5, 7, and 9 hand off to other slices/tasks in this epic or in EPIC-003
  (TASK-044's limiter, TASK-060's caps, TASK-061's tiering, `implement-task`'s existing `bail-out`,
  and TASK-042's halt routing respectively) — this task defines the taxonomy and the deterministic
  classification, not those mechanisms themselves.
