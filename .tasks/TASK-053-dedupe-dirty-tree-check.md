---
id: TASK-053
title: "implement-task: delegate dirty_files to guardrails.dirty_tree_violation"
type: refactor
status: todo
epic: EPIC-002
created: 2026-09-17
branch: task-053-dedupe-dirty-tree-check
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-053: implement-task: delegate dirty_files to guardrails.dirty_tree_violation

## Description

`implement-task/scaffold.py`'s `dirty_files` and `guardrails.py`'s `dirty_tree_violation` are the
same function with different names. Make `dirty_files` a thin delegate to the guardrails module so
the logic exists once, per SPEC-002's "define guardrail logic once" goal. Keep `dirty_files` as the
scaffold's public name — its 4 call sites and 6 test assertions stay untouched.

Two decisions already made (do not re-litigate):

1. **Thin wrapper, not removal.** `dirty_files(cwd, ignore=())` survives as a delegate; call sites
   and tests are not rewritten.
2. **Fail-open wins.** `dirty_tree_violation` keeps returning `[]` when `git status` exits
   non-zero — unchanged, because the hook path must never hard-fail on a broken git. The scaffold
   inherits that, losing today's `check=True` raise. Acceptable: `repo_root()` already exits
   non-zero outside a git repo, so a failing `git status` at these call sites is near-impossible.
   Record the delta below in Notes.

## Acceptance criteria

- [ ] `dirty_files` in `.claude/skills/implement-task/scaffold.py` contains no `git status`
      invocation or porcelain parsing of its own — it calls `guardrails.dirty_tree_violation`.
- [ ] `dirty_tree_violation` in `.tasks/bin/guardrails.py` is unchanged (signature and fail-open
      behavior both), so no hook behavior shifts.
- [ ] All 4 existing call sites (`scaffold.py:285`, `:320`, `:434`, `:488`) keep their current
      signature and results.
- [ ] Guardrails resolution does **not** depend on the `cwd` argument —
      `test_dirty_files_excludes_given_ignore_paths` passes a bare `tmp_path` git repo with no
      `.tasks/` in it, and must keep passing unmodified.
- [ ] `guardrails.py` stays independently vendorable — it gains no dependency on the skill.
- [ ] `pytest` green with no test file edits, and `python3 .tasks/bin/sync check` exits 0.

## Testing strategy

1. `python3 -m pytest -q` — the full suite, unmodified. The existing `dirty_files` tests
   (`tests/test_implement_task_scaffold.py:267`, `:414`, `:464`, `:502`, `:825`) and the
   `dirty_tree_violation` tests (`tests/test_branch_create_guardrail.py:78-101`) are the
   regression net; both sets must pass with no changes.
2. Confirm the `tmp_path`-without-`.tasks/` case specifically:
   `pytest -q tests/test_implement_task_scaffold.py::test_dirty_files_excludes_given_ignore_paths`.
3. Confirm the vendored/production path still resolves: run
   `python3 .claude/skills/implement-task/scaffold.py resume-state` from the repo root and check
   it emits JSON rather than a guardrails-import `SystemExit`.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

_(empty — appended during implementation)_

## Notes

- Implementation sketch: add a `load_guardrails_module()` next to the existing
  `load_sync_module` (`scaffold.py:47`), following the same `SourceFileLoader` technique. It must
  return `sys.modules["guardrails"]` when already registered (`tests/conftest.py:28-32` registers
  it) and otherwise load `.tasks/bin/guardrails.py` resolved from **the script's own location** —
  `Path(__file__).resolve().parents[3] / ".tasks" / "bin" / "guardrails.py"` — not from the `cwd`
  argument, which is what keeps the `tmp_path` test working and is still correct once vendored
  (`init-project` installs both files into the same target repo; see
  `.claude/skills/init-project/scaffold.py:301-302`). Cache the loaded module at module level.
- `ignore` is a tuple/sequence in the wrapper's signature but
  `dirty_tree_violation(cwd, ignored_paths)` takes it positionally — pass `tuple(ignore)`.
- Direction of the dependency is one-way on purpose: the skill script imports the vendored
  guardrails module, never the reverse.
- Source of this task: TASK-034's Notes
  (`.tasks/archive/TASK-034-branch-dirty-tree-gate-hook.md:74-76`).
