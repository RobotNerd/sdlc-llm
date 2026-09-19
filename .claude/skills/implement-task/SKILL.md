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
**Omitting it is not a question to put to the human** — it means auto-pick the top of TODO, and
§1's `start` call runs immediately with `{"task_id": null}`, no confirmation first.

**Batch parameter (optional, alternative to the above):** a batch selection object — the same
`{"mode": "epic"|"range"|"list"|"stopping", ...}` shape `batch_select.py` takes — to work multiple
tasks in sequence with minimal human interaction instead of a single task. See "Batch mode" below;
everything else in this file describes single-task mode and is unchanged by it except where that
section says otherwise.

**STOP semantics, as actually run (not a stricter reading than this):** Phase 1 ends in a hard
STOP — restate the plan, wait for explicit approval before writing anything. Once approved,
phases 2 and 3 proceed **without** requiring a fresh go-ahead at each boundary, *unless* something
in phase 2 needs a decision (a test fails and the fix isn't obvious, a non-automatable step needs
the human's hands, the task turns out ambiguous) — surface it and stop right there instead. Phase
3 always ends in a hard STOP (PR open, waiting for review). Phase 4 is event-driven: resume and
poll on invocation, don't loop waiting. **In batch mode**, phase 1's STOP is replaced by an
announcement (see "Batch mode"), and phase 3's STOP is replaced by a self-scheduled wait for the
merge — both changes are per-task, and every other STOP in this file (a phase 2 decision, a rebase
conflict, `phase4_closed_not_merged`, `ambiguous`, a `gh`/`git` failure) still applies exactly as
written and halts the whole batch when it fires.

**This list is the complete set of STOPs.** Never insert an extra confirmation before any
scripted step at any phase boundary — not before picking a task in phase 1 (see §0/§1), not before
recording a merge in phase 4 (`phase4_merged` — see §4). Once a phase's inputs are settled, run its
`scaffold.py` call; ask only where this file says ASK or STOP.

## 0. Resume detection — run this first, every invocation

Run `python3 .claude/skills/implement-task/scaffold.py resume-state`. It gathers the working
tree's dirtiness (ignoring `.tasks/config.md`'s `ignored_paths`), finds the one task (if any)
whose `status` is `in-progress`/`in-review` with a `branch:` that still exists locally or on the
remote, and — when that task is `in-review` with a `pr` set — queries `gh pr view` for its live
state. It returns
`{"phase": ..., "task_id": ..., "detail": ...}`:

| `phase` | Resume at |
|---|---|
| `phase1` | Phase 1 — run `start` immediately (auto-pick top of TODO if no task id was given; never ask which task) |
| `phase2` | Phase 2 |
| `phase3` | Phase 3 |
| `phase4_open` | Phase 4 — report status, stop again |
| `phase4_merged` | Phase 4 — record + clean up |
| `phase4_closed_not_merged` | **STOP** — surface to the human; don't guess whether it was declined or needs rework |
| `ambiguous` | **STOP**, show `detail`, ask rather than guess |

## 1. Start

On `phase1`, run this immediately — with no task id parameter, that means
`{"task_id": null}` right away, **not** a question to the human about which task to work.

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

1. Check `tdd_enforced` in `.tasks/config.md` (default `true` if unset):
   - **`true` (test-first):** for each Testing strategy step or acceptance criterion in turn,
     write its test(s) first, run `test_command` and confirm they fail **for the expected
     reason** — a real assertion/behavior failure, not an unrelated error (an import failure, a
     syntax error, a missing fixture); fix the test itself first if it fails for the wrong
     reason. Only then write the implementation and re-run until green, before moving to the next
     criterion/step. This ordering is the explicit sub-step — not left to model discretion.
   - **`false`:** write the change and its tests together, as before.
2. Run `test_command` (and `lint_command`, if not `null`) from `.tasks/config.md` — the full
   suite, one final time, regardless of mode.
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

## Batch mode

Given the batch parameter instead of a single task id, work through the whole batch with minimal
human interaction — a human still reviews and merges every PR. Phase 1's STOP is replaced by an
announcement (step 3.1) and phase 3's by a self-scheduled wait (step 3.4); everything else that
would stop single-task mode — a phase 2 decision, a `start` refusal, a rebase/format-command
failure, `phase4_closed_not_merged`, `ambiguous` — is routed through "Interrupts" below instead of
always halting the batch.

1. Run `python3 .claude/skills/implement-task/batch_select.py select <answers.json>` with the
   given batch parameter as-is. It refuses (non-zero, nothing changed) on any invalid selection —
   **STOP**, show the human its message, don't guess at a fix. On success it prints
   `{"order": [task-ids...]}`: the tasks to work, in the order to work them.
