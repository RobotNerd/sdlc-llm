---
id: TASK-043
title: Context/token usage safety-valve interrupt + usage reporting
type: feature
status: todo
epic: EPIC-003
created: 2026-09-14
branch: task-043-context-token-safety-valve
pr: null
merge_commit: null
blocked_by: [TASK-041]
blocks: [TASK-054, TASK-055, TASK-064]
---

# TASK-043: Context/token usage safety-valve interrupt + usage reporting

## Description

Blocked on TASK-041 (core autonomous loop).

Deliberately minimal, per SPEC-003's Non-goals: this task does not solve context-window
management — it adds a cheap guardrail and honest reporting as a stopgap until a dedicated future
spec/epic covers the real strategy (per-task session boundaries, compaction, summarization).

Two configurable thresholds (new `.tasks/config.md` keys):
- `context_usage_halt_pct` — halt the batch (systemic interrupt, per TASK-042's taxonomy) if
  context usage crosses this percentage mid-task. Default a conservative value (e.g. `85`).
- `token_budget_per_batch` — an optional cap on tokens spent in one batch run; `null` (default) =
  no cap. If set and crossed, halt the batch the same way.

Both checks happen between tasks (and, where practical, at natural checkpoints within a task —
after phase 2, before phase 3) rather than continuously, to keep the check itself cheap.

Also: track and report actual usage (context percentage at halt or at batch end; total
tokens/approximate cost for the run) as part of the end-of-batch summary from TASK-041, regardless
of whether a threshold was ever crossed — directly actionable for a human deciding whether
auto-merge/critic (TASK-045) is worth its cost on their plan tier.

## Acceptance criteria

- [ ] `context_usage_halt_pct` and `token_budget_per_batch` exist in `config.md` with sensible
      defaults (a conservative percentage; `null` for no token cap).
- [ ] Crossing either threshold halts the batch as a systemic interrupt, with a clear message
      naming which threshold and its value.
- [ ] The end-of-batch summary reports actual usage for the run even when no threshold was
      crossed.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the threshold-check functions against synthetic usage figures.
2. A test confirming the halt message names the specific threshold crossed.
3. A test confirming the summary includes usage figures on a run that never crosses either
   threshold.
4. `pytest` — full suite green.
5. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- This is explicitly a stopgap (SPEC-003 Non-goals) — a real context-management strategy is a
  future spec/epic, not this task's job.
