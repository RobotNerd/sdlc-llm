---
id: TASK-051
title: "Simplify and merge the unit test suite: cull redundant and mergeable test cases"
type: refactor
status: todo
epic: EPIC-001
created: 2026-09-16
branch: task-051-simplify-and-merge-the-unit-test-suite-cull-redundant-and-mergeable-test-cases
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-051: Simplify and merge the unit test suite: cull redundant and mergeable test cases

## Description

Audit all 375 tests across the 22 files in `tests/` (5,854 lines) for redundancy, mergeability,
and over-specification, then apply the cull. Reduce the context cost of the suite without
weakening what it actually asserts. This is a `tests/`-only change — no source file under
`.tasks/bin/sync` or `.claude/skills/*/scaffold.py` is modified.

A prior survey turned up concrete redundancy clusters worth starting from:

| Pattern | Evidence |
|---|---|
| Idempotence / "running twice is a no-op" | 17 separate tests across 10 files, several subsumed by `test_end_to_end.py::test_sync_twice_reaches_a_stable_no_op_state` |
| Pipe-in-title rejection | 4 near-identical tests (`test_board_renderers`, `test_epic_spec_renderers` ×2, `test_todo_merge`) |
| Duplicate test *names* across files | `test_slugify_normalizes_title`, `test_slugify_raises_on_unslugifiable_title`, `test_missing_keys_empty_when_all_present`, `test_missing_keys_reports_absent_ones` — duplicated across `test_add_task_scaffold.py`, `test_implement_task_scaffold.py`, `test_init_project_scaffold.py` |
| Single-assert refusal tests that want a `parametrize` table | 6 × `test_run_refuses_on_*` in `test_add_task_scaffold.py`; 5 × `test_run_refuses_*`/`test_run_target_*` in `test_init_project_scaffold.py` |
| Single-assert parser tests that want a table | 9 × `test_parses_*`/`test_*_is_ignored` in `test_sync.py` |
| Fixture-asserting tests | `test_end_to_end.py::test_fixture_exercises_every_status` and three siblings assert on the fixture itself, not on `sync` |

Caveat already surfaced by the survey: the duplicated `slugify`/`missing_keys` test names are
**not** pure redundancy — `add_task_scaffold` and `implement_task_scaffold` each carry their own
copy of these functions. Deleting one of the two tests would silently drop coverage of one module.
Rename (to name the module) rather than delete in these cases.

## Acceptance criteria

- [ ] A written disposition for every test file — which tests are kept, merged (into what), or
      deleted (and which surviving test subsumes each deletion) — recorded in the PR description.
- [ ] Baseline line coverage of `.tasks/bin/sync` and each `.claude/skills/*/scaffold.py` is
      captured **before** any test change (see Testing strategy).
- [ ] The 17 idempotence/no-op tests are consolidated — per-renderer "running twice is a no-op"
      tests collapse into the end-to-end idempotency assertion or a single shared parametrized
      test, keeping only those covering a genuinely distinct code path (`sync` archiving,
      `upgrade`, `apply_mechanical`, `merge_config_schema`).
- [ ] The 4 pipe-rejection tests collapse into one parametrized test over the renderers.
- [ ] Single-assert refusal/parse tests become `pytest.mark.parametrize` tables — at minimum the
      `test_run_refuses_*` clusters in `test_add_task_scaffold.py` and
      `test_init_project_scaffold.py`, and the `parse_frontmatter` scalar cases in `test_sync.py`.
- [ ] `test_end_to_end.py`'s fixture-asserting tests are removed or folded into fixture
      construction — the suite asserts on `sync`, not on its own fixture.
- [ ] Duplicate test names across files are resolved: either genuinely redundant (delete one) or
      testing separate module copies (rename so each names its module, e.g.
      `test_add_task_slugify_normalizes_title`). No two files define the same test name.
- [ ] Line coverage after the cull is **greater than or equal to** baseline for `.tasks/bin/sync`
      and every `scaffold.py` — no module loses coverage.
- [ ] Test count and total test-file line count both drop materially; the PR description states
      before/after numbers for both.
- [ ] No file outside `tests/` is modified. `pyproject.toml` still lists `pytest` as the sole dev
      dependency (`coverage` is used ad hoc, not added as a dependency).

## Testing strategy

1. Baseline: `python3 -m pytest -q` (record pass count). Then, with `coverage` installed into a
   throwaway venv (never added to `pyproject.toml`):
   `python3 -m coverage run --source=.tasks/bin,.claude/skills -m pytest -q && python3 -m coverage report`
   — save the per-file report as the baseline to diff against.
2. Work file by file. After each file's edits, `python3 -m pytest -q tests/<file>` stays green.
3. After the full pass: `python3 -m pytest -q` is green, and re-run the same `coverage` command.
   Diff the two reports; any module whose line coverage dropped means a deletion removed real
   coverage — restore or replace that test before proceeding.
4. `python3 .tasks/bin/sync check` exits 0 (nothing in `tests/` should affect it, but confirms no
   collateral damage).
5. Sanity-check the repo-reality tests still pass and still mean something:
   `test_portable_surface.py`,
   `test_review_docs_scaffold.py::test_report_against_this_repos_real_docs_is_clean`,
   `test_strip_project_references_scaffold.py::test_scan_against_this_repos_real_skills_tree_is_clean`.

## Worklog

_(empty — appended during implementation)_

## Notes

- `add_task_scaffold.slugify` and `implement_task_scaffold.slugify` are separate copies in
  separate modules; their identically-named tests are not redundant. Same caution applies to the
  `missing_keys` pairs. Rename rather than delete.
- Tests that run against this repo's *real* `.tasks/` tree
  (`test_discover_over_the_real_repo_tasks_directory`,
  `test_compute_branch_name_round_trips_every_real_task_branch`, the three repo-reality tests
  above) are high-value integration checks — keep them.
- Reducing count is the means, not the goal. A test that covers a distinct branch stays even if it
  looks like its neighbor on the surface.
