---
name: refine-backlog
description: Reviews the project's Kaneo backlog and proposes fixes. Use when the developer asks to refine, groom, tidy, triage, or review the backlog, to find blocked, stale, or under-specified tasks, or to check what's ready to work on.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py *), Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/validate_draft.py *), Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/active_days.py *)
---

# refine-backlog

Reviews the backlog, proposes changes, and makes only the ones the developer confirms.

## Parameters

None.

## Asking and stopping

- **ASK** means: run the notify script with `--kind ASK`, then ask with `AskUserQuestion`, with the recommended answer first. If `AskUserQuestion` isn't available, ask in your reply and end your turn. Never guess an answer.
- **STOP** means: run the notify script with `--kind STOP`, then say what's needed, and end your turn.
- **Notify script,** run with every ASK and STOP, even when notifications look off in the config: the script checks that itself. If it fails or can't run, carry on.

  ```bash
  python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py --skill refine-backlog --kind <ASK or STOP> --text "<what's needed>"
  ```

Never change a task without a confirmed answer. A proposal the developer doesn't answer, or declines, changes nothing.

## Steps

Read the [Kaneo backend map](../../lib/references/backends/kaneo.md) before the first tracker call. Every tracker operation below is done the way it says. Values in angle brackets come from `.sdlc/config.toml`. A task's key is `<kaneo.project_slug>-<number>`.

Copy this checklist into your reply, and tick each step off as you finish it:

```
- [ ] 1. Check the repo
- [ ] 2. Read the board
- [ ] 3. Blocked chains
- [ ] 4. Blocked order
- [ ] 5. Stale tasks
- [ ] 6. Under-specified tasks
- [ ] 7. Ready check
- [ ] 8. Propose
- [ ] 9. Apply
```

### 1. Check the repo (low)

1. Read `.sdlc/config.toml` at the repo root. If it's missing, **STOP**: the repo needs `/sdlc-llm:setup-project` first.
2. Tracker: `list_column` for to-do. This also checks that Kaneo answers. If the call fails, **STOP**, and tell the developer to run `/mcp` to see why.

### 2. Read the board (low)

1. Tracker: `list_column` for in-progress, needs-human, and `planned`. With the to-do column from step 1, these are the open tasks. Note each task's key, labels, position, and `createdAt`.
2. For each task in to-do and Planned: Tracker: `list_relations`, keeping the `blocks` relations, and Tracker: `list_comments`.

A blocker is **outstanding** when it's an open task. Leave tasks with the `epic` label out of every step below, except as a blocker.

### 3. Blocked chains (medium)

List each to-do task with an outstanding blocker. Follow each blocker's own outstanding blockers, and write the whole chain blocker first, such as `EX-10 → EX-11 → EX-12`.

### 4. Blocked order (medium)

Find each to-do task ranked above one of its outstanding blockers, directly or through a chain, that's also in to-do. When there's any, write a proposed to-do order: the current order, with each blocker moved up to just above the first task that needs it. Every other task keeps its place relative to the rest.

### 5. Stale tasks (low)

1. For each task in to-do and Planned, except `deferred` ones, take its start: `createdAt`, or the `createdAt` of its latest comment starting with `kept`, whichever is later.
2. Run the active-days script once, with every start:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/lib/active_days.py <start> <start> ...
   ```

   Run it exactly as shown, as one command. It prints one JSON object mapping each start to its count of days with commits to the default branch, such as `{"2026-09-01T10:00:00.000Z": 23}`.
3. A task whose count is over `stale_active_days` (20 when it isn't set) is stale. Its choices are: archive it as `wont-do`, keep it, or re-rank it.

### 6. Under-specified tasks (high)

Read the Task style guide now, from Outline with `mcp__plugin_sdlc-llm_outline__fetch` (`resource` `document`, `id` `guidelines.task_style`). When the id is empty, read the plugin's [default copy](../../lib/references/guidelines/task-style-guide.md).

1. Run the draft validator once, on every task in to-do and Planned. Each task is an entry with its key as `id`, its title, its type label as `type`, its description, and `blocked_by` empty. A `deferred` task goes under `deferred` instead, without `type` or `blocked_by`. Pass the draft as JSON on one line inside single quotes, writing each `'` as `'`:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/lib/validate_draft.py --json '<draft>'
   ```

   Run it exactly as shown, as one command. It prints `{"ok": true}`, or one error per line, as `<key>: <rule>: <detail>`.
2. Read each task against the guide's judgment rules too: whether each criterion is objective, each test names its criteria, and each manual test has a **Why manual:** line and full steps.
3. A task's `needs-refinement` comment is open unless a later comment starts with `refined`.
4. A task with a validator error, a judgment problem, or an open `needs-refinement` comment is under-specified. Its choices are: re-interview it now, or leave it flagged.

### 7. Ready check (medium)

Each Planned task that isn't under-specified is ready, unless it has the `deferred` label. That includes `follow-up` tasks. Propose moving each ready task to the end of to-do.

### 8. Propose (low)

Write one reply with:

1. **Blocked chains,** from step 3, for information.
2. **Numbered proposals,** each with its choices and the recommended one first:
   - the proposed to-do order, from step 4
   - each stale task, with its active days
   - each under-specified task, with its problems
   - each ready task
3. **The to-do order,** as it would be after the proposals, and whether to change it.

When the developer's request already declines every change, end there, and change nothing. Otherwise **STOP**: the developer answers each proposal by number.

### 9. Apply (medium)

Apply only the confirmed answers, then report every change made.

- **New order, re-rank, or priority change:** Tracker: `place_task` for each task that moves, in the confirmed order.
- **Archive as `wont-do`:** Tracker: `add_label` `wont-do`, then Tracker: `add_comment` with the reason, then Tracker: `archive_task`.
- **Keep a stale task:** Tracker: `add_comment` `kept after a stale review`, so its active days count again from now.
- **Re-interview:** **ASK** for what's missing, a few questions at a time. Tracker: `update_description` with the answers, by the Task style guide. Run the draft validator on the task again, and fix it until it passes. Then Tracker: `add_comment` starting with `refined`, saying what changed.
- **Leave flagged:** when the task has no open `needs-refinement` comment, Tracker: `add_comment` listing its problems:

  ```markdown
  needs-refinement

  - <problem>
  ```

- **Ready task to to-do:** Tracker: `set_status` `to-do`, then Tracker: `place_task` at `end`.
