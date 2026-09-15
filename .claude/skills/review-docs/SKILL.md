---
name: review-docs
description: A periodic pass over the project's docs — flag staleness, redundancy, and dangling cross-references (guidelines.md mirror drift, broken path references, skill-list mismatches), propose fixes, and wait for confirmation before editing anything.
---

# review-docs

A numbered checklist, not prose. **STOP** means pause for the human before continuing; **ASK**
means don't guess. This is a periodic, human-invoked pass — not run automatically — over the docs
named in `.tasks/config.md`'s `docs_review_paths`. Same shape as `refine-backlog`: propose, don't
act unilaterally.

Every mechanical check — diffing `.tasks/guidelines.md` against its portable-template mirror,
finding dangling path references, and cross-checking a doc's claimed skill list against
`.claude/skills/` — lives in `scaffold.py` next to this `SKILL.md`. This skill's own prose covers
only the judgment: is a flagged difference actually a problem, and what to do about it.

## 1. Run the report

Run `python3 .claude/skills/review-docs/scaffold.py report` (no input file — it reads
`docs_review_paths`/`docs_ignore_paths` from `.tasks/config.md` itself). Returns:

```json
{"dangling_references": {...}, "skill_list_mismatches": {...}, "guidelines_mirror_diff": [...] | null}
```

These checks are best-effort (see the script's own docstrings) — a flagged item may turn out to be
a false positive once you look at it; that judgment happens in the steps below, not in the script.

## 2. Guidelines mirror drift

If `guidelines_mirror_diff` is non-null, read it. `.tasks/guidelines.md` and
`.claude/skills/init-project/templates/guidelines.md` are meant to mirror each other except for
this project's own extra specificity (e.g. spec section pointers, an explicit skill path) that
doesn't belong in the portable template. For each changed hunk: is it one of those expected
differences, or genuine drift (an edit that landed in one file but not the other)? Propose fixing
genuine drift (make them consistent again) and **STOP** for confirmation before editing either
file.

## 3. Dangling references

For each doc with entries under `dangling_references`: read the actual sentence each reference
appears in. A flagged reference is either genuinely dangling (the file was moved, renamed, or
deleted and this doc wasn't updated) or a false positive from the check's own heuristic (rare, but
possible — note it if so, no action needed). For each genuine one, propose a fix: update the
reference, or remove the sentence if what it described no longer exists. **ASK** the human if you
can't tell which without more context (e.g., a design-rationale claim you can't verify by reading
the repo). **STOP** for confirmation before editing.

## 4. Skill-list mismatches

For each doc with an entry under `skill_list_mismatches`: `missing` names a real skill the doc
doesn't mention (add it); `extra` names something the doc claims that isn't a real skill directory
anymore (remove or fix it). Propose the specific edit and **STOP** for confirmation.

## 5. Read each reviewed doc for staleness and redundancy

Beyond what the mechanical checks catch, read every doc in `docs_review_paths` for content that's
gone stale (describes a state of the project that's no longer true — "the skills don't exist yet",
a task count, a "still to be built" note) or redundant (restates something `sync`'s own mechanical
behavior already enforces, or repeats what another doc in the list already says better). For each
finding: propose a specific fix — a trim, a relocation, or a rewrite — and where the right answer
depends on something you can't resolve by reading the repo, **ASK** rather than guess. **STOP**
for confirmation before editing.

## 6. Apply confirmed edits and re-verify

Make only the edits the human confirmed. Then re-run `report` — confirm every issue you fixed no
longer appears — and `python3 .tasks/bin/sync check` (docs aren't generated regions, but this
catches any incidental drift from editing adjacent files).

## 7. Summary

Report what changed and what's still open (anything flagged but left for later, anything the
human said to leave as-is). Nothing here needs a final STOP beyond what steps 2–5 already
required — this step just closes the loop.
