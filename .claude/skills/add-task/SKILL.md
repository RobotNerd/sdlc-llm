---
name: add-task
description: Turn a rough description into a well-formed .tasks/TASK-*.md — interview for concrete acceptance criteria and a testing strategy, prompt for epic assignment, size-check against one-PR, ask for TODO rank, then hand off to scaffold.py to allocate the ID, write the file, place it, and run sync.
---

# add-task

A numbered checklist, not prose. **STOP** means pause for the human before continuing; **ASK**
means don't guess — ask a follow-up instead. Requires `.tasks/` to already exist (run
`init-project` first if it doesn't) and `.tasks/bin/sync` to be runnable.

Everything mechanical — listing open epics, writing the task file's frontmatter, placing it on the
TODO list at the requested rank, running `sync`/`sync check` — lives in `scaffold.py` next to this
`SKILL.md` (TASK-022), not in this prose. This skill's own job is the interview and the STOPs; the
script writes only what's already been confirmed.

## 0. Parameters

A caller (a human, or a future skill fanning out per-slice, e.g. `plan-feature`) may pre-supply any
of these. A supplied parameter skips its corresponding interview step below instead of asking
anyway; anything omitted still gets the normal interview.

| Parameter | Required? | Default if omitted | Skips |
|---|---|---|---|
| `description` | required (no default — always interview if missing) | — | Step 1's interview |
| `type` | required (no default) | — | Step 1's type question |
| `epic` | optional | interview (step 3) | Step 3 |
| `blocked_by` | optional | `[]` | Step 4 |
| `priority_mode` | optional | interview (step 5) | Step 5 |
| `priority_after` | required alongside `priority_mode: "after"`; otherwise unused | — | (part of step 5) |

`priority_mode` is `"top"`, `"end"`, or `"after"` (with `priority_after` naming the task to follow)
— see step 5. These are exactly the keys `scaffold.py run` expects (step 6), so a fully-supplied
call passes straight through with no translation. A supplied `epic` still gets validated (must
exist) by `scaffold.py`, same as one chosen interactively.

## 1. Interview — don't transcribe

Take whatever description started this (a one-liner, a paste, a half-formed idea). Check: does it
already yield **concrete acceptance criteria** (things you could put a `- [ ]` in front of) and a
**testing strategy** (concrete steps to verify it, not just "test it")?

- If yes, continue.
- If no — **ASK** targeted follow-ups (what does "done" look like? how would you check it works?
  what's explicitly out of scope?) until it does. Repeat as many rounds as needed.
- **Do not create any file — not even a draft — until both exist.** A vague one-liner with no
  answers yet should end this run with nothing written, not a placeholder task.

Also settle `type` (`feature` | `bug` | `chore` | `refactor` | `docs`) — ask if it isn't obvious
from the description.

## 2. Size check

Read the acceptance criteria and testing strategy back and judge: does this fit one branch, one
PR, one sitting? Signs it doesn't: the criteria describe multiple independently-shippable pieces,
the change spans unrelated systems/files, or the testing strategy needs several separate setups.

- If it's oversized: propose a concrete split (name the resulting tasks, or propose promoting this
  to an epic with its own tasks) and **STOP** — ask the human which to do. Don't write the
  oversized task file.
- If it fits, continue.

## 3. Epic prompt

Skip this step if `epic` was pre-supplied (see step 0). Otherwise run
`python3 .claude/skills/add-task/scaffold.py list-open-epics` — a JSON array of
`{"id": ..., "title": ...}` for every epic whose `status` is not `done` or `wont-do` (the same
"open" definition `sync`'s board panel uses).

**ASK** the human to choose one of:

1. **Attach to an existing open epic** — show the list (`EPIC-NNN — title`), take their pick.
2. **Create a new epic now** — run a short interview (title, goal, in-scope, out-of-scope, at
   least one success criterion), allocate its ID with `sync next-id epic`, and write it from
   `.tasks/templates/epic.md` (drop the template's leading `<!-- ... -->` comment first). Use the
   new epic's ID for this task's `epic:` field. (Creating a *new* epic is judgement-driven — the
   script only handles listing *existing* ones.)
3. **Leave unassigned** — `epic: null`.

**STOP** after this choice is made, before writing the task file.

## 4. blocked_by (optional)

Skip this step if `blocked_by` was pre-supplied. Otherwise **ASK** whether this task depends on
any existing, not-yet-`done`/`wont-do` task. If so, record those ids in `blocked_by`. Leave `[]`
if none. Don't touch any other task's `blocks` field by hand — `sync` reconciles `blocks` from
every task's `blocked_by` automatically on the next run.

## 5. Priority placement

Skip this step if `priority_mode` was pre-supplied. Otherwise **ASK** where this task ranks in
`.tasks/BOARD.md`'s TODO list — top, bottom (end), or relative to a named existing task (after) —
rather than defaulting to "append it." Record the answer as `priority_mode` (`"top"` | `"end"` |
`"after"`) plus `priority_after` (the task id) when the mode is `"after"`.

## 6. Write and place

Once every answer above is settled, write them to a scratch JSON file (your scratchpad directory,
or any temp path) with these keys:

| Key | Value |
|---|---|
| `title` | the task's title |
| `type` | `feature` \| `bug` \| `chore` \| `refactor` \| `docs` |
| `epic` | `EPIC-NNN` or `null` |
| `blocked_by` | list of task ids, `[]` if none |
| `priority_mode` | `"top"` \| `"end"` \| `"after"` |
| `priority_after` | task id (only when `priority_mode` is `"after"`) |
| `slug` | optional — omit to derive one from the title |

Then run:

```
python3 .claude/skills/add-task/scaffold.py run <path-to-answers.json>
```

This allocates the id, writes `.tasks/TASK-<id>-<slug>.md` from the template (frontmatter and both
`id`/`title` occurrences filled — the body's Description/Acceptance criteria/Testing
strategy/Notes sections are left as `{{placeholder}}`s), runs `sync`, places the new TODO line at
the requested rank, and runs `sync check` — exiting non-zero with a clear message if anything was
invalid (unknown `epic`/`blocked_by` id, bad `type`/`priority_mode`, a missing required key) or if
`sync`/`sync check` didn't come back clean.

If it exits non-zero for a reason other than bad input: **STOP**, show the human the error — that's
a bug in this script or in `sync`, not something to paper over by hand-editing a generated region.

If it exits `0`: fill in the new task file's body (Description, Acceptance criteria, Testing
strategy, Notes) from what the interview in steps 1–2 produced — this is the one part of "write
and place" that still needs the LLM, since the script deliberately leaves those sections as
placeholders. Show the human the finished task file and its `BOARD.md` line.
