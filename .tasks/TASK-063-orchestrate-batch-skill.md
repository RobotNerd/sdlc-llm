---
id: TASK-063
title: "orchestrate-batch skill: wire orchestrator/worker/critic into implement-task's loop"
type: feature
status: todo
epic: EPIC-004
created: 2026-09-17
branch: task-063-orchestrate-batch-skill
pr: null
merge_commit: null
blocked_by: [TASK-056, TASK-057, TASK-058, TASK-059, TASK-060, TASK-061, TASK-062, TASK-064]
blocks: []
---

# TASK-063: orchestrate-batch skill: wire orchestrator/worker/critic into implement-task's loop

## Description

Blocked on every other slice in this epic (TASK-056 through TASK-062, plus TASK-064) — this is the
integration task that wires them into one runnable loop.

New `.claude/skills/orchestrate-batch/{SKILL.md,scaffold.py}`. Consumes EPIC-003's TASK-039 batch
selection/validation output (a concrete, ordered, validated task list) unchanged — this skill does
not re-implement batch selection. Per task in the validated batch:

1. Select a worker tier (TASK-061) and spawn `worker-<tier>` (TASK-054) to run `implement-task`
   phases 1-2 for that task.
2. Run the existing deterministic quality gate (`sync check` / `test_command` / `lint_command` /
   `format_command` — EPIC-002's TASK-035). **Only if it passes** does the critic run at all — a
   mechanically-broken diff never costs a paid review.
3. Run the critic (TASK-056), respecting pre-send safety (TASK-057) and the budget guardrail
   (TASK-058).
4. Triage the critic's findings (TASK-059) and act, bounded by rework state (TASK-060).
5. At each batch checkpoint (between tasks) and at the worker's phase-2/phase-3 boundary, run the
   compaction/reset checkpoint (TASK-064): clear-and-rehydrate the orchestrator's own context if
   `context_compact_pct` is crossed, and treat a worker crossing it mid-task as an isolated
   interrupt requiring a fresh worker retry rather than continuing that attempt.
6. On acceptance, proceed through `implement-task` phase 3 (open PR) as today — this epic does not
   change merge behavior; EPIC-003's TASK-045 auto-merge path, if enabled, is unaffected and
   unduplicated here.

Extends EPIC-003's TASK-041 end-of-batch summary with a new section: per task, which agent(s) ran
it, at what model and effort tier, and at what actual cost (Anthropic usage where available,
OpenRouter `usage.cost` for critic calls) — the concrete data a human needs to judge whether the
critic is earning its keep on their plan tier.

## Acceptance criteria

- [ ] The skill consumes TASK-039's batch-selection output directly, with no re-validation logic of
      its own.
- [ ] For each task, a worker subagent runs, the deterministic gate runs before any critic call, and
      the critic runs only on a passing gate.
- [ ] A rejected critic finding routes through the TASK-059 taxonomy and respects TASK-060's caps
      (3-strike, second-opinion) without this skill re-implementing that bookkeeping.
- [ ] The end-of-batch summary includes a per-task row naming the agent(s) used, their model/effort
      tier, and their cost — present even for tasks where the critic never ran (e.g. gate failure).
- [ ] Enabling `allow_auto_merge` (TASK-045) continues to work through this skill without any
      auto-merge logic duplicated here.
- [ ] The loop calls TASK-064's checkpoint at both the between-task boundary (orchestrator) and the
      worker's phase-2/phase-3 boundary, with no compaction/reset logic re-implemented here.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the per-task orchestration sequencing: gate-fail short-circuits before any critic
   call (assert the critic mock is never invoked); gate-pass proceeds to critic.
2. Unit tests on the summary-extension logic: given per-task agent/cost records, the rendered
   summary section contains the expected rows and fields.
3. Integration test with a fully mocked critic/worker boundary, running 2-3 synthetic tasks through
   the full sequence (gate → critic → triage → act) and asserting the recorded outcomes match the
   scripted mock responses.
4. `python3 -m pytest -q` — full suite green.
5. `python3 .tasks/bin/sync check` → exit 0.
6. Human-run scratch-branch dry run: 2-3 trivial scratch tasks run end-to-end with a real
   OpenRouter critic call, confirming cost figures in the summary match the OpenRouter dashboard —
   real spend and real subagent dispatch can't be meaningfully mocked for a final sanity check.

## Worklog

_(empty — appended during implementation)_

## Notes

- This is the capstone task for EPIC-004 — every other slice is a component this skill assembles,
  none of them are independently useful without it.
- Deliberately does not touch EPIC-003's own `orchestrate`-equivalent core loop (TASK-041) except to
  extend its summary — this skill is an alternate/enhanced execution path a project opts into via
  the TASK-054 config keys, not a replacement for TASK-041's simpler single-model loop.
- Must pass `tests/test_portable_surface.py` (no `TASK-NNN`/`EPIC-NNN`/`SPEC-NNN` ids or
  `CLAUDE.md` references inside the skill's own `SKILL.md`/`scaffold.py` text) since it ships as
  part of the portable skills surface.
