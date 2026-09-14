---
id: TASK-030
title: "Migrate config.md to the current schema during upgrade"
type: feature
status: todo
epic: EPIC-001
created: 2026-09-14
branch: task-030-config-schema-migration
pr: null
merge_commit: null
blocked_by: [TASK-029]
blocks: []
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

- [ ] An existing `config.md` missing a key the current template defines gains it, with the
      template's default, at the template's position.
- [ ] Every pre-existing key keeps its exact value; existing key order is preserved; project-added
      keys are left alone.
- [ ] The markdown body below the frontmatter is byte-identical after the merge.
- [ ] A `config.md` already matching the schema is left completely untouched (idempotent).
- [ ] The merged file round-trips through the installed `sync`'s `parse_frontmatter`.
- [ ] `workflow_version` is bumped when the template's value is higher, and reported.
- [ ] The upgrade summary names every key added, and the human sees the diff at a STOP.

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

_(empty — appended during implementation)_

## Notes

- Builds directly on TASK-029's `upgrade` command and manifest/clone machinery.
- TASK-028's `ignored_paths` key is the first real case this migration handles end to end.
