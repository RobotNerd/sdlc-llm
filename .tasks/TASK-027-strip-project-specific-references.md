---
id: TASK-027
title: Strip project-specific references from the portable surface
type: chore
status: in-review
epic: EPIC-001
created: 2026-09-14
branch: task-027-strip-project-specific-references
pr: "https://github.com/RobotNerd/sdlc-llm/pull/43"
merge_commit: null
blocked_by: [TASK-022, TASK-024, TASK-025, TASK-026]
blocks: [TASK-029, TASK-036]
---

# TASK-027: Strip project-specific references from the portable surface

## Description

The toolkit's shipped surface — the five skills, `scaffold.py`, `init-project/templates/*`, and
`vendored-sync` — is written as if it will only ever run in this repo. It cites `SPEC-001`
sections (~25 times), carries `TASK-NNN` provenance comments from the tasks that built it
(`(TASK-021)` in `init-project/SKILL.md` and `scaffold.py`; a `TASK-004`…`TASK-013` map in
`vendored-sync`'s module docstring), points at `CLAUDE.md`, and references `.tmp/workflow-plan.md`.

In another project none of those referents exist. `SPEC-001` there is some unrelated spec, and
`TASK-021` is a live task id that will collide — an agent reading the skill has every reason to
think it's being told about work in the repo it's actually standing in. Scope is the portable
surface only (everything under `.claude/skills/`); this repo's own `.tasks/` artifacts stay as
they are.

Blocked on TASK-022/024/025/026: each adds a new script to a skill and will almost certainly
reintroduce `TASK-NNN` provenance comments, so this task runs last and sweeps up.

Method for `SPEC-001 §"…"` citations: delete the parenthetical, keep the surrounding sentence —
every one sits next to prose that already states the rule. Do not repoint them at
`guidelines.md`; it doesn't document several of the cited sections (e.g. "Rendering details",
"Epic status derivation"), so the pointers would dangle.

`init-project/vendored-sync` and `.tasks/bin/sync` are byte-identical today. Apply the identical
edit to both — editing only the vendored copy sets a trap where the next `sync` bug fix, made in
`.tasks/bin/sync` and copied over wholesale, silently restores every comment this task removes.

`templates/guidelines.md`'s "this repo's kanban workflow" phrasing stays; it reads correctly in
the target repo and this template is already deliberately de-project-ified relative to
`.tasks/guidelines.md`. `init-project/templates/{spec,epic,task}.md` and
`pull_request_template.md` currently match this repo's own `.tasks/templates/*` and
`.github/pull_request_template.md` byte-for-byte; after this task their leading doc-comments
diverge, and reconciling the dogfooded copies (if wanted) is left to TASK-023.

## Acceptance criteria

- [x] No `TASK-`/`EPIC-`/`SPEC-` id followed by three digits appears anywhere under
      `.claude/skills/` (placeholders like `TASK-NNN` are fine).
- [x] No reference to `CLAUDE.md`, `.tmp/workflow-plan.md`, or "this repo's own …" remains in
      shipped content under `.claude/skills/`.
- [x] Every sentence that lost a `SPEC-001 §"…"` citation still states the rule it referenced, on
      its own, without the citation.
- [x] `init-project/vendored-sync` and `.tasks/bin/sync` are byte-identical.
- [x] A new `tests/test_portable_surface.py` mechanically enforces the id-absence and
      vendored/`.tasks/bin/sync` parity checks above.
- [x] `pytest` and `python3 .tasks/bin/sync check` both pass.
- [x] No behavior change: `sync`'s output on this repo is unchanged (`sync check` stays clean,
      no generated region diffs).

## Testing strategy

1. Write `tests/test_portable_surface.py` first and confirm it fails against the current
   (unedited) tree — proves the guard actually catches the problem.
2. Make the reference-stripping edits across every file listed in the Notes below.
3. Run `pytest` — full suite green, including the new test and the extended
   `tests/test_init_project_scaffold.py` coverage (id-grep over the actual *scaffolded* output,
   not just the template sources).
