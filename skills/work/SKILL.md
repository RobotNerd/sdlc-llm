---
name: work
description: Implements a batch of Kaneo To Do tasks on one branch and opens one pull request for it. Use when the developer asks to work, implement, build, or do one or more tasks by key, to start or resume a batch, or says "merged" after merging a batch's pull request.
allowed-tools: Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/board.py*), Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py *)
model: sonnet
---

# work

Implements the given tasks in order, one subagent per task, and stops only on a real blocker. The Kaneo project and repo settings are in `.sdlc/config.toml`. The repo's rules are in `CLAUDE.md`, and its guidelines are in `docs/guidelines/`.

## Hard rules

- Never push to the default branch, and never merge a pull request. The developer merges.
- Each task is implemented in a fresh subagent with `model: sonnet`. Keep only its summary; don't read its diff into this session.
- Kaneo is the batch's state. Read it before acting, so a new session resumes where the last one stopped.
- Read the board only with `python3 ${CLAUDE_PLUGIN_ROOT}/lib/board.py`. It prints one line per open task: key, status, title, labels, open blockers, and id.

## Stop

To stop, run the notify script, then say what you need, and end your turn:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/lib/notify.py --skill work --kind <ASK or STOP> --task <key> --text "<what's needed>" --link "<task or PR url>"
```

Use `ASK` for a question and `STOP` for anything else. Stop when:

- a task is blocked by an open task outside the batch, or later in it: stop before any work, so the developer can revise the batch
- a task's checks still fail after `quality_gate_attempts` honest fixes
- a decision is the developer's: an unclear criterion, a design choice, or a task that can't be done as written
- a task in the batch has the `manual` label: stop before any work, naming each, with no branch created and no task changed
- a task has a manual test marked `[blocks merge]`: commit it, push, open the pull request, then stop with where its steps are
- the next step is destructive or outward-facing, other than pushing the batch branch and opening its pull request

## Batch

1. Before any work, read the board, and find each task in the batch by its key. Skip tasks already in in-review or done. Stop, listing each problem, if any other task isn't in To Do or In Progress, or is blocked by a task that's outside the batch or later in it. A task missing from the board is done or archived; read it by number to tell which.
2. Branch: `<branch_prefix><number of the first task>-<short slug>`. If it exists locally or on the remote, check it out. Otherwise fetch, then branch from the up-to-date default branch.
3. For each remaining task, in the order given, start one subagent. Tell it the task key, and to:
   - set the task to in-progress, and implement it to its acceptance criteria and testing strategy
   - follow `CLAUDE.md` and the commit conventions, and read a `docs/guidelines/` file only when a step needs it
   - run the repo's checks (`test_command`, `lint_command`, `format_command`), fixing and re-running until they pass, at most `quality_gate_attempts` times
   - commit with the task key in the message, and never push
   - never ask the developer; return a blocker instead
   - return at most five lines: what changed, the checks' result, the commit, and any blocker or follow-up
4. After each subagent, check the commit exists. Then move the task to in-review with a comment: what changed, and any follow-up. On a blocker, stop.
5. After the last task, push the branch and open one pull request, unless one is open. Its title says what the batch does; its body lists each task's key and title with a line on what changed. Then stop, with `--link` set to the pull request.

## Merged

When the developer says "merged":

1. Check the pull request is merged. If not, stop.
2. Check out the default branch, pull, delete the batch branch, and `git fetch --prune`.
3. Move every task in the batch to done.
