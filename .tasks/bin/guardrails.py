#!/usr/bin/env python3
"""guardrails — the shared logic behind this workflow's structurally-enforced rules.

One module holds every guardrail as a small function taking explicit inputs (a command
string or a tool call's `tool_input`, the working directory, config values) and returning a
`GuardrailResult` — never raising, never touching anything but `git`'s own read-only
plumbing and the file a tool call already names. Every `PreToolUse` hook script
(`.claude/hooks/pretooluse_bash.py`, `.claude/hooks/pretooluse_edit_write.py`) and any skill
script that wants the same check call into these functions directly, so the rule is defined
once.

Covers, today:

- `gh pr merge` — denied unless a future critic-gated marker is present (none can exist yet;
  see `check_gh_pr_merge`'s docstring).
- `git push` of task work to the project's `default_branch` — denied unless every path it
  would introduce is board-managed (`BOARD.md`, `EPIC-*.md`, `.tasks/archive/**`, or a task
  file whose only changed frontmatter fields are `status`/`merge_commit`/`pr`).
- `git push --force` misuse — bare `--force` is always denied; `--force-with-lease` is denied
  on any branch that isn't the currently `in-progress` task's own.
- An `Edit`/`Write` that would actually change a generated region's content, or remove its
  markers — denied regardless of which file carries the region.
- An `Edit`/`Write` that hand-sets an epic's `status` to anything but `wont-do` — denied;
  status is otherwise derived, never hand-set.
- `git checkout -b`/`git switch -c` (branch creation) — denied when the working tree is dirty
  outside `ignored_paths`, or when the new branch name doesn't conform to
  `<branch_prefix><NNN>-<slug>`.

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
# Guardrail 4: branch-creation gate (dirty tree, non-conforming name)
# ---------------------------------------------------------------------------


_BRANCH_NAME_RE_TEMPLATE = r"^{prefix}\d{{3}}-[a-z0-9]+(?:-[a-z0-9]+)*$"


def branch_name_violation(branch: str, branch_prefix: str) -> str | None:
    """`None` if `branch` matches `<branch_prefix><NNN>-<slug>` (the workflow's branch-naming
    convention -- see `compute_branch_name`); otherwise a reason string.
    """
    pattern = re.compile(_BRANCH_NAME_RE_TEMPLATE.format(prefix=re.escape(branch_prefix)))
    if pattern.fullmatch(branch):
        return None
    return (
        f"branch name {branch!r} doesn't match the required {branch_prefix!r} + 3-digit id + "
        "'-' + slug pattern"
    )


def dirty_tree_violation(cwd: Path, ignored_paths: tuple[str, ...]) -> list[str]:
    """Paths `git status` reports as dirty in `cwd`, excluding `ignored_paths` -- `[]` if the
    tree is clean modulo those paths. `--untracked-files=all` matters: without it, git
    collapses a brand-new, entirely untracked directory into one `?? dirname/` line instead of
    listing the file inside it, and an `ignored_paths` entry naming that file would then never
    match.
    """
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=cwd, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return []
    files = []
    for line in result.stdout.splitlines():
        path = line[3:].strip()
        if " -> " in path:  # rename: "old -> new"
            path = path.split(" -> ", 1)[1]
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1]
        if path not in ignored_paths:
            files.append(path)
    return files


_CHECKOUT_CREATE_FLAGS = ("-b", "-B")
_SWITCH_CREATE_FLAGS = ("-c", "-C")


def _parse_branch_create(command: str) -> str | None:
    """The new branch name from a `git checkout -b|-B <name>` or `git switch -c|-C <name>`
    invocation found anywhere in `command` -- `None` if there isn't one.
    """
    for segment in _split_command_segments(command):
        tokens = _safe_split(segment)
        if len(tokens) < 2 or tokens[0] != "git":
            continue
        if tokens[1] == "checkout":
            flags = _CHECKOUT_CREATE_FLAGS
        elif tokens[1] == "switch":
            flags = _SWITCH_CREATE_FLAGS
        else:
            continue
        for i, tok in enumerate(tokens[2:], start=2):
            if tok in flags and i + 1 < len(tokens):
                return tokens[i + 1]
    return None


def check_branch_create(
    command: str, cwd: Path, branch_prefix: str, ignored_paths: tuple[str, ...]
) -> GuardrailResult:
    """Deny `git checkout -b`/`git switch -c` (branch creation) when the working tree is
    dirty outside `ignored_paths`, or when the new branch name doesn't conform to
    `<branch_prefix><NNN>-<slug>`. Makes `implement-task` phase 1's existing preconditions
    structural instead of relying on the model checking them itself.
    """
    branch = _parse_branch_create(command)
    if branch is None:
        return GuardrailResult(allow=True)

    dirty = dirty_tree_violation(cwd, ignored_paths)
    if dirty:
        return GuardrailResult(
            allow=False,
            reason=(
                "branch creation is denied -- the working tree is dirty outside "
                f"`ignored_paths`: {', '.join(sorted(dirty))}. Commit or stash first."
            ),
        )

    reason = branch_name_violation(branch, branch_prefix)
    if reason:
        return GuardrailResult(allow=False, reason=reason)
    return GuardrailResult(allow=True)


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
    ignored_paths = tuple(config.get("ignored_paths") or [])

    for result in (
        check_gh_pr_merge(command),
        check_push_to_default_branch(command, cwd, default_branch, remote),
        check_force_push(command, cwd, branch_prefix),
        check_branch_create(command, cwd, branch_prefix, ignored_paths),
    ):
        if not result.allow:
            return result
    return GuardrailResult(allow=True)


# ---------------------------------------------------------------------------
# Guardrail 4: hand-editing a generated region
# ---------------------------------------------------------------------------


_REGION_NAMES_BY_BOARD = ("epics", "in-progress", "in-review", "blocked", "done")


def _region_names_for_path(name: str) -> tuple[str, ...]:
    """The `BEGIN:name`/`END:name` region names that can legitimately appear in a file
    named `name`, given this workflow's fixed set of generated regions.
    """
    if name == "BOARD.md":
        return _REGION_NAMES_BY_BOARD
    if re.fullmatch(r"EPIC-\d{3}-.*\.md", name):
        return ("children",)
    if re.fullmatch(r"SPEC-\d{3}-.*\.md", name):
        return ("epics",)
    return ()


def region_edit_violation(path_name: str, old_content: str, new_content: str) -> str | None:
    """The name of the first generated region whose content actually changed (or whose
    markers were removed entirely) between `old_content` and `new_content` for a file named
    `path_name` -- `None` if every region that exists in `old_content` still has identical
    content in `new_content`. Reuses `sync.find_region` directly rather than reimplementing
    region detection; a file with no regions of the given kind is never a violation.
    """
    sync_mod = _load_sync()
    for name in _region_names_for_path(path_name):
        try:
            old_span = sync_mod.find_region(old_content, name)
        except sync_mod.RegionError:
            continue
        if old_span is None:
            continue
        old_body = old_content[old_span.begin_end:old_span.end_start]
        try:
            new_span = sync_mod.find_region(new_content, name)
        except sync_mod.RegionError:
            new_span = None
        new_body = new_content[new_span.begin_end:new_span.end_start] if new_span else None
        if new_body != old_body:
            return name
    return None


# ---------------------------------------------------------------------------
# Guardrail 5: hand-editing an epic's status away from a derived value
# ---------------------------------------------------------------------------


def epic_status_edit_violation(path_name: str, old_content: str, new_content: str) -> str | None:
    """The new `status` value if `path_name` is an epic file and its frontmatter `status`
    changed to anything but `wont-do` between `old_content` and `new_content` -- `None`
    otherwise (unchanged, changed *to* `wont-do`, not an epic file, or unparseable).
    """
    if not re.fullmatch(r"EPIC-\d{3}-.*\.md", path_name):
        return None
    sync_mod = _load_sync()
    try:
        old_fields, _old_body, _old_order = sync_mod.parse_frontmatter(old_content)
        new_fields, _new_body, _new_order = sync_mod.parse_frontmatter(new_content)
    except Exception:
        return None
    old_status = old_fields.get("status")
    new_status = new_fields.get("status")
    if new_status != old_status and new_status != "wont-do":
        return new_status
    return None


# ---------------------------------------------------------------------------
# Edit/Write: computing the hypothetical "after" content, and the dispatcher
# ---------------------------------------------------------------------------


def _apply_edit(old_content: str, old_string: str, new_string: str, replace_all: bool) -> str | None:
    """The file content `Edit` would produce, or `None` if `old_string` isn't found (or
    isn't unique and `replace_all` wasn't given) -- callers treat that as "can't tell, don't
    block on our own uncertainty," matching how the tool call itself would refuse.
    """
    count = old_content.count(old_string)
    if count == 0 or (count > 1 and not replace_all):
        return None
    if replace_all:
        return old_content.replace(old_string, new_string)
    return old_content.replace(old_string, new_string, 1)


def _edit_before_after(tool_name: str, tool_input: dict, cwd: Path) -> tuple[str | None, str | None, Path | None]:
    """`(old_content, new_content, path)` for an `Edit`/`Write` tool call against a file that
    exists on disk -- `(None, None, None)` if there's nothing to compare (a new file, a tool
    other than `Edit`/`Write`, or `Edit` input that doesn't resolve to a determinate result).
    """
    file_path = tool_input.get("file_path")
    if not file_path:
        return None, None, None
    path = Path(file_path)
    if not path.is_absolute():
        path = cwd / path
    if not path.is_file():
        return None, None, None
    old_content = path.read_text()

    if tool_name == "Write":
        new_content = tool_input.get("content")
        if new_content is None:
            return None, None, None
    elif tool_name == "Edit":
        old_string = tool_input.get("old_string")
        new_string = tool_input.get("new_string")
        if old_string is None or new_string is None:
            return None, None, None
        new_content = _apply_edit(old_content, old_string, new_string, bool(tool_input.get("replace_all")))
        if new_content is None:
            return None, None, None
    else:
        return None, None, None

    return old_content, new_content, path


def check_region_edit(tool_name: str, tool_input: dict, cwd: Path) -> GuardrailResult:
    old_content, new_content, path = _edit_before_after(tool_name, tool_input, cwd)
    if old_content is None:
        return GuardrailResult(allow=True)
    region = region_edit_violation(path.name, old_content, new_content)
    if region is None:
        return GuardrailResult(allow=True)
    return GuardrailResult(
        allow=False,
        reason=(
            f"hand-editing the {region!r} generated region in {path.name} is denied -- change "
            "the source task/epic file and run `.tasks/bin/sync` to regenerate it."
        ),
    )


def check_epic_status_edit(tool_name: str, tool_input: dict, cwd: Path) -> GuardrailResult:
    old_content, new_content, path = _edit_before_after(tool_name, tool_input, cwd)
    if old_content is None:
        return GuardrailResult(allow=True)
    new_status = epic_status_edit_violation(path.name, old_content, new_content)
    if new_status is None:
        return GuardrailResult(allow=True)
    return GuardrailResult(
        allow=False,
        reason=(
            f"hand-editing {path.name}'s epic `status` to {new_status!r} is denied -- epic status "
            "is derived by `sync` from its children; the only hand-set value allowed is `wont-do` "
            "(a cancellation decision)."
        ),
    )


def evaluate_edit_write(tool_name: str, tool_input: dict, cwd: Path) -> GuardrailResult:
    """Run every structural-edit guardrail above against an `Edit`/`Write` tool call, in
    order, returning the first denial (or an allow if none fires).
    """
    for check in (check_region_edit, check_epic_status_edit):
        result = check(tool_name, tool_input, cwd)
        if not result.allow:
            return result
    return GuardrailResult(allow=True)
