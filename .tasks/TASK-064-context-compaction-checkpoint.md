---
id: TASK-064
title: "Context compaction/reset: proactive orchestrator checkpoint-clear + worker mid-task guard"
type: feature
status: todo
epic: EPIC-004
created: 2026-09-17
branch: task-064-context-compaction-checkpoint
pr: null
merge_commit: null
blocked_by: [TASK-043, TASK-054, TASK-060]
blocks: [TASK-063]
---

# TASK-064: Context compaction/reset: proactive orchestrator checkpoint-clear + worker mid-task guard

## Description

Blocked on TASK-043 (extends its config keys and threshold pattern), TASK-054 (needs the
orchestrator/worker agent roster to exist), and TASK-060 (rehydrates from the same
`.tasks/.run/BATCH-<id>.json` state it defines).

TASK-043 was a deliberate stopgap — its own Notes defer "a real context-management strategy
(per-task session boundaries, compaction, summarization)" to "a future spec/epic." EPIC-004 is that
future: it's the first place a genuinely long-running role (the orchestrator, across a whole batch)
is architecturally distinct from a short-lived one (the worker, one task per instance), so the two
roles need different treatment instead of one shared halt-only valve.

**Worker architecture, made explicit here rather than left implicit:** each worker is a fresh
subagent spawned per task, never reused across tasks. This isn't a new decision — SPEC-004's
Alternatives section already argues a subagent's cold-start cost, paid once per task, beats
context-growth-every-turn on a quota-constrained plan, and TASK-061's per-task tiering only makes
sense against a freshly-spawned worker (effort/model are frontmatter-only, fixed for that
instance's life). A persistent worker reused across many tasks would just relocate the
context-accumulation problem this epic exists to solve, from the orchestrator into the worker, for
no offsetting benefit — the task files already carry the acceptance criteria and testing strategy,
so the worker is executing a spec, not accumulating exploration value worth preserving across tasks.
Consequence: the worker's own context risk is narrow (one pathologically large single task), not
batch-wide accumulation, since fresh-per-task already bounds the common case. The orchestrator is
the role that actually needs a real mechanism.

**Mechanism: clear-and-rehydrate, not model-driven summarization.** Per SPEC-001's "frontmatter is
the source of truth" principle, everything worth carrying across a checkpoint is already file-backed
— the validated remaining task list (TASK-039's output), the running per-task outcome table
(TASK-041), rework counts and critic-sha (TASK-060's `BATCH-<id>.json`), and usage totals so far
(TASK-043). Clearing the orchestrator's context at a checkpoint and rehydrating exactly those four
things is lossless here and matches the same pattern `implement-task`'s own `resume-state` already
uses (stateless, derived from repo state). No summarization step is needed because nothing
irreproducible lives only in the orchestrator's own reasoning trace.

Two-tier thresholds, extending rather than replacing TASK-043's single halt:
- `context_compact_pct` (new, lower than the halt threshold, default `65`) — at the next safe batch
  checkpoint (the same between-task checkpoint TASK-043 uses), proactively clear-and-rehydrate the
  orchestrator's context.
- `context_usage_halt_pct` (TASK-043's existing key, unchanged) — still the last-resort circuit
  breaker if usage crosses it regardless (a clear didn't help, or usage spiked faster than the
  checkpoint cadence catches).

Worker guard: at the existing `implement-task` phase boundary (after phase 2, before phase 3 — the
same checkpoint TASK-043 already uses), if *that worker's own* context usage crosses
`context_compact_pct` mid-task, route it as an **isolated interrupt** per TASK-042 — bail out this
attempt, record findings, and let the orchestrator retry the task with a fresh worker instance.
This is not live in-place compaction of a running subagent (the harness exposes no such capability
to a script) — a fresh retry is both the only available mechanism and the architecture already
recommended above.

## Acceptance criteria

- [ ] `context_compact_pct` exists as a new template-fixed config key, its default lower than
      `context_usage_halt_pct`'s default (e.g. `65` vs `85`).
- [ ] Crossing `context_compact_pct` at a batch checkpoint clears the orchestrator's context and
      rehydrates the validated remaining task list, running outcome table, rework/critic-sha state,
      and usage totals — the rehydrated state is verified equivalent to the pre-clear state.
- [ ] Crossing `context_compact_pct` mid-task in a worker (not the orchestrator) produces an
      isolated interrupt per TASK-042's taxonomy — the batch continues, only that task's current
      attempt is retried.
- [ ] `context_usage_halt_pct`'s existing TASK-043 behavior is unchanged — it still halts the batch
      if usage crosses it, whether or not a compact-clear already happened that checkpoint.
- [ ] The end-of-batch summary reports how many orchestrator compact-clears happened and how many
      worker retries the mid-task guard triggered.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the two-tier threshold check against synthetic usage figures: below both
   thresholds (no action), between `context_compact_pct` and the halt threshold (clear-and-
   rehydrate), at/above the halt threshold (halt, regardless of whether a clear already ran this
   checkpoint).
2. Unit test asserting the orchestrator's rehydrated state (task list, outcome table,
   rework/critic-sha state, usage totals) is equivalent to its pre-clear state, for a fixture
   `BATCH-<id>.json` plus in-progress batch state.
3. Unit test confirming a worker-side threshold crossing produces the isolated-interrupt signal
   (TASK-042), never the systemic halt signal used for the orchestrator's own breach.
4. `python3 -m pytest -q` — full suite green.
5. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- Confirms and documents the fresh-worker-per-task architecture decision explicitly for the first
  time — SPEC-004/TASK-054/TASK-061/TASK-062 already imply it, but no prior task states it as a
  decision in its own right.
- The `orchestrate-batch` skill (TASK-063) is this mechanism's caller — TASK-063 is `blocked_by`
  this task, so it can't be implemented until this checkpoint mechanism exists.
- Source: user follow-up on TASK-043's explicitly-deferred "future spec/epic" for real
  context-window management.
