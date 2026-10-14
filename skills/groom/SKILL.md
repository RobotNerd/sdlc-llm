---
name: groom
description: Reviews the project's Kaneo backlog and proposes fixes. Use when the developer asks to groom, refine, tidy, triage, or review the backlog, to find blocked, stale, or under-specified tasks, or to check what's ready to work on.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/board.py*), Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py *), Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/validate_draft.py *)
model: opus
---

# groom

Reviews the open tasks, proposes changes in one numbered list, and makes only the ones the developer confirms. The Kaneo project is in `.sdlc/config.toml`. A task's key is `<project_slug>-<number>`.

## Hard rules

- Never change a task without a confirmed answer. An unanswered or declined proposal changes nothing.
- Read task rules only from `docs/guidelines/task-style.md`.
- Kaneo tools take a task's id, not its key. Labels attach by the workspace label whose `taskId` is null. Setting one task's `position` leaves the others alone, so re-ranking renumbers the whole column.

## Stop

To stop, run the notify script, then say what you need, and end your turn:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py --skill groom --kind <ASK or STOP> --text "<what's needed>"
```

## Review

Read the board with the board script, never with the Kaneo board tool. It prints one line per open task, in board order: key, status, title, labels, open blockers, and id.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/board.py
```

Then read each to-do and Planned task, and its comments, by id. Then find:
1. **Blocked chains:** each to-do task with an open blocker, as a chain written blocker first, such as `KEY-10 → KEY-11`. For information only.
2. **Manual tasks:** each open task with the `manual` label, with the count and keys of the open tasks it blocks, directly or through a chain, each counted once. Highest count first. For information only; none if no open task has the label.
3. **Blocked order:** a to-do task ranked above its own blocker. Propose an order with each blocker moved up to just above the first task that needs it.
4. **Stale tasks:** a to-do or Planned task, not `deferred`, created more than 30 days ago with no `kept` comment since. Choices: archive as `wont-do`, keep, or re-rank.
5. **Under-specified tasks:** run the draft validator once on every to-do and Planned task, then read each against `task-style.md`'s judgment rules. A `needs-refinement` comment is open unless a later comment starts with `refined`. Choices: refine it now, or leave it flagged. Pass the draft as JSON on one line in single quotes, each `'` in it written as `\u0027`:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/lib/validate_draft.py --json '<draft>'
   ```

6. **Ready tasks:** a Planned task that isn't under-specified, deferred, or an epic. Propose moving it to the end of To Do.
7. **Deferred tasks:** each `deferred` task. Choices: promote it to a full task in Planned, keep it, or archive it as `wont-do`.
8. **Finished epics:** an epic whose subtasks are all done or archived. Propose moving it to done.

## Propose and apply

Write one reply: the blocked chains, the manual tasks list, then every proposal in one numbered list with its choices, recommended first. Stop; the developer answers by number.

Then apply only the confirmed answers, and report each change:

- **Re-rank or move to To Do:** set the status first, then renumber the column's positions in the new order.
- **Archive as `wont-do`:** add the `wont-do` label and a comment with the reason, then set the status to `archived`.
- **Keep:** add a comment starting with `kept`.
- **Refine:** ask for what's missing, rewrite the description by `task-style.md`, and run the validator until it passes. Then add a comment starting with `refined`.
- **Leave flagged:** add a `needs-refinement` comment listing the problems, unless an open one exists.
