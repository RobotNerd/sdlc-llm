---
id: TASK-052
title: Re-scope guidelines.md to the non-outsourceable core and add a skill-selection map
type: docs
status: todo
epic: EPIC-002
created: 2026-09-16
branch: task-052-re-scope-guidelines-md-to-the-non-outsourceable-core-and-add-a-skill-selection-map
pr: null
merge_commit: null
blocked_by: []
blocks: [TASK-037]
---

# TASK-052: Re-scope guidelines.md to the non-outsourceable core and add a skill-selection map

## Description

An audit of `.tasks/guidelines.md` (91 lines) against EPIC-002's seven hook tasks (TASK-032–038)
found it mostly redundant, and — in a scaffolded project — never actually loaded by anything.

The file's content breaks into three buckets:

1. **Already redundant today.** §"Working a task — four phases" plus Resumability and Bail-out
   (~33 lines) duplicates `implement-task/SKILL.md`'s own §0–4 almost verbatim. This has already
   drifted once: TASK-050 existed because `implement-task` disagreed with this file about
   auto-picking the top of TODO.
2. **Becomes structurally enforced once EPIC-002 ships.** Five of its seven Guardrails bullets are
   each covered by a specific hook: never push task work to `default_branch` (TASK-032 guardrail
   #2), never `gh pr merge` (TASK-032 #1), `--force-with-lease` only on the task's own branch
   (TASK-032 #3), never hand-edit a `BEGIN:`/`END:` region (TASK-033 check #1), never hand-edit an
   epic's `status` except `wont-do` (TASK-033 check #2).
3. **Cannot be outsourced to a hook or a skill.** The artifact model (spec/epic/task), terminology,
   what `sync` owns vs. what's hand-maintained, and two judgment-dependent guardrails (scope
   discipline; never skipping a non-automatable test step). A `PreToolUse` deny fires *after* the
   model has already chosen wrong — it corrects, it doesn't inform. A `SKILL.md` loads on trigger
   and describes only its own procedure. Neither carries cross-cutting orientation.

Trim both mirrors — `.tasks/guidelines.md` and its portable template
`.claude/skills/init-project/templates/guidelines.md` — down to bucket 3 only, plus a new
"which skill when" table that the file currently lacks.

Also: nothing today ever loads this file in a scaffolded project (no skill reads it;
`docs_review_paths` lists it but only `review-docs` reads that key). Making the trimmed file
actually reach a session's context is TASK-037's job (amended separately to inject it via the
`SessionStart` hook) — this task only has to leave TASK-037 something short enough to inject.

### Target shape (~40 lines, both mirrors)

Keep the `workflow_version: 1` frontmatter — `sync`'s `discover` explicitly treats this as a
non-artifact file, and `upgrade` hash-manages it by path, so the trim propagates to already-
scaffolded projects on their next `upgrade` automatically.

Sections, in order:

1. **Preamble + terminology** — what the file is, a pointer to `config.md`, one line noting each
   skill's own `SKILL.md` owns its procedure while this file holds the shared model. "task", never
   "ticket"/"story".
2. **The artifact model** — frontmatter is the source of truth; spec/epic/task definitions; one
   task = one branch = one PR = one sitting; no sub-tasks; `epic:` nullable; epic `status` derived
   by `sync`, never hand-set except `wont-do`.
3. **What `sync` owns, and what you own** — `sync` owns `next-id`, board regeneration, epic-status
   derivation, `blocked_by`/`blocks` reconciliation, archiving — never model judgement; `sync
   check` verifies, never fixes. You own the TODO list's hand-ordered priority and nothing else in
   `BOARD.md`; never hand-edit inside a `BEGIN:`/`END:` region.
4. **Which skill when** — new table mapping situation → skill (does not exist in the file today).
5. **Guardrails that need your judgement** — one line noting the mechanical guardrails are now
   hook-enforced, then the two that aren't: never touch files outside the task's scope
   (`git diff --name-only` is the check), and never skip a Testing strategy step silently — hand
   non-automatable steps to the human and record the result in the Worklog.

Drop the `- [ ]` checkbox formatting (nothing ever checks them) and the "if it isn't set up in this
repo yet, follow this checklist by hand" fallback — once EPIC-002 lands, the hooks contradict that
fallback (a human following it by hand would get denied).

## Acceptance criteria

- [ ] `.tasks/guidelines.md` and `.claude/skills/init-project/templates/guidelines.md` both drop
      the four-phase walkthrough, Resumability, and Bail-out sections entirely.
- [ ] Both drop the five hook-enforced Guardrails bullets listed above, keeping only the two that
      require judgement (scope discipline; never skip a test step silently).
- [ ] Both gain a new "which skill when" table. The portable mirror's table lists only the six
      portable skills (**not** `strip-project-references`, which is repo-only); the repo's own
      copy may list all seven.
- [ ] The portable mirror contains no concrete `TASK-`/`EPIC-`/`SPEC-NNN` id, no `§` citation, and
      none of `strip-project-references`'s banned phrases (`CLAUDE.md`, `.tmp/workflow-plan.md`,
      `this repo's own`) — verified by running that skill's own scanner (see Testing strategy).
- [ ] The two mirrors remain deliberately non-identical: the repo's own copy keeps its `SPEC-001`
      pointers, which the portable copy omits (per TASK-023's existing convention).
- [ ] `workflow_version: 1` frontmatter is preserved in both files, unchanged.
- [ ] `CLAUDE.md`'s "The workflow model" section still reads correctly against the trimmed file
      (update it if it now describes content that's been removed).
- [ ] `python3 -m pytest -q` is green, in particular
      `test_review_docs_scaffold.py::test_report_against_this_repos_real_docs_is_clean` (asserts
      `guidelines_mirror_diff` stays non-empty) and the `test_init_project_scaffold.py` /
      `test_init_project_upgrade.py` cases that reference `.tasks/guidelines.md` as a
      managed/scaffolded path.
- [ ] `python3 .tasks/bin/sync check` exits 0.

## Testing strategy

1. `python3 -m pytest -q` — full suite green, no regressions in the mirror-diff or
   scaffold/upgrade tests that reference `guidelines.md`.
2. `python3 .claude/skills/strip-project-references/scaffold.py scan` — confirm no new findings
   against the trimmed portable mirror (no id, no `§` citation, no banned phrase).
3. `python3 .claude/skills/review-docs/scaffold.py report` — confirm `dangling_references` and
   `skill_list_mismatches` are both empty, and `guidelines_mirror_diff` is still non-empty (the
   two files are expected to differ, just not in the ways being removed).
4. `python3 .tasks/bin/sync check` — exit 0.
5. Manual read-through: confirm the trimmed file, read on its own with no other context, still
   correctly orients a fresh session — the artifact model, what `sync` owns, and which skill to
   reach for are all answerable from it alone.

## Worklog

_(empty — appended during implementation)_

## Notes

- No test in the suite asserts on `guidelines.md`'s *content* — only its path (as a
  managed/scaffolded file) and the mirror-diff's non-emptiness — so this trim is test-safe by
  construction; the acceptance criteria above are the real check.
- TASK-037 (amended separately) is what makes the trimmed file actually reach a session's context
  via the `SessionStart` hook. This task only produces the trimmed content; it does not wire up
  injection.
- `README.md:81` mentions `guidelines.md` in the upgrade description — check it still reads
  correctly but no change is expected there.
