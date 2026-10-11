---
description: "Invoked by another skill with every parameter: the task is validated and created, with no questions and no notifications."
tags: [add-task]
model: claude-sonnet-5-5
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, AskUserQuestion]
---

This is plan-feature, creating the tasks for an approved spec. Invoke the add-task skill non-interactively with these parameters:

- invoked_by: plan-feature
- epic: none
- blocked_by: none
- placement: planned
- deferred: off
- type: feature
- title: Add a --version flag to the example CLI
- description:

```markdown
## Description
`example --version` prints the package version, so bug reports can say which version they ran.

## Acceptance criteria
- [ ] `example --version` prints the version from `pyproject.toml` and exits 0.

## Testing strategy
### Automated
#### Version flag → version printed   (criterion: first)
* **Given:** the package is installed
* **When:** `example --version` runs
* **Then:** it prints the version from `pyproject.toml`, and exits 0

### Manual
None

## Notes
None
```
