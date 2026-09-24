---
id: TASK-081
title: "implement-task-v2: docs updates and drop v1-only config keys"
type: docs
status: todo
epic: EPIC-005
created: 2026-09-23
branch: task-081-v2-docs-config
pr: null
merge_commit: null
blocked_by: [TASK-078, TASK-079, TASK-080]
blocks: []
---

# TASK-081: implement-task-v2: docs updates and drop v1-only config keys

## Description

Update the docs for v2 and remove the v1-only config keys.

**Docs:**

- `README.md`, `CLAUDE.md`, `.tasks/guidelines.md`, and its init-project template mirror say that
  `implement-task-v2` is in development next to `implement-task`.
- `CLAUDE.md`'s Guardrails section notes v2's local squash-merge and push to `main`, and that
  `pretooluse_bash.py` is unregistered in this repo; the other hooks still enforce.

**`.tasks/config.md`:** remove the deprecated keys that only v1 uses and v2 ignores, together
with their key notes:

- `allow_auto_merge`
- `autonomous_merge_cap` (including its commented-out note)
- `ci_checks`
- `delete_branch_after_merge`
- `merge_strategy`
- `rebase_before_pr`
- `tdd_enforced`

The remaining key notes say which skill reads each key. v1 keeps running on its built-in
defaults. The init-project template `config.md` is unchanged until cutover.

## Acceptance criteria

- [ ] `README.md`, `CLAUDE.md`, `.tasks/guidelines.md` and `.claude/skills/init-project/templates/guidelines.md` describe `implement-task-v2` accurately and concisely, and the two guidelines copies don't drift.
- [ ] `.tasks/config.md` no longer contains `allow_auto_merge`, `autonomous_merge_cap`, `ci_checks`, `delete_branch_after_merge`, `merge_strategy`, `rebase_before_pr` or `tdd_enforced`, as values or key notes.
- [ ] Each remaining key note names the skill(s) that read the key, and the notes are sorted where their order doesn't matter.
- [ ] The `.github/workflows/ci.yml` comment that cites `ci_checks` is updated.
- [ ] v1 still loads config: `python3 .claude/skills/implement-task/scaffold.py resume-state` runs without a config error.
- [ ] `test_command` and `sync check` pass.

## Testing strategy

1. `grep -E 'allow_auto_merge|autonomous_merge_cap|ci_checks|delete_branch_after_merge|merge_strategy|rebase_before_pr|tdd_enforced' .tasks/config.md` finds nothing.
2. `python3 .claude/skills/implement-task/scaffold.py resume-state` exits 0.
3. Run the `review-docs` skill and confirm it reports no guidelines-mirror drift and no dangling references.
4. `.venv/bin/pytest` and `python3 .tasks/bin/sync check` pass.

## Worklog

_(empty — appended during implementation)_

## Notes

- These are the v1-only keys listed in SPEC-005 §Design "Config". The init-project template `config.md` still ships them, because vendored projects run v1 until cutover.
