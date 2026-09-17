---
id: TASK-034
title: Branch-name + dirty-tree gate hook
type: feature
status: done
epic: EPIC-002
created: 2026-09-14
branch: task-034-branch-dirty-tree-gate-hook
pr: "https://github.com/RobotNerd/sdlc-llm/pull/61"
merge_commit: bcdc215982736fe19bf9af817ba24d35c019deed
blocked_by: [TASK-032, TASK-028]
blocks: [TASK-039, TASK-040]
---

# TASK-034: Branch-name + dirty-tree gate hook

## Description

Blocked on TASK-032 (hooks infrastructure) and TASK-028 (`ignored_paths` config key, which this
hook must respect).

On `git checkout -b`/`git switch -c`: deny if the working tree is dirty outside the paths listed
in `ignored_paths` (`.tasks/config.md`), or if the new branch name doesn't match
`<branch_prefix><NNN>-<slug>`. Makes `implement-task` phase 1's existing preconditions structural
instead of relying on the model checking them itself.

## Acceptance criteria

- [ ] A dirty tree (ignoring configured `ignored_paths`) denies branch creation.
- [ ] A clean tree with a non-conforming branch name denies branch creation.
- [ ] A clean tree with a conforming branch name is allowed.
- [ ] `ignored_paths: []` (the default) makes any dirty file block branch creation — no behavior
      change for a project that hasn't configured any.
- [ ] `pytest` and `python3 .tasks/bin/sync check` both pass.

## Testing strategy

1. Unit tests on the branch-name pattern function and the dirty-tree-minus-`ignored_paths` check,
   against `.tasks/config.md` fixtures with varying `branch_prefix`/`ignored_paths`.
2. Hook-script tests with representative `git checkout -b`/`git switch -c` commands and varied
   working-tree fixtures (clean, dirty-but-ignored, dirty-and-not-ignored).
3. `pytest` — full suite green.
4. `python3 .tasks/bin/sync check` → exit 0.

## Worklog

Added to `guardrails.py`: `branch_name_violation(branch, branch_prefix)` (pure -- matches
`<branch_prefix><NNN>-<slug>`, the exact shape `compute_branch_name` produces) and
`dirty_tree_violation(cwd, ignored_paths)` (mirrors `implement-task/scaffold.py`'s existing
`dirty_files` logic -- same `git status --porcelain --untracked-files=all` handling, including
the untracked-directory-collapse gotcha -- but self-contained here so `guardrails.py` stays
independently vendorable; didn't touch `implement-task/scaffold.py`'s own copy, out of this
task's stated scope -- flagging the duplication as a candidate follow-up, not doing it silently).
`check_branch_create` parses `command` for a `git checkout -b|-B`/`git switch -c|-C` anywhere
in it (reusing the existing command-segment/shlex helpers from TASK-032), checks dirty-tree
first, then branch-name pattern. No new hook script needed -- `checkout`/`switch` are `Bash`
commands, so this slots into the existing `evaluate_bash_command` dispatcher, which now also
reads `ignored_paths` from config.

Testing strategy:
1. Unit tests for both functions (`tests/test_branch_create_guardrail.py`) against
   config-shaped fixtures with varying `branch_prefix`/`ignored_paths` -- conforming/
   non-conforming names, clean/dirty/dirty-but-ignored trees, and the `ignored_paths: []`
   default flagging any dirty file. **Pass.**
2. Hook-script tests: real subprocess invocation of the existing `pretooluse_bash.py` with
   representative `git checkout -b`/`git switch -c` commands and varied working-tree fixtures.
   **Pass.**
3. `python3 -m pytest -q` -- 493 passed (464 + 29 new), no regressions. **Pass.**
4. `python3 .tasks/bin/sync check` -- exit 0. **Pass.**

## Notes

- Depends on TASK-032's `guardrails.py` module/hook-wiring and TASK-028's `ignored_paths` key.
- Follow-up candidate (not filed as a task, just noted): `implement-task/scaffold.py`'s own
  `dirty_files` could be migrated to call `guardrails.dirty_tree_violation` instead of keeping
  its own copy, per SPEC-002's "define guardrail logic once" goal -- out of this task's scope.
