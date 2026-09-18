"""Unit/integration tests for `.claude/skills/init-project/scaffold.py` (TASK-021).

`render_config`/`missing_keys` are tested directly (imported by file path, like
`.tasks/bin/sync` in `conftest.py` — this module lives outside any installable package). The
`run` subcommand is exercised as a real subprocess against real scratch git repos in `tmp_path`,
since its whole job is filesystem + git side effects, not pure computation.
"""

import importlib.util
import json
import re
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

import sync as sync_mod  # loaded by conftest.py from .tasks/bin/sync

SKILL_DIR = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "init-project"
SCRIPT_PATH = SKILL_DIR / "scaffold.py"

_loader = SourceFileLoader("init_project_scaffold", str(SCRIPT_PATH))
_spec = importlib.util.spec_from_loader("init_project_scaffold", _loader)
scaffold = importlib.util.module_from_spec(_spec)
sys.modules["init_project_scaffold"] = scaffold
_loader.exec_module(scaffold)


SAMPLE_ANSWERS = {
    "test_command": "pytest",
    "lint_command": None,
    "format_command": None,
    "docs_paths": ["README.md"],
    "default_branch": "main",
    "branch_prefix": "task-",
    "remote": "origin",
    "rebase_before_pr": True,
    "merge_strategy": "squash",
    "delete_branch_after_merge": True,
    "ci_checks": [],
    "archive_done": True,
}


def _init_git_repo(path):
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=path, check=True)
    (path / "README.md").write_text("# scratch\n")
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


def _run_scaffold(cwd, answers_path):
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "run", str(answers_path)],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# render_config / missing_keys
# ---------------------------------------------------------------------------


def test_render_config_fills_every_placeholder():
    text = scaffold.render_config(SAMPLE_ANSWERS)
    assert "{{" not in text
    assert "test_command: pytest" in text
    assert "lint_command: null" in text
    assert "docs_paths: [README.md]" in text
    assert "rebase_before_pr: true" in text
    assert "ci_checks: []" in text


def test_render_config_drops_leading_comment():
    text = scaffold.render_config(SAMPLE_ANSWERS)
    assert not text.startswith("<!--")
    assert text.startswith("---\n")


def test_init_project_missing_keys_empty_when_all_present():
    assert scaffold.missing_keys(SAMPLE_ANSWERS) == []


def test_init_project_missing_keys_reports_absent_ones():
    incomplete = dict(SAMPLE_ANSWERS)
    del incomplete["merge_strategy"]
    assert scaffold.missing_keys(incomplete) == ["merge_strategy"]


# ---------------------------------------------------------------------------
# `merge_gitignore` (TASK-066) -- pure function, hand-built fixtures
# ---------------------------------------------------------------------------


def test_merge_gitignore_creates_the_block_when_the_file_is_absent():
    merged, added = scaffold.merge_gitignore("")
    assert added == ["__pycache__/", "*.py[cod]", ".pytest_cache/"]
    assert merged == "# Python (added by init-project)\n__pycache__/\n*.py[cod]\n.pytest_cache/\n"


def test_merge_gitignore_appends_after_a_projects_existing_entries():
    merged, added = scaffold.merge_gitignore("node_modules/\n*.log\n")
    assert added == ["__pycache__/", "*.py[cod]", ".pytest_cache/"]
    assert merged == (
        "node_modules/\n*.log\n\n"
        "# Python (added by init-project)\n__pycache__/\n*.py[cod]\n.pytest_cache/\n"
    )
    assert "node_modules/\n*.log\n" in merged  # existing content untouched, not reordered


def test_merge_gitignore_handles_a_missing_trailing_newline():
    merged, added = scaffold.merge_gitignore("node_modules/")
    assert added == ["__pycache__/", "*.py[cod]", ".pytest_cache/"]
    assert merged.startswith("node_modules/\n\n# Python (added by init-project)\n")


def test_merge_gitignore_noop_when_all_entries_already_present():
    project = "__pycache__/\n*.py[cod]\n.pytest_cache/\n"
    merged, added = scaffold.merge_gitignore(project)
    assert added == []
    assert merged == project


