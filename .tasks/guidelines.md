---
workflow_version: 1
---

# Workflow guidelines

The operating rules for this repo's "kanban in markdown" workflow. This file states the rules;
`.tasks/config.md` holds the per-project values they refer to; `.tasks/specs/SPEC-001-*.md` is
the full spec these rules are drawn from. `.tmp/workflow-plan.md` is the narrative walkthrough for
a human who wants the mental model, not just the checklist.

Terminology: **task**, always — never "ticket" or "story".

## The lifecycle

### Spec → Epic → Task

- [ ] A **spec** (`.tasks/specs/SPEC-NNN-slug.md`) captures the "why": problem, alternatives
      considered, non-goals. Written by `plan-feature`.
- [ ] An **epic** (`.tasks/EPIC-NNN-slug.md`) groups a body of work and links back to its spec via
      `spec:`. Its `status` is **derived by `sync`** from its children — never hand-set, except to
      mark it `wont-do` (cancelling is a human decision).
- [ ] A **task** (`.tasks/TASK-NNN-slug.md`) is one unit of work: one branch, one PR, one sitting.
      No sub-tasks — split the task or promote it to an epic instead. Links to its epic via
      `epic:` (nullable — a loose chore needs none).
- [ ] IDs are allocated by `sync next-id <type>` — never by counting files yourself. It scans
      `.tasks/`, `.tasks/specs/`, and `.tasks/archive/`, so an archived ID is never reused.

### Board

- [ ] `.tasks/BOARD.md` is mostly generated. The **TODO list is the only hand-maintained part** —
      it is priority order, which nothing can infer. `sync` may drop a line whose task left
      `todo`, append a new `todo` task at the end, and re-annotate a line's epic tag and blocked
      marker, but it must **never reorder** TODO.
- [ ] Everything between `<!-- BEGIN:name -->` / `<!-- END:name -->` markers — in `BOARD.md`,
      every `EPIC-*.md`, and every `SPEC-*.md` — is generated. **Never hand-edit inside a marked
      region.** Change the source task/epic file and run `sync`; until `sync` exists, hand-update
      the region to the exact shape it will produce (see SPEC-001 §"Rendering details").

## Working a task — `implement-task`, four phases

Each phase ends in a **STOP** for human input. Until the skill exists, follow this checklist by
hand.

1. **Start.** Refuse to begin if the working tree is dirty (`.tmp/prompts.md`'s constant edits are
   the known exception — it is not part of any task). Pick the top unblocked TODO task, announcing
   any blocked ones skipped. `git fetch <remote>`, branch from `<remote>/<default_branch>` as
   `<branch_prefix><NNN>-<slug>`. Set `status: in-progress` and `branch:`. Update the board and
   epic by hand. **Restate the plan and acceptance criteria for approval before writing anything.**
   — STOP —
2. **Implement + test.** Write the change and its tests. Run `test_command` (and `lint_command`,
   if not `null`). Walk the task's Testing strategy; hand anything non-automatable to the human
   and record the result in the task's **Worklog** — never skip silently. Stay in scope: check
   `git diff --name-only` before committing. — STOP —
3. **Wrap up.** Update the files in `docs_paths` if the change touches them. Commit
   (conventional, citing the task ID). If `rebase_before_pr`, `git fetch <remote>` and rebase onto
   `<remote>/<default_branch>` — stop and surface any conflict rather than guessing. Push
   (`--force-with-lease` if the rebase rewrote already-pushed history). `gh pr create` with
   acceptance criteria as a checklist and test results filled in. Record the returned URL in
   `pr:`, set `status: in-review`. **STOP — a human reviews and merges.**
4. **Merge — observed, never performed.** A human reviews the PR on GitHub and **squash-merges**
   it (`merge_strategy`). Poll `gh pr view --json state,mergeCommit`; once `MERGED`, record
   `merge_commit:`, set `status: done`, run `sync` (which archives). If
   `delete_branch_after_merge`, delete the branch locally and on `<remote>`, then fast-forward
   local `<default_branch>`. **The skill never runs `gh pr merge`.**

**Resumability:** on invocation, infer the current phase from working-tree state, branch existence
(`git branch --list`), frontmatter `status`/`pr`, and `gh pr view --json state,mergeCommit` —
continue from there rather than restarting.

**Bail-out:** if the task turns out wrong or underspecified mid-flight, stop, write findings into
the task file, set `status` back to `todo` or `blocked`, run `sync`, and surface it.

## Guardrails

- Never push to `default_branch`. Always branch from the freshly-fetched
  `<remote>/<default_branch>`.
- **Never merge.** The skill opens the PR and stops; a human reviews and squash-merges on GitHub.
  Phase 4 only observes that merge and records it. Never run `gh pr merge`.
- Force-pushing is allowed **only** as `git push --force-with-lease` on the current task's own
  branch, immediately after a rebase onto `default_branch` — never plain `--force`, never on
  `default_branch`, never on a branch anyone else uses.
- Never touch files outside the current task's scope (`git diff --name-only` is the check).
- Never hand-edit text inside a `BEGIN:`/`END:` generated region — change the source task/epic
  file and run `sync`.
- Never hand-edit an epic's `status` except to set `wont-do`.
- Board regeneration, ID allocation, archiving, and "is this task blocked" are `sync`'s job, not
  model judgement.
