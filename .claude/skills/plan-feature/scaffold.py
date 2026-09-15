#!/usr/bin/env python3
"""Deterministic scripting for the `plan-feature` skill.

Same shape as `init-project`/`add-task`/`implement-task`/`refine-backlog`'s `scaffold.py`:
`SKILL.md` owns the interview, the vertical-slice decomposition judgment,
and both STOP checkpoints (spec draft, full decomposition before task creation). This script only
writes what's already been decided (spec/epic files) and validates it (the cycle check, replacing
`SKILL.md`'s old "eyeball it" placeholder; the post-creation `sync`/board check).

Standard library only. Imports the repo's own `.tasks/bin/sync` by file path (the same technique
`tests/conftest.py` uses) for `next_id`/`discover` rather than re-implementing id allocation.
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


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit("plan-feature: not inside a git repository")
    return Path(result.stdout.strip())


def load_sync_module(tasks_root: Path) -> ModuleType:
    sync_path = tasks_root / "bin" / "sync"
    if not sync_path.is_file():
        raise SystemExit(f"plan-feature: {sync_path} not found -- run `init-project` first")
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


def _strip_leading_comment(text: str) -> str:
    """Drop a template's leading `<!-- ... -->` instructional comment, if present."""
    return re.sub(r"^<!--.*?-->\n", "", text, count=1, flags=re.DOTALL)


def _fill_first_list_line(text: str, line_placeholder: str, items: list[str]) -> str:
    """Replace the *first* remaining occurrence of `line_placeholder` (a whole line, e.g.
    `"- {{item}}"`) with one line per `items`, same indentation/prefix. Templates that
    reuse the same placeholder name for two different sections (e.g. epic.md's `In
    scope`/`Out of scope`, both `{{item}}`) rely on being filled in document order, one
    call per section -- each call consumes the next remaining occurrence.
    """
    if line_placeholder not in text:
        raise ValueError(f"template is missing the {line_placeholder!r} placeholder")
    prefix = line_placeholder.split("{{", 1)[0]
    replacement = "\n".join(f"{prefix}{item}" for item in items)
    return text.replace(line_placeholder, replacement, 1)


def render_spec_file(
    template_text: str, *, spec_id: str, title: str, created: str,
    problem: str, goals: list[str], non_goals: list[str], alternatives: list[str],
) -> str:
    """Fill `.tasks/templates/spec.md`'s placeholders. Plain string substitution, not a
    round trip through `sync`'s own frontmatter parser -- the raw template's `id: {{id}}`
    etc. are unquoted tokens starting with `{`, which `parse_frontmatter` rejects as an
    unsupported YAML feature (same reasoning as `add-task`'s `render_task_file`).
    """
    text = _strip_leading_comment(template_text)
    text = text.replace("{{id}}", spec_id)
    text = text.replace("{{title}}", title)
    text = text.replace("{{created}}", created)
    if "{{problem}}" not in text:
        raise ValueError("template is missing the '{{problem}}' placeholder")
    text = text.replace("{{problem}}", problem)
    text = _fill_first_list_line(text, "- {{goal}}", goals)
    text = _fill_first_list_line(text, "- {{non_goal}}", non_goals)
    text = _fill_first_list_line(text, "- {{alternative}}", alternatives)
    return text


def render_epic_file(
    template_text: str, *, epic_id: str, title: str, spec_id: str | None, created: str,
    goal: str, in_scope: list[str], out_of_scope: list[str], success_criteria: list[str],
) -> str:
    """Fill `.tasks/templates/epic.md`'s placeholders. Same plain-substitution approach as
    `render_spec_file`. `in_scope`/`out_of_scope` share the same `{{item}}` placeholder
    name in the template -- filled in document order (in scope's occurrence first).
    """
    text = _strip_leading_comment(template_text)
    text = text.replace("{{id}}", epic_id)
    text = text.replace("{{title}}", title)
    text = text.replace("{{spec}}", spec_id if spec_id else "null")
    text = text.replace("{{created}}", created)
    if "{{goal}}" not in text:
        raise ValueError("template is missing the '{{goal}}' placeholder")
    text = text.replace("{{goal}}", goal, 1)
    text = _fill_first_list_line(text, "- {{item}}", in_scope)
    text = _fill_first_list_line(text, "- {{item}}", out_of_scope)
    text = _fill_first_list_line(text, "- [ ] {{criterion}}", success_criteria)
    return text


