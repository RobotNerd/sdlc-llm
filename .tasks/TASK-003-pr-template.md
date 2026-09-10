---
id: TASK-003
title: "Add .github/pull_request_template.md mirroring acceptance criteria"
type: chore
status: todo
epic: EPIC-001
created: 2026-09-10
branch: task-003-pr-template
pr: null
merge_commit: null
blocked_by: []
blocks: [TASK-014]
---

# TASK-003: Add .github/pull_request_template.md mirroring acceptance criteria

## Description

A PR template whose body mirrors the task acceptance-criteria checklist plus a filled-in test-results section, so `implement-task` phase 3 can open a PR that maps 1:1 to the task file (SPEC-001 §`init`, §`implement-task`).

## Acceptance criteria

- [ ] `.github/pull_request_template.md` has an 'Acceptance criteria' checklist section and a 'Test results' section (including a slot for non-automatable steps run by the human).
- [ ] Template references the task ID and PR-title convention from SPEC-001 §Guardrails (conventional commit + `TASK-NNN`).
- [ ] Structure lines up with the task-file body so phase 3 is a copy-with-checkboxes, not a rewrite.

## Testing strategy

1. Open a throwaway draft PR in a scratch branch using the template; confirm GitHub picks it up and the sections render.
2. Walk a sample task file and confirm each acceptance-criteria line has a home in the template.

## Worklog

_(empty — appended during implementation)_

## Notes

- No dependencies.
- Blocks TASK-014 (`init` writes this file).
