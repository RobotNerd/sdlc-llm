---
id: TASK-074
title: "implement-task-v2: per-task and per-batch summary reports"
type: feature
status: todo
epic: EPIC-005
created: 2026-09-23
branch: task-074-v2-summary-reports
pr: null
merge_commit: null
blocked_by: [TASK-073]
blocks: [TASK-075, TASK-076]
---

# TASK-074: implement-task-v2: per-task and per-batch summary reports

## Description

Add `references/summary-report.md`, with SPEC-005's per-task and batch formats, and implement
two steps:

- **create summary report** writes `reports/<branch>.md` after `merge changes`.
- **batch complete** writes `reports/batch-%Y-%m-%d-%H-%M-%S.md`.

`reports/` is gitignored. Sections whose data comes from later tasks in this epic (critic,
early stop, follow-ups, usage) print `none` for now; each later task fills in its own section.
The Manual testing section collects every Testing strategy step the agent couldn't run.

## Acceptance criteria

- [ ] `references/summary-report.md` exists with SPEC-005's per-task and batch templates, and `create summary report` / `batch complete` point to it.
- [ ] After a merge, `reports/task-NNN-<slug>.md` exists and has every per-task section.
- [ ] At batch end, `reports/batch-<YYYY-MM-DD-HH-MM-SS>.md` exists and has every batch section. Empty sections say `none`.
- [ ] A task whose Testing strategy has a human-only step shows that step, with its expected result, under Manual testing in both reports.
- [ ] `reports/` is gitignored, and writing reports never dirties the tree.
- [ ] `test_command` and `sync check` pass.

## Testing strategy

1. Extend `tests/test_implement_task_v2_skill.py` if a new reference doc needs to be listed there. The existing reference-integrity checks cover it.
2. Manual, in a scratch repo: `init-project --target <tmp>`, a local bare repo as `origin`, a few dummy `todo` tasks, and `.claude/skills/implement-task-v2/` copied in: run a no-argument batch on a dummy task that has one manual Testing strategy step. Check both report filenames, all sections, and the Manual testing content.
3. `git status` is clean after the batch.
4. `.venv/bin/pytest` and `python3 .tasks/bin/sync check` pass.

## Worklog

_(empty — appended during implementation)_

## Notes

- Report formats are in SPEC-005 §Design "Reference documents".
