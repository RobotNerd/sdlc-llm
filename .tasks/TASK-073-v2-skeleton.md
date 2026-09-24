---
id: TASK-073
title: "implement-task-v2 skeleton: 11-step SKILL.md with a single-task happy path"
type: feature
status: todo
epic: EPIC-005
created: 2026-09-23
branch: task-073-v2-skeleton
pr: null
merge_commit: null
blocked_by: []
blocks: [TASK-074]
---

# TASK-073: implement-task-v2 skeleton: 11-step SKILL.md with a single-task happy path

## Description

Create `.claude/skills/implement-task-v2/`. Its `SKILL.md` names all 11 steps (SPEC-005
§Design "Workflow"), and the default no-argument path works end to end:

- **ensure clean repo**: `gh` present, clean tree, update `main`.
- **build batch**: default mode only, the top unblocked TODO task. Any argument → STOP, saying
  argument forms aren't supported yet.
- **start task** → **write tests** → **implement task** → **run tests**.
- **merge changes**: bookkeeping on the branch, squash-merge to `main`, push, `git branch -D`,
  delete the throwaway tests.
- **batch complete**: print the result and STOP.

`detect interrupted batch`, `spawn critic` and `create summary report` are headings holding a
one-line "not yet implemented, skip" placeholder. Later tasks in this epic fill them in.

Reference docs, with the content SPEC-005 proposes: `naming-conventions.md`,
`testing-strategy.md`, `guardrails.md`.

Repo changes that come with the skeleton:

- `.gitignore` gains `tests/throwaway/`.
- `implement-task-v2` is added to init-project's `_REPO_ONLY_SKILLS`.
- `.claude/hooks/pretooluse_bash.py` is unregistered in this repo's `.claude/settings.json`, and
  `tests/test_guardrails.py`'s settings-parity test is updated to expect that. The other hooks
  stay registered.

## Acceptance criteria

- [ ] `SKILL.md` exists with frontmatter `name: implement-task-v2` and a one-line description.
- [ ] `SKILL.md` has the 11 steps as headings, in the exact order and with the exact names from SPEC-005 §Design "Workflow".
- [ ] A no-argument run takes the top unblocked TODO task through: a branch named per `naming-conventions.md`, `status: in-progress` on the branch, TDD tests, the implementation, green quality gates, bookkeeping (`status: done`, archived by `sync`), a squash commit on `main` with the conventional message, a push to `<remote>`, the local branch deleted, and throwaway tests deleted.
- [ ] The run stops before changing anything when `gh` is missing or the working tree is dirty (outside `ignored_paths`).
- [ ] Every step that changes files on the task branch ends with a commit (`chore(TASK-NNN): start task` or `wip(TASK-NNN): <step name>`).
- [ ] `references/naming-conventions.md`, `references/testing-strategy.md` and `references/guardrails.md` exist with SPEC-005's content, and `SKILL.md` points to each one at the step that needs it.
- [ ] `tests/throwaway/` is gitignored.
- [ ] `implement-task-v2` is in `_REPO_ONLY_SKILLS`.
- [ ] `pretooluse_bash.py` is unregistered only in `.claude/settings.json`. `pretooluse_edit_write.py`, `check-portable-references.py` and the `SessionStart` hook stay registered, and init-project's template `settings.json` is unchanged.
- [ ] The skill contains no concrete `TASK-`/`EPIC-`/`SPEC-` ids, so the portable-surface test passes.
- [ ] `test_command` and `sync check` pass.

## Testing strategy

1. Commit a new behavioral test, `tests/test_implement_task_v2_skill.py`: `SKILL.md`'s step headings equal the 11 names, in order; every `references/*.md` named in `SKILL.md` exists; and every file in `references/` is named in `SKILL.md`.
2. Update the settings-parity test in `tests/test_guardrails.py`. `.venv/bin/pytest` passes in full.
3. `python3 .tasks/bin/sync check` exits 0.
4. Manual, in a scratch repo: `init-project --target <tmp>`, a local bare repo as `origin`, a few dummy `todo` tasks, and `.claude/skills/implement-task-v2/` copied in: run `/implement-task-v2` with no argument. Confirm that `origin/main` has one squash commit citing the task, the task is archived, the local branch is gone, and `tests/throwaway/` is empty.
5. Manual, same scratch repo: dirty the tree, run the skill, and confirm it stops with nothing changed.

## Worklog

_(empty — appended during implementation)_

## Notes

- Design detail is in SPEC-005 §Design. This task implements the steps listed above; the other steps stay placeholders.
- Every task in this epic is developed on a local branch, then squash-merged into `main` and pushed. Until this task's `.claude/settings.json` change is in effect, `pretooluse_bash.py` denies that push. The session may need a restart, or a `/hooks` review, to pick up the new registration.
