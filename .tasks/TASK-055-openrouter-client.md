---
id: TASK-055
title: "OpenRouter client: live model catalog, pricing, and balance"
type: feature
status: todo
epic: EPIC-004
created: 2026-09-17
branch: task-055-openrouter-client
pr: null
merge_commit: null
blocked_by: [TASK-040, TASK-042, TASK-043, TASK-044, TASK-045]
blocks: [TASK-056, TASK-057, TASK-058]
---

# TASK-055: OpenRouter client: live model catalog, pricing, and balance

## Description

Foundational slice for EPIC-004 (see SPEC-004). Blocked on EPIC-003's five terminal tasks
(TASK-040, TASK-042, TASK-043, TASK-044, TASK-045), per this epic's placement decision. Independent
of TASK-054 — this is a standalone HTTP client, not a config consumer.

A new stdlib module, `.tasks/bin/openrouter.py`, using only `urllib.request`/`json` (no third-party
HTTP library — this repo is stdlib-only end to end, `pyproject.toml`'s `dependencies = []`). Auth
via the `OPENROUTER_API_KEY` environment variable — never written to a config file. Three
operations:

1. `GET /api/v1/models` — the live model catalog with current per-model input/output pricing and
   context length. This backs a ranked/filterable view (e.g. "cheapest by input price") rather than
   a hardcoded pricing table, since external pricing changes without notice and this repo already
   found conflicting third-party quotes for the same model.
2. `GET /api/v1/key` — returns `limit_remaining`, the usable proxy for "remaining balance" with a
   normal API key. (`GET /api/v1/credits` needs a *management* key and 403s on a normal one — do
   not build against it.)
3. `POST /api/v1/chat/completions` with `usage: {include: true}` in the request body, so every
   response carries its own actual token/cost accounting rather than requiring a separate estimate.

CLI surface: `openrouter.py catalog [--rank-by input-price|output-price]`, `openrouter.py balance`,
and a `send(messages, model, ...) -> (content, usage)` function for other scripts (TASK-056) to
import directly rather than shelling out.

## Acceptance criteria

- [ ] `openrouter.py catalog` prints the live model list with input/output price and context length
      per model, sourced from a real `GET /api/v1/models` call (or a fixture in tests).
- [ ] `openrouter.py balance` prints `limit_remaining` from `GET /api/v1/key`.
- [ ] `send()` posts to `/api/v1/chat/completions` with `usage: {include: true}` and returns both
      the response content and the usage/cost object from the response.
- [ ] A missing or invalid `OPENROUTER_API_KEY` produces a clear error message, not a raw traceback.
- [ ] An HTTP error (4xx/5xx) from OpenRouter is caught and re-raised with the response body
      included, not swallowed.
- [ ] No third-party HTTP library is imported — `urllib.request` only.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests against a stubbed `urllib.request.urlopen` (or a local `http.server` fixture) for all
   three operations: catalog parsing, balance parsing, and `send()`'s request construction
   (headers, body shape including `usage.include`) and response parsing (content + usage).
2. Unit tests for error handling: a 401/403 response, a malformed JSON response, and a missing
   `OPENROUTER_API_KEY` each produce the documented clear-error behavior, not a crash.
3. `python3 -m pytest -q` — full suite green (these tests must not make real network calls).
4. `python3 .tasks/bin/sync check` → exit 0.
5. Human-run: a real `openrouter.py balance` call against an actual `OPENROUTER_API_KEY`, confirming
   the printed balance matches the OpenRouter dashboard — network calls to a paid third party can't
   be meaningfully mocked for a final sanity check.

## Worklog

_(empty — appended during implementation)_

## Notes

- Fetching pricing live (rather than hardcoding a table) is a deliberate choice — third-party
  pricing quotes for the same model conflicted by as much as 3x across sources during this epic's
  planning research.
- `TASK-057` (pre-send safety) and `TASK-058` (budget guardrail) both build directly on this
  client's `send()`/`balance()` functions.
