#!/usr/bin/env python3
"""Deterministic scaffolding for the `init-project` skill.

Everything here is mechanical -- no judgement, no interviewing. `SKILL.md` owns the interview
(asking for `.tasks/config.md`'s values, warning about a missing `gh`) and the human confirmation
STOP; once the human has approved, the skill writes the confirmed answers to a JSON file and
invokes this script's `run` subcommand once. Nothing here prompts interactively.

Standard library only -- no third-party dependencies, consistent with `.tasks/bin/sync` itself.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SKILL_DIR / "templates"
VENDORED_SYNC = SKILL_DIR / "vendored-sync"

# Every key `.tasks/config.md`'s template expects. Keep in sync with
# `templates/config.md`'s `{{placeholder}}`s -- `workflow_version`,
# `allow_auto_merge`, `docs_review_paths`, and `docs_ignore_paths` are
# deliberately absent: SKILL.md never asks about any of them, they're
# fixed by the template itself.
REQUIRED_KEYS = (
    "test_command",
    "lint_command",
    "docs_paths",
    "default_branch",
    "branch_prefix",
    "remote",
    "rebase_before_pr",
    "merge_strategy",
    "delete_branch_after_merge",
    "ci_checks",
    "archive_done",
)


def _strip_leading_comment(text: str) -> str:
    """Drop a template's leading `<!-- ... -->` instructional comment, if present."""
    return re.sub(r"^<!--.*?-->\n", "", text, count=1, flags=re.DOTALL)


def _yaml_scalar(value) -> str:
    """Render a Python value the way it should appear in config.md's YAML frontmatter --
    bare (unquoted) strings and flow-style lists.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "[" + ", ".join(_yaml_scalar(v) for v in value) + "]"
    return str(value)


def render_config(answers: dict) -> str:
    """Render `.tasks/config.md`'s content from `templates/config.md` and `answers`.

    Raises `KeyError` if `answers` is missing a required key -- callers should validate
    with `missing_keys` first for a friendlier message.
    """
    text = _strip_leading_comment((TEMPLATES_DIR / "config.md").read_text())
    for key in REQUIRED_KEYS:
        text = text.replace("{{" + key + "}}", _yaml_scalar(answers[key]))
    return text


def missing_keys(answers: dict) -> list[str]:
    return [key for key in REQUIRED_KEYS if key not in answers]


def repo_root() -> Path:
    """The repo root, via `git rev-parse --show-toplevel`. Raises `SystemExit` if the
    current directory isn't inside a git repository at all.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise SystemExit("init-project: not inside a git repository")
    return Path(result.stdout.strip())


def cmd_run(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_dir = root / ".tasks"
    if tasks_dir.is_dir():
        print(
            f"init-project: {tasks_dir} already exists -- refusing to re-initialize "
            "(migrating an existing setup is a future `upgrade` skill's job)",
            file=sys.stderr,
        )
        return 2

    answers = json.loads(Path(args.answers).read_text())
    missing = missing_keys(answers)
    if missing:
        print(
            f"init-project: missing required answer(s): {', '.join(missing)}",
            file=sys.stderr,
        )
        return 2

    (tasks_dir / "bin").mkdir(parents=True, exist_ok=True)
    (tasks_dir / "templates").mkdir(parents=True, exist_ok=True)
    (root / ".github").mkdir(parents=True, exist_ok=True)

    (tasks_dir / "config.md").write_text(render_config(answers))
    (tasks_dir / "guidelines.md").write_text((TEMPLATES_DIR / "guidelines.md").read_text())
    (tasks_dir / "BOARD.md").write_text((TEMPLATES_DIR / "board.md").read_text())
    for name in ("spec.md", "epic.md", "task.md"):
        (tasks_dir / "templates" / name).write_text((TEMPLATES_DIR / name).read_text())
    (root / ".github" / "pull_request_template.md").write_text(
        (TEMPLATES_DIR / "pull_request_template.md").read_text()
    )

    sync_dst = tasks_dir / "bin" / "sync"
    shutil.copy(VENDORED_SYNC, sync_dst)
    sync_dst.chmod(0o755)

    sync_result = subprocess.run([sys.executable, str(sync_dst)], cwd=root)
    if sync_result.returncode != 0:
        print("init-project: `sync` failed after scaffolding", file=sys.stderr)
        return sync_result.returncode

    check_result = subprocess.run([sys.executable, str(sync_dst), "check"], cwd=root)
    if check_result.returncode != 0:
        print(
            "init-project: `sync check` is not clean immediately after scaffolding -- "
            "this is a bug in this script or in the vendored sync, not something to paper over",
            file=sys.stderr,
        )
        return check_result.returncode

    print(f"init-project: scaffolded {tasks_dir} -- sync check is clean")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scaffold.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run", help="scaffold .tasks/ into the current repo from a confirmed answers file"
    )
    run_parser.add_argument("answers", help="path to a JSON file with the interview answers")

    args = parser.parse_args(argv)
    if args.command == "run":
        return cmd_run(args)
    parser.error(f"unknown command {args.command!r}")
    return 2  # pragma: no cover -- parser.error already exits


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
