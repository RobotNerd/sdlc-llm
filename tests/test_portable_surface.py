"""Guards the shipped skills surface (`.claude/skills/**`) against project-specific references
that would confuse an agent running the toolkit in a different repo (TASK-027).

Two things are checked mechanically: no dangling `TASK-NNN`/`EPIC-NNN`/`SPEC-NNN` id, doc pointer,
or "this repo's own ..." phrasing survives anywhere under `.claude/skills/`; and the vendored copy
of `sync` stays byte-identical to `.tasks/bin/sync` so a future bug fix made only in the latter
doesn't silently drift from what ships.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

_ID_PATTERN = re.compile(r"\b(?:TASK|EPIC|SPEC)-\d{3}\b")
_BANNED_PHRASES = ("CLAUDE.md", ".tmp/workflow-plan.md", "this repo's own")

# `CLAUDE.md` is also a generic Claude Code convention filename (like `README.md`), not
# necessarily a pointer to *this* repo's own doc — these two spots use it as a legitimate default
# filename for any project, so they're exempt from the `CLAUDE.md` ban specifically. Matched by
# an anchor string on the same line so a *new* stray `CLAUDE.md` reference elsewhere still trips
# the check.
_CLAUDE_MD_EXEMPTIONS = {
    "init-project/templates/config.md": "docs_review_paths",
    "review-docs/scaffold.py": "_ROOT_DOC_NAMES",
}


def _skill_surface_files():
    for path in sorted(SKILLS_DIR.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            yield path


def test_no_dangling_ids_under_skills_surface():
    offenders = []
    for path in _skill_surface_files():
        text = path.read_text()
        for match in _ID_PATTERN.finditer(text):
            line_no = text.count("\n", 0, match.start()) + 1
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{line_no}: {match.group(0)}")
    assert offenders == [], "project-specific ids leaked into the portable surface:\n" + "\n".join(
        offenders
    )


def test_no_banned_project_references_under_skills_surface():
    offenders = []
    for path in _skill_surface_files():
        rel = str(path.relative_to(SKILLS_DIR))
        lines = path.read_text().splitlines()
        for line_no, line in enumerate(lines, start=1):
            for phrase in _BANNED_PHRASES:
                if phrase not in line:
                    continue
                anchor = _CLAUDE_MD_EXEMPTIONS.get(rel)
                if phrase == "CLAUDE.md" and anchor is not None and anchor in line:
                    continue
                offenders.append(f"{rel}:{line_no}: {phrase!r}")
    assert offenders == [], "project-specific references leaked into the portable surface:\n" + "\n".join(
        offenders
    )


def test_vendored_sync_is_byte_identical_to_tasks_bin_sync():
    vendored = SKILLS_DIR / "init-project" / "vendored-sync"
    canonical = REPO_ROOT / ".tasks" / "bin" / "sync"
    assert vendored.read_bytes() == canonical.read_bytes()
