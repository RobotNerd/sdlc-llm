"""Guards the shipped skills surface (`.claude/skills/**`) against project-specific references
that would confuse an agent running the toolkit in a different repo (TASK-027).

Two things are checked: no dangling `TASK-NNN`/`EPIC-NNN`/`SPEC-NNN` id, doc pointer, or
"this repo's own ..." phrasing survives anywhere under `.claude/skills/` (detection reused from
the `strip-project-references` skill's `scaffold.py` -- TASK-048 -- so this CI regression gate and
that interactive tool can't drift apart); and the vendored copy of `sync` stays byte-identical to
`.tasks/bin/sync` so a future bug fix made only in the latter doesn't silently drift from what
ships.
"""

import importlib.util
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

_SCRIPT_PATH = SKILLS_DIR / "strip-project-references" / "scaffold.py"
_loader = SourceFileLoader("strip_project_references_scaffold", str(_SCRIPT_PATH))
_spec = importlib.util.spec_from_loader("strip_project_references_scaffold", _loader)
_strip_refs = importlib.util.module_from_spec(_spec)
sys.modules["strip_project_references_scaffold"] = _strip_refs
_loader.exec_module(_strip_refs)


def _format_offenders(entries: list[dict]) -> str:
    lines = []
    for e in entries:
        detail = e.get("text") or e.get("phrase")
        lines.append(f"{e['path']}:{e['line']}: {e['kind']} {detail!r}")
    return "\n".join(lines)


def test_no_dangling_ids_under_skills_surface():
    result = _strip_refs.scan_surface(SKILLS_DIR)
    id_offenders = [e for e in result["mechanical"] + result["judgment"] if e["kind"] != "banned_phrase"]
    assert id_offenders == [], (
        "project-specific ids leaked into the portable surface:\n" + _format_offenders(id_offenders)
    )


def test_no_banned_project_references_under_skills_surface():
    result = _strip_refs.scan_surface(SKILLS_DIR)
    phrase_offenders = [e for e in result["judgment"] if e["kind"] == "banned_phrase"]
    assert phrase_offenders == [], (
        "project-specific references leaked into the portable surface:\n"
        + _format_offenders(phrase_offenders)
    )


def test_vendored_sync_is_byte_identical_to_tasks_bin_sync():
    vendored = SKILLS_DIR / "init-project" / "vendored-sync"
    canonical = REPO_ROOT / ".tasks" / "bin" / "sync"
    assert vendored.read_bytes() == canonical.read_bytes()
