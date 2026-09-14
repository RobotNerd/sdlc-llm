---
name: implement-task
description: Execute a task end to end — branch, implement, test, open a PR, and observe the human's squash-merge — across four checkpointed phases (Start, Implement+test, Wrap up, Merge). Resumable from repo state on every invocation. This is the workflow's git/gh driver; it never merges.
---

# implement-task

A numbered checklist, not prose. **STOP** means pause for the human before continuing; **ASK**
means don't guess. Requires `.tasks/` to exist, `.tasks/bin/sync` to be runnable, and `git`/`gh`
(authenticated).

**Parameter (optional):** a specific task id (e.g. `TASK-016`) to work instead of auto-picking the
top of TODO. If given, still verify it's actually unblocked before starting fresh — if it's
already `in-progress`/`in-review`, this is a resume, not a new start (see §0).

**STOP semantics, as actually run (not a stricter reading than this):** Phase 1 ends in a hard
STOP — restate the plan, wait for explicit approval before writing anything. Once approved,
phases 2 and 3 proceed **without** requiring a fresh go-ahead at each boundary, *unless* something
in phase 2 needs a decision (a test fails and the fix isn't obvious, a non-automatable step needs
the human's hands, the task turns out ambiguous) — surface it and stop right there instead. Phase
3 always ends in a hard STOP (PR open, waiting for review). Phase 4 is event-driven: resume and
poll on invocation, don't loop waiting.

## 0. Resume detection — run this first, every invocation

Don't assume phase 1. Infer where things stand:

1. `git status --short` (ignoring `.tmp/prompts.md` — see §1.1).
2. Is there a task whose `status` is `in-progress` or `in-review`, with a `branch:` that exists
   (locally or on the remote)? That's the task in flight, if any.
3. Read its `status` and `pr`. If `pr` is set, `gh pr view <pr> --json
   state,mergeCommit,statusCheckRollup` for live state.

| Signal | Resume at |
|---|---|
| No task `in-progress`/`in-review` with a branch | Phase 1 — pick a task |
| `in-progress`, branch exists, no `pr`, code not yet committed | Phase 2 |
| `in-progress`, branch exists, changes committed but not pushed / no PR | Phase 3 |
| `in-review`, `pr` set, `gh pr view` state `OPEN` | Phase 4 — report status, stop again |
| `in-review`, `pr` set, `gh pr view` state `MERGED`, `merge_commit` not yet recorded | Phase 4 — record + clean up |
| `in-review`, `pr` set, `gh pr view` state `CLOSED` (not merged) | **STOP** — surface to the human; don't guess whether it was declined or needs rework |

Anything that doesn't match cleanly: **STOP**, describe the ambiguous state, ask rather than guess.

## 1. Start

1. **Dirty-tree check.** `git status --short`. `.tmp/prompts.md` is the one standing exception —
   it's the human's private prompt scratch pad, always treated as dirty, never read or acted on.
   Anything else dirty → **STOP**, surface it.
2. **Pick the task.** If a task id parameter was given, use it (still confirm below it's actually
   `todo` and unblocked, or that it's a resume per §0). Otherwise read `.tasks/BOARD.md`'s TODO
   top to bottom, skip any line carrying `⛔ blocked_by ...`, announce which ones were skipped and
   why, and take the first unblocked one.
3. `git fetch <remote>` (from `.tasks/config.md`), then branch from `<remote>/<default_branch>` as
   `<branch_prefix><NNN>-<slug>`.
4. Set that task's `status: in-progress` and `branch:` in its frontmatter.
5. Run `python3 .tasks/bin/sync` — regenerates the board and epic.
6. Restate the plan: the task's Description, Acceptance criteria, and Testing strategy, plus how
   you intend to implement it. **STOP — wait for explicit approval before writing any code.**

## 2. Implement + test

1. Write the change and its tests.
2. Run `test_command` (and `lint_command`, if not `null`) from `.tasks/config.md`.
3. Walk the task's Testing strategy step by step. A step that can't be automated (real
   credentials, costs money, needs a human's hands) — **present it to the human to run**, record
   the result in the task's **Worklog**. Never skip one silently.
4. Before committing, check `git diff --name-only` against the task's own scope. **Do not fix
   unrelated things on this branch** — note anything else noticed as a candidate for a separate
   task instead.
5. If anything here needs a human decision, stop right there and ask (see STOP semantics above).
   Otherwise continue straight into phase 3 — the plan was already approved in phase 1.

## 3. Wrap up

1. Update the files in `docs_paths` (`.tasks/config.md`) if this task's change touches them.
2. Commit — conventional commit message, citing the task id.
3. If `rebase_before_pr`: stash `.tmp/prompts.md` if it's dirty
   (`git stash push -m "user prompts.md wip" .tmp/prompts.md`), `git fetch <remote>`, rebase onto
   `<remote>/<default_branch>`, then `git stash pop`. On a real conflict, **STOP** and surface
   it — don't guess a resolution.
4. Push — plain push normally; `--force-with-lease` only if the rebase actually rewrote
   already-pushed history, and only on this task's own branch.
5. `gh pr create` — title citing the task id (conventional-commit style); body from
   `.github/pull_request_template.md` filled in: acceptance criteria checked off, test results
   filled in for every Testing strategy step (including what the human ran for non-automatable
   ones).
6. Record the returned URL in `pr:`, set `status: in-review`, run `sync`.
7. Report `gh pr checks <pr>` to the human — a red or pending check gets surfaced, never worked
   around. **STOP here — the human reviews and merges. Never run `gh pr merge`.**

## 4. Merge — observed, never performed

On the next invocation (or when told the PR merged):

1. Confirm via `gh pr view <pr> --json state,mergeCommit`. If not `MERGED` yet, report current
   state (`gh pr checks` too) and stop again — don't poll in a tight loop, wait to be re-invoked.
2. Once `MERGED`: `git checkout <default_branch> && git pull --ff-only`.
3. Record `merge_commit:`, set `status: done`.
4. Run `sync` — regenerates the board/epic and archives the task to `.tasks/archive/`.
5. If `delete_branch_after_merge`: delete the branch locally (`git branch -d`); on `<remote>` too,
   if it isn't already gone (many platforms auto-delete on merge — check before erroring).
6. Confirm `sync check` exits `0`.
7. Commit this bookkeeping directly to `<default_branch>` and push — SPEC-001's guardrail
   carve-out: recording an already-reviewed merge is not new work, so it doesn't need its own PR.

## Bail-out

If, at any point before the PR is opened, the task turns out wrong, underspecified, or blocked on
something unexpected: stop, write findings into the task file (Worklog and/or Notes), set
`status` back to `todo` or `blocked`, run `sync`, and surface it to the human. Don't force a bad
implementation through to a PR.

## Guardrails (non-negotiable — SPEC-001 / CLAUDE.md)

- Never push *task work* to `default_branch`. The one exception is phase 4's own bookkeeping
  commit (step 7 above).
- **Never run `gh pr merge`.** The human always does the squash-merge on GitHub.
- `--force-with-lease` only, only on the current task's own branch, only immediately after a
  rebase.
- Never touch files outside the task's own scope.
- Never hand-edit a `BEGIN:`/`END:` region or an epic's `status` — that's `sync`'s job.

## If `gh` is missing or not authenticated

Check with `gh auth status` before any `gh`-dependent step. If it fails: stop at that exact
point, print the precise `git`/`gh` commands for the human to run themselves, and note that the
next invocation should resume from re-checking `gh pr view` (or wherever `gh` was needed) rather
than restarting the task.
