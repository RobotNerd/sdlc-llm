---
id: TASK-038
title: Wire hooks into upgrade and config migration
type: feature
status: todo
epic: EPIC-002
created: 2026-09-14
branch: task-038-wire-hooks-into-upgrade
pr: null
merge_commit: null
blocked_by: [TASK-032, TASK-029, TASK-030]
blocks: [TASK-039, TASK-040]
---

# TASK-038: Wire hooks into upgrade and config migration

## Description

Blocked on TASK-032 (hooks infrastructure), TASK-029 (`init-project upgrade`), and TASK-030
(config-schema migration).

Extend TASK-029's `managed_files()` to include `.claude/hooks/**` (or wherever TASK-032 places the
vendored hook scripts) and `.tasks/bin/guardrails.py`, following the exact same
drift-detection/manifest treatment `upgrade` already gives the skills and `.tasks/bin/sync`.

Extend TASK-030's additive-merge approach so an existing project's `.claude/settings.json` gains
new hook registrations the same way `config.md` gains new keys — inserting only registrations the
project lacks, never disturbing any hook entry the project added on its own.

Prove the repo-only hook from TASK-036 is invisible to both: it is never in `managed_files()`, and
running `upgrade` against this repo leaves it and its `.claude/settings.json` registration
untouched.

## Acceptance criteria

- [ ] `upgrade` on a project with stale hook scripts refreshes them exactly like it refreshes
      skills (new/clean-update/locally-modified classification applies identically).
- [ ] A project's own extra hook registrations in `.claude/settings.json` survive an `upgrade`
      untouched.
- [ ] This repo's dev-only hook (`.dev/hooks/check-portable-references.py` from TASK-036) and its
      `.claude/settings.json` registration are byte-identical before and after running `upgrade`
      on this repo.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Extend TASK-029's test suite with hook-script fixtures: a stale hook script gets refreshed; a
   locally-modified one produces the same diff+STOP behavior as any other managed file.
2. Extend TASK-030's test suite with `.claude/settings.json` fixtures: a project missing a hook
   registration gains it; a project's own extra registration is preserved; an already-current
   file is left untouched (idempotent).
3. Extend TASK-029's data-loss guard (hash every non-managed path before/after an upgrade) to
   include the dev-only hook path explicitly, so a regression here fails loudly.
4. `pytest` — full suite green.
5. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- Last task in EPIC-002's dependency graph — depends on TASK-032 plus both `upgrade`-path tasks
  from EPIC-001 (TASK-029, TASK-030).
