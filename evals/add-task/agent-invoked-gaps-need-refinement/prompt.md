---
description: "Invoked by another skill with no testing strategy: the task is created in Planned, with a needs-refinement comment listing the gap."
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
- placement: end
- deferred: off
- type: docs
- title: Add a troubleshooting section to the README
- description:

```markdown
## Description
Add a Troubleshooting section to README.md covering the three most common install errors.

## Acceptance criteria
- [ ] README.md has a "Troubleshooting" heading, with one entry per install error.

## Notes
None
```
