#!/usr/bin/env python3
"""Deterministic batch-selection validation for `implement-task`'s future autonomous batch mode.
A standalone stdlib script, not a new `sync` subcommand -- `sync` stays generic/skill-agnostic
(see its own module docstring) -- and deliberately not folded into
`scaffold.py`, since batch selection is a distinct concern from single-task phase-driving: it
answers "is this batch workable, and in what order" once, before any of `scaffold.py`'s phases run
for any task in it.

Four selection modes:

- "epic"     -- every non-`done`/`wont-do` task under a given `EPIC-NNN`, in ascending task-id
                order -- the same order `sync` itself renders in that epic's own generated
                children table (`sync.render_epic_children`), so "board order" here means exactly
                what a human sees when they open that epic file.
- "range"    -- a numeric task-id range `"TASK-A..TASK-B"`, inclusive, ascending id order; an id
                in the range that doesn't exist, or exists but is already `done`/`wont-do`, is
                silently skipped, not an error.
- "list"     -- an explicit list of task ids, in exactly the order given (may not match TODO
                order or id order at all); nothing is filtered here -- every id is validated for
                real by the shared validation step, same as every other mode.
- "stopping" -- `.tasks/BOARD.md`'s hand-ordered TODO list, top to bottom, through and including
                the named stopping task, literally. The one mode whose natural order is not "how
                `sync` would render it" but "how the human actually prioritized it".

Every mode reduces to the same two things: a candidate id list, and that same list read as the
"natural order" for it. A single shared validation step (`validate_and_order`) then checks the
resolved set against real `.tasks/` state and hands that exact order back as the execution order
-- it never reorders anything itself. A task's `blocked_by` dependency must be either (a) already
`done`/`wont-do`, or (b) inside the selection *and* ordered before its dependent in that natural
order; anything else is refused with a message naming the offending task and blocker, and nothing
is executed -- a caller (a future autonomous batch loop) can rely on "this call raised" meaning
"nothing should run", the same "writes nothing" posture as `sync check`.

Reuses `sync`'s own `discover()` (to load real task/epic state) and `_outstanding_blockers()` (to
decide which `blocked_by` entries are still unresolved) rather than reimplementing either, and the
same `_TODO_HEADING`/`_TODO_LINE_RE` BOARD.md-TODO-parsing technique this skill's own
`scaffold.py` already uses for `pick_top_unblocked`.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import ModuleType

_SELECTABLE_STATUSES = ("todo", "in-progress", "in-review")
_TERMINAL_STATUSES = ("done", "wont-do")
_RANGE_RE = re.compile(r"^(TASK-\d+)\.\.(TASK-\d+)$")


class BatchSelectionError(ValueError):
    """Raised for any invalid batch selection -- the message names the offending task/blocker.
    Never a partial resolution: raising this means the caller should execute nothing.
    """


# ---------------------------------------------------------------------------
# repo / sync module plumbing (same technique as this skill's own scaffold.py)
# ---------------------------------------------------------------------------


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit("batch_select: not inside a git repository")
    return Path(result.stdout.strip())


def load_sync_module(tasks_root: Path) -> ModuleType:
    sync_path = tasks_root / "bin" / "sync"
    if not sync_path.is_file():
        raise SystemExit(f"batch_select: {sync_path} not found -- run `init-project` first")
    loader = SourceFileLoader("sync", str(sync_path))
    spec = importlib.util.spec_from_loader("sync", loader)
    module = importlib.util.module_from_spec(spec)
    # `sync` defines `@dataclass class Artifact`, which looks itself up via
    # `sys.modules[cls.__module__]` -- it must already be registered before
    # `exec_module` runs, or that lookup returns `None` and crashes.
    sys.modules["sync"] = module
    loader.exec_module(module)
    return module


def _task_number(task_id: str) -> int:
    try:
        return int(task_id.split("-", 1)[1])
    except (IndexError, ValueError) as exc:
        raise BatchSelectionError(f"not a task id: {task_id!r}") from exc


# ---------------------------------------------------------------------------
# Per-mode candidate resolution -- each returns a plain id list in natural order
# ---------------------------------------------------------------------------


def resolve_epic(epic_id: str, tasks: dict) -> list[str]:
    """Every non-`done`/`wont-do` task whose `epic` field is `epic_id`, ascending id order."""
    epic = tasks.get(epic_id)
    if epic is None or epic.kind != "epic":
        raise BatchSelectionError(f"no such epic: {epic_id}")
    children = [
        t for t in tasks.values()
        if t.kind == "task" and t.fields.get("epic") == epic_id
        and t.fields.get("status") not in _TERMINAL_STATUSES
    ]
    return sorted((t.id for t in children), key=_task_number)


def resolve_range(range_str: str, tasks: dict) -> list[str]:
    """Every existing, non-`done`/`wont-do` task id in the inclusive numeric range described by
    `range_str` (`"TASK-A..TASK-B"`), ascending order. A gap in numbering and an already-done
    task are both silently skipped -- neither is an error.
    """
    match = _RANGE_RE.match(range_str.strip()) if isinstance(range_str, str) else None
    if not match:
        raise BatchSelectionError(f"malformed range {range_str!r} -- expected 'TASK-NNN..TASK-MMM'")
    start_id, end_id = match.group(1), match.group(2)
    start, end = _task_number(start_id), _task_number(end_id)
    if start > end:
        raise BatchSelectionError(f"range is backwards: {start_id}..{end_id}")

    ids = []
    for n in range(start, end + 1):
        task_id = f"TASK-{n:03d}"
        task = tasks.get(task_id)
        if task is None or task.fields.get("status") in _TERMINAL_STATUSES:
            continue
        ids.append(task_id)
    return ids


def resolve_list(task_ids: list[str]) -> list[str]:
    """An explicit list, verbatim -- no filtering; every id is validated for real by
    `validate_and_order` next, same as every other mode.
    """
    return list(task_ids)


def resolve_stopping(stopping_id: str, board_text: str, sync_mod: ModuleType) -> list[str]:
    """`.tasks/BOARD.md`'s hand-ordered TODO list, top to bottom, through and including
    `stopping_id`. Raises if the TODO heading is missing, or `stopping_id` never appears in it
    (not `todo`, doesn't exist, or was simply never prioritized) -- the TODO list only ever lists
    `todo` tasks (`sync.merge_todo`), so this doubles as that status check for this one mode.
    """
    heading = sync_mod._TODO_HEADING
    if heading not in board_text:
        raise BatchSelectionError("no '## TODO' heading found in BOARD.md")
    start = board_text.index(heading) + len(heading)
    next_heading = board_text.find("\n## ", start - 1)
    end = len(board_text) if next_heading == -1 else next_heading + 1
    lines = [line for line in board_text[start:end].splitlines() if sync_mod._TODO_LINE_RE.match(line)]

    ids = []
    for line in lines:
        task_id = sync_mod._TODO_LINE_RE.match(line).group(1)
        ids.append(task_id)
        if task_id == stopping_id:
            return ids
    raise BatchSelectionError(f"{stopping_id} is not on the TODO list (not todo, or never prioritized)")


# ---------------------------------------------------------------------------
# Shared validation -- every mode funnels through this
# ---------------------------------------------------------------------------


def validate_and_order(candidate_ids: list[str], tasks: dict, sync_mod: ModuleType) -> list[str]:
    """Validate `candidate_ids` (already in a mode's natural order) against real task state and
    hand that same order back as the execution order -- this never reorders anything; a selection
    whose natural order doesn't already respect a real intra-set dependency is refused, not
    silently fixed.

    Checks, per id, in order:
    - it refers to a real task
    - that task's status is `todo`, `in-progress`, or `in-review` (a `blocked`/`done`/`wont-do`
      task is never a valid batch member -- `resolve_epic`/`resolve_range` already filter
      `done`/`wont-do` before this runs, but `list`/`stopping` don't, so it's still checked here)
    - every still-outstanding `blocked_by` entry (via `sync`'s own `_outstanding_blockers` --
      a blocker already `done`/`wont-do` is satisfied and never examined further) is either
      inside the selection and ordered before this task, or named in a refusal

    Raises `BatchSelectionError` naming the offending task (and blocker, where relevant) on the
    first problem found; writes/changes nothing either way.
    """
    if not candidate_ids:
        raise BatchSelectionError("selection resolved to zero tasks")

    index_of = {task_id: i for i, task_id in enumerate(candidate_ids)}
    for task_id in candidate_ids:
        task = tasks.get(task_id)
        if task is None:
            raise BatchSelectionError(f"{task_id} does not exist")
        status = task.fields.get("status")
        if status not in _SELECTABLE_STATUSES:
            raise BatchSelectionError(f"{task_id} has status {status!r} -- not eligible for a batch")

        for blocker_id in sync_mod._outstanding_blockers(task, tasks):
            if blocker_id not in index_of:
                raise BatchSelectionError(
                    f"{task_id} is blocked by {blocker_id}, which is outside the selection "
                    "and not done/wont-do"
                )
            if index_of[blocker_id] > index_of[task_id]:
                raise BatchSelectionError(
                    f"{task_id} is ordered before its blocker {blocker_id} in this selection"
                )

    return list(candidate_ids)


# ---------------------------------------------------------------------------
# Mode dispatch + CLI
# ---------------------------------------------------------------------------


def select_batch(params: dict, tasks: dict, board_text: str, sync_mod: ModuleType) -> list[str]:
    """Resolve `params` (`{"mode": "epic"|"range"|"list"|"stopping", ...}`) to a candidate id
    list via the matching `resolve_*` function, then validate+order it.

    - `"epic"`: `{"mode": "epic", "epic": "EPIC-NNN"}`
    - `"range"`: `{"mode": "range", "range": "TASK-A..TASK-B"}`
    - `"list"`: `{"mode": "list", "tasks": ["TASK-A", "TASK-B", ...]}`
    - `"stopping"`: `{"mode": "stopping", "stopping_task": "TASK-NNN"}`

    Raises `BatchSelectionError` (invalid selection or unknown mode) or `KeyError` (a required
    mode-specific parameter missing) -- the CLI (`cmd_select`) turns either into a clear non-zero
    exit rather than a traceback.
    """
    mode = params["mode"]
    if mode == "epic":
        candidates = resolve_epic(params["epic"], tasks)
    elif mode == "range":
        candidates = resolve_range(params["range"], tasks)
    elif mode == "list":
        candidates = resolve_list(params["tasks"])
    elif mode == "stopping":
        candidates = resolve_stopping(params["stopping_task"], board_text, sync_mod)
    else:
        raise BatchSelectionError(f"unknown mode {mode!r} -- expected epic|range|list|stopping")
    return validate_and_order(candidates, tasks, sync_mod)


def cmd_select(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    tasks = sync_mod.discover(tasks_root)
    board_text = (tasks_root / "BOARD.md").read_text()

    params = json.loads(Path(args.answers).read_text())
    try:
        order = select_batch(params, tasks, board_text, sync_mod)
    except (BatchSelectionError, KeyError) as exc:
        print(f"batch_select: invalid selection: {exc}", file=sys.stderr)
        return 2

    print(json.dumps({"order": order}))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="batch_select.py")
    subparsers = parser.add_subparsers(dest="command", required=True)
    select_parser = subparsers.add_parser(
        "select", help="resolve+validate a batch selection, print its execution order"
    )
    select_parser.add_argument("answers", help="path to a JSON file: {mode, ...mode-specific params}")

    args = parser.parse_args(argv)
    if args.command == "select":
        return cmd_select(args)
    parser.error(f"unknown command {args.command!r}")
    return 2  # pragma: no cover -- parser.error already exits


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