def find_cycle(slices: list[dict]) -> list[str] | None:
    """DFS cycle detection over a proposed `blocked_by` graph: `slices` is
    `[{"name": ..., "blocked_by": [other names]}, ...]` for slices that don't have real
    task ids yet (`plan-feature` runs this *before* any tasks exist). Returns the cycle
    as a list of names closing back on itself (e.g. `["A", "B", "C", "A"]`) if one
    exists, else `None`. Replaces `SKILL.md`'s old "eyeball it for cycles" step.
    """
    graph = {s["name"]: list(s.get("blocked_by") or []) for s in slices}
    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def dfs(node: str) -> list[str] | None:
        if node in visiting:
            return path[path.index(node):] + [node]
        if node in visited or node not in graph:
            return None
        visiting.add(node)
        path.append(node)
        for dep in graph[node]:
            found = dfs(dep)
            if found:
                return found
        visiting.discard(node)
        visited.add(node)
        path.pop()
        return None

    for node in graph:
        found = dfs(node)
        if found:
            return found
    return None


def _region_content(text: str, name: str) -> str | None:
    begin = f"<!-- BEGIN:{name}"
    end = f"<!-- END:{name}"
    if begin not in text or end not in text:
        return None
    start = text.index("\n", text.index(begin)) + 1
    stop = text.index(end, start)
    return text[start:stop].strip()


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_check_cycles(args: argparse.Namespace) -> int:
    answers = json.loads(Path(args.answers).read_text())
    cycle = find_cycle(answers["slices"])
    print(json.dumps({"cycle": cycle}))
    return 0


def cmd_write_spec(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    answers = json.loads(Path(args.answers).read_text())

    spec_id = sync_mod.next_id(tasks_root, "spec")
    slug = answers.get("slug") or re.sub(r"[^a-z0-9]+", "-", answers["title"].lower()).strip("-")
    template_text = (tasks_root / "templates" / "spec.md").read_text()
    rendered = render_spec_file(
        template_text,
        spec_id=spec_id,
        title=answers["title"],
        created=answers["created"],
        problem=answers["problem"],
        goals=answers["goals"],
        non_goals=answers["non_goals"],
        alternatives=answers["alternatives"],
    )
    spec_path = tasks_root / "specs" / f"{spec_id}-{slug}.md"
    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(rendered)

    print(json.dumps({"spec_id": spec_id, "path": str(spec_path.relative_to(root))}))
    return 0


def cmd_write_epics(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    answers = json.loads(Path(args.answers).read_text())
    spec_id = answers.get("spec_id")
    template_text = (tasks_root / "templates" / "epic.md").read_text()

    created_epics = []
    for epic_answers in answers["epics"]:
        epic_id = sync_mod.next_id(tasks_root, "epic")
        # allocate before writing, so a second epic in the same batch doesn't reuse an id
        slug = epic_answers.get("slug") or re.sub(
            r"[^a-z0-9]+", "-", epic_answers["title"].lower()
        ).strip("-")
        rendered = render_epic_file(
            template_text,
            epic_id=epic_id,
            title=epic_answers["title"],
            spec_id=spec_id,
            created=epic_answers["created"],
            goal=epic_answers["goal"],
            in_scope=epic_answers["in_scope"],
            out_of_scope=epic_answers["out_of_scope"],
            success_criteria=epic_answers["success_criteria"],
        )
        epic_path = tasks_root / f"{epic_id}-{slug}.md"
        epic_path.write_text(rendered)
        created_epics.append({"epic_id": epic_id, "path": str(epic_path.relative_to(root))})

    print(json.dumps({"epics": created_epics}))
    return 0


def cmd_finish(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    answers = json.loads(Path(args.answers).read_text())

    sync_path = tasks_root / "bin" / "sync"
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

    epic_ids = answers.get("epic_ids", [])
    board_text = (tasks_root / "BOARD.md").read_text()
    epics_panel = _region_content(board_text, "epics") or ""

    results = []
    for epic_id in epic_ids:
        epic_path = next(tasks_root.glob(f"{epic_id}-*.md"), None)
        children_populated = False
        if epic_path is not None:
            children = _region_content(epic_path.read_text(), "children")
            children_populated = bool(children) and children != "_(none)_"
        results.append({
            "epic_id": epic_id,
            "in_epics_panel": epic_id in epics_panel,
            "children_populated": children_populated,
        })

    print(json.dumps({"epics": results}))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scaffold.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("check-cycles", "check a proposed slice blocked_by graph for cycles"),
        ("write-spec", "allocate a spec id and write SPEC-*.md from the template"),
        ("write-epics", "allocate epic id(s) and write EPIC-*.md from the template"),
        ("finish", "run sync + sync check, report on the new epic(s)"),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("answers", help="path to a JSON file with this subcommand's inputs")

    args = parser.parse_args(argv)
    dispatch = {
        "check-cycles": cmd_check_cycles,
        "write-spec": cmd_write_spec,
        "write-epics": cmd_write_epics,
        "finish": cmd_finish,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
