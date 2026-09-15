---
name: plan-feature
description: Requirements-gathering skill — interview for the "why", write a SPEC-*.md (problem, alternatives, non-goals), decompose the feature into vertical slices with blocked_by/blocks between them, group slices under one or more epics linked to the spec, then fan out to add-task per slice.
---

# plan-feature

A numbered checklist, not prose. **STOP** means pause for the human before continuing; **ASK**
means don't guess. This is how work beyond the existing backlog enters the system.

Every deterministic step — allocating spec/epic ids, writing `SPEC-*.md`/`EPIC-*.md` from their
templates, the cycle check over a proposed slice graph, and the closing `sync`/`sync check` +
board confirmation — lives in `scaffold.py` next to this `SKILL.md` (TASK-026). This skill's own
prose covers only the interview, the vertical-slice decomposition judgment, and both STOP
checkpoints.

## 1. Interview for the "why"

Take whatever description started this. **ASK** until you have real answers, not placeholders,
for:

- **Problem** — what's actually wrong or missing, and for whom.
- **Goals** — what this feature needs to achieve.
- **Non-goals** — what's explicitly out of scope (as important as the goals; stops scope creep
  later).
- **Alternatives considered** — at least one other approach and why it wasn't chosen (even "do
  nothing" counts, if that's genuinely a live option).

Don't draft the spec file until all four have concrete content — same discipline as `add-task`'s
own interview.

## 2. Draft the spec

Run `python3 .claude/skills/plan-feature/scaffold.py write-spec <answers.json>` with
`{"title", "created" (today, YYYY-MM-DD), "problem", "goals": [...], "non_goals": [...],
"alternatives": [...], "slug"}` (`slug` optional — omit to derive one from the title). It
allocates the spec id, writes `.tasks/specs/SPEC-<id>-<slug>.md` from the template, and leaves the
`epics` region at its template default (`_(none)_`) — that's `sync`'s job once epics link to it.
Returns `{"spec_id", "path"}`.

**STOP — show the human the full spec draft. Wait for approval before decomposing into tasks.**
Catching a wrong problem statement here is far cheaper than after tasks exist.

## 3. Decompose into vertical slices

A **vertical slice** is something independently shippable and testable on its own — a thin
end-to-end piece of the feature, not a horizontal layer. "Add the API endpoint, wire it to a
stub, and show it in the UI (even crudely)" is a slice; "do the backend" then "do the frontend"
are not — neither ships or proves anything alone.

For each slice: a short description, enough for a testing strategy (this feeds `add-task`'s own
interview in step 6, so front-loading it here saves re-asking). Capture `blocked_by`/`blocks`
between slices as you go — most decompositions have at least one real ordering constraint;
don't force one where there isn't any.

## 4. Group into epic(s)

Decide whether every slice fits one epic or needs splitting into more than one (e.g. genuinely
separable bodies of work sharing one spec) — this is judgment, not scripted.

Once decided, run `python3 .claude/skills/plan-feature/scaffold.py write-epics <answers.json>`
with `{"spec_id": "SPEC-NNN" or null, "epics": [{"title", "created", "goal", "in_scope": [...],
"out_of_scope": [...], "success_criteria": [...], "slug"}, ...]}` — one entry per epic. It
allocates each epic's id (sequentially, so a batch of epics in one call never collides) and writes
each `.tasks/EPIC-<id>-<slug>.md` from the template with `spec:` set. Returns
`{"epics": [{"epic_id", "path"}, ...]}`.

## 5. Restate and confirm

Show the human the full decomposition: the epic(s), every slice (with its proposed
`blocked_by`/`blocks`), and the resulting dependency graph. Run
`python3 .claude/skills/plan-feature/scaffold.py check-cycles <answers.json>` with
`{"slices": [{"name": "<a temporary slice name — these aren't real task ids yet>",
"blocked_by": ["<other slice names>", ...]}, ...]}` — replaces the old "eyeball it" placeholder
with a real check. It returns `{"cycle": null}` if the graph is acyclic, or
`{"cycle": ["A", "B", "C", "A"]}` naming the exact loop if not — if a cycle comes back, that's a
real decomposition mistake: fix the dependencies (with the human) before continuing, don't just
proceed anyway.

**STOP — wait for approval before creating any task files.**

## 6. Fan out to `add-task`

For each slice, in dependency order (a slice's blockers before the slice itself), invoke
`add-task` with the slice's description/acceptance-criteria material from step 3 and its epic
already named (e.g. "... attach to EPIC-<id> ..."; `add-task`'s own `epic` parameter, TASK-022,
means this skips straight past its epic-prompt interview step instead of showing a blind menu).
Carry the `blocked_by` ids decided in step 3 into each slice's `blocked_by` answer.

## 7. Finish

Run `python3 .claude/skills/plan-feature/scaffold.py finish <answers.json>` with
`{"epic_ids": ["EPIC-NNN", ...]}` (every epic created in step 4). It runs `sync` then confirms
`sync check` exits `0`, then reports, per epic, whether it appears in `.tasks/BOARD.md`'s `epics`
panel and whether its `children` region is populated (i.e. the slices just created actually landed
under it) — `{"epics": [{"epic_id", "in_epics_panel", "children_populated"}, ...]}`. Show the
human this confirmation; if either flag comes back `false` for an epic that should have children,
that's a bug to investigate, not something to paper over.
