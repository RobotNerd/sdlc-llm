---
id: TASK-004
title: "sync: stdlib frontmatter parser and artifact loader"
type: feature
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-004-sync-frontmatter-parser
pr: null
merge_commit: null
blocked_by: [TASK-002]
blocks: [TASK-006, TASK-010, TASK-011]
---

# TASK-004: sync: stdlib frontmatter parser and artifact loader

## Description

The foundation of `sync`: a single-file Python 3 module, standard library only, that reads a `.tasks/` tree and returns typed Spec/Epic/Task records. Hand-parses the frontmatter subset SPEC-001 §'The sync script' names — scalars, `null`, and `[a, b]` lists — with no YAML dependency.

## Acceptance criteria

- [ ] Parser handles: quoted and bare scalars, `null`, integers, and inline `[a, b, c]` lists; ignores trailing `# comments`; rejects anything outside that subset with a clear error.
- [ ] Loader discovers `SPEC-*.md`, `EPIC-*.md`, `TASK-*.md` under `.tasks/`, `.tasks/specs/`, and `.tasks/archive/`, returning records keyed by ID.
- [ ] Loader round-trips: writing a record back produces byte-identical frontmatter for the supported subset.
- [ ] No import outside the Python standard library.
- [ ] Unit tests cover each frontmatter form and the malformed-input errors.

## Testing strategy

1. Run the parser over every file created in this epic and confirm all fields load with correct types.
2. Feed deliberately malformed frontmatter (tab indent, nested map, unterminated list) and confirm each raises a specific error, not a stack trace.
3. `python3 -c 'import ast; ast.parse(open("sync").read())'` — script parses.

## Worklog

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-002 (schema the parser targets).
- Blocks TASK-006, TASK-010, TASK-011 and, transitively, the rest of `sync`.
- Decide the script's home now (`.tasks/bin/sync` proposed) — later tasks hard-code it.
