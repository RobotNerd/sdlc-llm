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


def test_missing_keys_empty_when_all_present():
    assert scaffold.missing_keys(SAMPLE_ANSWERS) == []


def test_missing_keys_reports_absent_ones():
    incomplete = dict(SAMPLE_ANSWERS)
    del incomplete["merge_strategy"]
    assert scaffold.missing_keys(incomplete) == ["merge_strategy"]


# ---------------------------------------------------------------------------
# `run` subcommand, against real scratch git repos
# ---------------------------------------------------------------------------


def test_run_refuses_if_tasks_already_exists(tmp_path):
    _init_git_repo(tmp_path)
    (tmp_path / ".tasks").mkdir()
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(SAMPLE_ANSWERS))

    result = _run_scaffold(tmp_path, answers_path)

    assert result.returncode != 0
    assert "already exists" in result.stderr
    assert not (tmp_path / ".tasks" / "config.md").exists()


def test_run_refuses_if_not_a_git_repo(tmp_path):
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(SAMPLE_ANSWERS))

    result = _run_scaffold(tmp_path, answers_path)

    assert result.returncode != 0
    assert not (tmp_path / ".tasks").exists()


def test_run_refuses_if_required_answer_missing(tmp_path):
    _init_git_repo(tmp_path)
    incomplete = dict(SAMPLE_ANSWERS)
    del incomplete["merge_strategy"]
    answers_path = tmp_path / "answers.json"
    answers_path.write_text(json.dumps(incomplete))

    result = _run_scaffold(tmp_path, answers_path)

    assert result.returncode != 0
    assert "merge_strategy" in result.stderr
    assert not (tmp_path / ".tasks").exists()


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
