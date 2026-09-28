---
id: TASK-079
title: "implement-task-v2: context and token usage safety valve"
type: feature
status: todo
epic: EPIC-005
created: 2026-09-23
branch: task-079-v2-usage-valve
pr: null
merge_commit: null
blocked_by: [TASK-077]
blocks: [TASK-081]
---

# TASK-079: implement-task-v2: context and token usage safety valve

## Description

Reimplement v1's usage safety valve as prose (SPEC-005, `interrupts.md` "Usage checkpoint").
Run it at **start task** and **spawn critic**:

1. Estimate `context_pct`.
2. Compute `tokens_used` exactly by summing the session transcript JSONL, using v1's
   `compute_session_token_usage` algorithm.
3. Check context first (`context_usage_halt_pct`), then tokens (`token_budget_per_batch`, if not
   `null`).

Crossing either threshold pauses with `context_usage_exceeded` or `token_budget_exceeded`. If
the transcript can't be read, note it in the Worklog and check context only. The batch report's
Usage section records the final figures.

## Acceptance criteria

- [ ] `interrupts.md` documents the checkpoint: where it runs, how the transcript path is derived, the summing rules (drop streaming partials except the last entry; sum the four token fields), the order of the two checks, and the fallback.
- [ ] `SKILL.md` runs the checkpoint at `start task` and `spawn critic`.
- [ ] Crossing either threshold pauses the batch with the matching kind.
- [ ] An unreadable transcript never pauses; the Worklog notes it.
- [ ] The batch report's Usage section shows the context %, tokens used and the budget (or `no cap`).
- [ ] `test_command` and `sync check` pass.

## Testing strategy

1. Manual: in one session, compare the prose method's token total against v1's `python3 .claude/skills/implement-task/scaffold.py session-token-usage` on the same transcript. They should match.
2. Manual, in a scratch repo: `init-project --target <tmp>`, a local bare repo as `origin`, a few dummy `todo` tasks, and `.claude/skills/implement-task-v2/` copied in: `context_usage_halt_pct: 1` pauses at the first checkpoint with `context_usage_exceeded`.
3. Manual: `token_budget_per_batch: 1` pauses with `token_budget_exceeded`.
4. `.venv/bin/pytest` and `python3 .tasks/bin/sync check` pass.

## Worklog

_(empty — appended during implementation)_

## Notes

- Prose-only means the sum is computed with an ad-hoc command during the run. Scripting it is on SPEC-005's automation-candidate list.
