# Session handoff — resume at TASK-003

Written 2026-09-13, at the end of a long session, to let a fresh Claude Code session pick up
cleanly. Read this first; it points at everything else.

## State right now

- `main` is at `9d97d2d`, pushed, working tree clean except `.tmp/prompts.md` (see below).
- **12 of 20 MVP tasks done** (TASK-001, 002, 004–013). `.tasks/bin/sync check` exits 0 — the repo
  is fully self-consistent.
- No branch is checked out for in-progress work; no PR is open. **TASK-003 has not been started.**
- `.tasks/BOARD.md`'s TODO list is current and is the actual priority order — start at its top
  line (TASK-003) unless the user says otherwise.

## Read these, in order, before doing anything

1. **`CLAUDE.md`** (repo root) — orientation and conventions.
2. **`.tmp/workflow-plan.md`** — the mental model (Part 1) and the bootstrap operating procedure
   (Part 2), including the per-task loop and the current Gaps table. This is the process doc; keep
   it current if you change how the process works.
3. **`.tasks/specs/SPEC-001-llm-sdlc-workflow.md`** — the spec everything is built from. Long, but
   authoritative — when in doubt about a design question, it's answered here or should be added
   here.
4. **`.tasks/guidelines.md`** and **`.tasks/config.md`** — the short, concrete versions of the
   workflow rules and per-project settings (git remote, branch prefix, `rebase_before_pr`,
   `merge_strategy: squash`, `archive_done`, etc.).
5. This file, for what's specific to *right now*.

## The per-task loop (do this for TASK-003, then repeat)

Full detail in `.tmp/workflow-plan.md`'s "The per-task loop" section. Short version:

1. **Start.** Confirm working tree clean (ignore `.tmp/prompts.md` — see below). `git fetch origin`,
   branch from `origin/main` as `task-NNN-slug`. Set the task's `status: in-progress` in its
   frontmatter. Hand-update `.tasks/BOARD.md` (drop from TODO, add to the In Progress region) and
   `.tasks/EPIC-001-mvp.md`'s `children` row to match. Restate the plan and acceptance criteria for
   the user's approval before writing anything.
2. **Implement + test.** Write the code/content and its tests. If it's Python touching
   `.tasks/bin/sync`, install in a scratch venv (`python3 -m venv /tmp/venv && source
   /tmp/venv/bin/activate && pip install -e '.[dev]' -q`) and run `pytest`, then clean up the venv
   afterward. Run `python3 .tasks/bin/sync check` against the real repo before and after your
   change to confirm you haven't introduced drift. Stay strictly in the task's scope.