@pytest.mark.parametrize(
    "existing_line",
    ["__pycache__", "__pycache__/", "**/__pycache__/", "**/__pycache__"],
    ids=["bare", "trailing-slash", "double-star-prefixed", "double-star-prefixed-bare"],
)
def test_merge_gitignore_recognizes_pycache_spelling_variants(existing_line):
    _, added = scaffold.merge_gitignore(existing_line + "\n")
    assert "__pycache__/" not in added


@pytest.mark.parametrize("existing_line", ["*.pyc", "*.py[cod]"], ids=["pyc-glob", "brace-glob"])
def test_merge_gitignore_recognizes_pyc_spelling_variants(existing_line):
    _, added = scaffold.merge_gitignore(existing_line + "\n")
    assert "*.py[cod]" not in added


@pytest.mark.parametrize(
    "existing_line", [".pytest_cache", ".pytest_cache/"], ids=["bare", "trailing-slash"]
)
def test_merge_gitignore_recognizes_pytest_cache_spelling_variants(existing_line):
    _, added = scaffold.merge_gitignore(existing_line + "\n")
    assert ".pytest_cache/" not in added


def test_merge_gitignore_ignores_comments_and_blank_lines_when_scanning():
    merged, added = scaffold.merge_gitignore("# __pycache__/\n\n*.log\n")
    assert added == ["__pycache__/", "*.py[cod]", ".pytest_cache/"]
    # the commented-out line is left alone; a real, uncommented entry is still appended
    assert merged.startswith("# __pycache__/\n\n*.log\n")
    assert "\n__pycache__/\n" in merged


def test_merge_gitignore_adds_only_the_genuinely_missing_subset():
    merged, added = scaffold.merge_gitignore("__pycache__/\n*.log\n")
    assert added == ["*.py[cod]", ".pytest_cache/"]
    assert "__pycache__/\n*.log\n" in merged
    assert merged.count("__pycache__/") == 1


def test_merge_gitignore_is_idempotent():
    once, added_once = scaffold.merge_gitignore("*.log\n")
    twice, added_twice = scaffold.merge_gitignore(once)
    assert added_once != []
    assert added_twice == []
    assert twice == once


def test_merge_gitignore_does_not_mutate_a_missing_file_case_repeatedly():
    # calling twice from "" both times (not chained) always yields the identical full block --
    # confirms the function has no hidden state across calls.
    first, _ = scaffold.merge_gitignore("")
    second, _ = scaffold.merge_gitignore("")
    assert first == second


# ---------------------------------------------------------------------------
# `run` subcommand, against real scratch git repos
# ---------------------------------------------------------------------------


def _setup_tasks_already_exists(tmp_path):
    _init_git_repo(tmp_path)
    (tmp_path / ".tasks").mkdir()
    return SAMPLE_ANSWERS


def _setup_not_a_git_repo(tmp_path):
    return SAMPLE_ANSWERS


def _setup_missing_required_answer(tmp_path):
    _init_git_repo(tmp_path)
    incomplete = dict(SAMPLE_ANSWERS)
    del incomplete["merge_strategy"]
    return incomplete


@pytest.mark.parametrize(
    "setup,needle",
    [
        (_setup_tasks_already_exists, "already exists"),
        (_setup_not_a_git_repo, None),
        (_setup_missing_required_answer, "merge_strategy"),
    ],
    ids=["tasks-already-exists", "not-a-git-repo", "missing-required-answer"],
)
def test_run_refuses(tmp_path, setup, needle):
    answers = setup(tmp_path)
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(answers))

    result = _run_scaffold(tmp_path, answers_path)

    assert result.returncode != 0
    if needle:
        assert needle in result.stderr
    assert not (tmp_path / ".tasks" / "config.md").exists()


