---
name: strip-project-references
description: Repo-only periodic pass — scan .claude/skills/** for project-specific references (TASK-/EPIC-/SPEC- ids, CLAUDE.md, .tmp/workflow-plan.md, "this repo's own …") that leak into the portable skills surface, auto-fix the mechanically-safe ones, propose fixes for the rest, and wait for confirmation before editing. Excluded from every project this toolkit is vendored into — see step 0.
---

# strip-project-references

A numbered checklist, not prose. **STOP** means pause for the human before continuing. This is a
short periodic pass, not a ceremony — scan, auto-fix what's safe, propose the rest, wait.

Every mechanical piece — the scan itself, classifying an offender as safe-to-auto-fix or
needing judgment, and applying the safe fixes — lives in `scaffold.py` next to this `SKILL.md`.
This skill's own prose covers only the judgment: what's the right rewrite for something that
can't be fixed by pattern substitution alone.

## 0. Repo-only — do not vendor

This skill only makes sense in the repo that authors the portable skills surface — it exists to
keep that surface (`.claude/skills/**`) free of references that would confuse an agent working in
a *different* project once this toolkit is vendored there. It is deliberately excluded from
whatever copies skills into other projects (once that mechanism exists — nothing does yet); its
own `scaffold.py` excludes its own directory from the very scan it runs, for the same reason.
Nothing to do here — this step is just the reminder.

## 1. Run the scan

Run `python3 .claude/skills/strip-project-references/scaffold.py scan` — no input file. Returns:

```json
{"mechanical": [...], "judgment": [...]}
```

Every entry is `{"path", "line", "kind", ...}`, `path` relative to `.claude/skills/`. `mechanical`
entries are safe to fix by pattern substitution (step 2); `judgment` entries need a
human/LLM-authored rewrite (step 3). If both are empty, skip to step 5 — nothing to do.

## 2. Auto-fix the mechanical bucket

If `mechanical` is non-empty, run
`python3 .claude/skills/strip-project-references/scaffold.py apply-mechanical` — writes the fixes
in place, returns `{"changed": [{"path", "count"}, ...]}`. These are exactly two narrow,
deterministic transforms (see the script's own docstring for the precise rule): stripping a
parenthetical whose entire content is one or more ids and nothing else (`(TASK-024)`), or
replacing a bare example id's digits with `NNN` (`` `TASK-016` `` → `` `TASK-NNN` ``). No
confirmation needed before this step — the script never touches a `§`-citation sentence or a
banned-phrase occurrence, only these two shapes.

## 3. Judgment bucket — propose, then STOP

For each `judgment` entry: read the file at that line and the surrounding sentence/paragraph, and
propose a specific rewrite that keeps the sentence's stated meaning without the citation or banned
phrase. Two recurring shapes:

- **`id_needs_rewrite`** (a `SPEC-NNN §"…"`-style citation, or any id sharing a paragraph with
  one) — delete the citation, keep the sentence; the rule it referenced almost always already sits
  in the surrounding prose on its own. Don't repoint it at another doc (e.g. `guidelines.md`) —
  that doc may not cover the cited section, which just dangles the pointer somewhere else.
- **`banned_phrase`** (`CLAUDE.md` outside `templates/config.md`'s `docs_review_paths` default and
  `review-docs/scaffold.py`'s `_ROOT_DOC_NAMES` constant, `.tmp/workflow-plan.md`, or
  `"this repo's own"`) — reword to generic phrasing (e.g. "this repo's own convention" → "the
  project's own convention") or drop the clause entirely if nothing generic is worth keeping.

Show the human every proposed rewrite as a diff. **STOP** for confirmation before editing
anything.

## 4. Apply confirmed edits and re-verify

Make only the edits the human confirmed. Then re-run `scan` — confirm both buckets are now empty
for everything you fixed. A real false positive is possible (a `§` or banned phrase that isn't
actually a citation/reference in context); note it in your summary rather than forcing a change.
Run `pytest` and `python3 .tasks/bin/sync check` — both must pass before calling this done.

## 5. Summary

Report what changed (mechanical fixes applied, judgment fixes applied) and anything left open
(a noted false positive, anything intentionally left as-is).