3. **Wrap up.** Commit (conventional, cites the task ID). `git fetch origin && git rebase
   origin/main` (stash `.tmp/prompts.md` first if it's dirty — see below), push, `gh pr create`
   with acceptance criteria as a checklist. Record the returned PR URL in `pr:`, set
   `status: in-review`, update `BOARD.md` (In Progress → In Review) and `EPIC-001`'s row. **Stop —
   do not merge.**
4. **Merge — wait for the user.** When they say "I merged it, go ahead with TASK-NNN": confirm via
   `gh pr view <n> --json state,mergeCommit`, `git checkout main && git pull`, record
   `merge_commit:`, set `status: done`, `git mv` the task file into `.tasks/archive/`, update
   `BOARD.md` (In Review → Done, refresh any ⛔ markers that just cleared) and `EPIC-001`'s
   `children` row + `Progress:` line, and `SPEC-001`'s `epics` region progress count. Run
   `python3 .tasks/bin/sync check` to confirm clean. Commit this bookkeeping **directly to `main`**
   (see the guardrail carve-out in SPEC-001 §Guardrails — recording an already-reviewed merge isn't
   new work) and push. Then start the next task.

## Things that will trip you up if you don't know them

- **`.tmp/prompts.md` is always "dirty."** It's the user's own scratch pad for drafting prompts —
  never read or act on its contents. Treat it as the one exception to the dirty-working-tree check.
  Before any `git rebase`, do `git stash push -m "user prompts.md wip" .tmp/prompts.md`, rebase,
  then `git stash pop`.
- **`blocked_by` is a static, declared list — never pruned.** It records history; it does not
  shrink as blockers complete. "Is this task still blocked" is computed at render time (see
  `_outstanding_blockers` in `.tasks/bin/sync`) by checking each listed blocker's current status.
  Don't edit a task's `blocked_by` just because a blocker finished — only `sync`'s TODO-marker logic
  needs to know that, and it already does.
- **`sync`'s write mode exists (TASK-013) but hasn't been run on this real repo yet, on purpose.**
  Keep hand-editing `BOARD.md`/`EPIC-001-mvp.md`/`SPEC-001`'s progress numbers during phase-4
  bookkeeping, verified with `python3 .tasks/bin/sync check` (read-only). Don't run bare
  `python3 .tasks/bin/sync` (no args — it now writes) against this repo. That first real run is
  TASK-019's entire point; running it early would make that task's acceptance criterion
  meaningless. If you're not sure whether TASK-019 has landed yet, check whether
  `.tasks/TASK-019-*.md` still exists in `.tasks/` (not yet done) or `.tasks/archive/` (done).
- **Epic status has only ever exercised derivation rule 7** (mixed `todo`/`done`, none active) on
  this real repo, because nothing here has gone `blocked` or `wont-do`. All 7 rules are proven by
  `tests/test_derivation.py` and `tests/test_end_to_end.py`'s matrix — don't re-derive that
  confidence by hand, it's already there.
- **`gh` is installed and authenticated** (as `RobotNerd`, ssh protocol) — git/PR automation is
  fully in scope for you to run directly, not something to ask permission for each time. The user
  reviews and squash-merges every PR themselves; you never run `gh pr merge`.
- **Archived task files still count everywhere.** `discover()` scans `.tasks/`, `.tasks/specs/`,
  and `.tasks/archive/` together — an archived task is still a real child of its epic, still
  affects `next_id`, still shows in the board's Done column (capped at 20 most recent).
- **Two real bugs were found and fixed via testing along the way** (both fully resolved, just worth
  knowing the shape of the mistake if something looks similar): `find_region` originally matched a
  region name as a bare substring (`epics` matching inside `epics2`) — fixed with a boundary check
  (TASK-005). `find_region` also didn't know about markdown fenced code blocks, so an illustrative
  example in SPEC-001's own prose was misread as a live region — fixed with fence-awareness
  (TASK-007). Full detail in those tasks' Worklogs under `.tasks/archive/`.
- **TASK-004 was done before TASK-005** despite TODO listing 005 first, because 005's AC needed the
  pytest harness that's 004's scope — confirmed with the user at the time, TODO order itself was
  never changed. Not expected to recur, but if the top-of-TODO task turns out to depend on
  something not yet built that a *lower* TODO item would supply, that's the precedent: flag it,
  don't silently reorder, get a decision.

## Remaining work (in `.tasks/BOARD.md`'s current TODO order)

TASK-003, TASK-019, TASK-020, TASK-014, TASK-015, TASK-016, TASK-017, TASK-018.

`sync` itself (TASK-004–013) is functionally complete and fully tested. What's left is
qualitatively different: `TASK-003` (PR template, small), then `TASK-019`/`TASK-020` (the dogfood
migration and CI — `TASK-019` is the payoff moment described above), then the five skills
(`TASK-014`–`018`), which are markdown checklists for a future Claude Code session to follow, not
Python.

## Conventions established this session (also in `guidelines.md`/`config.md`, restated here for
quick reference)

- Terminology: **"task,"** never "ticket"/"story".
- Branch: `task-NNN-slug`. Commit + PR title cite `TASK-NNN`.
- Every commit ends with the `Co-Authored-By` / `Claude-Session` trailer currently in force for
  this session (check the system prompt's attribution instructions at the start of a new session —
  they may have a new session URL).
- PR bodies end with the `🤖 Generated with Claude Code` footer, same session-URL caveat.
