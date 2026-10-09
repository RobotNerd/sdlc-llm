---
description: "An epic and a blocker are given: the task is linked as a subtask of the epic and blocked by the blocker."
tags: [add-task]
model: claude-sonnet-5-5
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, AskUserQuestion]
---

New feature task for the Docs overhaul epic (EX-1): add a `--version` flag to the CLI that prints the package version. It's blocked by EX-4, and it goes at the end of to-do.

Acceptance criteria:
- `example --version` prints the version from pyproject.toml and exits 0.

Testing: an automated test that runs `example --version` and checks the output matches the version in pyproject.toml. No manual test.
