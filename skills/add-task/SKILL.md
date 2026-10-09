---
name: add-task
description: Turns a rough request into a well-formed Kaneo task. Interviews the developer until the task has objective acceptance criteria and a testing strategy, checks for duplicates and size, then creates the task with its description template, type label, epic and blocker relations, and its place in the to-do column. Also files deferred work. Use when the developer asks to add, create, file, or log a task, bug, chore, or feature, to put something on the backlog, or to defer an idea for later.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py *)
---

# add-task

Creates one Kaneo task that someone who knows the codebase can do from its text alone.

## Parameters

Each parameter the developer gives skips its question in step 2.

| Parameter | Default | Skips |
|---|---|---|
| description | none | what the task changes, and why |
| type | none | the type label: `feature`, `bug`, `chore`, `refactor`, or `docs` |
| epic | none | the epic, as a task key such as `KEY-12` |
| `blocked_by` | none | the blocking tasks, as task keys |
| placement | `end` | `top`, `end`, or `after <key>` in to-do, or `planned` |
| `deferred` | off | files deferred work instead of a task to do |

## Asking and stopping

- **ASK** means: ask with `AskUserQuestion`, a few questions at a time, with the recommended answer first. If `AskUserQuestion` isn't available, ask in your reply and end your turn. Never guess an answer.
- **STOP** means: say what's needed, and end your turn.
- With each ASK and STOP, also run the notify script. If it fails or can't run, carry on.

  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py --skill add-task --kind ASK --text "<what's needed>"
  ```

## Steps

Read the [Kaneo backend map](../../lib/references/backends/kaneo.md) before the first tracker call. Every tracker operation below is done the way it says. Values in angle brackets come from `.sdlc/config.toml`.

Copy this checklist into your reply, and tick each step off as you finish it:

```
- [ ] 1. Check the repo
- [ ] 2. Interview
- [ ] 3. Check for duplicates
- [ ] 4. Check the size
- [ ] 5. Resolve the epic, blockers, and placement
- [ ] 6. Write the task
- [ ] 7. Create the task
- [ ] 8. Report
```

### 1. Check the repo (low)

1. Read `.sdlc/config.toml` at the repo root. If it's missing, **STOP**: the repo needs `/sdlc-llm:setup-project` first.
2. Tracker: `list_column` for to-do. This also checks that Kaneo answers. If the call fails, **STOP**, and tell the developer to run `/mcp` to see why.

### 2. Interview (high)

Collect what the task needs, and skip anything the request or the parameters already give.

- **A task to do:**
  - the outcome, in a few words, for the title
  - what changes, and why
  - acceptance criteria: each one observable and objective, so two people would agree whether it's met
  - a testing strategy: the automated tests, and a manual test only for what can't be automated
  - the type
- **Deferred work:** what's deferred, why, what would bring it back, and the source (a link to the spec or PRD, or "none").

Take the type from the request when it's clear, such as "fix" for `bug` or "README" for `docs`. Leave out the epic and blockers unless the developer names them. When the request leaves any of the items above open, or a criterion can't be checked, **ASK** for exactly what's missing. Don't create anything until every item is settled.

### 3. Check for duplicates (medium)

Tracker: `search_tasks` with the key words of the outcome. Ignore results that are done or archived.

If an open task covers the same outcome, **ASK**, naming its key and title: create the new task anyway, change the existing task instead, or cancel. On anything but "create anyway", end the skill there.

### 4. Check the size (high)

A task is one branch and one sitting. If the criteria describe separately shippable pieces, or the changes span unrelated areas, **ASK** whether to split it into several tasks, or to plan it as a feature with `/sdlc-llm:plan-feature`. Deferred work skips this step.

### 5. Resolve the epic, blockers, and placement (low)

1. Turn each task key (the epic, each blocker, and an `after <key>` anchor) into its task id, by `number`. Blockers and anchors are in the to-do column you read in step 1. The epic is in Planned: Tracker: `list_column` for `planned`. If a key isn't found, **ASK** for the right one.
2. Status: `planned` for deferred work and for the `planned` placement, otherwise `to-do`.

### 6. Write the task (high)

Read these guideline docs now, from Outline with `mcp__plugin_sdlc-llm_outline__fetch` (`resource` `document`, `id` from the config). When an id is empty, read the plugin's default copy instead.

| Doc | Config key | Default copy |
|---|---|---|
| Task style guide | `guidelines.task_style` | [task-style-guide.md](../../lib/references/guidelines/task-style-guide.md) |
| Testing strategy | `guidelines.testing` | [testing-strategy.md](../../lib/references/guidelines/testing-strategy.md) |
| Documentation style | `guidelines.doc_style` | [documentation-style.md](../../lib/references/guidelines/documentation-style.md) |

Write the title and the description by those rules:

- **A task to do:** every section of the template, in this order, with `None` in any that's empty:

  ```markdown
  ## Description
  ## Acceptance criteria
  - [ ] ...
  ## Testing strategy
  ### Automated
  ### Manual
  ## Notes
  ```

  Every criterion has at least one test. Write each manual test out in full: every command, agent prompt, and value to paste in its own code block or list, and the expected result of each step.
- **Deferred work:**

  ```markdown
  ## Deferred
  ## Why
  ## Brings it back
  ## Source
  ```

### 7. Create the task (low)

1. Tracker: `create_task` with the title, the description, and the status from step 5.
2. Tracker: `add_label` with the type. For deferred work, also `add_label` with `deferred`.
3. Tracker: `add_relation` `subtask` from the epic to the new task, when there's an epic.
4. Tracker: `add_relation` `blocks` from each blocker to the new task.
5. Tracker: `place_task` at the placement, when the status is `to-do`. The new task may not be in the column you read yet; add it to the list before you renumber.

### 8. Report (low)

Show the task's key, `<kaneo.project_slug>-<number>`, its title, and its link:

```
<kaneo.url>/dashboard/workspace/<kaneo.workspace_id>/project/<kaneo.project_id>/task/<task id>
```

Then say where it landed: its column and position, its epic, and its blockers.
