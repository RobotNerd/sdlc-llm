---
description: "A task in an epic has a manual test that doesn't block merge: it's added to the epic's validation task, and the new task blocks that task."
tags: [add-task]
model: claude-sonnet-5-5
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, AskUserQuestion]
---

New feature for the Docs overhaul epic (EX-1): `example notify` sends a test message to the team's Slack channel. Nothing blocks it, and it goes at the end of to-do.

Acceptance criteria:
- `example notify` exits 0, and the message shows up in the Slack channel.

Testing: an automated test runs `example notify` against a fake Slack server and checks the request it sent. Manual test, because only a person can see the real channel: run `example notify` and check that the message arrives in Slack. The manual test doesn't block merge; it can wait for the end of the epic.
