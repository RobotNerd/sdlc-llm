#!/usr/bin/env python3
"""guardrails — the shared logic behind this workflow's structurally-enforced rules.

One module holds every guardrail as a small function taking explicit inputs (a command
string, the working directory, config values) and returning a `GuardrailResult` — never
raising, never touching anything but `git`'s own read-only plumbing. Both the `PreToolUse`
hook script (`.claude/hooks/pretooluse_bash.py`) and any skill script that wants the same
check call into these functions directly, so the rule is defined once.

Covers, today:

- `gh pr merge` — denied unless a future critic-gated marker is present (none can exist yet;
  see `check_gh_pr_merge`'s docstring).
- `git push` of task work to the project's `default_branch` — denied unless every path it
  would introduce is board-managed (`BOARD.md`, `EPIC-*.md`, `.tasks/archive/**`, or a task
  file whose only changed frontmatter fields are `status`/`merge_commit`/`pr`).
- `git push --force` misuse — bare `--force` is always denied; `--force-with-lease` is denied
  on any branch that isn't the currently `in-progress` task's own.

It imports nothing outside the Python standard library (plus `sync`, its sibling in this same
directory), to stay dependency-free for any project it's vendored into.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
from dataclasses import dataclass
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType


@dataclass
class GuardrailResult:
    allow: bool
    reason: str = ""


def _load_sync() -> ModuleType:
    """`sync` (no `.py` suffix) can't be found by normal import machinery -- load it by file
    path, reusing an already-loaded copy (e.g. the test suite's `conftest.py`) if present so
    two independently-loaded copies never coexist.
    """
    if "sync" in sys.modules:
        return sys.modules["sync"]
    sync_path = Path(__file__).resolve().parent / "sync"
    loader = SourceFileLoader("sync", str(sync_path))
    spec = importlib.util.spec_from_loader("sync", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync"] = module
    loader.exec_module(module)
    return module


def load_project_config(cwd: Path) -> dict:
    """`.tasks/config.md`'s fields for the project rooted at `cwd` -- `{}` if it doesn't
    exist yet (a repo mid-bootstrap, or a test fixture that doesn't need one).
    """
    return _load_sync().load_config(cwd / ".tasks")


# ---------------------------------------------------------------------------
# Shell-command parsing -- deliberately not a full shell parser. This is a backstop for a
# cooperative-but-fallible agent running ordinary git/gh commands, not a security boundary
# against deliberately obfuscated input.
# ---------------------------------------------------------------------------


_SEGMENT_SPLIT_RE = re.compile(r"&&|\|\||[;|]")


def _split_command_segments(command: str) -> list[str]:
    """`command` broken on unquoted `&&`/`||`/`;`/`|` -- good enough to find a `git push` or
    `gh pr merge` anywhere in a chained command, without a real shell grammar.
    """
    return [seg.strip() for seg in _SEGMENT_SPLIT_RE.split(command) if seg.strip()]


def _safe_split(segment: str) -> list[str]:
    import shlex

    try:
        return shlex.split(segment)
    except ValueError:
        return []


@dataclass
class ParsedPush:
    remote: str | None
    branch: str | None
    force: str | None  # None | "bare" | "with-lease"


def _parse_git_push(command: str) -> ParsedPush | None:
    """The first `git push` invocation found in `command`, or `None` if there isn't one."""
    for segment in _split_command_segments(command):
        tokens = _safe_split(segment)
        if len(tokens) < 2 or tokens[0] != "git" or tokens[1] != "push":
            continue
        force: str | None = None
        positional: list[str] = []
        for tok in tokens[2:]:
            if tok == "--force-with-lease" or tok.startswith("--force-with-lease="):
                force = "with-lease"
            elif tok in ("--force", "-f"):
                force = "bare"
            elif tok.startswith("-"):
                continue
            else:
                positional.append(tok)
        remote = positional[0] if positional else None
        branch = None
        if len(positional) > 1:
            # `<local-ref>:<remote-ref>` -- the *remote* side (after the colon) is what
            # actually names the branch being pushed to; a bare ref with no colon pushes to
            # the same-named branch on the remote.
            token = positional[1]
            branch = token.split(":", 1)[1] if ":" in token else token
            branch = branch or None  # `origin :some-branch` deletes -- nothing to compare here
        return ParsedPush(remote=remote, branch=branch, force=force)
    return None


_GH_PR_MERGE_RE = re.compile(r"(?:^|[;&|]\s*)gh\s+pr\s+merge\b")


def _is_gh_pr_merge(command: str) -> bool:
    return bool(_GH_PR_MERGE_RE.search(command))


def _current_branch(cwd: Path) -> str | None:
    result = subprocess.run(
        ["git", "branch", "--show-current"], cwd=cwd, capture_output=True, text=True
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


# ---------------------------------------------------------------------------
# Guardrail 1: `gh pr merge`
# ---------------------------------------------------------------------------


def check_gh_pr_merge(command: str, marker_present: bool = False) -> GuardrailResult:
    """Deny `gh pr merge` unless `marker_present` is `True`.

    `marker_present` is the hook point for a future opt-in, critic-gated, capped auto-merge
    path -- once that's built, its own scripted merge step would be the only caller that can
    ever pass `True` here (a recorded critic approval, under that batch's merge cap). No such
    marker exists yet, and nothing today constructs one, so this denies every `gh pr merge`
    unconditionally in practice -- deliberately shaped as "deny unless marker present" rather
    than a bare unconditional deny, so that future work can wire in the real marker without
    this check's shape changing.
    """
    if not _is_gh_pr_merge(command):
        return GuardrailResult(allow=True)
    if marker_present:
        return GuardrailResult(allow=True)
    return GuardrailResult(
        allow=False,
        reason=(
            "`gh pr merge` is denied -- a human reviews and merges on GitHub; "
            "implement-task's phase 4 only observes and records an already-completed merge."
        ),
    )


# ---------------------------------------------------------------------------
# Guardrail 2: pushing task work to `default_branch`
# ---------------------------------------------------------------------------


_ALLOWED_TASK_FIELD_CHANGES = {"status", "merge_commit", "pr"}


def _is_unconditionally_board_path(rel_path: str) -> bool:
    if rel_path == ".tasks/BOARD.md":
        return True
    if rel_path.startswith(".tasks/archive/"):
        return True
    if rel_path.count("/") == 1 and rel_path.startswith(".tasks/"):
        name = rel_path.rsplit("/", 1)[-1]
        if re.fullmatch(r"EPIC-\d{3}-.*\.md", name):
            return True
    return False


def _is_task_file(rel_path: str) -> bool:
    if rel_path.count("/") != 1 or not rel_path.startswith(".tasks/"):
        return False
    name = rel_path.rsplit("/", 1)[-1]
    return bool(re.fullmatch(r"TASK-\d{3}-.*\.md", name))


def _git_show(cwd: Path, rev: str, rel_path: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{rev}:{rel_path}"], cwd=cwd, capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else None


def _task_file_only_bookkeeping_fields_changed(cwd: Path, ref: str, rel_path: str) -> bool:
    """`True` iff `rel_path` (a task file) differs between `ref` and the working tree's `HEAD`
    only in `_ALLOWED_TASK_FIELD_CHANGES` -- same set of fields, same order, same body, and
    every other field byte-identical. A file that can't be read at either revision is
    conservatively treated as a real change (not bookkeeping).
    """
    old_text = _git_show(cwd, ref, rel_path)
    new_text = _git_show(cwd, "HEAD", rel_path)
    if old_text is None or new_text is None:
        return False
    sync_mod = _load_sync()
    try:
        old_fields, old_body, old_order = sync_mod.parse_frontmatter(old_text)
        new_fields, new_body, new_order = sync_mod.parse_frontmatter(new_text)
    except Exception:
        return False
    if old_body != new_body or old_order != new_order or set(old_fields) != set(new_fields):
        return False
    changed = {k for k in old_fields if old_fields[k] != new_fields[k]}
    return changed <= _ALLOWED_TASK_FIELD_CHANGES


def _default_branch_push_violations(cwd: Path, remote: str, default_branch: str) -> list[str] | None:
    """Repo-relative paths a push to `default_branch` would introduce that fall outside the
    phase-4 bookkeeping pattern -- `[]` if every changed path is board-managed. `None` if the
    comparison couldn't be established at all (no such remote-tracking ref yet, network
    trouble fetching it, ...); the caller treats that as "can't tell, don't block on our own
    uncertainty."
    """
    fetch = subprocess.run(
        ["git", "fetch", remote, default_branch], cwd=cwd, capture_output=True, text=True
    )
    if fetch.returncode != 0:
        return None
    ref = f"{remote}/{default_branch}"
    diff = subprocess.run(
        ["git", "diff", "--name-status", f"{ref}...HEAD"], cwd=cwd, capture_output=True, text=True
    )
    if diff.returncode != 0:
        return None

    entries: list[tuple[str, str]] = []
    archived_now: set[str] = set()
    for line in diff.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        status, rel_path = parts[0], parts[-1]
        entries.append((status, rel_path))
        if rel_path.startswith(".tasks/archive/"):
            archived_now.add(rel_path.rsplit("/", 1)[-1])

    violations: list[str] = []
    for status, rel_path in entries:
        if _is_unconditionally_board_path(rel_path):
            continue
        if _is_task_file(rel_path):
            name = rel_path.rsplit("/", 1)[-1]
            if status == "D" and name in archived_now:
                continue  # moved into .tasks/archive/ -- the archive-side entry is itself allowed
            if status.startswith("M") and _task_file_only_bookkeeping_fields_changed(cwd, ref, rel_path):
                continue
        violations.append(rel_path)
    return violations


def check_push_to_default_branch(
    command: str, cwd: Path, default_branch: str, remote: str
) -> GuardrailResult:
    """Deny a `git push` whose target is `default_branch` unless every path it would
    introduce is the phase-4 bookkeeping pattern (`BOARD.md`, `EPIC-*.md`,
    `.tasks/archive/**`, or a task file's `status`/`merge_commit`/`pr` fields).
    """
    push = _parse_git_push(command)
    if push is None:
        return GuardrailResult(allow=True)
    target_branch = push.branch or _current_branch(cwd)
    if target_branch != default_branch:
        return GuardrailResult(allow=True)

    violations = _default_branch_push_violations(cwd, push.remote or remote, default_branch)
    if violations is None or not violations:
        return GuardrailResult(allow=True)
    return GuardrailResult(
        allow=False,
        reason=(
            f"`git push` to {default_branch!r} touches path(s) outside the phase-4 bookkeeping "
            f"pattern: {', '.join(sorted(violations))}. Only BOARD.md, EPIC-*.md, "
            f".tasks/archive/**, and a task file's status/merge_commit/pr fields may reach "
            f"{default_branch!r} directly -- everything else needs a PR."
        ),
    )


# ---------------------------------------------------------------------------
# Guardrail 3: force-push misuse
# ---------------------------------------------------------------------------


def _is_in_progress_task_branch(cwd: Path, branch: str) -> bool:
    sync_mod = _load_sync()
    try:
        artifacts = sync_mod.discover(cwd / ".tasks")
    except Exception:
        return False
    return any(
        art.kind == "task" and art.fields.get("status") == "in-progress" and art.fields.get("branch") == branch
        for art in artifacts.values()
    )


def check_force_push(command: str, cwd: Path, branch_prefix: str) -> GuardrailResult:
    """Deny a bare `--force` push outright; deny `--force-with-lease` on any branch that
    isn't the currently `in-progress` task's own `branch:`.
    """
    push = _parse_git_push(command)
    if push is None or push.force is None:
        return GuardrailResult(allow=True)
    if push.force == "bare":
        return GuardrailResult(
            allow=False,
            reason="bare `git push --force` is denied -- use `--force-with-lease`, and only on the current task's own branch.",
        )

    target_branch = push.branch or _current_branch(cwd)
    if target_branch and target_branch.startswith(branch_prefix) and _is_in_progress_task_branch(cwd, target_branch):
        return GuardrailResult(allow=True)
    return GuardrailResult(
        allow=False,
        reason=(
            f"`--force-with-lease` on {target_branch!r} is denied -- only allowed on the "
            "current in-progress task's own branch, immediately after a rebase."
        ),
    )


# ---------------------------------------------------------------------------
# Dispatcher -- what the `PreToolUse`/`Bash` hook script actually calls
# ---------------------------------------------------------------------------


def evaluate_bash_command(command: str, cwd: Path) -> GuardrailResult:
    """Run every guardrail above against `command`, in order, returning the first denial (or
    an allow if none fires). Loads `.tasks/config.md` itself so the hook script doesn't have to.
    """
    config = load_project_config(cwd)
    default_branch = config.get("default_branch") or "main"
    remote = config.get("remote") or "origin"
    branch_prefix = config.get("branch_prefix") or ""

    for result in (
        check_gh_pr_merge(command),
        check_push_to_default_branch(command, cwd, default_branch, remote),
        check_force_push(command, cwd, branch_prefix),
    ):
        if not result.allow:
            return result
    return GuardrailResult(allow=True)
