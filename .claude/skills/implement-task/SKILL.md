---
name: implement-task
description: Execute a task end to end — branch, implement, test, open a PR, and observe the human's squash-merge — across four checkpointed phases (Start, Implement+test, Wrap up, Merge). Resumable from repo state on every invocation. This is the workflow's git/gh driver; it never merges.
---

# implement-task

A numbered checklist, not prose. **STOP** means pause for the human before continuing; **ASK**
means don't guess. Requires `.tasks/` to exist, `.tasks/bin/sync` to be runnable, and `git`/`gh`
(authenticated).

Every deterministic git/gh action, every `sync`/`sync check` call, the resume-detection lookup,
TODO-picking, and the frontmatter field edits (`status`/`branch`/`pr`/`merge_commit`) live in
`scaffold.py` next to this `SKILL.md` — not in this prose. This skill's own job is
everything genuinely judgment- or content-driven: restating the plan, writing code/tests, deciding
what's automatable, composing commit messages and PR titles/bodies, the bail-out call — each
paired with exactly one `scaffold.py` invocation for the mechanical part that follows it.

Every `scaffold.py` subcommand takes its answers as a JSON file (a scratch path is fine) and prints
a JSON result on success (exit `0`); on failure it prints a message to stderr and exits non-zero —
`resume-state` and `gh-auth-status` take no input file.

**Parameter (optional):** a specific task id (e.g. `TASK-NNN`) to work instead of auto-picking the
top of TODO. If given, `start` still verifies it's actually `todo` and unblocked — if it's already
`in-progress`/`in-review`, `start` refuses and says so; that's a resume, not a new start (see §0).

**STOP semantics, as actually run (not a stricter reading than this):** Phase 1 ends in a hard
STOP — restate the plan, wait for explicit approval before writing anything. Once approved,
phases 2 and 3 proceed **without** requiring a fresh go-ahead at each boundary, *unless* something
in phase 2 needs a decision (a test fails and the fix isn't obvious, a non-automatable step needs
the human's hands, the task turns out ambiguous) — surface it and stop right there instead. Phase
3 always ends in a hard STOP (PR open, waiting for review). Phase 4 is event-driven: resume and
poll on invocation, don't loop waiting.

## 0. Resume detection — run this first, every invocation

Run `python3 .claude/skills/implement-task/scaffold.py resume-state`. It gathers the working
tree's dirtiness (ignoring `.tasks/config.md`'s `ignored_paths`), finds the one task (if any)
whose `status` is `in-progress`/`in-review` with a `branch:` that still exists locally or on the
remote, and — when that task is `in-review` with a `pr` set — queries `gh pr view` for its live
state. It returns
`{"phase": ..., "task_id": ..., "detail": ...}`:

| `phase` | Resume at |
|---|---|
| `phase1` | Phase 1 — pick a task |
| `phase2` | Phase 2 |
| `phase3` | Phase 3 |
| `phase4_open` | Phase 4 — report status, stop again |
| `phase4_merged` | Phase 4 — record + clean up |
| `phase4_closed_not_merged` | **STOP** — surface to the human; don't guess whether it was declined or needs rework |
| `ambiguous` | **STOP**, show `detail`, ask rather than guess |

## 1. Start

Run `python3 .claude/skills/implement-task/scaffold.py start <answers.json>` with
`{"task_id": "TASK-NNN"}` (the given parameter) or `{"task_id": null}` to auto-pick the top
unblocked TODO task. It refuses (non-zero, nothing changed) if the working tree is dirty, if the
given/picked task isn't `todo`, or if it's still blocked. Otherwise it fetches, branches from
`<remote>/<default_branch>` as `<branch_prefix><NNN>-<slug>`, sets `status: in-progress` +
`branch:`, and runs `sync` — returning `{"task_id", "branch", "skipped"}` (`skipped` lists any
blocked TODO tasks it passed over while auto-picking; announce them and why).

Once it succeeds: restate the plan — the task's Description, Acceptance criteria, and Testing
strategy, plus how you intend to implement it. **STOP — wait for explicit approval before writing
any code.**

## 2. Implement + test

1. Write the change and its tests.
2. Run `test_command` (and `lint_command`, if not `null`) from `.tasks/config.md`.
3. Walk the task's Testing strategy step by step. A step that can't be automated (real
   credentials, costs money, needs a human's hands) — **present it to the human to run**, record
   the result in the task's **Worklog**. Never skip one silently.
4. Before committing, check `git diff --name-only` against the task's own scope. **Do not fix
   unrelated things on this branch** — note anything else noticed as a candidate for a separate
   task instead. This scope list is exactly what you'll pass as `wrap-up`'s `paths` next.
5. If anything here needs a human decision, stop right there and ask (see STOP semantics above).
   Otherwise continue straight into phase 3 — the plan was already approved in phase 1.

## 3. Wrap up

1. Update the files in `docs_paths` (`.tasks/config.md`) if this task's change touches them —
   content-authoring, stays here, not in the script.
2. Compose: a conventional commit message citing the task id; a PR title (same convention); a PR
   body from `.github/pull_request_template.md` filled in (acceptance criteria checked off, test
   results for every Testing strategy step, including what the human ran for non-automatable
   ones); a bookkeeping commit message for step 3's own `pr:`/`status:` update (e.g.
   `chore(TASK-NNN): record PR, set status in-review`).
