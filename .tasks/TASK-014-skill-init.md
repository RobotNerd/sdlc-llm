---
id: TASK-014
title: "init skill: scaffold .tasks/ in a new repo"
type: feature
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-014-skill-init
pr: null
merge_commit: null
blocked_by: [TASK-002, TASK-003, TASK-010]
blocks: []
---

# TASK-014: init skill: scaffold .tasks/ in a new repo

## Description

A checklist skill that scaffolds the workflow into a fresh repo: empty `BOARD.md` with all regions, `config.md` (interviewing for `test_command` etc.), `guidelines.md` with `workflow_version`, the `.tasks/templates/` set, and `.github/pull_request_template.md` (SPEC-001 §`init`).

## Acceptance criteria

- [ ] Skill is a numbered checklist with explicit STOP markers and 'if X ambiguous, ASK' rules — not prose.
- [ ] Produces: `BOARD.md` (with `epics` + four column regions, empty → `_(none)_`), `config.md`, `guidelines.md`, `.tasks/templates/{spec,epic,task}.md`, `.github/pull_request_template.md`.
- [ ] Interviews the user for every `config.md` value rather than guessing, including the git settings (`remote`, `rebase_before_pr`, `merge_strategy`, `delete_branch_after_merge`) with sensible defaults offered; writes `workflow_version: 1`.
- [ ] Generated `guidelines.md` includes the git-workflow section and the never-merge / `--force-with-lease`-only guardrails (SPEC-001 §Guardrails).
- [ ] Detects whether `gh` is installed and authenticated (`gh auth status`) and warns if not, since `implement-task` needs it.
- [ ] Refuses to run if `.tasks/` already exists (points at an `upgrade` path instead).
- [ ] Ends by running `sync` and showing the clean board.

## Testing strategy

1. Run `init` in an empty scratch git repo; confirm every listed file appears and `sync check` exits 0 immediately after.
2. Run `init` again in the same repo; confirm it refuses.
3. Verify the generated `BOARD.md` region shapes match SPEC-001 §'Rendering details'.

## Worklog

_(empty — appended during implementation)_

## Notes

- Blocked by TASK-002 (templates), TASK-003 (PR template), TASK-010 (no IDs yet, but shares the config-reading helper).
- Independent of the other skills.
