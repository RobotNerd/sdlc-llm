"""Unit/integration tests for `.claude/skills/review-docs/scaffold.py` (TASK-047).

`mirror_diff`/`find_path_references`/`dangling_references`/`claimed_skill_names`/
`skill_list_mismatch` are pure functions, tested directly against small fixtures. The four
subcommands are exercised as real subprocesses -- `report` both against a small isolated fixture
repo and (per the task's own testing strategy) against this repo's real, current docs.
"""

import importlib.util
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "review-docs"
SCRIPT_PATH = SKILL_DIR / "scaffold.py"

_loader = SourceFileLoader("review_docs_scaffold", str(SCRIPT_PATH))
_spec = importlib.util.spec_from_loader("review_docs_scaffold", _loader)
review_docs_scaffold = importlib.util.module_from_spec(_spec)
sys.modules["review_docs_scaffold"] = review_docs_scaffold
_loader.exec_module(review_docs_scaffold)


# ---------------------------------------------------------------------------
# mirror_diff
# ---------------------------------------------------------------------------


def test_mirror_diff_empty_when_identical(tmp_path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("same content\n")
    b.write_text("same content\n")
    assert review_docs_scaffold.mirror_diff(a, b) == []


def test_mirror_diff_reports_lines_when_diverging(tmp_path):
    a = tmp_path / "a.md"
    b = tmp_path / "b.md"
    a.write_text("line one\nline two\n")
    b.write_text("line one\nDIFFERENT\n")
    diff = review_docs_scaffold.mirror_diff(a, b)
    assert diff
    assert any("DIFFERENT" in line for line in diff)


# ---------------------------------------------------------------------------
# find_path_references / dangling_references
# ---------------------------------------------------------------------------


def test_find_path_references_extracts_real_looking_paths():
    text = (
        "See `.tasks/guidelines.md` and `CLAUDE.md` for the rules. "
        "Also `.claude/skills/init-project/SKILL.md`."
    )
    assert review_docs_scaffold.find_path_references(text) == [
        ".tasks/guidelines.md",
        "CLAUDE.md",
        ".claude/skills/init-project/SKILL.md",
    ]


@pytest.mark.parametrize("token", [
    "origin/main",
    "<remote>/<default_branch>",
    "sync check",
    "--force-with-lease",
    "TASK-NNN",
    "EPIC-*.md",
    "https://github.com/example/repo",
])
def test_find_path_references_ignores_non_paths(token):
    text = f"Run `{token}` as described."
    assert review_docs_scaffold.find_path_references(text) == []


def test_find_path_references_strips_trailing_punctuation():
    text = "See `README.md`, then `CLAUDE.md`."
    assert review_docs_scaffold.find_path_references(text) == ["README.md", "CLAUDE.md"]


def test_dangling_references_finds_missing_and_skips_ignored(tmp_path):
    (tmp_path / "README.md").write_text("# ok\n")
    doc = tmp_path / "doc.md"
    doc.write_text(
        "See `README.md` (exists), `.tasks/missing.md` (gone), and "
        "`.tmp/prompts.md` (ignored)."
    )
    missing = review_docs_scaffold.dangling_references(tmp_path, doc, ignore_paths={".tmp/prompts.md"})
    assert missing == [".tasks/missing.md"]


def test_dangling_references_empty_when_all_present(tmp_path):
    (tmp_path / "README.md").write_text("# ok\n")
    doc = tmp_path / "doc.md"
    doc.write_text("See `README.md`.")
    assert review_docs_scaffold.dangling_references(tmp_path, doc, ignore_paths=set()) == []


# ---------------------------------------------------------------------------
# claimed_skill_names / skill_list_mismatch
# ---------------------------------------------------------------------------


SKILL_LIST_TEXT = (
    "## Skills\n\n"
    "- **`add-task`** — interview a request.\n"
    "- **`implement-task`** — the four-phase loop.\n"
)


def test_claimed_skill_names_extracts_bullet_format():
    assert review_docs_scaffold.claimed_skill_names(SKILL_LIST_TEXT) == {"add-task", "implement-task"}


def test_claimed_skill_names_empty_for_unrecognized_format():
    assert review_docs_scaffold.claimed_skill_names("Skills: add-task, implement-task") == set()


def _make_skills_dir(root, names):
    skills_dir = root / ".claude" / "skills"
    skills_dir.mkdir(parents=True)
    for name in names:
        (skills_dir / name).mkdir()


def test_skill_list_mismatch_none_when_matching(tmp_path):
    _make_skills_dir(tmp_path, ["add-task", "implement-task"])
    doc = tmp_path / "doc.md"
    doc.write_text(SKILL_LIST_TEXT)
    assert review_docs_scaffold.skill_list_mismatch(tmp_path, doc) is None


def test_skill_list_mismatch_reports_missing_and_extra(tmp_path):
    _make_skills_dir(tmp_path, ["add-task", "plan-feature"])  # implement-task missing, plan-feature extra
    doc = tmp_path / "doc.md"
    doc.write_text(SKILL_LIST_TEXT)
    assert review_docs_scaffold.skill_list_mismatch(tmp_path, doc) == {
        "missing": ["plan-feature"],
        "extra": ["implement-task"],
    }


def test_skill_list_mismatch_none_when_doc_lists_nothing(tmp_path):
    _make_skills_dir(tmp_path, ["add-task"])
    doc = tmp_path / "doc.md"
    doc.write_text("No skill list here.")
    assert review_docs_scaffold.skill_list_mismatch(tmp_path, doc) is None


# ---------------------------------------------------------------------------
# Subcommands -- real subprocesses
# ---------------------------------------------------------------------------


def _git(args, cwd, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


@pytest.fixture
def fixture_repo(tmp_path):
    """A minimal real git repo -- `repo_root()` needs one -- with a couple of docs and a
    `.claude/skills/` directory, standing in for a real project without needing the full
    init-project/add-task scaffold chain (this skill doesn't touch `.tasks/` task files).
    """
    _git(["init", "-q"], cwd=tmp_path)
    _git(["config", "user.email", "t@example.com"], cwd=tmp_path)
    _git(["config", "user.name", "Test"], cwd=tmp_path)
    (tmp_path / "README.md").write_text(
        "# scratch\n\n## Skills\n\n"
        "- **`add-task`** — x.\n- **`implement-task`** — y.\n- **`init-project`** — z.\n"
    )
    (tmp_path / "CLAUDE.md").write_text("See `README.md` and `.tasks/missing.md`.\n")
    (tmp_path / ".tasks").mkdir()
    (tmp_path / ".tasks" / "guidelines.md").write_text("rules\n")
    _make_skills_dir(tmp_path, ["add-task", "implement-task"])
    (tmp_path / ".claude" / "skills" / "init-project").mkdir(exist_ok=True)
    (tmp_path / ".claude" / "skills" / "init-project" / "templates").mkdir()
    (tmp_path / ".claude" / "skills" / "init-project" / "templates" / "guidelines.md").write_text(
        "rules\n"
    )
    (tmp_path / ".tasks" / "config.md").write_text(
        "---\n"
        "docs_review_paths: [README.md, CLAUDE.md]\n"
        "docs_ignore_paths: [.tmp/prompts.md]\n"
        "---\n\n# config\n"
    )
    (tmp_path / ".tasks" / "bin").mkdir()
    sync_src = REPO_ROOT / ".tasks" / "bin" / "sync"
    (tmp_path / ".tasks" / "bin" / "sync").write_text(sync_src.read_text())
    _git(["add", "-A"], cwd=tmp_path)
    _git(["commit", "-q", "-m", "init"], cwd=tmp_path)
    return tmp_path


def _run(cwd, command, answers=None):
    args = [sys.executable, str(SCRIPT_PATH), command]
    if answers is not None:
        answers_path = cwd.parent / f"{command}-answers.json"
        answers_path.write_text(json.dumps(answers))
        args.append(str(answers_path))
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def test_mirror_diff_subcommand(fixture_repo):
    (fixture_repo / ".tasks" / "guidelines.md").write_text("rules v2\n")
    result = _run(fixture_repo, "mirror-diff", {
        "path_a": ".tasks/guidelines.md",
        "path_b": ".claude/skills/init-project/templates/guidelines.md",
    })
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["identical"] is False
    assert output["diff"]


def test_dangling_refs_subcommand(fixture_repo):
    result = _run(fixture_repo, "dangling-refs", {
        "doc_paths": ["CLAUDE.md"],
        "ignore_paths": [],
    })
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["dangling_references"] == {"CLAUDE.md": [".tasks/missing.md"]}


def test_skill_list_check_subcommand(fixture_repo):
    result = _run(fixture_repo, "skill-list-check", {"doc_paths": ["README.md"]})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"skill_list_mismatches": {}}


def test_report_subcommand_reads_config_and_finds_everything(fixture_repo):
    result = _run(fixture_repo, "report")
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["dangling_references"] == {"CLAUDE.md": [".tasks/missing.md"]}
    assert output["skill_list_mismatches"] == {}
    assert output["guidelines_mirror_diff"] is None  # both guidelines.md say "rules\n" identically


def test_report_subcommand_finds_guidelines_mirror_drift(fixture_repo):
    (fixture_repo / ".tasks" / "guidelines.md").write_text("rules v2\n")
    result = _run(fixture_repo, "report")
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["guidelines_mirror_diff"]


# ---------------------------------------------------------------------------
# Real repo dry run (testing strategy step 2): this repo's own docs, right now,
# should report clean -- TASK-023 already brought them up to date.
# ---------------------------------------------------------------------------


def test_report_against_this_repos_real_docs_is_clean():
    """`mirror_diff` reports the *raw* diff always -- judging whether a difference is expected
    (this repo's own extra specificity -- SPEC-001 pointers, an explicit skill path -- that the
    portable template correctly omits, per TASK-023) is `SKILL.md`'s job, not this function's. So
    the real repo's `guidelines.md` pair is expected to show a non-empty diff (they're
    deliberately not byte-identical); everything else should report clean, same as TASK-023 and
    TASK-047 left it.
    """
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "report"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["dangling_references"] == {}
    assert output["skill_list_mismatches"] == {}
    assert output["guidelines_mirror_diff"]  # non-empty: the documented intentional differences
