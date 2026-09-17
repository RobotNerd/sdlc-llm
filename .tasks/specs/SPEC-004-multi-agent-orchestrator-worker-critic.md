---
id: SPEC-004
title: Multi-agent orchestrator, worker, and critic
status: draft
created: 2026-09-17
---

# SPEC-004: Multi-agent orchestrator, worker, and critic

## Problem

The workflow today runs as a single Claude Code session that plans, implements, and self-reviews every task at one uniform model and effort level. There is no independent review step distinct from the implementer, so review blind spots (the same model missing the same class of issue it just wrote) go uncaught. Reasoning spend is uniform regardless of task difficulty -- a one-line chore consumes the same effort tier as a genuinely hard refactor -- and every token of that spend lands on a single Anthropic plan (a $20/mo Pro tier in the base case), which is the binding constraint on how much autonomous batch work (EPIC-003) can actually run before hitting session/weekly limits. There is currently no mechanism to route any part of the loop to a different, cheaper model or provider, and no independent role whose job is specifically to catch what the implementer missed before a human ever looks at the diff.

## Goals

- Three distinct roles -- orchestrator (plans and triages), worker (implements), critic (reviews) -- each with independently configurable model and effort level.
- The critic is routable to a cheap external (non-Anthropic) provider via OpenRouter, since Claude Code has no per-subagent provider routing and the critic is the one role that can be a plain script rather than a subagent.
- A bounded critic-to-orchestrator rework loop: the orchestrator decides what a critic finding means (accept, rework, escalate, follow-up task, second opinion, halt), gated by a hard 3-strike cap so a disagreement can never loop forever.
- External (OpenRouter) spend is monitored and the run halts on a configurable credit-floor or burn-rate breach, before it can silently exhaust a budget.
- The critic runs only after the existing deterministic quality gate (sync check / test / lint / format) passes, so a mechanically-broken diff never costs a paid review.
- Deterministic behavior (model catalog/pricing lookups, secret scanning, budget math, rework-count bookkeeping, effort-tier selection) lives in stdlib scripts; the mechanically-checkable guardrails among them (pre-send safety, worker scope) are hook-enforced, matching this repo's existing script/hook split.
- A worker's completion is checked against its task's declared file scope structurally (a hook), not left to model self-discipline, closing the one remaining prose-only guardrail in guidelines.md.

## Non-goals

- Not giving the orchestrator or the worker per-agent provider routing -- Claude Code's subagent model has no such mechanism (ANTHROPIC_BASE_URL is session-wide), so both stay Anthropic subagents; only the critic, which needs no tools and can be a plain HTTP call, is externalized.
- Not parallelizing worker execution -- one worker runs at a time, sequentially, to keep the 5-hour rolling usage window and the OpenRouter burn rate both predictable.
- Not building a general-purpose multi-agent or multi-provider framework for other skills -- scope is these three roles for implement-task's own loop.
- Not replacing or restating any part of EPIC-003's existing surface -- its batch-selection validation, its core loop, its interrupt taxonomy, its context/token safety valve, its follow-up-task limit, or its critic-gated auto-merge marker. This feature supplies the concrete mechanism for the 'cheap/fast model that isn't the implementer' that EPIC-003's own critic-gated auto-merge task leaves undefined, and otherwise consumes that surface as-is.
- Not self-hosting or fine-tuning any model -- every external call goes to a hosted provider (OpenRouter) via its public API.
- Not changing the standing human-reviews-and-merges default -- nothing here touches when or whether a PR merges beyond what EPIC-003 already defines.

## Alternatives considered

- Route the whole session (orchestrator, worker, and critic alike) to OpenRouter for a run, via a launcher that sets ANTHROPIC_BASE_URL for the process. Rejected for the default path -- it forfeits the Anthropic Pro plan's included usage entirely for that run, trading a hard-to-reverse subscription cost for a per-token one; kept as a possible future opt-in, not this feature's default.
- Write a from-scratch Python agentic loop (tool dispatch, file edits, git driving, retry/repair) so every one of the three roles could run on any provider independently. Rejected -- this would duplicate a large fraction of what Claude Code's own harness already does, at high implementation and maintenance cost, for freedom this feature doesn't need (only the critic needs to be provider-flexible).
- Keep the existing self-review model (the implementer also judges its own diff) rather than adding an independent critic role. Rejected -- the whole point is catching the blind spots an implementer has about its own output, which self-review structurally cannot do.
- Default the critic to GLM-5.2 instead of DeepSeek V4 Pro. Rejected as the default -- GLM-5.2 scores higher on SWE-bench Pro but costs roughly 4x as much on output tokens for this large-input/small-output workload, and a stricter-but-costlier critic converts directly into more rework cycles, which is the most expensive outcome in the loop; kept as a documented upgrade path for a project that wants a stricter default.
- Keep SPEC-003's stated non-goal of never spawning worker subagents, and instead scale one session's own context to cover implementation too. Deliberately reversed here: a worker subagent's cold start is a one-time cost paid once per task, while keeping implementation detail in the orchestrator's own context window is a cost paid on every single turn for the rest of the run. On a quota-constrained plan, the growing-context cost dominates the cold-start cost for anything but a very short batch, so isolating the worker's context is the better trade for this feature's stated goal of reducing Anthropic-quota burn.

<!-- BEGIN:epics (generated by sync — do not edit) -->
| Epic | Status | Progress |
|---|---|---|
| EPIC-004 | todo | 0/10 done |
<!-- END:epics -->
