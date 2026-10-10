---
description: "A complete request: the task is created from the template, labelled, and placed at the top of to-do."
tags: [add-task]
model: claude-sonnet-5-5
max_turns: 40
timeout_seconds: 600
allowed_tools: [Read, Glob, Grep, Skill, AskUserQuestion]
---

Add a task: the README should say how to run the tests. It's a docs change, it isn't part of any epic, nothing blocks it, and it goes at the top of the to-do column.

Done means:
- The README has a "Running the tests" section.
- That section shows the exact command, `python3 -m pytest`.

Testing: an automated test checks that README.md has the section and the command in a code block. Manual test, because only a person can judge it: on a fresh clone, follow the section alone and check that the tests run. It doesn't block merge.
