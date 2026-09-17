---
id: TASK-053
title: "implement-task: delegate dirty_files to guardrails.dirty_tree_violation"
type: refactor
status: done
epic: EPIC-002
created: 2026-09-17
branch: task-053-dedupe-dirty-tree-check
pr: "https://github.com/RobotNerd/sdlc-llm/pull/63"
merge_commit: 8abf1d6ca0a88caf11090d6fbe588f74fd8914b8
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

- [x] `dirty_files` in `.claude/skills/implement-task/scaffold.py` contains no `git status`
      invocation or porcelain parsing of its own — it calls `guardrails.dirty_tree_violation`.
- [x] `dirty_tree_violation` in `.tasks/bin/guardrails.py` is unchanged (signature and fail-open
      behavior both), so no hook behavior shifts.
- [x] All 4 existing call sites (`scaffold.py:285`, `:320`, `:434`, `:488`) keep their current
      signature and results.
- [x] Guardrails resolution does **not** depend on the `cwd` argument —
      `test_dirty_files_excludes_given_ignore_paths` passes a bare `tmp_path` git repo with no
      `.tasks/` in it, and must keep passing unmodified.
- [x] `guardrails.py` stays independently vendorable — it gains no dependency on the skill.
- [x] `pytest` green with no test file edits, and `python3 .tasks/bin/sync check` exits 0.

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

- Added `load_guardrails_module()` to `scaffold.py` next to `load_sync_module`, following the
  same `SourceFileLoader` technique `guardrails.py`'s own `_load_sync()` uses: reuse
  `sys.modules["guardrails"]` if already registered (as `tests/conftest.py` does), else load
  `.tasks/bin/guardrails.py` resolved from `Path(__file__).resolve().parents[3]` (the script's own
  location, not `cwd`).
- Rewrote `dirty_files` as a one-line delegate: `load_guardrails_module().dirty_tree_violation(cwd,
  tuple(ignore))`. Signature, call sites, and public name unchanged.
- `guardrails.py`'s `dirty_tree_violation` was not touched — no signature or behavior change,
  including its fail-open-on-broken-`git status` return of `[]`. See the delta this introduces in
  the scaffold's own behavior, noted below.
- Full suite: `.venv/bin/pytest -q` → 493 passed.
- `test_dirty_files_excludes_given_ignore_paths` (the bare-`tmp_path`-with-no-`.tasks/` case) →
  passed unmodified, confirming guardrails resolution doesn't depend on `cwd`.
- `python3 .claude/skills/implement-task/scaffold.py resume-state` from the repo root → emitted
  JSON (`{"phase": "phase2", "task_id": "TASK-053"}`), not a guardrails-import `SystemExit`,
  confirming the vendored/production path resolves.
- `python3 .tasks/bin/sync check` → exit 0.

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
- **Fail-open delta (as anticipated above):** `dirty_files` previously ran `git status` with
  `check=True`, raising `CalledProcessError` if it exited non-zero. It now inherits
  `dirty_tree_violation`'s fail-open behavior — a broken `git status` at any of the 4 call sites
  now returns `[]` (tree reads as clean) instead of raising. Accepted per the task's own framing:
  `repo_root()` already exits non-zero outside a git repo, so a failing `git status` at these call
  sites (all reached only after `repo_root()` succeeds) is near-impossible in practice.
