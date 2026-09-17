---
id: TASK-054
title: "Agent roster: per-role config keys and generated .claude/agents/*.md"
type: feature
status: todo
epic: EPIC-004
created: 2026-09-17
branch: task-054-agent-roster-config-and-generation
pr: null
merge_commit: null
blocked_by: [TASK-040, TASK-042, TASK-043, TASK-044, TASK-045]
blocks: [TASK-056, TASK-061, TASK-062]
---

# TASK-054: Agent roster: per-role config keys and generated .claude/agents/*.md

## Description

Foundational slice for EPIC-004 (see SPEC-004). Blocked on EPIC-003's five terminal tasks
(TASK-040, TASK-042, TASK-043, TASK-044, TASK-045), per this epic's placement decision to run after
the autonomous-batch epic completes in full.

New, flat, template-fixed keys in `.claude/skills/init-project/templates/config.md`'s frontmatter
(flat only — `parse_frontmatter` rejects nested maps, `.tasks/bin/sync:123-161`):
`orchestrator_model`, `orchestrator_effort`, `worker_model`, `worker_effort`,
`worker_effort_tiers` (a flat list like `[low, medium, high]`, consumed by TASK-061), `critic_provider`
(`openrouter` | `anthropic`), `critic_model`, `critic_effort`, `external_review` (default `false`).
Keep them out of `REQUIRED_KEYS` (`init-project/scaffold.py:61-74`) so `merge_config_schema`
back-fills them into every already-scaffolded project on upgrade, with no interview needed.

A new stdlib generator, `.tasks/bin/agents.py`, renders `.claude/agents/{orchestrator,
worker-low, worker-medium, worker-high, critic-anthropic}.md` — Claude Code subagent frontmatter
(`name`, `description`, `tools`, `model`, `effort`) — from those config values. The worker variants
exist because `effort` is frontmatter-only (no per-invocation override), so "pick an effort level at
dispatch time" means "pick which pre-defined agent to spawn" (this is what TASK-061 consumes).
`critic-anthropic.md` is the fallback path when `critic_provider: anthropic` (no tools needed — see
TASK-056).

## Acceptance criteria

- [ ] All nine new keys exist in `init-project/templates/config.md`'s frontmatter with documented
      defaults in its `## Key notes` section, and are **not** added to `REQUIRED_KEYS`.
- [ ] Running `migrate-config`/`upgrade` against an already-scaffolded project (no interview) adds
      all nine keys with their template defaults, changing nothing else in that project's
      `config.md`.
- [ ] `agents.py generate` writes `.claude/agents/orchestrator.md`, `worker-low.md`,
      `worker-medium.md`, `worker-high.md`, and `critic-anthropic.md` from current config, each with
      valid subagent frontmatter (`name`, `description`, `model`, `effort`).
- [ ] Changing a config key (e.g. `worker_model`) and re-running `agents.py generate` updates only
      the affected agent file(s) — idempotent otherwise (no diff on a second run with no config
      change).
- [ ] This repo's own `.tasks/config.md` and `.claude/agents/` are updated to match.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on `merge_config_schema` with the nine new template keys present, against a fixture
   project `config.md` missing them — confirms all nine get added with template defaults and every
   existing key/value/order/body is untouched (existing test pattern in
   `tests/test_init_project_upgrade.py`).
2. Unit tests on `agents.py`'s rendering function: given a config dict, assert each of the five
   generated files' frontmatter matches the config values, and that a second generate with
   unchanged config produces a byte-identical file (idempotency).
3. `python3 -m pytest -q` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- This is the config/roster foundation every other slice in this epic depends on (directly or
  transitively) except TASK-055 (OpenRouter client), which is independent.
- Source: SPEC-004 Goal 1 and the plan-feature decomposition for EPIC-004.
