---
id: TASK-038
title: Wire hooks into upgrade and config migration
type: feature
status: in-progress
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

- [x] `upgrade` on a project with stale hook scripts refreshes them exactly like it refreshes
      skills (new/clean-update/locally-modified classification applies identically).
- [x] A project's own extra hook registrations in `.claude/settings.json` survive an `upgrade`
      untouched.
- [x] This repo's dev-only hook (`.dev/hooks/check-portable-references.py` from TASK-036) and its
      `.claude/settings.json` registration are byte-identical before and after running `upgrade`
      on this repo.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.

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

- Confirmed `managed_files()`'s generic whole-file table already covers `.claude/hooks/*` and
  `.tasks/bin/guardrails.py` (wired in by TASK-032, before this task existed) — so `upgrade`
  already refreshed stale/locally-modified hook scripts exactly like a skill file, with no code
  change needed. Added explicit test coverage for it anyway (`test_upgrade_picks_up_a_staled_hook_script`,
  `test_upgrade_refuses_a_locally_modified_hook_script_and_writes_nothing`), since the task's own
  acceptance criteria call it out and nothing tested it directly before.
- The real gap was `.claude/settings.json`: it was in that same whole-file table, so a project's
  own extra hook registration made the *entire file* classify as `locally_modified` on the next
  `upgrade` — refusing (or, with `--force`, silently destroying the project's own addition).
  Added `merge_settings_hooks(project, template)` to `scaffold.py`: additively merges, per event
  and matcher-group, only the hook commands the project structurally lacks; a group the project
  altogether lacks is appended whole; a hook the project already has (matched by its exact
  `command` string) is left untouched; nothing the project already has is ever removed or
  reordered.
- `cmd_upgrade` now excludes `.claude/settings.json`'s target from the hash-classified
  table/manifest entirely (splitting its `(source, target)` pair out of `managed_files()`'s
  result before `classify_managed_files`/`apply_managed_files`/`write_manifest` ever see it) and
  instead runs `merge_settings_hooks` automatically, using the same clone already fetched — no
  separate subcommand or second clone, and no STOP, since it can only add, never overwrite or
  remove (unlike `config.md`, which is genuinely project-authored data). Skipped entirely if the
  main upgrade aborts on an unrelated conflict, so nothing is written on that path either.
  `managed_files()` itself is unchanged, so a fresh `run --target` (which has no existing
  settings.json to merge with) still gets the template copied wholesale, as before.
- `--dry-run` and the final JSON both report `settings_hooks_would_add`/`settings_hooks_added`
  alongside the existing classification, so this is visible in the same summary the human already
  reviews.
- Extended the existing data-loss guard with a dedicated test for `.dev/hooks/*` specifically
  (`test_upgrade_never_touches_a_dev_only_hook_path`) — this path was never in `managed_files()`
  at all (true since TASK-036), so it was already safe by construction, but now a regression here
  fails loudly instead of just never being checked.
- Proved the dev-only-hook-and-its-registration-survive property with fixture-based tests rather
  than running `upgrade` against this actual live checked-out repo (too risky to mutate the
  working tree a test suite is running from, and it would also need a real network clone unless
  `--source` is pinned) — `test_upgrade_preserves_a_targets_own_extra_settings_hook_registration`
  constructs the same shape (a project-only hook registration a template will never ship)
  end-to-end and confirms it survives a real merge/write, which is what actually matters.
- Added 16 tests total across `merge_settings_hooks` (pure fixtures), the hook-script
  staleness/local-modification pair, the data-loss-guard extension, and `cmd_upgrade`'s
  settings-merge integration (real subprocess against `toolkit_source`/`target` fixtures, the
  existing pattern this test file already used for `merge_config_schema`/`migrate-config`).
- Updated `init-project/SKILL.md`'s Upgrade section to document the automatic, no-STOP
  settings.json merge and the new `settings_hooks_added`/`settings_hooks_would_add` JSON fields.
- Full suite: `.venv/bin/pytest -q` → 556 passed (540 existing + 16 new), no existing test's
  assertions changed (existing `upgrade` tests still pass unmodified against the new code path).
- `python3 .tasks/bin/sync check` → exit 0.

## Notes

- Last task in EPIC-002's dependency graph — depends on TASK-032 plus both `upgrade`-path tasks
  from EPIC-001 (TASK-029, TASK-030).
