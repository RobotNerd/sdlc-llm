---
description: "Invoked by another skill, the search finds a similar open task: the task is created anyway, with a comment naming the similar one."
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
- type: docs
- title: Add a CHANGELOG file at the repo root
- description:

```markdown
## Description
Keep a CHANGELOG.md at the repo root, so users can see what changed between releases.

## Acceptance criteria
- [ ] CHANGELOG.md exists at the repo root, with an "Unreleased" heading.

## Testing strategy
### Automated
#### Repo root → changelog with Unreleased   (criterion: first)
* **Given:** the repo at the task's branch
* **When:** a test reads CHANGELOG.md
* **Then:** the file exists, and has an "Unreleased" heading

### Manual
None

## Notes
None
```
