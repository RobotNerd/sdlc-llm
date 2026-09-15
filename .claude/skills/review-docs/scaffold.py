#!/usr/bin/env python3
"""Deterministic scripting for the `review-docs` skill.

Same shape as the other skills' `scaffold.py`: judging whether a doc's
prose is still accurate, redundant, or should be relocated is judgment -- that stays in
`SKILL.md`. What's mechanical -- and lives here -- is finding *candidates* for the human/LLM to
judge: a diff between the two guidelines.md mirrors, a reference to a repo path that no longer
exists, or a doc's claimed skill list not matching the real `.claude/skills/` directory.

These checks are deliberately best-effort, not exhaustive static analysis: `dangling_references`
extracts backtick-quoted tokens that *look* like repo paths (heuristic, see its docstring) rather
than parsing markdown/prose exhaustively. A false positive here just means the human/LLM judges it
not-actually-dangling during the review step; the checks never edit anything themselves.

Standard library only. Imports the repo's own `.tasks/bin/sync` by file path (the same technique
`tests/conftest.py` uses) for `load_config`.
"""

from __future__ import annotations

import argparse
import difflib
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
        raise SystemExit("review-docs: not inside a git repository")
    return Path(result.stdout.strip())


def load_sync_module(tasks_root: Path) -> ModuleType:
    sync_path = tasks_root / "bin" / "sync"
    if not sync_path.is_file():
        raise SystemExit(f"review-docs: {sync_path} not found -- run `init-project` first")
    loader = SourceFileLoader("sync", str(sync_path))
    spec = importlib.util.spec_from_loader("sync", loader)
    module = importlib.util.module_from_spec(spec)
    # `sync` defines `@dataclass class Artifact`, which looks itself up via
    # `sys.modules[cls.__module__]` -- it must already be registered before
    # `exec_module` runs, or that lookup returns `None` and crashes.
    sys.modules["sync"] = module
    loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Pure functions
# ---------------------------------------------------------------------------


def mirror_diff(path_a: Path, path_b: Path) -> list[str]:
    """Unified diff lines between two files -- empty if identical. Reports the raw diff only;
    judging whether a difference is expected (e.g. this project's own extra specificity that the
    portable template correctly omits) is `SKILL.md`'s job, not this function's.
    """
    a_lines = path_a.read_text().splitlines(keepends=True)
    b_lines = path_b.read_text().splitlines(keepends=True)
    return list(difflib.unified_diff(a_lines, b_lines, fromfile=str(path_a), tofile=str(path_b)))


_BACKTICK_RE = re.compile(r"`([^`\n]+)`")
_PLACEHOLDER_MARKERS = ("<", ">", "*", "...", "NNN")
_ROOT_DOC_NAMES = ("README.md", "CLAUDE.md")
_NON_PATH_PREFIXES = ("origin/", "<remote>/", "http://", "https://")


def _looks_like_path(token: str) -> bool:
    """Best-effort heuristic: does this backtick-quoted token look like a checkable repo path,
    as opposed to a command, flag, or placeholder pattern (`sync check`, `--force-with-lease`,
    `origin/main`, `TASK-NNN`, `EPIC-*.md`)?
    """
    if token.startswith(_NON_PATH_PREFIXES):
        return False
    if any(marker in token for marker in _PLACEHOLDER_MARKERS):
        return False
    if token in _ROOT_DOC_NAMES:
        return True
    if "/" not in token:
        return False
    return bool(re.search(r"\.\w+$", token)) or token.startswith(
        (".tasks/", ".claude/", ".tmp/", ".github/")
    )


def find_path_references(text: str) -> list[str]:
    """Every distinct backtick-quoted token in `text` that looks like a repo path, in first-seen
    order. Trailing prose punctuation (a token at the end of a sentence) is stripped first.
    """
    seen: list[str] = []
    for token in _BACKTICK_RE.findall(text):
        token = token.rstrip(".,;:)")
        if _looks_like_path(token) and token not in seen:
            seen.append(token)
    return seen


def dangling_references(root: Path, doc_path: Path, ignore_paths: set[str]) -> list[str]:
    """Path-like references `doc_path` makes that don't exist under `root`, excluding
    `ignore_paths`. Best-effort (see `find_path_references`) -- not exhaustive.
    """
    text = doc_path.read_text()
    missing = []
    for ref in find_path_references(text):
        if ref in ignore_paths:
            continue
        if not (root / ref).exists():
            missing.append(ref)
    return missing


