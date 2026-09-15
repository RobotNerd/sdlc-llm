---
name: refine-backlog
description: A short periodic backlog pass — recompute blocked/epic status via sync, surface stale todo tasks as wont-do candidates, flag under-specified tasks for re-refinement, confirm or reorder TODO priority. Proposes changes and waits for the human; never acts unilaterally on priority.
---

# refine-backlog

A numbered checklist, not prose. **STOP** means pause for the human before continuing. This is a
short periodic pass, not a ceremony — report, propose, wait. It never changes anything on its own
judgement; every change here is the human's call.

Every mechanical computation — the resync, the blocked-chain report, the stale-`todo` scan (an
**active-days-elapsed** measure, not raw wall-clock age — see step 3), the under-specified scan,
and applying a confirmed TODO reorder — lives in `scaffold.py` next to this `SKILL.md` (TASK-025).
This skill's own prose covers only the human-facing proposals and decisions.

## 1. Resync first

Run `python3 .claude/skills/refine-backlog/scaffold.py resync` — runs `sync` then confirms
`sync check` exits `0`. Every report below reads off freshly-recomputed `blocked`/`blocks`/epic
status, not stale data.

## 2. Run the report

Run `python3 .claude/skills/refine-backlog/scaffold.py report` — one call, three findings:

```json
{"blocked_chain": [...], "stale_todo": [...], "underspecified": [...]}
```

## 3. Blocked-chain report

`blocked_chain` lists every TODO task currently carrying a `⛔ blocked_by ...` marker (these are
`sync`-derived — only *currently outstanding* blockers show, per `guidelines.md`), each with its
blockers' own current status. Narrate the chain to the human (e.g. "TASK-B is blocked by TASK-A,
which is itself in-progress"; if a listed blocker itself appears elsewhere in `blocked_chain`,
call out that transitive link). Purely informational — nothing to confirm here.

## 4. Stale-`todo` scan

`stale_todo` lists every `todo` task where **active-days-elapsed** exceeds the threshold (a
constant in `scaffold.py`, default 30 — not a `config.md` value, since no other skill reads it):
distinct calendar days with at least one commit to `default_branch` between the task's `created`
date and now. This is deliberately not a raw `today - created > 30 days` check — a project dropped
and resumed later shouldn't have every pre-existing `todo` task flagged the instant it's picked
back up; active-days-elapsed contributes ~0 across a dormant gap, so only a task genuinely bypassed
through real ongoing work gets flagged.

For each one: **STOP** and ask the human, one at a time or as a batch, whether to mark it
`wont-do` (compose why and add it to the task's Notes yourself first — content-authoring stays
here), leave it as-is, or reconsider its priority instead. Never mark `wont-do` without being
told to. For each confirmed `wont-do`: run
`python3 .claude/skills/refine-backlog/scaffold.py mark-wont-do <answers.json>` with
`{"task_id": "TASK-NNN"}` — it sets the status and runs `sync` (archiving it if `archive_done`).

## 5. Under-specified scan

`underspecified` lists every `todo`/`blocked` task whose Acceptance criteria or Testing strategy
section is empty, a single vague line, or still carries an unfilled template placeholder (e.g. a
lone `{{criterion}}`/`{{step}}` — a criterion that merely *mentions* `{{...}}` syntax in passing
doesn't count, only one that *is* nothing but the placeholder). For each one found: **STOP**,
propose running an `add-task`-style re-interview on it (don't perform the interview here — this
skill flags, `add-task`'s own checklist does the actual re-specification), and ask whether to do
that now or leave it flagged for later.

## 6. Priority placement

Show the current TODO order as it stands in `.tasks/BOARD.md`. **ASK** the human whether anything
should be reprioritized — don't propose changes unprompted; this step exists so priority doesn't
silently drift, not to second-guess it.

If they want changes: work out the complete new ordering (every current `todo` task id, in the
new order) and run
`python3 .claude/skills/refine-backlog/scaffold.py reorder <answers.json>` with
`{"new_order": ["TASK-NNN", ...]}`. It refuses (nothing changed) if the given ids aren't exactly a
permutation of the current `todo` set, and otherwise rewrites `BOARD.md`'s TODO section and
confirms `sync check` stays clean.

## 7. Summary

Report what changed (any `wont-do`s, any re-interview flags acted on, any reordering) and what's
still open (re-interviews not yet done, reorder requests not made). Nothing here needs a final
STOP beyond what steps 4–6 already required — this step is just closing the loop.
