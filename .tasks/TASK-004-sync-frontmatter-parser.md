---
id: TASK-004
title: "sync: stdlib frontmatter parser and artifact loader"
type: feature
status: in-progress
epic: EPIC-001
created: 2026-09-10
branch: task-004-sync-frontmatter-parser
pr: null
merge_commit: null
blocked_by: []
blocks: [TASK-006, TASK-010, TASK-011]
---

# TASK-004: sync: stdlib frontmatter parser and artifact loader

## Description

The foundation of `sync`: a single-file Python 3 module at `.tasks/bin/sync`, standard library only, that reads a `.tasks/` tree and returns typed Spec/Epic/Task records. Hand-parses the frontmatter subset SPEC-001 §'The sync script' names — scalars, `null`, and `[a, b]` lists — with no YAML dependency. As the first task to ship Python, it also lays down the project's test scaffold.

## Acceptance criteria

- [ ] Script lives at `.tasks/bin/sync` and is executable.
- [ ] Parser handles: quoted and bare scalars, `null`, integers, and inline `[a, b, c]` lists; ignores trailing `# comments`; rejects anything outside that subset with a clear error.
- [ ] Loader discovers `SPEC-*.md`, `EPIC-*.md`, `TASK-*.md` under `.tasks/`, `.tasks/specs/`, and `.tasks/archive/`, returning records keyed by ID.
- [ ] Loader round-trips: writing a record back produces byte-identical frontmatter for the supported subset.
- [ ] No import outside the Python standard library.
- [ ] A `pyproject.toml` at the repo root declares `pytest` as the sole dev dependency (a `[dependency-groups] dev` or `[project.optional-dependencies] dev` entry — nothing else), and a `tests/` directory exists. No conda/uv requirement; plain `pip install` works.
- [ ] Unit tests (under `tests/`, run by `pytest`) cover each frontmatter form and the malformed-input errors.

## Testing strategy

1. `pip install -e '.[dev]'` (or `uv sync`), then `pytest` — the parser suite passes.
2. Run the parser over every file created in this epic and confirm all fields load with correct types.
3. Feed deliberately malformed frontmatter (tab indent, nested map, unterminated list) and confirm each raises a specific error, not a stack trace.
4. `python3 -c 'import ast; ast.parse(open(".tasks/bin/sync").read())'` — script parses.

## Worklog

- 2026-09-11: Picked out of TODO order (TASK-005 is listed first but has no `blocked_by`; both
  are unblocked). TASK-005's AC requires pytest-run unit tests, and the pytest scaffold
  (`pyproject.toml`, `tests/`) is this task's scope. Doing TASK-004 first avoids TASK-005 either
  bootstrapping that scaffold itself (scope creep across task boundaries) or shipping without
  real tests. TODO list order is unchanged — this is a one-off pick of the top *practically*
  unblocked task, confirmed with the user.

## Notes

- Not blocked by TASK-002: the parser targets the frontmatter schema in SPEC-001 §'Data model',
  which already exists. The templates are a convenience for humans/skills, not an input to the
  parser. (Dropped the TASK-002 → TASK-004 edge during the git-automation refinement pass so
  `sync` can start sooner.)
- Blocks TASK-006, TASK-010, TASK-011 and, transitively, the rest of `sync`.
- Script home is fixed at `.tasks/bin/sync` (SPEC-001 §'The sync script'); later tasks hard-code it.
