---
id: TASK-056
title: "Critic client: diff to structured findings JSON"
type: feature
status: todo
epic: EPIC-004
created: 2026-09-17
branch: task-056-critic-client
pr: null
merge_commit: null
blocked_by: [TASK-054, TASK-055]
blocks: [TASK-059, TASK-063]
---

# TASK-056: Critic client: diff to structured findings JSON

## Description

Blocked on TASK-054 (agent roster/config keys) and TASK-055 (OpenRouter client).

A new stdlib module, `.tasks/bin/critic.py`, with `critic.py review --task TASK-NNN --base <sha>`.
Builds a review prompt from the task's Acceptance criteria, `git diff <sha>...HEAD`, and the
deterministic gate's results (test/lint/format/`sync check` output), scoped narrowly per SPEC-003's
TASK-045: does the diff satisfy every acceptance criterion, does `git diff --name-only` stay in the
task's declared scope, did every quality gate actually pass, is there anything alarming. Not an
open-ended code-quality review — cost is the reason this stays scoped narrowly.

Sends the prompt via `openrouter.send()` (TASK-055) when `critic_provider: openrouter`, or spawns
the `critic-anthropic` subagent (TASK-054) when `critic_provider: anthropic`. Parses the response
into `[{severity, file, line, summary, rationale}]`; validates against that schema; on a malformed
response, retries once with a "your last response didn't parse, return only valid JSON matching
this schema" repair prompt before giving up and surfacing a clear error (never silently drops a
malformed review).

## Acceptance criteria

- [ ] `critic.py review` builds a prompt containing the task's acceptance criteria, the actual diff,
      and the gate results — not the whole repo.
- [ ] With `critic_provider: openrouter`, the review is sent via `openrouter.send()` using
      `critic_model`/`critic_effort` from config.
- [ ] With `critic_provider: anthropic`, the review runs via the `critic-anthropic` subagent
      instead, with no OpenRouter call made.
- [ ] A well-formed critic response parses into a list of `{severity, file, line, summary,
      rationale}` findings; an empty list (no findings) is a valid, distinct outcome from an error.
- [ ] A malformed response triggers exactly one repair-prompt retry before failing loudly.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on prompt construction: given a task file, a diff, and gate results, assert the
   composed prompt contains all three and excludes unrelated repo content.
2. Unit tests on response parsing against fixture responses: well-formed JSON, JSON wrapped in
   prose/markdown fences, and genuinely malformed output (confirming exactly one repair retry, then
   a clear failure).
3. Unit tests for provider branching: `critic_provider: openrouter` calls `openrouter.send()`;
   `critic_provider: anthropic` does not call it at all (mocked/stubbed boundary).
4. `python3 -m pytest -q` — full suite green, no real network calls.
5. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- This is the checklist-style critic pass EPIC-003's TASK-045 (critic-gated auto-merge) leaves
  undefined — TASK-045 calls into this client rather than this task re-implementing merge-gating
  logic, which stays owned there.
- TASK-059 (triage taxonomy) is the next consumer: it interprets this client's findings list.
