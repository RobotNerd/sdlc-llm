---
id: TASK-030
title: Migrate config.md to the current schema during upgrade
type: feature
status: in-progress
epic: EPIC-001
created: 2026-09-14
branch: task-030-config-schema-migration
pr: null
merge_commit: null
blocked_by: [TASK-029]
blocks: [TASK-038]
---

# TASK-030: Migrate config.md to the current schema during upgrade

## Description

`config.md` is project-owned — it holds interview answers from `init-project`'s original run and
must survive an `upgrade` (TASK-029) unchanged except for keys the schema has genuinely gained
since. So it is never copied wholesale; it is **merged, additively, frontmatter only**.

- Derive the current key set from the source's `init-project/templates/config.md`:
  `REQUIRED_KEYS` plus the template-fixed keys (`workflow_version`, `allow_auto_merge`, and
  `ignored_paths` once TASK-028 lands).
- Parse the project's existing `config.md` with `parse_frontmatter` from the **freshly-installed**
  `.tasks/bin/sync` (loaded by `SourceFileLoader`, as `tests/conftest.py` already does) — using the
  same parser that will read the file back guarantees the merge writes something it accepts.
- Insert only keys the project lacks, at their template position, with the template's default.
  **Never** change an existing value, never remove a key the project added, and preserve the body
  prose below the frontmatter byte-for-byte.
- Bump `workflow_version` to the template's value when the template's is higher; report it.
- Report added keys in the upgrade summary (e.g. `config.md: +ignored_paths`) and present the
  proposed frontmatter diff at a STOP before writing — `config.md` stays outside TASK-029's
  manifest drift flow since it is only ever added to, never overwritten wholesale.

## Acceptance criteria

- [x] An existing `config.md` missing a key the current template defines gains it, with the
      template's default, at the template's position.
- [x] Every pre-existing key keeps its exact value; existing key order is preserved; project-added
      keys are left alone.
- [x] The markdown body below the frontmatter is byte-identical after the merge.
- [x] A `config.md` already matching the schema is left completely untouched (idempotent).
- [x] The merged file round-trips through the installed `sync`'s `parse_frontmatter`.
- [x] `workflow_version` is bumped when the template's value is higher, and reported.
- [x] The upgrade summary names every key added, and the human sees the diff at a STOP.

## Testing strategy

1. Unit tests over the merge function with hand-built `config.md` fixtures: missing key, complete
   file, project-added extra key, unusual-but-valid key order, body prose containing a `---` line.
2. Round-trip assertion: merged output parses via `parse_frontmatter` with the union of expected
   keys and unchanged values.
3. Idempotency: merging twice produces byte-identical output.
4. Integration: in a `tmp_path` project scaffolded at an older schema, run `upgrade` end to end and
   assert `config.md` gained exactly the missing keys and nothing else changed.
5. `pytest` and `python3 .tasks/bin/sync check` pass.

## Worklog

- Added `load_sync_module` to `init-project/scaffold.py` (same by-path-import pattern already
  used in `add-task`/`plan-feature`/`implement-task`/`refine-backlog`/`review-docs`), plus
  `_template_frontmatter_pairs` (reads `templates/config.md`'s ordered key list as literal text,
  since `{{placeholder}}` tokens for `REQUIRED_KEYS` aren't valid YAML) and `merge_config_schema`
  (the additive merge itself).
- Added a `migrate-config [--target] [--apply]` subcommand, deliberately separate from `upgrade`:
  a bare call previews (added keys / version bump / unified diff, writes nothing); `--apply`
  writes and reruns `sync` + `sync check`. Kept as its own step (run after `upgrade`, against the
  freshly-installed `.tasks/bin/sync`) so `SKILL.md` has a STOP between preview and write, per the
  task's requirement that `config.md` stay outside `upgrade`'s manifest/hash-classified flow.
- Updated `init-project/SKILL.md` §5 with a "config.md migration" subsection describing the
  preview → STOP → `--apply` flow.
- Tests: 15 new cases in `tests/test_init_project_upgrade.py` — `merge_config_schema` unit tests
  (no-op on current schema, single/multiple missing keys at template position, project-added key
  preserved, body byte-identical including a `---`-lookalike line, round-trips through
  `parse_frontmatter`, idempotent on a second pass, `workflow_version` bump, never invents a
  missing `REQUIRED_KEYS` value) plus `migrate-config` subprocess tests (preview writes nothing,
  `--apply` writes and passes `sync check`, no-op JSON on an already-current schema, and a full
  `upgrade` → `migrate-config --apply` integration run).
- Full suite: `pytest` 417 passed; `python3 .tasks/bin/sync check` exits 0.

## Notes

- Builds directly on TASK-029's `upgrade` command and manifest/clone machinery.
- TASK-028's `ignored_paths` key is the first real case this migration handles end to end.
