---
id: TASK-034
title: Branch-name + dirty-tree gate hook
type: feature
status: todo
epic: EPIC-002
created: 2026-09-14
branch: task-034-branch-dirty-tree-gate-hook
pr: null
merge_commit: null
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

_(empty — appended during implementation)_

## Notes

- Depends on TASK-032's `guardrails.py` module/hook-wiring and TASK-028's `ignored_paths` key.