4. Run `python3 .tasks/bin/sync check` — exit 0, and `git diff` shows no change to any generated
   region.
5. `diff .claude/skills/init-project/vendored-sync .tasks/bin/sync` — identical.
6. Human read-through of the `vendored-sync` and template diffs, confirming no docstring lost its
   meaning when a citation was dropped. Non-automatable — record the result in the Worklog.

## Worklog

- Scope grew beyond the Notes' file list: `add-task`, `plan-feature`, and `review-docs` (plus
  `implement-task/scaffold.py`) weren't listed there since they postdated this task's authoring
  (`TASK-047`/review-docs merged after), but the acceptance criteria's grep is repo-wide under
  `.claude/skills/` and caught the same class of reference in all of them. Confirmed with the
  human before starting: acceptance criteria treated as authoritative, all 17 files with matches
  cleaned (not just the 10 in Notes).
- `templates/config.md`'s `docs_review_paths: [CLAUDE.md, README.md, .tasks/guidelines.md]`
  default and `review-docs/scaffold.py`'s `_ROOT_DOC_NAMES = ("README.md", "CLAUDE.md")` constant
  were kept as-is: `CLAUDE.md` there is a generic Claude Code convention filename (like
  `README.md`), not a citation pointing at *this* repo's own doc — the new test
  (`tests/test_portable_surface.py`) has an explicit, narrow exemption for exactly these two
  spots so a *new* stray `CLAUDE.md` reference elsewhere still trips the check.
- Testing strategy steps 1–5: all automated, all passed (`pytest` — 346 passed, including the new
  `tests/test_portable_surface.py` and the extended `tests/test_init_project_scaffold.py`
  id-grep-over-scaffolded-output coverage; `sync check` exit 0 with no generated-region diff;
  `vendored-sync`/`.tasks/bin/sync` confirmed byte-identical).
- Step 6 (human read-through, non-automatable): presented the full diff of every edited file to
  the human for review. Confirmed — no docstring lost its stated meaning when its citation was
  dropped; approved proceeding to wrap-up.

## Notes

- Files and references to remove, file by file:
  - `.claude/skills/init-project/SKILL.md` — `(TASK-021)`; `(SPEC-001)` in the `description:`
    frontmatter.
  - `.claude/skills/init-project/scaffold.py` — `(TASK-021)` in the module docstring; "matching
    this repo's own `config.md`".
  - `.claude/skills/implement-task/SKILL.md` — `SPEC-001` refs; `CLAUDE.md`; `e.g. TASK-016` →
    `TASK-NNN`.
  - `.claude/skills/refine-backlog/SKILL.md` — "per SPEC-001's epic-status rules".
  - `init-project/templates/spec.md` — `SPEC-001` refs; "this repo's own SPEC-001 and the
    original analysis doc"; `TASK-002's acceptance criteria`.
  - `init-project/templates/epic.md` — `SPEC-001` refs.
  - `init-project/templates/task.md` — `SPEC-001` ref; `[TASK-004, TASK-006]` → `[TASK-NNN,
    TASK-NNN]`; `task-021-my-task` → `task-NNN-my-task`.
  - `init-project/templates/config.md` — "the seam SPEC-001 describes".
  - `init-project/templates/pull_request_template.md` — `SPEC-001` refs; `CLAUDE.md §Guardrails`;
    hardcoded `` `pytest` `` → `` `<test_command>` ``.
  - `init-project/vendored-sync` (and `.tasks/bin/sync`, kept identical) — the
    `TASK-004`…`TASK-013` docstring map; `.tasks/specs/SPEC-001-llm-sdlc-workflow.md`; inline
    `SPEC-001 §'…'` citations; the `"TASK-004"` example; the `TASK-012`/`TASK-011`/`TASK-013`
    comments near the bottom of the file.