def test_run_scaffolds_a_fresh_repo_and_sync_check_is_clean(tmp_path):
    _init_git_repo(tmp_path)
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(SAMPLE_ANSWERS))

    result = _run_scaffold(tmp_path, answers_path)
    assert result.returncode == 0, result.stderr

    for rel in (
        ".tasks/config.md",
        ".tasks/guidelines.md",
        ".tasks/BOARD.md",
        ".tasks/bin/sync",
        ".tasks/templates/spec.md",
        ".tasks/templates/epic.md",
        ".tasks/templates/task.md",
        ".github/pull_request_template.md",
    ):
        assert (tmp_path / rel).exists(), rel

    check = subprocess.run(
        [sys.executable, str(tmp_path / ".tasks" / "bin" / "sync"), "check"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert check.returncode == 0, check.stdout + check.stderr

    fields, _body, _order = sync_mod.parse_frontmatter((tmp_path / ".tasks" / "config.md").read_text())
    assert fields["ignored_paths"] == []


# ---------------------------------------------------------------------------
# `run`'s `.gitignore` merge (TASK-066)
# ---------------------------------------------------------------------------


def test_run_creates_gitignore_when_the_target_has_none(tmp_path):
    _init_git_repo(tmp_path)
    assert not (tmp_path / ".gitignore").exists()
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(SAMPLE_ANSWERS))

    result = _run_scaffold(tmp_path, answers_path)

    assert result.returncode == 0, result.stderr
    gitignore = (tmp_path / ".gitignore").read_text()
    assert "__pycache__/" in gitignore
    assert "*.py[cod]" in gitignore
    assert ".pytest_cache/" in gitignore
    assert "added" in result.stdout


def test_run_preserves_an_existing_gitignore_and_adds_only_missing_entries(tmp_path):
    _init_git_repo(tmp_path)
    (tmp_path / ".gitignore").write_text("node_modules/\n__pycache__/\n")
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(SAMPLE_ANSWERS))

    result = _run_scaffold(tmp_path, answers_path)

    assert result.returncode == 0, result.stderr
    gitignore = (tmp_path / ".gitignore").read_text()
    assert gitignore.startswith("node_modules/\n__pycache__/\n")
    assert "*.py[cod]" in gitignore
    assert ".pytest_cache/" in gitignore
    assert gitignore.count("__pycache__/") == 1  # not duplicated


def test_run_reports_nothing_needed_when_gitignore_already_covers_python(tmp_path):
    _init_git_repo(tmp_path)
    (tmp_path / ".gitignore").write_text("__pycache__/\n*.py[cod]\n.pytest_cache/\n")
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(SAMPLE_ANSWERS))

    result = _run_scaffold(tmp_path, answers_path)

    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".gitignore").read_text() == "__pycache__/\n*.py[cod]\n.pytest_cache/\n"
    assert "nothing needed" in result.stdout


def test_run_scaffolds_a_fresh_repo_with_no_dangling_ids(tmp_path):
    """id-grep over the actual scaffolded *output*, not just the template sources --
    catches a stray hardcoded id that a template edit could reintroduce (TASK-027).
    """
    _init_git_repo(tmp_path)
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(SAMPLE_ANSWERS))

    result = _run_scaffold(tmp_path, answers_path)
    assert result.returncode == 0, result.stderr

    id_pattern = re.compile(r"\b(?:TASK|EPIC|SPEC)-\d{3}\b")
    offenders = []
    for rel_dir in (".tasks", ".github"):
        for path in (tmp_path / rel_dir).rglob("*"):
            if path.is_file():
                match = id_pattern.search(path.read_text())
                if match:
                    offenders.append(f"{path.relative_to(tmp_path)}: {match.group(0)}")
    assert offenders == [], "scaffolded output contains dangling ids:\n" + "\n".join(offenders)


def test_run_refuses_second_time_in_same_repo(tmp_path):
    _init_git_repo(tmp_path)
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(SAMPLE_ANSWERS))

    first = _run_scaffold(tmp_path, answers_path)
    assert first.returncode == 0

    second = _run_scaffold(tmp_path, answers_path)
    assert second.returncode != 0
    assert "already exists" in second.stderr


# ---------------------------------------------------------------------------
# `run --target` (TASK-049) -- scaffolding a separate project by path, from an unrelated cwd
# ---------------------------------------------------------------------------


