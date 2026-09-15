"""Unit tests for `.claude/skills/strip-project-references/scaffold.py` (TASK-048).

`scan_surface`/`apply_mechanical_fixes` are pure functions (well, `apply_mechanical_fixes` writes
files, but takes a directory and no other side effects), tested directly against small fixture
trees built in `tmp_path` -- fast, and exercises the exact classification logic
`tests/test_portable_surface.py` now relies on for its own regression gate. The `scan`/
`apply-mechanical` subcommands are exercised as real subprocesses, and a final pair of tests run
against this repo's actual `.claude/skills/` tree per the task's own testing strategy.
"""

import importlib.util
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "strip-project-references"
SCRIPT_PATH = SKILL_DIR / "scaffold.py"

_loader = SourceFileLoader("strip_project_references_scaffold", str(SCRIPT_PATH))
_spec = importlib.util.spec_from_loader("strip_project_references_scaffold", _loader)
scaffold = importlib.util.module_from_spec(_spec)
sys.modules["strip_project_references_scaffold"] = scaffold
_loader.exec_module(scaffold)


def _write(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# scan_surface -- mechanical bucket
# ---------------------------------------------------------------------------


def test_scan_flags_id_only_parenthetical_as_mechanical(tmp_path):
    _write(tmp_path, "a/SKILL.md", "next to this `SKILL.md` (TASK-024) — not in this prose.\n")
    result = scaffold.scan_surface(tmp_path)
    assert result["judgment"] == []
    assert result["mechanical"] == [
        {"path": "a/SKILL.md", "line": 1, "kind": "id_parenthetical", "text": "(TASK-024)"}
    ]


def test_scan_flags_multi_id_parenthetical_as_mechanical(tmp_path):
    _write(tmp_path, "a/scaffold.py", "`scaffold.py` (TASK-021/022/024): `SKILL.md` owns everything.\n")
    result = scaffold.scan_surface(tmp_path)
    assert result["judgment"] == []
    assert result["mechanical"] == [
        {"path": "a/scaffold.py", "line": 1, "kind": "id_parenthetical", "text": "(TASK-021/022/024)"}
    ]


def test_scan_flags_bare_example_id_as_mechanical(tmp_path):
    _write(tmp_path, "a/SKILL.md", "a specific task id (e.g. `TASK-016`) to work instead.\n")
    result = scaffold.scan_surface(tmp_path)
    assert result["judgment"] == []
    assert result["mechanical"] == [
        {"path": "a/SKILL.md", "line": 1, "kind": "id_example", "text": "TASK-016"}
    ]


def test_scan_flags_each_id_in_a_bracketed_example_list(tmp_path):
    _write(tmp_path, "a/task.md", "a bracketed list of task ids, e.g. [TASK-004, TASK-006], or [] if none\n")
    result = scaffold.scan_surface(tmp_path)
    assert result["judgment"] == []
    kinds = [(e["kind"], e["text"]) for e in result["mechanical"]]
    assert kinds == [("id_example", "TASK-004"), ("id_example", "TASK-006")]


# ---------------------------------------------------------------------------
# scan_surface -- judgment bucket
# ---------------------------------------------------------------------------


def test_scan_flags_mixed_parenthetical_as_judgment_not_mechanical(tmp_path):
    """A parenthetical with prose alongside the id (not id-only) must never be treated as the
    safe strip-the-whole-parenthetical case -- it needs a sentence rewrite.
    """
    _write(tmp_path, "a/pr.md", "can't be scripted (SPEC-001 §implement-task phase 2). List each one.\n")
    result = scaffold.scan_surface(tmp_path)
    assert result["mechanical"] == []
    assert {"path": "a/pr.md", "line": 1, "kind": "id_needs_rewrite", "text": "SPEC-001"} in result["judgment"]


def test_scan_flags_same_line_citation_as_judgment(tmp_path):
    _write(tmp_path, "a/sync", "Implements the seven ordered rules of SPEC-001 §'Epic status derivation'.\n")
    result = scaffold.scan_surface(tmp_path)
    assert result["mechanical"] == []
    assert {"path": "a/sync", "line": 1, "kind": "id_needs_rewrite", "text": "SPEC-001"} in result["judgment"]


def test_scan_flags_next_line_citation_as_judgment():
    """The real regression case: the `§` mark lands on the line *after* the id, inside the same
    paragraph (no blank line between them) -- a same-line-only check would miss this.
    """
    text = "padded to three digits (SPEC-001\n§'ID allocation'). Archived files count too.\n"
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        _write(root, "a/sync", text)
        result = scaffold.scan_surface(root)
        assert result["mechanical"] == []
        assert {"path": "a/sync", "line": 1, "kind": "id_needs_rewrite", "text": "SPEC-001"} in result["judgment"]


def test_scan_flags_banned_phrases(tmp_path):
    _write(
        tmp_path,
        "a/scaffold.py",
        "matching this repo's own `config.md`.\nSee CLAUDE.md and .tmp/workflow-plan.md.\n",
    )
    result = scaffold.scan_surface(tmp_path)
    phrases = {(e["line"], e["phrase"]) for e in result["judgment"] if e["kind"] == "banned_phrase"}
    assert phrases == {
        (1, "this repo's own"),
        (2, "CLAUDE.md"),
        (2, ".tmp/workflow-plan.md"),
    }


def test_scan_exempts_claude_md_default_list_spots(tmp_path):
    _write(
        tmp_path,
        "init-project/templates/config.md",
        "docs_review_paths: [CLAUDE.md, README.md, .tasks/guidelines.md]\n",
    )
    _write(
        tmp_path,
        "review-docs/scaffold.py",
        '_ROOT_DOC_NAMES = ("README.md", "CLAUDE.md")\n',
    )
    result = scaffold.scan_surface(tmp_path)
    assert result["judgment"] == []
    assert result["mechanical"] == []


def test_scan_does_not_exempt_claude_md_elsewhere(tmp_path):
    _write(tmp_path, "review-docs/scaffold.py", "See CLAUDE.md for the rules.\n")
    result = scaffold.scan_surface(tmp_path)
    assert {"path": "review-docs/scaffold.py", "line": 1, "kind": "banned_phrase", "phrase": "CLAUDE.md"} in result["judgment"]


def test_scan_excludes_its_own_skill_directory(tmp_path):
    """This skill's own files necessarily document real ids/phrases as examples of what they
    detect -- excluded from the scan since a repo-only skill (never vendored) has nothing to be
    portable for. Simulates the real file: nested one level under skills_dir.
    """
    _write(
        tmp_path,
        "strip-project-references/scaffold.py",
        "References TASK-027 and CLAUDE.md and this repo's own convention.\n",
    )
    result = scaffold.scan_surface(tmp_path)
    assert result == {"mechanical": [], "judgment": []}


# ---------------------------------------------------------------------------
# apply_mechanical_fixes
# ---------------------------------------------------------------------------


def test_apply_mechanical_strips_id_only_parenthetical(tmp_path):
    path = _write(tmp_path, "a/SKILL.md", "next to this `SKILL.md` (TASK-024) — not in this prose.\n")
    changes = scaffold.apply_mechanical_fixes(tmp_path)
    assert changes == [{"path": "a/SKILL.md", "count": 1}]
    assert path.read_text() == "next to this `SKILL.md` — not in this prose.\n"


def test_apply_mechanical_nnn_ifies_bare_example(tmp_path):
    path = _write(tmp_path, "a/SKILL.md", "a specific task id (e.g. `TASK-016`) to work instead.\n")
    changes = scaffold.apply_mechanical_fixes(tmp_path)
    assert changes == [{"path": "a/SKILL.md", "count": 1}]
    assert path.read_text() == "a specific task id (e.g. `TASK-NNN`) to work instead.\n"


def test_apply_mechanical_leaves_judgment_bucket_untouched(tmp_path):
    original = "padded to three digits (SPEC-001\n§'ID allocation'). Archived files count too.\n"
    path = _write(tmp_path, "a/sync", original)
    changes = scaffold.apply_mechanical_fixes(tmp_path)
    assert changes == []
    assert path.read_text() == original


def test_apply_mechanical_leaves_banned_phrase_paragraph_untouched(tmp_path):
    original = "matching this repo's own `config.md` (TASK-021).\n"
    path = _write(tmp_path, "a/scaffold.py", original)
    changes = scaffold.apply_mechanical_fixes(tmp_path)
    # the id sits in the same (dirty) paragraph as the banned phrase, so it's judgment too --
    # even though "(TASK-021)" looks like the mechanical id-only-parenthetical shape.
    assert changes == []
    assert path.read_text() == original


def test_apply_mechanical_dry_run_writes_nothing(tmp_path):
    original = "next to this `SKILL.md` (TASK-024) — not in this prose.\n"
    path = _write(tmp_path, "a/SKILL.md", original)
    changes = scaffold.apply_mechanical_fixes(tmp_path, dry_run=True)
    assert changes == [{"path": "a/SKILL.md", "count": 1}]
    assert path.read_text() == original


def test_apply_mechanical_is_idempotent(tmp_path):
    _write(tmp_path, "a/SKILL.md", "next to this `SKILL.md` (TASK-024) — not in this prose.\n")
    scaffold.apply_mechanical_fixes(tmp_path)
    second_pass = scaffold.apply_mechanical_fixes(tmp_path)
    assert second_pass == []


# ---------------------------------------------------------------------------
# Subcommands -- real subprocesses
# ---------------------------------------------------------------------------


def _run(cwd, *args):
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args], cwd=cwd, capture_output=True, text=True
    )