3. Run `python3 .claude/skills/implement-task/scaffold.py wrap-up <answers.json>` with
   `{"task_id", "paths" (the in-scope file list from step 2.4 above), "commit_message", "pr_title",
   "pr_body", "bookkeeping_commit_message"}`. It adds+commits those paths, rebases onto
   `<remote>/<default_branch>` if `rebase_before_pr` (stashing/popping any dirty `ignored_paths`
   around it), pushes (plain, or `--force-with-lease` only when the rebase — or the formatting
   step below — actually rewrote already-pushed history), runs `gh pr create`, records `pr:` +
   `status: in-review`, runs `sync`, then commits+pushes that resulting change too (using
   `bookkeeping_commit_message`) — no separate manual follow-up commit needed — and reports
   `gh pr checks`, returning `{"pr_url", "checks_output", "checks_exit"}`. After the rebase and
   before the push, if `format_command` is set it's run once; any files it changes are folded into
   the existing commit via `--amend` rather than a new one, and a non-zero exit from the formatter
   itself is treated exactly like the rebase-conflict case below.
4. On a rebase conflict it leaves the repo mid-rebase and exits non-zero with `git status`'s
   output — **STOP**, resolve it by hand (`git rebase --continue`, `git stash pop` if it mentions
   one), then re-run `wrap-up`. Don't guess a resolution. A `format_command` that itself exits
   non-zero (a real tool error, not just "it reformatted files") gets the same treatment: **STOP**,
   show the human the output, resolve by hand, then re-run `wrap-up`.
5. Otherwise: show the human `checks_output` — a red or pending check gets surfaced, never worked
   around. **STOP here — the human reviews and merges. Never run `gh pr merge`.**

## 4. Merge — observed, never performed

On the next invocation (or when told the PR merged), run
`python3 .claude/skills/implement-task/scaffold.py finish-merge <answers.json>` with
`{"task_id", "bookkeeping_commit_message"}` (compose the latter now — conventional, e.g.
`chore(TASK-NNN): phase 4 — record merge, archive, unblock downstream`).

- If the PR isn't `MERGED` yet, it returns `{"merged": false, "state", "checks_output"}` and
  changes nothing — report the state and checks, and stop again; don't poll in a tight loop, wait
  to be re-invoked.
- If `MERGED`, it does everything phase 4 owns in one call: `checkout <default_branch>` +
  `pull --ff-only`; record `merge_commit:` + `status: done`; run `sync` (archives the task to
  `.tasks/archive/`); if `delete_branch_after_merge`, delete the branch locally and on `<remote>`
  (tolerating an already-gone remote branch); confirm `sync check` exits `0`; and — the one
  scripted exception to "never push to `default_branch`" — commit the resulting `.tasks/` changes
  with `bookkeeping_commit_message` and push directly to `<default_branch>` (a deliberate guardrail
  carve-out: recording an already-reviewed merge is not new work, so it doesn't need its own PR).
  Returns `{"merged": true, "merge_commit"}`.

## Bail-out

If, at any point before the PR is opened, the task turns out wrong, underspecified, or blocked on
something unexpected: stop, write findings into the task file (Worklog and/or Notes) yourself
first (content-authoring), then run
`python3 .claude/skills/implement-task/scaffold.py bail-out <answers.json>` with
`{"task_id", "status": "todo"|"blocked"}` — it sets that status and runs `sync`. Don't force a bad
implementation through to a PR.

## Guardrails (non-negotiable)

Enforced *in the script*, not only documented here:

- Never push *task work* to `default_branch`. The one exception is `finish-merge`'s own
  bookkeeping commit, and only once it has independently confirmed the PR is `MERGED` and the
  current branch actually is `default_branch`.
- **Never run `gh pr merge`.** The human always does the squash-merge on GitHub — no subcommand
  here does this.
- `wrap-up`'s push refuses outright (raises before running any `git` command) if the current
  branch isn't the task's own branch, or if that branch is `default_branch`; `--force-with-lease`
  only fires when a rebase actually rewrote already-pushed history.
- Never touch files outside the task's own scope — `wrap-up` only ever adds the `paths` it's given.
- Never hand-edit a `BEGIN:`/`END:` region or an epic's `status` — that's `sync`'s job, always
  invoked through the script, never by hand.

## If `gh` is missing or not authenticated

Run `python3 .claude/skills/implement-task/scaffold.py gh-auth-status` before any `gh`-dependent
step. If it fails: stop at that exact point, print the precise `git`/`gh` commands for the human to
run themselves, and note that the next invocation should resume from `resume-state` (or wherever
`gh` was needed) rather than restarting the task.