_SKILL_BULLET_RE = re.compile(r"^- \*\*`([a-z][a-z0-9-]*)`\*\*", re.MULTILINE)


def claimed_skill_names(text: str) -> set[str]:
    """Skill names a doc enumerates, in the project's own convention: a top-level bullet whose
    first token is a bold backtick-quoted name (`- **`init-project`** — ...`). A doc using a
    different format simply yields an empty set -- nothing to check against it.
    """
    return set(_SKILL_BULLET_RE.findall(text))


def skill_list_mismatch(root: Path, doc_path: Path) -> dict | None:
    """`{"missing": [...], "extra": [...]}` if `doc_path` enumerates skill names that don't
    exactly match the real `.claude/skills/` directory; `None` if it matches, or if the doc
    doesn't enumerate skills in the recognized format at all.
    """
    claimed = claimed_skill_names(doc_path.read_text())
    if not claimed:
        return None
    skills_dir = root / ".claude" / "skills"
    real = {p.name for p in skills_dir.iterdir() if p.is_dir()} if skills_dir.is_dir() else set()
    missing = sorted(real - claimed)
    extra = sorted(claimed - real)
    if not missing and not extra:
        return None
    return {"missing": missing, "extra": extra}


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_mirror_diff(args: argparse.Namespace) -> int:
    root = repo_root()
    answers = json.loads(Path(args.answers).read_text())
    diff = mirror_diff(root / answers["path_a"], root / answers["path_b"])
    print(json.dumps({"identical": not diff, "diff": diff}))
    return 0


def cmd_dangling_refs(args: argparse.Namespace) -> int:
    root = repo_root()
    answers = json.loads(Path(args.answers).read_text())
    ignore_paths = set(answers.get("ignore_paths", []))
    results = {}
    for rel in answers["doc_paths"]:
        doc_path = root / rel
        if not doc_path.is_file():
            results[rel] = ["<doc itself missing>"]
            continue
        missing = dangling_references(root, doc_path, ignore_paths)
        if missing:
            results[rel] = missing
    print(json.dumps({"dangling_references": results}))
    return 0


def cmd_skill_list_check(args: argparse.Namespace) -> int:
    root = repo_root()
    answers = json.loads(Path(args.answers).read_text())
    results = {}
    for rel in answers["doc_paths"]:
        doc_path = root / rel
        if not doc_path.is_file():
            continue
        mismatch = skill_list_mismatch(root, doc_path)
        if mismatch:
            results[rel] = mismatch
    print(json.dumps({"skill_list_mismatches": results}))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    root = repo_root()
    tasks_root = root / ".tasks"
    sync_mod = load_sync_module(tasks_root)
    config = sync_mod.load_config(tasks_root)
    review_paths = config.get("docs_review_paths") or []
    ignore_paths = set(config.get("docs_ignore_paths") or [])

    dangling = {}
    skill_mismatches = {}
    for rel in review_paths:
        if rel in ignore_paths:
            continue
        doc_path = root / rel
        if not doc_path.is_file():
            dangling[rel] = ["<doc itself missing>"]
            continue
        missing = dangling_references(root, doc_path, ignore_paths)
        if missing:
            dangling[rel] = missing
        mismatch = skill_list_mismatch(root, doc_path)
        if mismatch:
            skill_mismatches[rel] = mismatch

    mirror = None
    guidelines_a = tasks_root / "guidelines.md"
    guidelines_b = root / ".claude" / "skills" / "init-project" / "templates" / "guidelines.md"
    if guidelines_a.is_file() and guidelines_b.is_file():
        diff_lines = mirror_diff(guidelines_a, guidelines_b)
        if diff_lines:
            mirror = diff_lines

    print(json.dumps({
        "dangling_references": dangling,
        "skill_list_mismatches": skill_mismatches,
        "guidelines_mirror_diff": mirror,
    }))
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="scaffold.py")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("report", help="run every check using .tasks/config.md's doc lists")

    for name, help_text in (
        ("mirror-diff", "diff two files (e.g. guidelines.md and its portable-template mirror)"),
        ("dangling-refs", "find path-like references in given docs that don't exist on disk"),
        ("skill-list-check", "check a doc's claimed skill list against .claude/skills/"),
    ):
        sub = subparsers.add_parser(name, help=help_text)
        sub.add_argument("answers", help="path to a JSON file with this subcommand's inputs")

    args = parser.parse_args(argv)
    dispatch = {
        "report": cmd_report,
        "mirror-diff": cmd_mirror_diff,
        "dangling-refs": cmd_dangling_refs,
        "skill-list-check": cmd_skill_list_check,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
