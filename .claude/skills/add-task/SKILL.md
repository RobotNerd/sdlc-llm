---
name: add-task
description: Turn a rough description into a well-formed .tasks/TASK-*.md — interview for concrete acceptance criteria and a testing strategy, prompt for epic assignment, size-check against one-PR, ask for TODO rank, allocate the ID via sync next-id, then run sync.
---

# add-task

A numbered checklist, not prose. **STOP** means pause for the human before continuing; **ASK**
means don't guess — ask a follow-up instead. Requires `.tasks/` to already exist (run
`init-project` first if it doesn't) and `.tasks/bin/sync` to be runnable.

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

Read every `.tasks/EPIC-*.md` (and `.tasks/archive/EPIC-*.md`). List the ones whose `status` is
not `done` or `wont-do` (the same "open" definition `sync`'s board panel uses) as candidates.

**ASK** the human to choose one of:

1. **Attach to an existing open epic** — show the list (`EPIC-NNN — title`), take their pick.
2. **Create a new epic now** — run a short interview (title, goal, in-scope, out-of-scope, at
   least one success criterion), allocate its ID with `sync next-id epic`, and write it from
   `.tasks/templates/epic.md` (drop the template's leading `<!-- ... -->` comment first). Use the
   new epic's ID for this task's `epic:` field.
3. **Leave unassigned** — `epic: null`.

**STOP** after this choice is made, before writing the task file.

## 4. blocked_by (optional)

**ASK** whether this task depends on any existing, not-yet-`done`/`wont-do` task. If so, record
those ids in `blocked_by`. Leave `[]` if none. Don't touch any other task's `blocks` field by
hand — `sync` reconciles `blocks` from every task's `blocked_by` automatically on the next run.

## 5. Priority placement

**ASK** where this task ranks in `.tasks/BOARD.md`'s TODO list — top, bottom, or relative to a
named existing task — rather than defaulting to "append it." `sync next-id task` only allocates
the id; it never touches TODO order, and bare `sync` only ever *appends* a newly-`todo` task at
the end (TODO order is hand-maintained, by design — see `guidelines.md`).

## 6. Write and place

1. Allocate the id: `python3 .tasks/bin/sync next-id task`.
2. Write `.tasks/TASK-<id>-<slug>.md` from `.tasks/templates/task.md`, filling every
   `{{placeholder}}` (including `branch: <branch_prefix><id>-<slug>` from `.tasks/config.md`) —
   drop the template's leading `<!-- ... -->` comment first. `status: todo`, `pr: null`,
   `merge_commit: null`, `blocks: []` — don't fill these in, the template already fixes them.
   **The title appears twice** — once quoted in frontmatter (`title: "{{title}}"`) and again
   unquoted in the `# {{id}}: {{title}}` heading right after it — fill in both; a plain
   find-and-replace on `{{title}}` catches both occurrences in one pass.
3. Run `python3 .tasks/bin/sync` (bare). This appends the new task's TODO line, correctly
   rendered, at the *end* of the list, and (if it was assigned to an epic) regenerates that
   epic's `children` region.
4. If the requested rank (step 5) wasn't "at the end": in `.tasks/BOARD.md`, cut that exact
   rendered TODO line from the end of the list and paste it back in at the requested position —
   move the literal line `sync` just rendered, don't hand-compose a new one. TODO order is the one
   thing `sync` never touches, so this is a plain, safe hand-edit.
5. Run `python3 .tasks/bin/sync check` and confirm it exits `0`. Show the human the new task file
   and its `BOARD.md` line.