def _git(args, cwd, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


def test_scan_subcommand(tmp_path):
    _git(["init", "-q"], cwd=tmp_path)
    _write(tmp_path, ".claude/skills/a/SKILL.md", "next to this `SKILL.md` (TASK-024) — not in this prose.\n")
    result = _run(tmp_path, "scan")
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["mechanical"] == [
        {"path": "a/SKILL.md", "line": 1, "kind": "id_parenthetical", "text": "(TASK-024)"}
    ]


def test_apply_mechanical_subcommand(tmp_path):
    _git(["init", "-q"], cwd=tmp_path)
    path = _write(
        tmp_path, ".claude/skills/a/SKILL.md", "next to this `SKILL.md` (TASK-024) — not in this prose.\n"
    )
    result = _run(tmp_path, "apply-mechanical")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"changed": [{"path": "a/SKILL.md", "count": 1}]}
    assert path.read_text() == "next to this `SKILL.md` — not in this prose.\n"


def test_apply_mechanical_subcommand_dry_run_flag(tmp_path):
    _git(["init", "-q"], cwd=tmp_path)
    original = "next to this `SKILL.md` (TASK-024) — not in this prose.\n"
    path = _write(tmp_path, ".claude/skills/a/SKILL.md", original)
    result = _run(tmp_path, "apply-mechanical", "--dry-run")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"changed": [{"path": "a/SKILL.md", "count": 1}]}
    assert path.read_text() == original


# ---------------------------------------------------------------------------
# Real repo dry run (testing strategy steps 3-4): this repo's own tree, right now, should scan
# clean and apply_mechanical_fixes should be a true no-op -- TASK-027 already did this by hand.
# ---------------------------------------------------------------------------


def test_scan_against_this_repos_real_skills_tree_is_clean():
    skills_dir = REPO_ROOT / ".claude" / "skills"
    result = scaffold.scan_surface(skills_dir)
    assert result == {"mechanical": [], "judgment": []}


def test_apply_mechanical_against_this_repos_real_skills_tree_is_a_noop():
    skills_dir = REPO_ROOT / ".claude" / "skills"
    changes = scaffold.apply_mechanical_fixes(skills_dir, dry_run=True)
    assert changes == []
