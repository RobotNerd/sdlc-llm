---
id: TASK-001
title: "Author guidelines.md and config.md for this repo"
type: chore
status: in-progress
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

- [ ] `.tasks/config.md` contains every key from SPEC-001 §`.tasks/config.md` with values for this repo: `test_command: pytest`, `lint_command`, `docs_paths`, `default_branch: main`, `branch_prefix: task-`, `remote: origin`, `rebase_before_pr: true`, `merge_strategy: squash`, `delete_branch_after_merge: true`, `allow_auto_merge: false`, `ci_checks`, `archive_done: true`, `workflow_version: 1`.
- [ ] `.tasks/guidelines.md` states the Guardrails list from SPEC-001 verbatim (including never-merge, and `--force-with-lease`-only) and the task/epic/spec lifecycle in checklist form.
- [ ] `guidelines.md` has a git-workflow section: branch from freshly-fetched `origin/main`, rebase before PR, `gh pr create`, human squash-merges on GitHub, phase 4 only observes the merge.
- [ ] `guidelines.md` carries a `workflow_version` field so a future `upgrade` path can migrate the repo.
- [ ] Terminology is 'task' throughout, per CLAUDE.md.

## Testing strategy

1. Load `config.md` as YAML (`python3 -c` with PyYAML for now; the stdlib parser from TASK-004 later) and confirm every documented key is present and correctly typed.
2. Cross-check `guidelines.md` guardrails line-for-line against SPEC-001 §Guardrails.
3. Dry-check the git-workflow section against SPEC-001 §`implement-task` phases 1/3/4 — same commands, same order.

## Worklog

_(empty — appended during implementation)_

## Notes

- No dependencies — pure authoring.
- Blocks TASK-014 (`init` generates these from templates).
