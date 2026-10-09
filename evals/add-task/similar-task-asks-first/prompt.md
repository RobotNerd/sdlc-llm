---
description: "Search finds a similar open task: the skill asks before creating a duplicate."
tags: [add-task]
model: claude-sonnet-5-5
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, AskUserQuestion]
---

Create a chore task to add a CHANGELOG.md at the repo root, at the end of to-do, no epic, no blockers.

Acceptance criteria:
- CHANGELOG.md exists at the repo root, with an "Unreleased" heading.

Testing: no automated tests. Manual: check that CHANGELOG.md exists and has the heading.
