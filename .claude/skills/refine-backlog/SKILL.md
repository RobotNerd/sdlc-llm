---
name: refine-backlog
description: A short periodic backlog pass — recompute blocked/epic status via sync, surface stale todo tasks as wont-do candidates, flag under-specified tasks for re-refinement, confirm or reorder TODO priority. Proposes changes and waits for the human; never acts unilaterally on priority.
---

# refine-backlog

A numbered checklist, not prose. **STOP** means pause for the human before continuing. This is a
short periodic pass, not a ceremony — report, propose, wait. It never changes anything on its own
judgement; every change here is the human's call.

## 1. Resync first

Run `python3 .tasks/bin/sync` (bare). Every report below reads off freshly-recomputed
`blocked`/`blocks`/epic status, not stale data. Confirm `python3 .tasks/bin/sync check` exits `0`
before reporting anything.

## 2. Blocked-chain report

Read `.tasks/BOARD.md`'s TODO list for `⛔ blocked_by ...` markers (these are `sync`-derived —
only *currently outstanding* blockers show, per `guidelines.md`). Report the chain: which tasks
are blocked, by which still-open tasks, transitively if relevant (e.g. "TASK-B blocked by
TASK-A, which is itself in-progress"). Purely informational — nothing to confirm here, just
visibility into what's actually workable right now.

## 3. Stale-`todo` scan

Scan every task with `status: todo` for a `created` date more than **30 days** old (adjust this
threshold in this file if the project wants a different one — it isn't a `config.md` value, since
no other skill reads it).

For each stale task found: **STOP** and ask the human, one at a time or as a batch, whether to
mark it `wont-do` (record why in its Notes), leave it as-is, or reconsider its priority instead.
Never set `wont-do` without being told to — a human decision, per SPEC-001's epic-status rules.
Apply any `wont-do` decisions, then re-run `sync` (archives it if `archive_done`).

## 4. Under-specified scan

Flag any `todo`/`blocked` task whose **Acceptance criteria** or **Testing strategy** section is
empty, a single vague line, or still carries template placeholder text (e.g. `{{criterion}}`,
`{{step}}`, or a lone `- [ ]` with nothing concrete after it). For each one found: **STOP**,
propose running an `add-task`-style re-interview on it (don't perform the interview here — this
skill flags, `add-task`'s own checklist does the actual re-specification), and ask whether to do
that now or leave it flagged for later.

## 5. Priority placement

Show the current TODO order as it stands in `.tasks/BOARD.md`. **ASK** the human whether anything
should be reprioritized — don't propose changes unprompted; this step exists so priority doesn't
silently drift, not to second-guess it.

If they want changes: hand-edit the TODO list's line order in `.tasks/BOARD.md` directly (this is
the one thing `sync` never touches — see `guidelines.md`). Move existing rendered lines rather
than retyping them. Then run `python3 .tasks/bin/sync check` and confirm it still exits `0` —
reordering must never show up as drift.

## 6. Summary

Report what changed (any `wont-do`s, any re-interview flags acted on, any reordering) and what's
still open (re-interviews not yet done, reorder requests not made). Nothing here needs a final
STOP beyond what steps 3–5 already required — this step is just closing the loop.
