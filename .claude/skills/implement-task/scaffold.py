#!/usr/bin/env python3
"""Deterministic scripting for the `implement-task` skill.

Same shape as `init-project`/`add-task`'s `scaffold.py`: `SKILL.md` owns everything
genuinely judgment-driven -- restating the plan, writing code/tests, deciding what's automatable,
composing commit/PR content, the bail-out call -- and every STOP. Each such step is paired with
exactly one call into this script for the mechanical git/gh/frontmatter/`sync` action that follows
it. Nothing here prompts interactively, and nothing here authors content (commit messages, PR
bodies) -- those arrive as already-composed strings.

Standard library only. Imports the repo's own `.tasks/bin/sync` by file path (the same technique
`tests/conftest.py` uses) rather than re-implementing frontmatter parsing/writing or "what does a
TODO line look like".
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType

_DONE_STATUSES = ("done", "wont-do")
_IN_FLIGHT_STATUSES = ("in-progress", "in-review")


# ---------------------------------------------------------------------------
# repo / sync module plumbing (same technique as add-task's scaffold.py)
# ---------------------------------------------------------------------------


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit("implement-task: not inside a git repository")
    return Path(result.stdout.strip())


def load_sync_module(tasks_root: Path) -> ModuleType:
    sync_path = tasks_root / "bin" / "sync"
    if not sync_path.is_file():
        raise SystemExit(f"implement-task: {sync_path} not found -- run `init-project` first")
    loader = SourceFileLoader("sync", str(sync_path))
    spec = importlib.util.spec_from_loader("sync", loader)
    module = importlib.util.module_from_spec(spec)
    # `sync` defines `@dataclass class Artifact`, which looks itself up via
    # `sys.modules[cls.__module__]` -- it must already be registered before
    # `exec_module` runs, or that lookup returns `None` and crashes.
    sys.modules["sync"] = module
    loader.exec_module(module)
    return module


def _run_sync(sync_path: Path, *extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(sync_path), *extra_args], capture_output=True, text=True
    )


def load_guardrails_module() -> ModuleType:
    """`.tasks/bin/guardrails.py`, reusing an already-loaded copy (e.g. `tests/conftest.py`'s)
    if present so the hook path and this skill never run two independent instances of the same
    module. Resolved from this script's own location, not any `cwd` argument -- `init-project`
    vendors `scaffold.py` and `guardrails.py` at the same fixed relative offset in every target
    repo, so this holds both here and once vendored.
    """
    if "guardrails" in sys.modules:
        return sys.modules["guardrails"]
    guardrails_path = Path(__file__).resolve().parents[3] / ".tasks" / "bin" / "guardrails.py"
    loader = SourceFileLoader("guardrails", str(guardrails_path))
    spec = importlib.util.spec_from_loader("guardrails", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["guardrails"] = module
    loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# git/gh wrappers -- thin, side-effecting; kept separate from the pure
# decision functions below so those can be unit-tested without real git/gh
# ---------------------------------------------------------------------------


def dirty_files(cwd: Path, ignore: tuple[str, ...] = ()) -> list[str]:
    """Paths `git status` reports as dirty in `cwd`, excluding `ignore` -- the project's own
    `ignored_paths` (`.tasks/config.md`), a carve-out for paths like a personal prompt scratchpad
    that aren't part of any task's actual work. Thin delegate to
    `guardrails.dirty_tree_violation`, which owns the actual `git status`/porcelain-parsing logic
    (and its fail-open-on-broken-git behavior) so it's defined once for both the hook path and
    this skill.
    """
    return load_guardrails_module().dirty_tree_violation(cwd, tuple(ignore))


def current_branch(cwd: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def local_branch_exists(cwd: Path, branch: str) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=cwd
    )
    return result.returncode == 0


def remote_branch_exists(cwd: Path, remote: str, branch: str) -> bool:
    result = subprocess.run(
        ["git", "ls-remote", "--exit-code", "--heads", remote, branch],
        cwd=cwd, capture_output=True, text=True,
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Pure functions -- the four AC7 asks unit tests for, plus their small
# supporting helpers. No git/gh/filesystem I/O in here.
# ---------------------------------------------------------------------------


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise ValueError(f"cannot derive a slug from title {title!r}")
    return slug


def compute_branch_name(branch_prefix: str, task_id: str, slug: str) -> str:
    """`<branch_prefix><id-number>-<slug>` (the workflow's branch-naming convention).

    `slug` is not re-derived from the task's full title here -- real task slugs are
    short, hand-chosen summaries (e.g. a title like "implement-task skill: four
    phases, STOP markers, resumable, bail-out" might get the branch
    `task-NNN-skill-implement-task`), not a mechanical `slugify(title)`. This
    function only does the formatting; callers supply the slug -- from an existing
    task's `branch:` field when one's already set (the normal case, since `add-task`
    always sets it at creation), or `slugify(title)` as a last-resort fallback.
    """
    number = task_id.split("-", 1)[1]
    return f"{branch_prefix}{number}-{slug}"


def pick_top_unblocked(board_text: str, sync_mod: ModuleType) -> dict:
    """The TODO-picking rule: read `BOARD.md`'s TODO list top to bottom,
    skip any line carrying `⛔ blocked_by ...`, take the first one that doesn't.
    Returns `{"task_id": id-or-None, "skipped": [{"id", "reason"}, ...]}` -- `None`
    if every TODO task is blocked (or the list is empty).
    """
    heading = sync_mod._TODO_HEADING
    if heading not in board_text:
        raise ValueError("no '## TODO' heading found in BOARD.md")
    start = board_text.index(heading) + len(heading)
    next_heading = board_text.find("\n## ", start - 1)
    end = len(board_text) if next_heading == -1 else next_heading + 1
    lines = [line for line in board_text[start:end].splitlines() if sync_mod._TODO_LINE_RE.match(line)]

    skipped = []
    for line in lines:
        task_id = sync_mod._TODO_LINE_RE.match(line).group(1)
        if "⛔" in line:
            skipped.append({"id": task_id, "reason": line.split("⛔", 1)[1].strip()})
            continue
        return {"task_id": task_id, "skipped": skipped}
    return {"task_id": None, "skipped": skipped}


def stop_required_for_phase1(*, batch_mode: bool) -> bool:
    """Phase 1's announce-vs-block decision, for the autonomous batch mode: outside a batch, the
    plan restatement always ends in a hard STOP (unchanged). Inside an approved batch, the batch
    selection itself was the approval, so the plan is printed for the record but nothing blocks on
    it -- the caller proceeds straight into phase 2.
    """
    return not batch_mode


def record_outcome(outcomes: list[dict], entry: dict) -> list[dict]:
    """Append one task's outcome record to a batch run's accumulator, in encounter order. Returns
    a new list -- `outcomes` itself is never mutated, so a caller can keep holding the prior list.

    `entry` must carry `task_id`/`title`/`status` (a `link` of `None` is fine -- not every status,
    e.g. a task still `in-progress`, has a PR/merge-commit link yet); missing any of the first
    three raises `ValueError` naming it, since a silently incomplete row would make the
    end-of-batch summary misleading.
    """
    for key in ("task_id", "title", "status"):
        if key not in entry:
            raise ValueError(f"outcome entry missing required key: {key!r}")
    return [*outcomes, dict(entry)]


def render_outcome_table(outcomes: list[dict]) -> str:
    """The end-of-batch summary table: `Task | Title | Status | PR/Merge`, one row per outcome in
    accumulation order. An empty batch still renders a header-only table rather than raising --
    the caller always has something to print. A missing/`None` `link` renders as `—` (halted
    before a PR ever opened, or a task the batch skipped).
    """
    lines = ["| Task | Title | Status | PR/Merge |", "|---|---|---|---|"]
    for entry in outcomes:
        link = entry.get("link") or "—"
        lines.append(f"| {entry['task_id']} | {entry['title']} | {entry['status']} | {link} |")
    return "\n".join(lines)


_ISOLATED_INTERRUPT_KINDS = frozenset({
    "needs_clarification", "unexpected_blocker", "quality_gate_failure", "guardrail_denial",
})
_SYSTEMIC_INTERRUPT_KINDS = frozenset({"infra_failure"})


def interrupt_routing(kind: str) -> dict:
    """Route one of batch mode's five interrupt conditions: `needs_clarification`/
    `unexpected_blocker`/`quality_gate_failure`/`guardrail_denial` are isolated -- bail out this
    one task and continue the batch at its next task; `infra_failure` is systemic -- halt the
    whole batch before starting anything else, since the tooling itself (not this task's code) is
    broken and every remaining task would hit the same wall. Raises `ValueError` on any other
    `kind`.
    """
    if kind in _ISOLATED_INTERRUPT_KINDS:
        return {"routing": "isolated", "continue_batch": True}
    if kind in _SYSTEMIC_INTERRUPT_KINDS:
        return {"routing": "systemic", "continue_batch": False}
    raise ValueError(f"unknown interrupt kind: {kind!r}")


def resume_phase(*, in_flight: dict | None, working_tree_dirty: bool, gh_pr_state: str | None) -> dict:
    """The resume-detection table, as a pure function of already-gathered
    state (no git/gh calls in here -- see `cmd_resume_state` for the real gathering).

    `in_flight` is `None` (no in-progress/in-review task at all) or
    `{"id", "status", "pr", "merge_commit", "branch_exists"}` for the one task
    currently in flight. `gh_pr_state` is `"OPEN"` | `"MERGED"` | `"CLOSED"` | `None`
    (not fetched -- no `pr` yet, or `status` isn't `in-review`).

    Returns `{"phase": ..., "task_id": ..., "detail": ...}` -- `phase` is one of
    `phase1` | `phase2` | `phase3` | `phase4_open` | `phase4_merged` |
    `phase4_closed_not_merged` | `ambiguous` (with `detail` explaining why on the
    last one; surface this to the human rather than guess).
    """
    if in_flight is None or not in_flight.get("branch_exists"):
        return {"phase": "phase1"}

    task_id = in_flight["id"]
    status = in_flight["status"]
    pr = in_flight.get("pr")

    if status == "in-progress":
        if pr:
            return {"phase": "ambiguous", "task_id": task_id, "detail": "in-progress but pr is already set"}
        if working_tree_dirty:
            return {"phase": "phase2", "task_id": task_id}
        return {"phase": "phase3", "task_id": task_id}

    if status == "in-review":
        if not pr:
            return {"phase": "ambiguous", "task_id": task_id, "detail": "in-review with no pr recorded"}
        if gh_pr_state == "OPEN":
            return {"phase": "phase4_open", "task_id": task_id}
        if gh_pr_state == "MERGED":
            if in_flight.get("merge_commit"):
                return {
                    "phase": "ambiguous",
                    "task_id": task_id,
                    "detail": "merge_commit already recorded but status is still in-review",
                }
            return {"phase": "phase4_merged", "task_id": task_id}
        if gh_pr_state == "CLOSED":
            return {"phase": "phase4_closed_not_merged", "task_id": task_id}
        return {"phase": "ambiguous", "task_id": task_id, "detail": f"unexpected gh pr state {gh_pr_state!r}"}

    return {"phase": "ambiguous", "task_id": task_id, "detail": f"unexpected task status {status!r}"}


def decide_push_args(
    *, current_branch: str, task_branch: str, default_branch: str, remote: str, force: bool
) -> list[str]:
    """The `git push` argument list for phase 3's push -- plain, or
    `--force-with-lease` when `force` (a rebase actually rewrote already-pushed
    history). Raises `ValueError` -- refusing to build the command at all -- if
    `current_branch` isn't `task_branch` (guardrail: force-with-lease, and this push
    in general, only on the task's own branch) or if that branch is the default
    branch (never push task work to `default_branch`).
    """
    if current_branch != task_branch:
        raise ValueError(
            f"refusing to push: current branch {current_branch!r} is not this task's own "
            f"branch {task_branch!r}"
        )
    if current_branch == default_branch:
        raise ValueError(f"refusing to push task work to the default branch {default_branch!r}")
    args = ["push"]
    if force:
        args.append("--force-with-lease")
    args += [remote, current_branch]
    return args


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_resume_state(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    config = sync_mod.load_config(tasks_root)
    remote = config.get("remote", "origin")
    ignored_paths = tuple(config.get("ignored_paths") or [])

    artifacts = sync_mod.discover(tasks_root)
    in_flight_tasks = [
        a for a in artifacts.values() if a.kind == "task" and a.fields.get("status") in _IN_FLIGHT_STATUSES
    ]
    if len(in_flight_tasks) > 1:
        print(json.dumps({
            "phase": "ambiguous",
            "detail": f"multiple in-flight tasks: {', '.join(sorted(t.id for t in in_flight_tasks))}",
        }))
        return 0

    in_flight = None
    if in_flight_tasks:
        task = in_flight_tasks[0]
        branch = task.fields.get("branch")
        exists = bool(branch) and (
            local_branch_exists(root, branch) or remote_branch_exists(root, remote, branch)
        )
        in_flight = {
            "id": task.id,
            "status": task.fields.get("status"),
            "pr": task.fields.get("pr"),
            "merge_commit": task.fields.get("merge_commit"),
            "branch_exists": exists,
        }

    working_dirty = bool(dirty_files(root, ignore=ignored_paths))

    gh_pr_state = None
    if in_flight and in_flight["status"] == "in-review" and in_flight["pr"]:
        view = subprocess.run(
            ["gh", "pr", "view", in_flight["pr"], "--json", "state,mergeCommit"],
            cwd=root, capture_output=True, text=True,
        )
        if view.returncode != 0:
            print(json.dumps({
                "phase": "ambiguous",
                "task_id": in_flight["id"],
                "detail": f"gh pr view failed: {view.stderr.strip()}",
            }))
            return 0
        gh_pr_state = json.loads(view.stdout)["state"]

    result = resume_phase(in_flight=in_flight, working_tree_dirty=working_dirty, gh_pr_state=gh_pr_state)
    print(json.dumps(result))
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    answers = json.loads(Path(args.answers).read_text())
    task_id = answers.get("task_id")
    batch_mode = bool(answers.get("batch_mode", False))

    config = sync_mod.load_config(tasks_root)
    remote = config.get("remote", "origin")
    default_branch = config.get("default_branch", "main")
    branch_prefix = config.get("branch_prefix", "task-")
    ignored_paths = tuple(config.get("ignored_paths") or [])

    dirty = dirty_files(root, ignore=ignored_paths)
    if dirty:
        print(f"implement-task: working tree is dirty: {', '.join(dirty)}", file=sys.stderr)
        return 2

    skipped: list[dict] = []
    if task_id is None:
        board_text = (tasks_root / "BOARD.md").read_text()
        picked = pick_top_unblocked(board_text, sync_mod)
        skipped = picked["skipped"]
        task_id = picked["task_id"]
        if task_id is None:
            print("implement-task: no unblocked TODO task found", file=sys.stderr)
            return 2

    artifacts = sync_mod.discover(tasks_root)
    if task_id not in artifacts or artifacts[task_id].kind != "task":
        print(f"implement-task: {task_id} not found", file=sys.stderr)
        return 2
    task = artifacts[task_id]
    if task.fields.get("status") != "todo":
        print(
            f"implement-task: {task_id} status is {task.fields.get('status')!r}, not 'todo' -- "
            "this looks like a resume, not a fresh start; use `resume-state` instead",
            file=sys.stderr,
        )
        return 2
    outstanding = [
        b for b in (task.fields.get("blocked_by") or [])
        if b not in artifacts or artifacts[b].fields.get("status") not in _DONE_STATUSES
    ]
    if outstanding:
        print(f"implement-task: {task_id} is still blocked by: {', '.join(outstanding)}", file=sys.stderr)
        return 2

    branch = task.fields.get("branch") or compute_branch_name(
        branch_prefix, task_id, slugify(task.fields.get("title", task_id))
    )

    fetch = subprocess.run(["git", "fetch", remote], cwd=root, capture_output=True, text=True)
    if fetch.returncode != 0:
        print(fetch.stderr, file=sys.stderr)
        return fetch.returncode
    checkout = subprocess.run(
        ["git", "checkout", "-b", branch, f"{remote}/{default_branch}"],
        cwd=root, capture_output=True, text=True,
    )
    if checkout.returncode != 0:
        print(checkout.stderr, file=sys.stderr)
        return checkout.returncode

    task.fields["status"] = "in-progress"
    task.fields["branch"] = branch
    task.write()

    sync_result = _run_sync(tasks_root / "bin" / "sync")
    if sync_result.returncode != 0:
        print(sync_result.stdout)
        print(sync_result.stderr, file=sys.stderr)
        return sync_result.returncode

    print(json.dumps({
        "task_id": task_id, "branch": branch, "skipped": skipped,
        "stop_required": stop_required_for_phase1(batch_mode=batch_mode),
    }))
    return 0


def cmd_wrap_up(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    answers = json.loads(Path(args.answers).read_text())
    task_id = answers["task_id"]
    paths = answers["paths"]

    artifacts = sync_mod.discover(tasks_root)
    if task_id not in artifacts:
        print(f"implement-task: {task_id} not found", file=sys.stderr)
        return 2
    task = artifacts[task_id]
    branch = task.fields.get("branch")
    if not branch:
        print(f"implement-task: {task_id} has no branch set", file=sys.stderr)
        return 2

    cur = current_branch(root)
    if cur != branch:
        print(
            f"implement-task: current branch {cur!r} is not {task_id}'s branch {branch!r}",
            file=sys.stderr,
        )
        return 2

    config = sync_mod.load_config(tasks_root)
    remote = config.get("remote", "origin")
    default_branch = config.get("default_branch", "main")
    rebase_before_pr = config.get("rebase_before_pr", True)
    ignored_paths = tuple(config.get("ignored_paths") or [])
    format_command = config.get("format_command")

    add_result = subprocess.run(["git", "add", "-A", "--", *paths], cwd=root, capture_output=True, text=True)
    if add_result.returncode != 0:
        print(add_result.stderr, file=sys.stderr)
        return add_result.returncode

    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root).returncode != 0:
        commit_result = subprocess.run(
            ["git", "commit", "-m", answers["commit_message"]], cwd=root, capture_output=True, text=True
        )
        if commit_result.returncode != 0:
            print(commit_result.stderr, file=sys.stderr)
            return commit_result.returncode

    remote_existed_before_rebase = remote_branch_exists(root, remote, branch)

    if rebase_before_pr:
        all_dirty = dirty_files(root, ignore=())
        dirty_ignored_paths = [p for p in ignored_paths if p in all_dirty]
        stashed = False
        if dirty_ignored_paths:
            # `-u`: an ignored path may never have been committed yet (git otherwise refuses to
            # stash a pathspec matching only untracked files).
            stash_result = subprocess.run(
                ["git", "stash", "push", "-u", "-m", "ignored-paths wip", "--", *dirty_ignored_paths],
                cwd=root, capture_output=True, text=True,
            )
            if stash_result.returncode != 0:
                print(stash_result.stderr, file=sys.stderr)
                return stash_result.returncode
            stashed = True

        fetch = subprocess.run(["git", "fetch", remote], cwd=root, capture_output=True, text=True)
        if fetch.returncode != 0:
            print(fetch.stderr, file=sys.stderr)
            return fetch.returncode

        rebase_result = subprocess.run(
            ["git", "rebase", f"{remote}/{default_branch}"], cwd=root, capture_output=True, text=True
        )
        if rebase_result.returncode != 0:
            print(rebase_result.stdout)
            print(rebase_result.stderr, file=sys.stderr)
            print(
                "implement-task: rebase conflict -- resolve it by hand, then `git rebase --continue`"
                + (" and `git stash pop`" if stashed else "") + ", and re-run wrap-up",
                file=sys.stderr,
            )
            return rebase_result.returncode

        if stashed:
            pop_result = subprocess.run(["git", "stash", "pop"], cwd=root, capture_output=True, text=True)
            if pop_result.returncode != 0:
                print(pop_result.stderr, file=sys.stderr)
                return pop_result.returncode

    amended = False
    if format_command:
        format_result = subprocess.run(
            format_command, shell=True, cwd=root, capture_output=True, text=True
        )
        if format_result.returncode != 0:
            print(format_result.stdout)
            print(format_result.stderr, file=sys.stderr)
            print(
                f"implement-task: format_command {format_command!r} exited "
                f"{format_result.returncode} -- STOP, resolve by hand and re-run wrap-up",
                file=sys.stderr,
            )
            return format_result.returncode

        formatted = dirty_files(root, ignore=ignored_paths)
        if formatted:
            format_add = subprocess.run(
                ["git", "add", "-A", "--", *formatted], cwd=root, capture_output=True, text=True
            )
            if format_add.returncode != 0:
                print(format_add.stderr, file=sys.stderr)
                return format_add.returncode
            amend_result = subprocess.run(
                ["git", "commit", "--amend", "--no-edit"], cwd=root, capture_output=True, text=True
            )
            if amend_result.returncode != 0:
                print(amend_result.stderr, file=sys.stderr)
                return amend_result.returncode
            amended = True

    push_args = decide_push_args(
        current_branch=current_branch(root),
        task_branch=branch,
        default_branch=default_branch,
        remote=remote,
        # An amend rewrites history exactly like a rebase would -- if this branch was already
        # pushed by an earlier, interrupted `wrap-up` run, a plain push would now be rejected.
        force=(rebase_before_pr or amended) and remote_existed_before_rebase,
    )
    push_result = subprocess.run(["git", *push_args], cwd=root, capture_output=True, text=True)
    if push_result.returncode != 0:
        print(push_result.stderr, file=sys.stderr)
        return push_result.returncode

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as body_file:
        body_file.write(answers["pr_body"])
        body_path = Path(body_file.name)
    try:
        pr_create = subprocess.run(
            ["gh", "pr", "create", "--title", answers["pr_title"], "--body-file", str(body_path)],
            cwd=root, capture_output=True, text=True,
        )
    finally:
        body_path.unlink(missing_ok=True)
    if pr_create.returncode != 0:
        print(pr_create.stderr, file=sys.stderr)
        return pr_create.returncode
    pr_url = pr_create.stdout.strip().splitlines()[-1]

    task.fields["pr"] = pr_url
    task.fields["status"] = "in-review"
    task.write()

    sync_result = _run_sync(tasks_root / "bin" / "sync")
    if sync_result.returncode != 0:
        print(sync_result.stdout)
        print(sync_result.stderr, file=sys.stderr)
        return sync_result.returncode

    # Commit+push the pr:/status: in-review update and sync's regenerated board/epic --
    # otherwise this sits as uncommitted local drift and the PR's own diff never reflects
    # it (found for real: `wrap-up` reported success, but `git status` immediately
    # after showed this exact change uncommitted).
    bookkeeping_add = subprocess.run(["git", "add", "--", ".tasks"], cwd=root, capture_output=True, text=True)
    if bookkeeping_add.returncode != 0:
        print(bookkeeping_add.stderr, file=sys.stderr)
        return bookkeeping_add.returncode
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root).returncode != 0:
        bookkeeping_commit = subprocess.run(
            ["git", "commit", "-m", answers["bookkeeping_commit_message"]],
            cwd=root, capture_output=True, text=True,
        )
        if bookkeeping_commit.returncode != 0:
            print(bookkeeping_commit.stderr, file=sys.stderr)
            return bookkeeping_commit.returncode
        bookkeeping_push_args = decide_push_args(
            current_branch=current_branch(root), task_branch=branch,
            default_branch=default_branch, remote=remote, force=False,
        )
        bookkeeping_push = subprocess.run(
            ["git", *bookkeeping_push_args], cwd=root, capture_output=True, text=True
        )
        if bookkeeping_push.returncode != 0:
            print(bookkeeping_push.stderr, file=sys.stderr)
            return bookkeeping_push.returncode

    checks = subprocess.run(["gh", "pr", "checks", pr_url], cwd=root, capture_output=True, text=True)
    print(json.dumps({
        "pr_url": pr_url,
        "checks_output": checks.stdout + checks.stderr,
        "checks_exit": checks.returncode,
    }))
    return 0


def cmd_finish_merge(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    answers = json.loads(Path(args.answers).read_text())
    task_id = answers["task_id"]

    artifacts = sync_mod.discover(tasks_root)
    if task_id not in artifacts:
        print(f"implement-task: {task_id} not found", file=sys.stderr)
        return 2
    task = artifacts[task_id]
    pr = task.fields.get("pr")
    if not pr:
        print(f"implement-task: {task_id} has no pr recorded", file=sys.stderr)
        return 2

    view = subprocess.run(
        ["gh", "pr", "view", pr, "--json", "state,mergeCommit"], cwd=root, capture_output=True, text=True
    )
    if view.returncode != 0:
        print(view.stderr, file=sys.stderr)
        return view.returncode
    data = json.loads(view.stdout)
    state = data["state"]
    if state != "MERGED":
        checks = subprocess.run(["gh", "pr", "checks", pr], cwd=root, capture_output=True, text=True)
        print(json.dumps({
            "merged": False,
            "state": state,
            "checks_output": checks.stdout + checks.stderr,
        }))
        return 0

    merge_commit = data["mergeCommit"]["oid"]
    config = sync_mod.load_config(tasks_root)
    remote = config.get("remote", "origin")
    default_branch = config.get("default_branch", "main")
    delete_after = config.get("delete_branch_after_merge", True)
    branch = task.fields.get("branch")

    checkout = subprocess.run(["git", "checkout", default_branch], cwd=root, capture_output=True, text=True)
    if checkout.returncode != 0:
        print(checkout.stderr, file=sys.stderr)
        return checkout.returncode
    pull = subprocess.run(["git", "pull", "--ff-only"], cwd=root, capture_output=True, text=True)
    if pull.returncode != 0:
        print(pull.stderr, file=sys.stderr)
        return pull.returncode

    task.fields["status"] = "done"
    task.fields["merge_commit"] = merge_commit
    task.write()

    sync_result = _run_sync(tasks_root / "bin" / "sync")
    if sync_result.returncode != 0:
        print(sync_result.stdout)
        print(sync_result.stderr, file=sys.stderr)
        return sync_result.returncode

    if delete_after and branch:
        del_local = subprocess.run(["git", "branch", "-d", branch], cwd=root, capture_output=True, text=True)
        if del_local.returncode != 0:
            # a squash merge isn't a fast-forward ancestor of local HEAD; `gh pr
            # view` already confirmed it's genuinely MERGED, so force-deleting the
            # local branch is safe.
            del_local = subprocess.run(["git", "branch", "-D", branch], cwd=root, capture_output=True, text=True)
            if del_local.returncode != 0:
                print(del_local.stderr, file=sys.stderr)
                return del_local.returncode
        del_remote = subprocess.run(
            ["git", "push", remote, "--delete", branch], cwd=root, capture_output=True, text=True
        )
        if del_remote.returncode != 0 and "remote ref does not exist" not in del_remote.stderr:
            print(del_remote.stderr, file=sys.stderr)
            return del_remote.returncode

    check_result = _run_sync(tasks_root / "bin" / "sync", "check")
    if check_result.returncode != 0:
        print(check_result.stdout)
        print(check_result.stderr, file=sys.stderr)
        return check_result.returncode

    if current_branch(root) != default_branch:
        print(
            f"implement-task: not on {default_branch!r} -- refusing to run the bookkeeping commit",
            file=sys.stderr,
        )
        return 2
    add_result = subprocess.run(["git", "add", "--", ".tasks"], cwd=root, capture_output=True, text=True)
    if add_result.returncode != 0:
        print(add_result.stderr, file=sys.stderr)
        return add_result.returncode
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=root).returncode != 0:
        commit_result = subprocess.run(
            ["git", "commit", "-m", answers["bookkeeping_commit_message"]],
            cwd=root, capture_output=True, text=True,
        )
        if commit_result.returncode != 0:
            print(commit_result.stderr, file=sys.stderr)
            return commit_result.returncode
        push_result = subprocess.run(
            ["git", "push", remote, default_branch], cwd=root, capture_output=True, text=True
        )
        if push_result.returncode != 0:
            print(push_result.stderr, file=sys.stderr)
            return push_result.returncode

    print(json.dumps({"merged": True, "merge_commit": merge_commit}))
    return 0


def cmd_bail_out(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    answers = json.loads(Path(args.answers).read_text())
    task_id = answers["task_id"]
    status = answers["status"]
    if status not in ("todo", "blocked"):
        print(f"implement-task: bail-out status must be 'todo' or 'blocked', got {status!r}", file=sys.stderr)
        return 2

    artifacts = sync_mod.discover(tasks_root)
    if task_id not in artifacts:
        print(f"implement-task: {task_id} not found", file=sys.stderr)
        return 2
    task = artifacts[task_id]
    task.fields["status"] = status
    task.write()

    sync_result = _run_sync(tasks_root / "bin" / "sync")
    if sync_result.returncode != 0:
        print(sync_result.stdout)
        print(sync_result.stderr, file=sys.stderr)
        return sync_result.returncode

    print(json.dumps({"task_id": task_id, "status": status}))
    return 0


def cmd_record_outcome(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    try:
        outcomes = record_outcome(answers.get("outcomes") or [], answers["entry"])
    except ValueError as exc:
        print(f"implement-task: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"outcomes": outcomes}))
    return 0


def cmd_render_outcome_table(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    table = render_outcome_table(answers.get("outcomes") or [])
    print(json.dumps({"table": table}))
    return 0


def cmd_classify_interrupt(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    try:
        result = interrupt_routing(answers["kind"])
    except ValueError as exc:
        print(f"implement-task: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0


def cmd_gh_auth_status(args: argparse.Namespace) -> int:
    result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    return result.returncode


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scaffold.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("resume-state", help="determine which phase to resume at")
    subparsers.add_parser("gh-auth-status", help="wrap `gh auth status`")

    for name, help_text in (
        ("start", "phase 1: pick/validate a task, branch, set status+branch, run sync"),
        ("wrap-up", "phase 3: commit, rebase, push, gh pr create, record pr, run sync"),
        ("finish-merge", "phase 4: observe the merge, record it, archive, clean up branches"),
        ("bail-out", "set status back to todo/blocked and run sync"),
        ("record-outcome", "batch mode: append one task's outcome to the accumulator"),
        ("render-outcome-table", "batch mode: render the end-of-batch outcome table"),
        ("classify-interrupt", "batch mode: route an interrupt kind to isolated/systemic"),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("answers", help="path to a JSON file with this subcommand's inputs")

    args = parser.parse_args(argv)
    dispatch = {
        "resume-state": cmd_resume_state,
        "gh-auth-status": cmd_gh_auth_status,
        "start": cmd_start,
        "wrap-up": cmd_wrap_up,
        "finish-merge": cmd_finish_merge,
        "bail-out": cmd_bail_out,
        "record-outcome": cmd_record_outcome,
        "render-outcome-table": cmd_render_outcome_table,
        "classify-interrupt": cmd_classify_interrupt,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
