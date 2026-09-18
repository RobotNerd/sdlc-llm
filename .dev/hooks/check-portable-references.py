#!/usr/bin/env python3
"""`PreToolUse`/`Bash` hook, repo-only (TASK-036): denies `gh pr create` if the portable skills
surface (`.claude/skills/**`) contains a concrete `TASK-`/`EPIC-`/`SPEC-NNN` id -- these would
leak this repo's own state into what other projects vendor from this toolkit.

Lives outside `.claude/hooks/**` (which `init-project`/`upgrade` copy into every scaffolded
project -- see `managed_files()` in `.claude/skills/init-project/scaffold.py`) and is registered
only in this repo's own `.claude/settings.json`, never in
`.claude/skills/init-project/templates/settings.json` -- so no scaffolded project ever inherits a
check that would be meaningless (and possibly always-failing, since `TASK-NNN` placeholders are
legitimate template content) outside this repo. Per SPEC-002's Goals, this is the one guardrail
hook in that epic that is deliberately never portable.

Reuses `strip-project-references/scaffold.py`'s `scan_surface` -- the same detector
`tests/test_portable_surface.py` already uses for the CI regression gate -- so this local gate and
that interactive tool can't drift apart.
"""

import importlib.util
import json
import re
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_STRIP_REFS_SCRIPT = _REPO_ROOT / ".claude" / "skills" / "strip-project-references" / "scaffold.py"


def _load_strip_refs():
    """`strip-project-references/scaffold.py`, reusing an already-loaded copy (e.g. the test
    suite's) if present. Always resolved from this repo's own fixed location -- never from a
    tool call's `cwd` -- since this check is repo-only and never runs against another project.
    """
    if "strip_project_references_scaffold" in sys.modules:
        return sys.modules["strip_project_references_scaffold"]
    loader = SourceFileLoader("strip_project_references_scaffold", str(_STRIP_REFS_SCRIPT))
    spec = importlib.util.spec_from_loader("strip_project_references_scaffold", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["strip_project_references_scaffold"] = module
    loader.exec_module(module)
    return module


def find_id_offenders(skills_dir: Path) -> list[dict]:
    """Every concrete `TASK-`/`EPIC-`/`SPEC-NNN` id under `skills_dir`, `[]` if none. Reuses
    `scan_surface`'s detection -- both its `mechanical` and `judgment` buckets carry ids; only a
    `banned_phrase` entry isn't one.
    """
    strip_refs = _load_strip_refs()
    result = strip_refs.scan_surface(skills_dir)
    return [e for e in result["mechanical"] + result["judgment"] if e["kind"] != "banned_phrase"]


_GH_PR_CREATE_RE = re.compile(r"(?:^|[;&|]\s*)gh\s+pr\s+create\b")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command")
    if not command or not _GH_PR_CREATE_RE.search(command):
        return 0

    cwd = Path(payload.get("cwd") or ".")
    skills_dir = cwd / ".claude" / "skills"
    if not skills_dir.is_dir():
        return 0

    offenders = find_id_offenders(skills_dir)
    if not offenders:
        return 0

    lines = [f"{e['path']}:{e['line']}: {e['text']!r}" for e in offenders]
    print(
        "`gh pr create` is denied -- concrete TASK-/EPIC-/SPEC- ids leaked into the portable "
        "skills surface (.claude/skills/**), which other projects vendor from this toolkit:\n\n"
        + "\n".join(lines),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
