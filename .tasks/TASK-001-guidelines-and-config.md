---
id: TASK-001
title: "Author guidelines.md and config.md for this repo"
type: chore
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-001-guidelines-and-config
pr: null
merge_commit: null
blocked_by: []
blocks: []
---

# TASK-001: Author guidelines.md and config.md for this repo

## Description

Write the two per-project files SPEC-001 depends on: `.tasks/guidelines.md` (the workflow rules, carrying `workflow_version: 1`) and `.tasks/config.md` (the config seam every skill and `sync` reads). Values are filled for *this* repo; `init` (TASK-014) will later generate both for a fresh repo.

## Acceptance criteria

- [ ] `.tasks/config.md` contains every key from SPEC-001 §`.tasks/config.md` with values for this repo (`test_command`, `lint_command`, `default_branch: main`, `branch_prefix: task-`, `allow_auto_merge: false`, `ci_checks`, `archive_done: true`, `workflow_version: 1`).
- [ ] `.tasks/guidelines.md` states the Guardrails list from SPEC-001 verbatim and the task/epic/spec lifecycle in checklist form.
- [ ] `guidelines.md` carries a `workflow_version` field so a future `upgrade` path can migrate the repo.
- [ ] Terminology is 'task' throughout, per CLAUDE.md.

## Testing strategy

1. Load `config.md` as YAML (stdlib parser once TASK-004 lands, `python3 -c` with PyYAML until then) and confirm every documented key is present and correctly typed.
2. Cross-check `guidelines.md` guardrails line-for-line against SPEC-001 §Guardrails.

## Worklog

_(empty — appended during implementation)_

## Notes

- No dependencies — pure authoring.
- Blocks TASK-014 (`init` generates these from templates).
