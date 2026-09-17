---
id: TASK-061
title: Dynamic worker effort/model tiering by task difficulty
type: feature
status: todo
epic: EPIC-004
created: 2026-09-17
branch: task-061-effort-tiering
pr: null
merge_commit: null
blocked_by: [TASK-054]
blocks: [TASK-063]
---

# TASK-061: Dynamic worker effort/model tiering by task difficulty

## Description

Blocked on TASK-054 (agent roster) — this selects among the `worker-<tier>` agents it defines.

Since Claude Code's `effort` is frontmatter-only (no per-invocation override — confirmed against the
subagent docs during this epic's planning), "adjust effort on the fly" means picking which
pre-defined worker agent variant (`worker-low`/`worker-medium`/`worker-high`, from TASK-054) to
spawn as the `subagent_type`, not changing a running agent's effort.

A deterministic difficulty estimator in a script (not model judgment) computes a suggested tier from
task-file signals available before any work starts: `type` (chore/docs lean low, feature/refactor
lean medium+), acceptance-criteria count, an estimated file/scope count from the task's stated
scope, and `blocked_by` depth (how deep in the dependency chain, as a rough proxy for
accumulated complexity). The orchestrator may override the suggestion (e.g. after a TASK-059
escalation action), but only when doing so is a genuine efficiency improvement — spawning a
higher tier "just in case" defeats the point of tiering. Log which tier was chosen and why (default
vs. override) for the end-of-batch summary (TASK-063).

## Acceptance criteria

- [ ] A deterministic function maps task-file signals to a suggested tier (`low`/`medium`/`high`),
      with the mapping rules documented, not implicit in scattered conditionals.
- [ ] The mapping is a pure function of the task file's own frontmatter/content plus static config
      thresholds — no network or model call needed to produce a suggestion.
- [ ] The orchestrator can override the suggested tier; both the suggested and the actually-used
      tier are recorded per task.
- [ ] `chore`/`docs` tasks default to a lower tier than `feature`/`refactor` tasks of similar size,
      demonstrated by a test fixture pair.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the difficulty estimator against fixture task files spanning each `type` and a
   range of acceptance-criteria counts, confirming the tier boundaries are applied consistently and
   documented thresholds are hit exactly (not off-by-one).
2. Unit test confirming an orchestrator override is recorded distinctly from the deterministic
   suggestion (both values present, not overwritten).
3. `python3 -m pytest -q` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- Anthropic's own SWE-bench data (cited during this epic's planning) shows medium-effort runs use
  roughly 76% fewer output tokens than high-effort for the same completion rate on many tasks —
  tiering down by default is a real efficiency lever, not a cosmetic one.
- TASK-059's action 3 ("rework with escalated effort/model") is this task's main runtime consumer
  besides the initial per-task dispatch.
