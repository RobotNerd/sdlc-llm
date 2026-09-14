---
name: plan-feature
description: Requirements-gathering skill — interview for the "why", write a SPEC-*.md (problem, alternatives, non-goals), decompose the feature into vertical slices with blocked_by/blocks between them, group slices under one or more epics linked to the spec, then fan out to add-task per slice.
---

# plan-feature

A numbered checklist, not prose. **STOP** means pause for the human before continuing; **ASK**
means don't guess. This is how work beyond the existing backlog enters the system.

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

Allocate the id: `python3 .tasks/bin/sync next-id spec`. Write `.tasks/specs/SPEC-<id>-<slug>.md`
from `.tasks/templates/spec.md` (drop the template's leading `<!-- ... -->` comment first), filling
Problem / Goals / Non-goals / Alternatives considered from step 1. Leave the `epics` region as its
template default (`_(none)_`) — that's `sync`'s job once epics link to it.

**STOP — show the human the full spec draft. Wait for approval before decomposing into tasks.**
Catching a wrong problem statement here is far cheaper than after tasks exist.

## 3. Decompose into vertical slices

A **vertical slice** is something independently shippable and testable on its own — a thin
end-to-end piece of the feature, not a horizontal layer. "Add the API endpoint, wire it to a
stub, and show it in the UI (even crudely)" is a slice; "do the backend" then "do the frontend"
are not — neither ships or proves anything alone.

For each slice: a short description, enough for a testing strategy (this feeds `add-task`'s own
interview in step 5, so front-loading it here saves re-asking). Capture `blocked_by`/`blocks`
between slices as you go — most decompositions have at least one real ordering constraint;
don't force one where there isn't any.

## 4. Group into epic(s)

Decide whether every slice fits one epic or needs splitting into more than one (e.g. genuinely
separable bodies of work sharing one spec). For each epic: allocate the id
(`python3 .tasks/bin/sync next-id epic`), write it from `.tasks/templates/epic.md` (drop the
leading comment) with `spec:` set to this spec's id, filling Goal / In scope / Out of scope /
Success criteria.

## 5. Restate and confirm

Show the human the full decomposition: the epic(s), every slice (with its proposed
`blocked_by`/`blocks`), and the resulting dependency graph. Eyeball it for cycles — with a
handful of slices this is a quick manual check, not a reason to build tooling for it.

**STOP — wait for approval before creating any task files.**

## 6. Fan out to `add-task`

For each slice, in dependency order (a slice's blockers before the slice itself), invoke
`add-task` with the slice's description/acceptance-criteria material from step 3 and its epic
already named (e.g. "... attach to EPIC-<id> ...") — `add-task`'s own epic-prompt step then
degrades to a quick confirmation instead of a blind menu, since the epic is already given. Carry
the `blocked_by` ids decided in step 3 into each slice's `blocked_by` answer.

## 7. Finish

Run `python3 .tasks/bin/sync` and confirm `python3 .tasks/bin/sync check` exits `0`. Confirm the
new epic(s) appear in `.tasks/BOARD.md`'s `epics` panel and each has its `children` region
populated with the slices just created.
