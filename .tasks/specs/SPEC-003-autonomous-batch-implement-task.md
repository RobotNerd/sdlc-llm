---
id: SPEC-003
title: Autonomous multi-task execution for implement-task
status: draft
created: 2026-09-14
---

# SPEC-003: Autonomous multi-task execution for implement-task

## Problem

`implement-task` works one task at a time and requires a human to re-invoke it after every PR is
opened (phase 3's STOP) and again after every merge (phase 4 is "event-driven... don't loop
waiting"). For a backlog of many similar, well-specified tasks (exactly the shape this repo's own
script-extraction wave produces — TASK-022/024/025/026 and now EPIC-002's seven hook tasks), that
means active babysitting: approve a plan, wait, review a PR, merge it, re-invoke, repeat. There is
no way to hand the skill a body of work and have it work through all of it, stopping only when it
genuinely needs a human — an ambiguous task, a real blocker, a repeated failure — rather than at
every mechanical checkpoint along the way.

Making this autonomous also surfaces two problems that don't exist in single-task mode: (1) the
review gate between "PR open" and "next task starts" was one person, working serially, by
design — removing that gate for real autonomy is a genuine trade against the standing "a human
always reviews and merges" guardrail (SPEC-001 §Guardrails; §"Resolved during planning" notes why
— auto-merge "defeats the purpose of opening a PR at all", even solo); and (2) a long unattended
run has failure modes single-task mode never has to
consider — running out of context, spending unbounded tokens, or autonomously creating enough new
tasks to explode the backlog.

## Goals

- Accept a batch of tasks to work — by epic, by numeric task-ID range, by an explicit (possibly
  out-of-TODO-order) task list, or by "work TODO top-to-bottom through this stopping task" — and
  deterministically validate the selection is workable before starting any work.
- Work through the batch with minimal per-task human interaction: announce each task's plan
  without blocking on it, and don't require manual re-invocation between a PR opening and the
  next task starting.
- Provide an explicit, narrow, opt-in path to close the merge gate autonomously — a cheap critic
  pass gates each merge, and a per-batch cap forces a human checkpoint regardless of how many
  critic approvals have accumulated. Off by default; the standing "human reviews and merges"
  behavior is unchanged unless a project turns this on.
- Interrupt and notify the human on: work needing clarification, an unexpected blocker, a
  quality-gate failure surviving a bounded number of retries, repeated guardrail/hook denial,
  `git`/`gh` infrastructure failure, a context-usage threshold, and a token-usage threshold —
  routing an isolated per-task problem to "skip this task, keep going" and a systemic one to
  "halt the whole batch."
- Let the LLM create follow-up tasks autonomously (e.g. splitting a task that turns out oversized)
  up to a configurable per-batch limit; beyond the limit, flag rather than create, and keep
  working everything else.
- Produce one end-of-batch summary: a per-task outcome table, any critic findings, any follow-up
  tasks created, and token/cost usage for the run.
- Add an opt-in, project-wide TDD mode: write the failing test first, confirm it fails, then
  implement until it passes — a `implement-task` behavior change independent of batch mode.

## Non-goals

- Not spawning worker subagents or parallelizing task execution. A spawned subagent starts cold
  and re-derives context already held by the current session — direct tension with the token-cost
  concern this spec exists partly to manage. Single session, one task at a time, sequential.
- Not solving context-window management in general (compaction strategy, per-task session
  boundaries, summarization strategy). This spec adds only a cheap safety-valve interrupt when a
  configurable context-usage threshold is crossed; a dedicated future spec/epic covers the real
  strategy.
- Not building a general-purpose autonomous-agent framework. Scope is `implement-task` working a
  human-specified, pre-approved batch of already-written tasks — not open-ended planning,
  discovery, or backlog grooming (that's `plan-feature`/`refine-backlog`'s job).
- Not removing the PR mechanism or the default human-reviews-and-merges behavior. Auto-merge is an
  explicit, capped, off-by-default opt-in, never the new default.
- Not designing a general critic-agent framework for other skills — the critic here is scoped
  narrowly to gating one merge decision on one task's diff.

## Alternatives considered

- **Manual re-invocation between every task** (i.e., ship only the deterministic batch-selection
  validation, keep every existing STOP). Rejected as insufficient — it's the status quo's
  babysitting problem with a nicer task-selection front end, not the autonomy the backlog actually
  needs.
- **Fully autonomous with no merge gate at all** (auto-merge unconditionally once opted in, no
  critic, no cap). Rejected — removes the single standing checkpoint in the entire workflow with
  nothing replacing it; one bad task could compound silently across an entire batch before a human
  ever looks at it.
- **A full code-review-quality critic** (open-ended "review this diff for quality") rather than a
  narrow acceptance-criteria/gate checklist. Rejected on cost grounds raised directly by the user:
  an open-ended review pass is expensive and slow on a constrained plan tier; a checklist-style
  pass against acceptance criteria and gate results is cheap and plays to what an LLM verifies
  reliably.
- **Worker-agent parallelism to speed up a batch.** Rejected for this spec (see Non-goals) — the
  token-cost profile of spawning fresh subagents runs directly counter to the stated goal of
  keeping usage low, and sequential execution is simpler to reason about for a first version.

<!-- BEGIN:epics (generated by sync — do not edit) -->
| Epic | Status | Progress |
|---|---|---|
| EPIC-003 | in-progress | 8/11 done |
<!-- END:epics -->
