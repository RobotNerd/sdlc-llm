---
description: "Invoked by another skill with a task that spans unrelated areas: it's created anyway, with a comment saying why it looks too big."
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
- title: Add a version flag, move CI to GitHub Actions, and add a logo
- description:

```markdown
## Description
Three changes for the next release: `example --version` prints the package version, CI moves from Travis to GitHub Actions, and the README gets a logo.

## Acceptance criteria
- [ ] `example --version` prints the version from `pyproject.toml` and exits 0.
- [ ] `.github/workflows/ci.yml` runs the tests on every push, and `.travis.yml` is gone.
- [ ] README.md shows `docs/logo.svg` above its first heading.

## Testing strategy
### Automated
#### Version flag → version printed   (criterion: first)
* **Given:** the package is installed
* **When:** `example --version` runs
* **Then:** it prints the version from `pyproject.toml`, and exits 0
#### Push → CI runs   (criterion: second, agent-run)
* **Given:** the branch is pushed
* **When:** GitHub Actions runs
* **Then:** the run passes, and no Travis config is left
#### README → logo first   (criterion: third)
* **Given:** the repo at the task's branch
* **When:** a test reads README.md
* **Then:** its first line is an image of `docs/logo.svg`

### Manual
None

## Notes
None
```
