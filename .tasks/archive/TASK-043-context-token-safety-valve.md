---
id: TASK-043
title: Context/token usage safety-valve interrupt + usage reporting
type: feature
status: done
epic: EPIC-003
created: 2026-09-14
branch: task-043-context-token-safety-valve
pr: "https://github.com/RobotNerd/sdlc-llm/pull/81"
merge_commit: 97d6afd3e76f996ab3c7d03a51344d90bf9f8b37
blocked_by: [TASK-041]
blocks: [TASK-054, TASK-055, TASK-064, TASK-068]
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

- [x] `context_usage_halt_pct` and `token_budget_per_batch` exist in `config.md` with sensible
      defaults (a conservative percentage; `null` for no token cap).
- [x] Crossing either threshold halts the batch as a systemic interrupt, with a clear message
      naming which threshold and its value.
- [x] The end-of-batch summary reports actual usage for the run even when no threshold was
      crossed.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the threshold-check functions against synthetic usage figures.
2. A test confirming the halt message names the specific threshold crossed.
3. A test confirming the summary includes usage figures on a run that never crosses either
   threshold.
4. `pytest` — full suite green.
5. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

- 2026-09-18: This harness exposes no tool that reports exact context-window percentage or
  cumulative token count to a script or to the model directly — confirmed by checking the
  available/deferred tool list before designing this. So `context_pct`/`tokens_used` are the
  model's own best-effort estimate at each checkpoint, not a real measurement; documented plainly
  in `SKILL.md` and `.tasks/config.md`'s Key notes rather than implying more precision than
  exists. Deliberately left out a fabricated dollar-cost figure (Description mentions
  "approximate cost", but the AC only asks for context % + tokens) -- no reliable in-repo pricing
  table to compute one from without risking a stale/misleading number.
- 2026-09-18: Added `check_usage_thresholds`/`render_usage_summary` to
  `.claude/skills/implement-task/scaffold.py` (context checked before the token budget; message
  names the specific value and threshold crossed), wired to new `check-usage-thresholds`/
  `render-usage-summary` CLI subcommands. Extended `interrupt_routing`'s systemic set with
  `context_usage_exceeded`/`token_budget_exceeded` (TASK-042's `classify-interrupt` already
  recognizes them, no changes needed there beyond the set).
- 2026-09-18: Added `context_usage_halt_pct: 85` / `token_budget_per_batch: null` to
  `init-project`'s `templates/config.md` as fixed, non-interview defaults -- same posture as
  `allow_auto_merge`/`ignored_paths` (`REQUIRED_KEYS` deliberately excludes them; `migrate-config`
  picks up new template keys generically, no code changes needed for existing projects to gain
  them). Added both to this repo's own `.tasks/config.md` by hand, same precedent `tdd_enforced`
  set. Updated `test_init_project_upgrade.py`'s `_CURRENT_CONFIG` fixture (now genuinely current)
  and two position assertions that shifted as a result, plus a new dedicated migration test for
  the pair.
- 2026-09-18: Rewrote `SKILL.md`'s Batch mode section: a usage checkpoint before each task starts
  and again after phase 2/before phase 3 (per the Description's own checkpoint timing), routed
  through "Interrupts" on a halt; batch-end summary now prints `render-usage-summary` alongside
  TASK-041's `render-outcome-table` unconditionally.
- 2026-09-18: TDD per `tdd_enforced: true`: added failing tests for `check_usage_thresholds`
  (under-both/context-over/token-over/no-cap/context-checked-first) and `render_usage_summary`,
  the `interrupt_routing` extension, and all three new CLI subcommands' wiring; confirmed each
  failed for the expected reason before implementing until green.
- 2026-09-18: A first pass leaked `SPEC-003`/`TASK-045` references into two new `scaffold.py`
  docstrings, caught by the same portable-surface test suite TASK-039/041's Worklogs already
  flagged -- reworded both before re-running the suite (same recurring mistake, same fix; worth
  remembering to grep for `TASK-`/`EPIC-`/`SPEC-` in new `scaffold.py` prose before the first
  test run, not after).
- 2026-09-18: `.venv/bin/pytest`: 656 passed, 0 failed.
- 2026-09-18: `python3 .tasks/bin/sync check` exits 0.

## Notes

- This is explicitly a stopgap (SPEC-003 Non-goals) — a real context-management strategy is a
  future spec/epic, not this task's job.
