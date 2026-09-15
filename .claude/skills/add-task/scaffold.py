#!/usr/bin/env python3
"""Deterministic scripting for the `add-task` skill (TASK-022).

Same shape as `init-project`'s `scaffold.py` (TASK-021): `SKILL.md` owns the interview (rough
description -> concrete acceptance criteria/testing strategy, size check, epic choice,
`blocked_by`, priority rank) and every STOP; once the human has approved, the skill writes the
confirmed answers to a JSON file and invokes this script once. Nothing here prompts
interactively -- it independently re-verifies anything `SKILL.md` already checked, so a direct
call with bad input fails loudly instead of writing something wrong.

Standard library only. Imports the repo's own `.tasks/bin/sync` by file path (the same technique
`tests/conftest.py` uses, since it has no `.py` suffix) rather than re-implementing frontmatter
parsing/rendering or "what does a TODO line look like" -- one parser, one renderer, one regex.
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

_ALLOWED_TYPES = ("feature", "bug", "chore", "refactor", "docs")
_ARCHIVED_EPIC_STATUSES = ("done", "wont-do")
_REQUIRED_KEYS = ("title", "type", "epic", "blocked_by", "priority_mode")
_PRIORITY_MODES = ("top", "end", "after")


def _strip_leading_comment(text: str) -> str:
    """Drop a template's leading `<!-- ... -->` instructional comment, if present."""
    return re.sub(r"^<!--.*?-->\n", "", text, count=1, flags=re.DOTALL)