def _run_scaffold_target(cwd, answers_path, target, *extra_args):
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "run", str(answers_path), "--target", str(target), *extra_args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def test_run_with_target_scaffolds_full_skill_table_into_a_separate_repo(tmp_path):
    cwd = tmp_path / "unrelated-cwd"
    cwd.mkdir()
    target = tmp_path / "target-repo"
    target.mkdir()
    _init_git_repo(target)
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(SAMPLE_ANSWERS))

    result = _run_scaffold_target(cwd, answers_path, target)
    assert result.returncode == 0, result.stderr

    for rel in (
        ".tasks/BOARD.md",
        ".tasks/config.md",
        ".tasks/bin/sync",
        ".tasks/bin/guardrails.py",
        ".claude/settings.json",
        ".claude/hooks/pretooluse_bash.py",
        ".claude/hooks/pretooluse_edit_write.py",
        ".github/pull_request_template.md",
        ".claude/skills/add-task/SKILL.md",
        ".claude/skills/init-project/SKILL.md",
    ):
        assert (target / rel).exists(), rel
    assert (target / ".tasks" / "bin" / "sync").stat().st_mode & 0o777 == 0o755
    assert (target / ".tasks" / "bin" / "guardrails.py").stat().st_mode & 0o777 == 0o755
    assert (target / ".claude" / "hooks" / "pretooluse_bash.py").stat().st_mode & 0o777 == 0o755
    assert (target / ".claude" / "hooks" / "pretooluse_edit_write.py").stat().st_mode & 0o777 == 0o755
    assert not (target / ".claude" / "skills" / "strip-project-references").exists()
    # nothing was written to the unrelated cwd
    assert not (cwd / ".tasks").exists()

    check = subprocess.run(
        [sys.executable, str(target / ".tasks" / "bin" / "sync"), "check"],
        cwd=target, capture_output=True, text=True,
    )
    assert check.returncode == 0, check.stdout + check.stderr


def test_run_with_target_manifest_covers_skill_files(tmp_path):
    target = tmp_path / "target-repo"
    target.mkdir()
    _init_git_repo(target)
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(SAMPLE_ANSWERS))

    result = _run_scaffold_target(tmp_path, answers_path, target)
    assert result.returncode == 0, result.stderr

    manifest = scaffold.load_manifest(target)
    assert ".claude/skills/add-task/SKILL.md" in manifest["files"]


def _nonexistent_target(tmp_path):
    return tmp_path / "does-not-exist"


def _non_git_target(tmp_path):
    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    return plain_dir


@pytest.mark.parametrize(
    "make_target",
    [_nonexistent_target, _non_git_target],
    ids=["nonexistent-path", "not-a-git-repo"],
)
def test_run_target_bad_path_exits_nonzero(tmp_path, make_target):
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(SAMPLE_ANSWERS))
    target = make_target(tmp_path)

    result = _run_scaffold_target(tmp_path, answers_path, target)

    assert result.returncode != 0
    assert str(target) in result.stderr


def test_run_target_already_has_tasks_dir_exits_2(tmp_path):
    target = tmp_path / "target-repo"
    target.mkdir()
    _init_git_repo(target)
    (target / ".tasks").mkdir()
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(SAMPLE_ANSWERS))

    result = _run_scaffold_target(tmp_path, answers_path, target)

    assert result.returncode == 2
    assert "already exists" in result.stderr


def test_run_target_conflict_refuses_then_force_overwrites(tmp_path):
    target = tmp_path / "target-repo"
    target.mkdir()
    _init_git_repo(target)
    conflicting = target / ".claude" / "skills" / "add-task" / "SKILL.md"
    conflicting.parent.mkdir(parents=True)
    conflicting.write_text("# a pre-existing, unrelated add-task doc\n")
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(SAMPLE_ANSWERS))

    refused = _run_scaffold_target(tmp_path, answers_path, target)
    assert refused.returncode != 0
    assert "add-task/SKILL.md" in refused.stderr
    assert "--force" in refused.stderr
    assert conflicting.read_text() == "# a pre-existing, unrelated add-task doc\n"
    assert not (target / ".tasks").exists()

    forced = _run_scaffold_target(tmp_path, answers_path, target, "--force")
    assert forced.returncode == 0, forced.stderr
    assert conflicting.read_text() != "# a pre-existing, unrelated add-task doc\n"
    assert (target / ".tasks" / "BOARD.md").exists()
