#!/usr/bin/env python3
"""Deterministic scripting for the `refine-backlog` skill.

Same shape as `init-project`/`add-task`/`implement-task`'s `scaffold.py`:
`SKILL.md` owns the human-facing proposals and decisions (which `wont-do`/re-interview/reorder
suggestions to act on) and every STOP; this script performs the mechanical computation and
reporting behind each one. It never decides anything on its own -- `mark-wont-do`/`reorder` only
apply a choice the human has already confirmed.

Standard library only. Imports the repo's own `.tasks/bin/sync` by file path (the same technique
`tests/conftest.py` uses) rather than re-implementing frontmatter parsing or "what does a TODO line
look like".
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from datetime import date
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType

_STALE_THRESHOLD_ACTIVE_DAYS = 30  # not a config.md field -- no other skill reads it


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit("refine-backlog: not inside a git repository")
    return Path(result.stdout.strip())


def discover_or_exit(sync_mod: ModuleType, tasks_root: Path) -> dict:
    """`sync_mod.discover(tasks_root)`, but a malformed task/epic/spec file (`FrontmatterError`,
    whose message already names the file and the problem) becomes a one-line error and a non-zero
    exit instead of a traceback. Never skips the bad file -- it still fails the command.
    """
    try:
        return sync_mod.discover(tasks_root)
    except sync_mod.FrontmatterError as exc:
        raise SystemExit(f"refine-backlog: {exc}") from None


def load_sync_module(tasks_root: Path) -> ModuleType:
    sync_path = tasks_root / "bin" / "sync"
    if not sync_path.is_file():
        raise SystemExit(f"refine-backlog: {sync_path} not found -- run `init-project` first")
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


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def _todo_lines(board_text: str, sync_mod: ModuleType) -> list[str]:
    heading = sync_mod._TODO_HEADING
    if heading not in board_text:
        raise ValueError("no '## TODO' heading found in BOARD.md")
    start = board_text.index(heading) + len(heading)
    next_heading = board_text.find("\n## ", start - 1)
    end = len(board_text) if next_heading == -1 else next_heading + 1
    return [line for line in board_text[start:end].splitlines() if sync_mod._TODO_LINE_RE.match(line)]


def blocked_chain_report(board_text: str, tasks: dict, sync_mod: ModuleType) -> list[dict]:
    """Every TODO line carrying a `⛔ blocked_by ...` marker (`sync`-derived -- only
    *currently outstanding* blockers show, per `guidelines.md`), with each blocker's own
    current status so a transitive chain (a blocker that's itself still blocked, or
    in-progress elsewhere) is visible to whoever reads the report.
    """
    report = []
    for line in _todo_lines(board_text, sync_mod):
        if "⛔" not in line:
            continue
        task_id = sync_mod._TODO_LINE_RE.match(line).group(1)
        blocker_ids = [b.strip() for b in line.split("⛔ blocked_by", 1)[1].strip().split(",")]
        blockers = [
            {"id": bid, "status": tasks[bid].fields.get("status") if bid in tasks else None}
            for bid in blocker_ids
        ]
        report.append({"task_id": task_id, "blocked_by": blockers})
    return report


def active_days_elapsed(cwd: Path, default_branch: str, since: str) -> int:
    """Distinct calendar days with >=1 commit to `default_branch`, strictly after `since`
    (an ISO `YYYY-MM-DD` date -- a task's `created` date) through now. Backdated wall-clock
    dormancy (a project dropped and resumed later) contributes ~0 here, unlike a raw
    `today - created > threshold` check.
    """
    result = subprocess.run(
        ["git", "log", default_branch, f"--since={since}", "--date=short", "--pretty=%ad"],
        cwd=cwd, capture_output=True, text=True, check=True,
    )
    days = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    days.discard(since)  # "strictly after" -- created's own day doesn't count
    return len(days)


def stale_todo_scan(cwd: Path, default_branch: str, tasks: dict, threshold: int = _STALE_THRESHOLD_ACTIVE_DAYS) -> list[dict]:
    flagged = []
    for task_id, task in tasks.items():
        if task.fields.get("status") != "todo":
            continue
        created = task.fields.get("created")
        if not created:
            continue
        elapsed = active_days_elapsed(cwd, default_branch, created)
        if elapsed > threshold:
            flagged.append({"task_id": task_id, "created": created, "active_days_elapsed": elapsed})
    return flagged


def _extract_section(body: str, heading: str) -> str:
    marker = f"{heading}\n"
    if marker not in body:
        return ""
    start = body.index(marker) + len(marker)
    next_heading = body.find("\n## ", start - 1)
    end = len(body) if next_heading == -1 else next_heading + 1
    return body[start:end].strip()


_LIST_MARKER_RE = re.compile(r"^(-\s*\[.\]|-|\d+\.)\s*")
_LONE_PLACEHOLDER_RE = re.compile(r"^\{\{\w+\}\}$")


def _is_placeholder_or_empty(section_text: str) -> bool:
    if not section_text:
        return True
    lines = [line for line in section_text.splitlines() if line.strip()]
    if not lines:
        return True
    for line in lines:
        content = _LIST_MARKER_RE.sub("", line.strip()).strip()
        # A real, filled-in criterion can *mention* `{{...}}` syntax in passing (e.g.
        # documenting what NOT to do) without being one -- only flag a line that, once
        # list markup is stripped, *is* nothing but the placeholder token itself.
        if _LONE_PLACEHOLDER_RE.match(content):
            return True
    if len(lines) == 1:
        content = _LIST_MARKER_RE.sub("", lines[0].strip()).strip()
        if len(content) < 3:
            return True
    return False


def underspecified_scan(tasks: dict) -> list[dict]:
    """Flags any `todo`/`blocked` task whose Acceptance criteria or Testing strategy
    section is empty, a single vague line, or still carries template placeholder text
    (e.g. `{{criterion}}`, `{{step}}`).
    """
    flagged = []
    for task_id, task in tasks.items():
        if task.fields.get("status") not in ("todo", "blocked"):
            continue
        ac_bad = _is_placeholder_or_empty(_extract_section(task.body, "## Acceptance criteria"))
        ts_bad = _is_placeholder_or_empty(_extract_section(task.body, "## Testing strategy"))
        if ac_bad or ts_bad:
            flagged.append({"task_id": task_id, "acceptance_criteria": ac_bad, "testing_strategy": ts_bad})
    return flagged


def apply_reorder(board_text: str, new_order: list[str], tasks: dict, sync_mod: ModuleType) -> str:
    """Replace `BOARD.md`'s TODO section with `new_order`, each line freshly rendered via
    `sync`'s own `render_todo_line` (so annotations stay correct). Raises `ValueError` if
    `new_order` isn't exactly a permutation of the current `todo` task set -- refuses to
    silently add, drop, or reorder-in a non-`todo` task.
    """
    heading = sync_mod._TODO_HEADING
    if heading not in board_text:
        raise ValueError("no '## TODO' heading found in BOARD.md")
    current_todo_ids = {tid for tid, t in tasks.items() if t.fields.get("status") == "todo"}
    given_ids = set(new_order)
    if given_ids != current_todo_ids:
        missing = sorted(current_todo_ids - given_ids)
        extra = sorted(given_ids - current_todo_ids)
        raise ValueError(
            "new_order must contain exactly the current todo tasks"
            + (f" -- missing: {', '.join(missing)}" if missing else "")
            + (f" -- unexpected: {', '.join(extra)}" if extra else "")
        )
    if len(new_order) != len(given_ids):
        raise ValueError("new_order contains a duplicate task id")

    start = board_text.index(heading) + len(heading)
    next_heading = board_text.find("\n## ", start - 1)
    end = len(board_text) if next_heading == -1 else next_heading + 1
    lines = "".join(sync_mod.render_todo_line(tasks[tid], tasks) + "\n" for tid in new_order)
    trailer = "\n" if next_heading != -1 else ""
    return board_text[:start] + lines + trailer + board_text[end:]


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_resync(args: argparse.Namespace) -> int:
    root = repo_root()
    sync_path = root / ".tasks" / "bin" / "sync"
    sync_result = _run_sync(sync_path)
    if sync_result.returncode != 0:
        print(sync_result.stdout)
        print(sync_result.stderr, file=sys.stderr)
        return sync_result.returncode
    check_result = _run_sync(sync_path, "check")
    if check_result.returncode != 0:
        print(check_result.stdout)
        print(check_result.stderr, file=sys.stderr)
        return check_result.returncode
    print(json.dumps({"changed": bool(sync_result.stdout.strip() and "Already up to date" not in sync_result.stdout)}))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    config = sync_mod.load_config(tasks_root)
    default_branch = config.get("default_branch", "main")

    artifacts = discover_or_exit(sync_mod, tasks_root)
    tasks = {a.id: a for a in artifacts.values() if a.kind == "task"}
    board_text = (tasks_root / "BOARD.md").read_text()

    result = {
        "blocked_chain": blocked_chain_report(board_text, tasks, sync_mod),
        "stale_todo": stale_todo_scan(root, default_branch, tasks),
        "underspecified": underspecified_scan(tasks),
    }
    print(json.dumps(result))
    return 0


def cmd_mark_wont_do(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    answers = json.loads(Path(args.answers).read_text())
    task_id = answers["task_id"]

    artifacts = discover_or_exit(sync_mod, tasks_root)
    if task_id not in artifacts:
        print(f"refine-backlog: {task_id} not found", file=sys.stderr)
        return 2
    task = artifacts[task_id]
    task.fields["status"] = "wont-do"
    task.write()

    sync_result = _run_sync(tasks_root / "bin" / "sync")
    if sync_result.returncode != 0:
        print(sync_result.stdout)
        print(sync_result.stderr, file=sys.stderr)
        return sync_result.returncode

    print(json.dumps({"task_id": task_id, "status": "wont-do"}))
    return 0


def cmd_reorder(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    answers = json.loads(Path(args.answers).read_text())
    new_order = answers["new_order"]

    artifacts = discover_or_exit(sync_mod, tasks_root)
    tasks = {a.id: a for a in artifacts.values() if a.kind == "task"}
    board_path = tasks_root / "BOARD.md"
    board_text = board_path.read_text()

    try:
        new_board_text = apply_reorder(board_text, new_order, tasks, sync_mod)
    except ValueError as exc:
        print(f"refine-backlog: {exc}", file=sys.stderr)
        return 2
    board_path.write_text(new_board_text)

    check_result = _run_sync(tasks_root / "bin" / "sync", "check")
    if check_result.returncode != 0:
        print(check_result.stdout)
        print(check_result.stderr, file=sys.stderr)
        return check_result.returncode

    print(json.dumps({"new_order": new_order}))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scaffold.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("resync", help="run sync then sync check")
    subparsers.add_parser("report", help="blocked-chain + stale-todo + under-specified reports")

    for name, help_text in (
        ("mark-wont-do", "set a task's status to wont-do and run sync"),
        ("reorder", "apply a confirmed full TODO reordering and confirm sync check"),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("answers", help="path to a JSON file with this subcommand's inputs")

    args = parser.parse_args(argv)
    dispatch = {
        "resync": cmd_resync,
        "report": cmd_report,
        "mark-wont-do": cmd_mark_wont_do,
        "reorder": cmd_reorder,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
