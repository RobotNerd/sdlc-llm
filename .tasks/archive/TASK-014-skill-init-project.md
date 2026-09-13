---
id: TASK-014
title: "init-project skill: scaffold .tasks/ in a new repo"
type: feature
status: done
epic: EPIC-001
created: 2026-09-10
branch: task-014-skill-init-project
pr: https://github.com/RobotNerd/sdlc-llm/pull/20
merge_commit: 977989af6f4b07402b358cfe6dc41ac7ff862f2a
blocked_by: [TASK-002, TASK-003, TASK-010]
blocks: []
---

# TASK-014: init-project skill: scaffold .tasks/ in a new repo

## Description

A checklist skill that scaffolds the workflow into a fresh repo: empty `BOARD.md` with all regions, `config.md` (interviewing for `test_command` etc.), `guidelines.md` with `workflow_version`, the `.tasks/templates/` set, and `.github/pull_request_template.md` (SPEC-001 §`init-project`).

Named `init-project` rather than SPEC-001's `init` (decided during this task): a real Claude Code
project skill lives at `.claude/skills/<name>/SKILL.md`, and this repo already has a global `init`
skill (initializes a `CLAUDE.md`) — naming this one identically would shadow it for anyone
working in this repo. `init-project` names what it actually does and can't collide. This is a
naming choice only; SPEC-001's behavioral description of `init` is otherwise unchanged, and its
prose has been updated to `init-project` everywhere it names the skill.

## Acceptance criteria

- [x] Skill lives at `.claude/skills/init-project/SKILL.md` — a real Claude Code project skill (frontmatter `name`/`description` + a numbered-checklist body), invocable as `/init-project`.
- [x] Skill is a numbered checklist with explicit STOP markers and 'if X ambiguous, ASK' rules — not prose.
- [x] Produces: `BOARD.md` (with `epics` + four column regions, empty → `_(none)_`), `config.md`, `guidelines.md`, `.tasks/templates/{spec,epic,task}.md`, `.github/pull_request_template.md`.
- [x] Interviews the user for every `config.md` value rather than guessing, including the git settings (`remote`, `rebase_before_pr`, `merge_strategy`, `delete_branch_after_merge`) with sensible defaults offered; writes `workflow_version: 1`.
- [x] Generated `guidelines.md` includes the git-workflow section and the never-merge / `--force-with-lease`-only guardrails (SPEC-001 §Guardrails).
- [x] Detects whether `gh` is installed and authenticated (`gh auth status`) and warns if not, since `implement-task` needs it.
- [x] Refuses to run if `.tasks/` already exists (points at an `upgrade` path instead).
- [x] Ends by running `sync` and showing the clean board.

## Testing strategy

1. Run `/init-project` in an empty scratch git repo; confirm every listed file appears and `sync check` exits 0 immediately after.
2. Run `/init-project` again in the same repo; confirm it refuses.
3. Verify the generated `BOARD.md` region shapes match SPEC-001 §'Rendering details'.

## Worklog

- 2026-09-12: Renamed the skill from SPEC-001's `init` to `init-project` before writing any code
  — confirmed with the user first (see Description). Propagated the rename through SPEC-001
  (§`init-project` header, the "Five skills" bullet, the `.tasks/config.md` prose), `EPIC-001`'s
  In-scope bullet, `README.md`, and `CLAUDE.md`.
- Built `.claude/skills/init-project/`: `SKILL.md` (the checklist) plus a `templates/` directory
  holding everything the skill writes verbatim or with substitution (`board.md`, `config.md`,
  `guidelines.md`, copies of `.tasks/templates/{spec,epic,task}.md` and
  `.github/pull_request_template.md`), and `vendored-sync` — a copy of `.tasks/bin/sync`.
- **Gap not in the AC list, filled in anyway:** nothing in TASK-014's AC mentions
  `.tasks/bin/sync` itself, but AC #8 ("ends by running `sync`") is impossible in a genuinely
  fresh repo without it — `sync` is "a single stdlib file beside the data it manages"
  (`.tmp/workflow-plan.md`'s Decisions table), not a separately-installed tool. Vendoring a copy
  into the skill directory is the minimal thing that makes the skill actually work standalone;
  packaging/distributing `sync` properly (so a vendored copy doesn't silently drift from the
  original) is exactly the "reusable global workflow" SPEC-001 lists as a non-goal / follow-on
  spec, so a plain vendored copy is the right scope for this MVP, not a shortcut around a decision
  that was actually asked for.
- **Real `sync` bug found and fixed via testing, not routed around:** building `templates/board.md`
  (an empty `## TODO` section immediately followed by `## In Progress`, with no items and no
  blank-line gap between them) and running the vendored `sync` against it in a scratch repo
  silently deleted `## In Progress` and everything after it from `BOARD.md`. Root cause:
  `apply_todo_merge` searched for the next `## ` heading starting at `start` (right after the
  literal `"## TODO\n\n"` heading text), but when the heading immediately follows with zero TODO
  lines, that heading's leading `\n` sits at `start - 1` — one position earlier — so the search
  always missed it and fell through to "TODO is the last section," discarding the heading and
  everything after it as unrecognised TODO text. This isn't a fresh-repo-only edge case — any
  project hits it the moment its TODO count drops to zero while another board section follows.
  Fixed by starting the heading search at `start - 1` instead of `start` (`.tasks/bin/sync`);
  added two regression tests to `tests/test_todo_merge.py` (data isn't lost, and idempotency
  holds, both for a completely empty TODO section and for one that later gains a line). Confirmed
  the fix converges to a stable, idempotent shape (an empty TODO section canonically renders with
  an extra blank line before the next heading) and updated `templates/board.md` to match that
  exact byte shape, so a freshly-scaffolded board needs zero corrective diff.
- Full pytest suite: 211 passed (209 + 2 new), before and after the fix confirmed the fix doesn't
  regress anything else. `python3 .tasks/bin/sync check` stayed clean on this real repo throughout.
- **Testing strategy, all three steps run against a real scratch git repo** (`git init`, not just
  a bare directory), following `SKILL.md`'s checklist by hand step for step:
  1. Scaffolded every listed file (`config.md` with substituted interview answers and its leading
     comment stripped, `guidelines.md`, `BOARD.md`, `.tasks/templates/*`,
     `.github/pull_request_template.md`, `.tasks/bin/sync`). `python3 .tasks/bin/sync` printed
     "Already up to date." — zero diff immediately after scaffolding, and `sync check` exited `0`.
  2. Re-checked the precondition in the same repo: `.tasks/` now exists, so the skill's step 0
     correctly refuses.
  3. `sync check`'s pass in step 1 *is* the region-shape verification — it diffs every generated
     region against SPEC-001's rendering rules byte-for-byte.
- The `gh auth status` / not-a-git-repo preflight checks were exercised directly (both true in
  this environment: real git repo, `gh` authenticated as `RobotNerd`) rather than the negative
  path (no `gh`, no git repo) — the negative path is straightforward shell-conditional logic
  described plainly enough in `SKILL.md`'s step 1 that a dedicated test wasn't worth a second
  scratch environment just to prove an `if` statement.

## Notes

- Blocked by TASK-002 (templates), TASK-003 (PR template), TASK-010 (no IDs yet, but shares the config-reading helper).
- Independent of the other skills.
- Renamed from `init` to `init-project` (see Description) — SPEC-001 and the other docs referring
  to the skill by name were updated in the same change.