def repo_root() -> Path:
    """The repo root, via `git rev-parse --show-toplevel`. Raises `SystemExit` if the
    current directory isn't inside a git repository at all.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit("add-task: not inside a git repository")
    return Path(result.stdout.strip())


def load_sync_module(tasks_root: Path) -> ModuleType:
    """Import `<tasks_root>/bin/sync` by file path -- it has no `.py` suffix so a normal
    `import` can't find it. Raises `SystemExit` if `.tasks/bin/sync` doesn't exist yet
    (this repo hasn't run `init-project`).
    """
    sync_path = tasks_root / "bin" / "sync"
    if not sync_path.is_file():
        raise SystemExit(f"add-task: {sync_path} not found -- run `init-project` first")
    loader = SourceFileLoader("sync", str(sync_path))
    spec = importlib.util.spec_from_loader("sync", loader)
    module = importlib.util.module_from_spec(spec)
    # `sync` defines `@dataclass class Artifact`, which looks itself up via
    # `sys.modules[cls.__module__]` -- it must already be registered before
    # `exec_module` runs, or that lookup returns `None` and crashes.
    sys.modules["sync"] = module
    loader.exec_module(module)
    return module


def missing_keys(answers: dict) -> list[str]:
    """Required answer keys absent from `answers`. `priority_after` is only required
    when `priority_mode` is `"after"` -- checked here rather than in `_REQUIRED_KEYS`
    since it's conditional.
    """
    missing = [key for key in _REQUIRED_KEYS if key not in answers]
    if answers.get("priority_mode") == "after" and "priority_after" not in answers:
        missing.append("priority_after")
    return missing


def slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug:
        raise ValueError(f"cannot derive a slug from title {title!r}")
    return slug


def list_open_epics(tasks_root: Path, sync_mod: ModuleType) -> list[dict]:
    """Every epic whose `status` is not `done`/`wont-do` -- the same "open" definition
    `sync`'s board panel uses -- scanning `.tasks/` and `.tasks/archive/`. Sorted by id.
    """
    artifacts = sync_mod.discover(tasks_root)
    open_epics = [
        {"id": art.id, "title": art.fields.get("title")}
        for art in artifacts.values()
        if art.kind == "epic" and art.fields.get("status") not in _ARCHIVED_EPIC_STATUSES
    ]
    return sorted(open_epics, key=lambda e: e["id"])


def render_task_file(
    template_text: str,
    *,
    task_id: str,
    title: str,
    type_: str,
    epic: str | None,
    created: str,
    branch: str,
    blocked_by: list[str],
    sync_mod: ModuleType,
) -> str:
    """Step 2a: fill every mechanical frontmatter field, plus both the `id` and
    `title` occurrences (the heading repeats them), leaving the body's Description/
    Acceptance criteria/Testing strategy/Notes sections as `{{placeholder}}`s for the
    LLM to fill in at step 2b.

    Plain `{{placeholder}}` substitution -- the same technique `init-project`'s
    `render_config` uses -- rather than a round trip through `sync`'s own
    `parse_frontmatter`/`render_frontmatter`: the *raw* template text isn't valid
    frontmatter (`id: {{id}}` etc. are unquoted tokens starting with `{`, which
    `parse_frontmatter` rejects as an unsupported YAML feature). `epic`/`blocked_by`
    are still rendered via `sync`'s own `render_value`, so `null`/list formatting
    matches what `sync` itself would produce for the same fields.
    """
    if '"' in title:
        raise ValueError(f"title cannot contain a double quote: {title!r}")
    text = _strip_leading_comment(template_text)
    replacements = {
        "id": task_id,
        "title": title,
        "type": type_,
        "epic": sync_mod.render_value(epic),
        "created": created,
        "branch": branch,
        "blocked_by": sync_mod.render_value(list(blocked_by)),
    }
    for key, value in replacements.items():
        placeholder = "{{" + key + "}}"
        if placeholder not in text:
            raise ValueError(f"task.md template is missing the {placeholder!r} placeholder")
        text = text.replace(placeholder, value)
    return text


def reposition_todo_line(
    board_text: str, task_id: str, mode: str, after_id: str | None, sync_mod: ModuleType
) -> str:
    """Move `task_id`'s TODO line -- which a prior bare `sync` run just appended at the
    end -- to the requested rank. Only the TODO section's lines change; the heading and
    the rest of the file are untouched. `mode` is one of "top" | "end" | "after" (with
    `after_id` naming the task this one should follow). Raises `ValueError` if the
    `## TODO` heading, `task_id`, or (for "after") `after_id` can't be found.
    """
    heading = sync_mod._TODO_HEADING
    if heading not in board_text:
        raise ValueError("no '## TODO' heading found in BOARD.md")
    start = board_text.index(heading) + len(heading)
    # See sync's own `apply_todo_merge` for why this searches from `start - 1`: an
    # empty TODO section's next heading starts right at `start - 1`.
    next_heading = board_text.find("\n## ", start - 1)
    end = len(board_text) if next_heading == -1 else next_heading + 1
    # The raw slice can include a trailing blank line (the separator before the next
    # heading) -- keep only real `- TASK-NNN — ...` lines, same as `sync`'s own
    # `merge_todo` does, so it doesn't end up preserved mid-list after reordering.
    lines = [line for line in board_text[start:end].splitlines() if sync_mod._TODO_LINE_RE.match(line)]

    def _line_index(target_id: str) -> int | None:
        return next(
            (
                i
                for i, line in enumerate(lines)
                if (m := sync_mod._TODO_LINE_RE.match(line)) and m.group(1) == target_id
            ),
            None,
        )

    idx = _line_index(task_id)
    if idx is None:
        raise ValueError(f"{task_id} not found in BOARD.md's TODO section")
    line = lines.pop(idx)

    if mode == "top":
        lines.insert(0, line)
    elif mode == "end":
        lines.append(line)
    elif mode == "after":
        after_idx = _line_index(after_id)
        if after_idx is None:
            raise ValueError(f"{after_id} not found in BOARD.md's TODO section")
        lines.insert(after_idx + 1, line)
    else:
        raise ValueError(f"unknown priority mode {mode!r}")

    body = "".join(line + "\n" for line in lines)
    trailer = "\n" if next_heading != -1 else ""
    return board_text[:start] + body + trailer + board_text[end:]


def _run_sync(sync_path: Path, *extra_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(sync_path), *extra_args], capture_output=True, text=True
    )


def cmd_list_open_epics(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    print(json.dumps(list_open_epics(tasks_root, sync_mod)))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)

    answers = json.loads(Path(args.answers).read_text())
    missing = missing_keys(answers)
    if missing:
        print(f"add-task: missing required answer(s): {', '.join(missing)}", file=sys.stderr)
        return 2

    type_ = answers["type"]
    if type_ not in _ALLOWED_TYPES:
        print(
            f"add-task: unknown type {type_!r} -- expected one of: {', '.join(_ALLOWED_TYPES)}",
            file=sys.stderr,
        )
        return 2

    artifacts = sync_mod.discover(tasks_root)

    epic = answers["epic"]
    if epic is not None and (epic not in artifacts or artifacts[epic].kind != "epic"):
        print(f"add-task: epic {epic!r} does not exist", file=sys.stderr)
        return 2

    blocked_by = answers["blocked_by"]
    unknown_blockers = [b for b in blocked_by if b not in artifacts or artifacts[b].kind != "task"]
    if unknown_blockers:
        print(
            f"add-task: blocked_by references unknown task(s): {', '.join(unknown_blockers)}",
            file=sys.stderr,
        )
        return 2

    priority_mode = answers["priority_mode"]
    if priority_mode not in _PRIORITY_MODES:
        print(
            f"add-task: unknown priority_mode {priority_mode!r} -- expected one of: "
            f"{', '.join(_PRIORITY_MODES)}",
            file=sys.stderr,
        )
        return 2
    priority_after = answers.get("priority_after")
    if priority_mode == "after" and priority_after not in artifacts:
        print(f"add-task: priority_after task {priority_after!r} does not exist", file=sys.stderr)
        return 2

    title = answers["title"]
    slug = answers.get("slug") or slugify(title)
    task_id = sync_mod.next_id(tasks_root, "task")
    config = sync_mod.load_config(tasks_root)
    branch_prefix = config.get("branch_prefix", "task-")
    branch = f"{branch_prefix}{task_id.split('-', 1)[1]}-{slug}"
    created = date.today().isoformat()

    template_text = (tasks_root / "templates" / "task.md").read_text()
    rendered = render_task_file(
        template_text,
        task_id=task_id,
        title=title,
        type_=type_,
        epic=epic,
        created=created,
        branch=branch,
        blocked_by=blocked_by,
        sync_mod=sync_mod,
    )
    task_path = tasks_root / f"{task_id}-{slug}.md"
    task_path.write_text(rendered)

    sync_path = tasks_root / "bin" / "sync"
    sync_result = _run_sync(sync_path)
    if sync_result.returncode != 0:
        print(sync_result.stdout)
        print(sync_result.stderr, file=sys.stderr)
        print("add-task: `sync` failed after writing the task file", file=sys.stderr)
        return sync_result.returncode

    if priority_mode != "end":
        board_path = tasks_root / "BOARD.md"
        board_text = board_path.read_text()
        try:
            new_board_text = reposition_todo_line(
                board_text, task_id, priority_mode, priority_after, sync_mod
            )
        except ValueError as exc:
            print(f"add-task: {exc}", file=sys.stderr)
            return 2
        board_path.write_text(new_board_text)

    check_result = _run_sync(sync_path, "check")
    if check_result.returncode != 0:
        print(check_result.stdout)
        print(check_result.stderr, file=sys.stderr)
        print("add-task: `sync check` is not clean after writing the task", file=sys.stderr)
        return check_result.returncode

    print(f"add-task: wrote {task_path} ({task_id}) -- sync check is clean")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scaffold.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser(
        "list-open-epics", help="print every open epic (id + title) as a JSON array"
    )

    run_parser = subparsers.add_parser(
        "run", help="write a task file, place it on the TODO list, and run sync + sync check"
    )
    run_parser.add_argument("answers", help="path to a JSON file with the interview answers")

    args = parser.parse_args(argv)
    if args.command == "list-open-epics":
        return cmd_list_open_epics(args)
    if args.command == "run":
        return cmd_run(args)
    parser.error(f"unknown command {args.command!r}")
    return 2  # pragma: no cover -- parser.error already exits


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
