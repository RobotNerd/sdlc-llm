#!/usr/bin/env python3
"""`SessionStart` hook: injects this workflow's board/task state and `.tasks/guidelines.md`
into `additionalContext`, so a new session starts from fact already in context instead of
re-deriving it (`BOARD.md` reads, task-file reads) via tool calls every time.

Reads the hook's stdin JSON and, for a `SessionStart` event, builds context from `.tasks/`
relative to the event's `cwd`: `BOARD.md`'s rendered `In Progress`/`In Review` regions
verbatim, an explicit id/title/status/`pr` summary if any task is `in-progress`/`in-review`,
and `.tasks/guidelines.md`'s contents verbatim (never a copy embedded here). Prints
`{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ...}}` and
exits `0` when there's something to add; prints nothing and exits `0` otherwise -- `.tasks/`
not existing (a non-workflow repo) and `guidelines.md` specifically being absent are both
just "less to report", never an error. `SessionStart` has no blocking/deny concept at all
(unlike `PreToolUse`), so this hook never has a reason to exit non-zero.

Vendored into every scaffolded project at this same relative path -- see
`.claude/skills/init-project/vendored-hooks/sessionstart_board_context.py` and
`managed_files()` in `init-project/scaffold.py`. Registered in `.claude/settings.json`.
"""

import importlib.util
import json
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType

_IN_FLIGHT_STATUSES = ("in-progress", "in-review")


def _load_sync(tasks_root: Path) -> ModuleType | None:
    """`.tasks/bin/sync`, reusing an already-loaded copy (e.g. the test suite's) if present --
    `None` if it doesn't exist yet (a repo mid-bootstrap, or a non-workflow repo).
    """
    if "sync" in sys.modules:
        return sys.modules["sync"]
    sync_path = tasks_root / "bin" / "sync"
    if not sync_path.is_file():
        return None
    loader = SourceFileLoader("sync", str(sync_path))
    spec = importlib.util.spec_from_loader("sync", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["sync"] = module
    loader.exec_module(module)
    return module


def _board_sections(tasks_root: Path, sync_mod: ModuleType) -> list[str]:
    board_path = tasks_root / "BOARD.md"
    if not board_path.is_file():
        return []
    board_text = board_path.read_text()
    sections = []
    for name, heading in (("in-progress", "In Progress"), ("in-review", "In Review")):
        span = sync_mod.find_region(board_text, name)
        if span is None:
            continue
        body = board_text[span.begin_end:span.end_start].strip()
        sections.append(f"### {heading}\n\n{body}")
    return sections


def _current_task_section(tasks_root: Path, sync_mod: ModuleType) -> str | None:
    artifacts = sync_mod.discover(tasks_root)
    task = next(
        (a for a in artifacts.values() if a.kind == "task" and a.fields.get("status") in _IN_FLIGHT_STATUSES),
        None,
    )
    if task is None:
        return None
    return (
        "## Current task\n\n"
        f"- id: {task.id}\n"
        f"- title: {task.fields.get('title')}\n"
        f"- status: {task.fields.get('status')}\n"
        f"- pr: {task.fields.get('pr') or 'none yet'}"
    )


def build_context(tasks_root: Path) -> str | None:
    """The full `additionalContext` string for a session rooted at `tasks_root`'s parent, or
    `None` if there's nothing to report (`.tasks/` doesn't exist, or it exists but is entirely
    empty of board/guidelines content -- both harmless, not error states).
    """
    if not tasks_root.is_dir():
        return None

    sections: list[str] = []

    sync_mod = _load_sync(tasks_root)
    if sync_mod is not None:
        board_sections = _board_sections(tasks_root, sync_mod)
        if board_sections:
            sections.append("## Board state\n\n" + "\n\n".join(board_sections))
        current_task = _current_task_section(tasks_root, sync_mod)
        if current_task:
            sections.append(current_task)

    guidelines_path = tasks_root / "guidelines.md"
    if guidelines_path.is_file():
        sections.append("## Workflow guidelines (.tasks/guidelines.md)\n\n" + guidelines_path.read_text())

    if not sections:
        return None
    return "\n\n".join(sections)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    if payload.get("hook_event_name") != "SessionStart":
        return 0

    cwd = Path(payload.get("cwd") or ".")
    context = build_context(cwd / ".tasks")
    if not context:
        return 0

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