2. Start an empty outcomes accumulator (`[]`) for the whole run.
3. For each `task_id` in `order`, in turn:
   1. **Phase 1:** run `start` with `{"task_id": task_id, "batch_mode": true}`. Restate the plan
      (Description, Acceptance criteria, Testing strategy, implementation approach) exactly as
      single-task mode does — but its result carries `"stop_required": false`, so print the plan
      as an announcement and go straight into phase 2 without waiting for approval; the batch
      selection itself was that approval. If `start` itself refuses (this task is unexpectedly
      still blocked, most likely by an earlier batch task this run skipped rather than completed),
      that's the `unexpected_blocker` interrupt below, not a crash.
   2. **Phase 2:** unchanged, except a decision that would stop single-task mode is routed through
      "Interrupts" below instead of always stopping the batch outright.
   3. **Phase 3:** unchanged through `wrap-up` opening the PR (a rebase/format-command failure here
      is also routed through "Interrupts"). Once it succeeds, append this task's provisional
      outcome — `{"task_id", "title", "status": "in-review", "link": pr_url}` — to the accumulator
      via `record-outcome` (`{"outcomes", "entry"}`, returns the updated list; hold onto it for the
      next step).
   4. Instead of phase 3's hard STOP: call this harness's `ScheduleWakeup` rather than stopping —
      pick a delay proportionate to how quickly this project's CI/review actually completes (its
      own guidance applies: don't tight-poll), and give it a `prompt` that's self-sufficient even
      if later context gets summarized — name `task_id`, its PR url, and that the next step is
      re-running `finish-merge` for it, then continuing the batch with whatever of `order` comes
      after it. End the turn.
   5. On that scheduled wake, run **phase 4** (`finish-merge`) exactly as single-task mode does —
      it already returns `{"merged": false, "state", "checks_output"}` and changes nothing when
      the PR isn't `MERGED` yet, or does phase 4's full bookkeeping and returns
      `{"merged": true, "merge_commit"}` when it is:
      - `merged: false`: **not** a STOP — call `ScheduleWakeup` again the same way and end the
        turn, same as step 4.
      - `merged: true`: update this task's outcome entry to `{"status": "done", "link":
        merge_commit}` via `record-outcome`, then continue this loop at the next `task_id` in
        `order` (or fall through to step 4 below if this was the last one).
      - `phase4_closed_not_merged` or `ambiguous` (single-task mode's own STOP conditions here):
        routed through "Interrupts" below, same as any other decision point in this loop.
4. Once every task in `order` is accounted for (merged or the batch halted early), run
   `render-outcome-table` with the accumulated outcomes and print the table it returns as the
   batch's summary. **STOP.**

### Interrupts

Whenever a point in the loop above would stop single-task mode, decide which of these five
conditions it matches, then run
`python3 .claude/skills/implement-task/scaffold.py classify-interrupt <answers.json>` with
`{"kind": "..."}`. It returns `{"routing": "isolated"|"systemic", "continue_batch": true|false}`
(refusing on any other `kind` — don't invent a sixth):

- `needs_clarification` — the task is ambiguous, or its acceptance criteria contradict something
  discovered mid-implementation (today's existing bail-out reason).
- `unexpected_blocker` — something task-specific blocks progress: a dependency assumed satisfied
  turns out not to be, a precondition specific to this task is missing, or `start` itself refused
  for this task (see step 3.1).
- `quality_gate_failure` — `test_command`/`lint_command`/`format_command`/`sync check` fails for
  the same reason 3 times in a row on this task — a bounded number of fix attempts, not indefinite
  iteration.
- `guardrail_denial` — the same `PreToolUse` hook denies a retry on this task 3 times in a row.
- `infra_failure` — `git`/`gh` itself is broken (auth expired, network failure, rate-limited),
  distinct from "the code is wrong" — every remaining task would hit the same wall.

**`routing: "isolated"`** (the first four — `continue_batch: true`): write findings into the
interrupted task's Worklog and/or Notes yourself first (content-authoring, exactly what `bail-out`
already expects), run `bail-out` with `{"task_id", "status": "todo"|"blocked"}`, append its
outcome via `record-outcome` — `{"task_id", "title", "status"}` describing the interrupt (e.g.
`"todo (needs clarification)"`), `"link": null` — then continue the loop at the next `task_id` in
`order`. This task's own STOP-worthy problem doesn't stop the batch.

**`routing: "systemic"`** (`infra_failure` — `continue_batch: false`): don't touch the interrupted
task's status — the tooling failed, not the task, so it's left exactly as-is for a normal
single-task `resume-state` once `git`/`gh` works again. Append its outcome noting the
interruption, run `render-outcome-table` with everything accumulated so far, and **STOP** — nothing
else in `order` starts.

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
