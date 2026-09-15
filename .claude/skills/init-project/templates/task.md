<!--
  Template for .tasks/TASK-NNN-slug.md.
  Placeholders, filled in by the skill or human creating the task:
    {{id}}         TASK-NNN, from `sync next-id task`
    {{title}}      short summary; quoted here since a title often contains
                   a colon (e.g. "sync: stdlib frontmatter parser") -- keep
                   the quotes even if this particular title doesn't need them
    {{type}}       feature | bug | chore | refactor | docs
    {{epic}}       EPIC-NNN, or `null` for a loose task with no epic
    {{created}}    today's date, YYYY-MM-DD
    {{branch}}     <branch_prefix><id-number>-<slug>, e.g. task-NNN-my-task
    {{blocked_by}} a bracketed list of task ids, e.g. [TASK-NNN, TASK-NNN],
                   or [] if none
  Fields the skill does NOT fill in -- they start at these fixed values
  and only change as the task moves through implement-task's phases:
    status: todo | pr: null | merge_commit: null | blocks: []
-->
---
id: {{id}}
title: "{{title}}"
type: {{type}}
status: todo
epic: {{epic}}
created: {{created}}
branch: {{branch}}
pr: null
merge_commit: null
blocked_by: {{blocked_by}}
blocks: []
---

# {{id}}: {{title}}

## Description

{{description}}

## Acceptance criteria

- [ ] {{criterion}}

## Testing strategy

1. {{step}}

## Worklog

_(empty — appended during implementation)_

## Notes

- {{note}}
