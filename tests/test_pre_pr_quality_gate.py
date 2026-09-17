"""Unit and hook-script tests for `.tasks/bin/guardrails.py`'s pre-PR quality gate
(TASK-035): `gh pr create` denied unless `sync check`, `test_command`, `lint_command` (if
set), and `format_command` (if set, check-only) all pass.

Acceptance criteria this covers:
- each of the four gates independently denies `gh pr create` on failure, with the failing
  command's output attached
- all four passing allows `gh pr create` to proceed
- a `null` `lint_command`/`format_command` skips that gate entirely
- the hook never writes to the working tree under any outcome
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import guardrails
from test_sync_check import write_clean_repo

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_SCRIPT = REPO_ROOT / ".claude" / "hooks" / "pretooluse_bash.py"

_PASS = f'"{sys.executable}" -c "import sys; sys.exit(0)"'
_FAIL = f'"{sys.executable}" -c "import sys; print(\'boom\', file=sys.stderr); sys.exit(1)"'


def _git(args, cwd, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


def _status(cwd) -> str:
    return _git(["status", "--porcelain", "--untracked-files=all"], cwd=cwd).stdout


@pytest.fixture
def repo(tmp_path):
    """A real git repo with a clean, internally-consistent `.tasks/` tree (via
    `write_clean_repo`), committed clean. `config.md` carries no `test_command`/
    `lint_command`/`format_command` -- unit tests below pass those explicitly to
    `check_pre_pr_quality_gate` rather than relying on config parsing.
    """
    work = tmp_path / "work"
    work.mkdir()
    _git(["init", "-q"], cwd=work)
    _git(["config", "user.email", "t@example.com"], cwd=work)
    _git(["config", "user.name", "Test"], cwd=work)
    (work / ".tasks").mkdir()
    write_clean_repo(work / ".tasks")
    (work / ".tasks" / "config.md").write_text("---\nworkflow_version: 1\n---\n")
    _git(["add", "-A"], cwd=work)
    _git(["commit", "-q", "-m", "init"], cwd=work)
    _git(["branch", "-M", "main"], cwd=work)
    return work


# ---------------------------------------------------------------------------
# check_pre_pr_quality_gate -- direct calls, explicit commands
# ---------------------------------------------------------------------------


def test_ignores_unrelated_commands(repo):
    result = guardrails.check_pre_pr_quality_gate("git status", repo, _FAIL, _FAIL, _FAIL)
    assert result.allow is True


def test_allows_when_sync_clean_and_no_commands_configured(repo):
    result = guardrails.check_pre_pr_quality_gate("gh pr create --title x", repo, None, None, None)
    assert result.allow is True


def test_denies_on_sync_check_drift(repo):
    board = repo / ".tasks" / "BOARD.md"
    board.write_text(board.read_text().replace("1/2 done", "0/2 done"))
    result = guardrails.check_pre_pr_quality_gate("gh pr create --title x", repo, None, None, None)
    assert result.allow is False
    assert "sync check" in result.reason
    assert "EPIC-001" in result.reason


def test_denies_on_failing_test_command(repo):
    result = guardrails.check_pre_pr_quality_gate("gh pr create", repo, _FAIL, None, None)
    assert result.allow is False
    assert "boom" in result.reason


def test_allows_on_passing_test_command(repo):
    result = guardrails.check_pre_pr_quality_gate("gh pr create", repo, _PASS, None, None)
    assert result.allow is True


def test_null_lint_command_skips_the_gate_even_though_it_would_fail(repo):
    result = guardrails.check_pre_pr_quality_gate("gh pr create", repo, _PASS, None, None)
    assert result.allow is True


def test_denies_on_failing_lint_command(repo):
    result = guardrails.check_pre_pr_quality_gate("gh pr create", repo, _PASS, _FAIL, None)
    assert result.allow is False
    assert "boom" in result.reason


def test_null_format_command_skips_the_gate(repo):
    result = guardrails.check_pre_pr_quality_gate("gh pr create", repo, _PASS, _PASS, None)
    assert result.allow is True


def test_gates_run_in_order_test_before_lint(repo):
    """A failing `test_command` is reported even when `lint_command` would also fail --
    order shouldn't matter for allow/deny, just confirms the earlier gate's message wins.
    """
    result = guardrails.check_pre_pr_quality_gate("gh pr create", repo, _FAIL, _FAIL, None)
    assert result.allow is False
    assert "test_command" in result.reason


# ---------------------------------------------------------------------------
# format_command -- check-only, never left applied
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_with_file(repo):
    (repo / "a.txt").write_text("original\n")
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "add a.txt"], cwd=repo)
    return repo


def test_denies_and_reverts_when_format_command_would_change_a_tracked_file(repo_with_file):
    format_cmd = f'"{sys.executable}" -c "open(\'a.txt\', \'w\').write(\'formatted\\n\')"'
    result = guardrails.check_pre_pr_quality_gate(
        "gh pr create", repo_with_file, _PASS, None, format_cmd
    )
    assert result.allow is False
    assert "formatted" in result.reason
    assert (repo_with_file / "a.txt").read_text() == "original\n"
    assert _status(repo_with_file) == ""


def test_denies_and_removes_a_new_file_created_by_format_command(repo):
    format_cmd = f'"{sys.executable}" -c "open(\'new.txt\', \'w\').write(\'x\\n\')"'
    result = guardrails.check_pre_pr_quality_gate("gh pr create", repo, _PASS, None, format_cmd)
    assert result.allow is False
    assert not (repo / "new.txt").exists()
    assert _status(repo) == ""


def test_allows_when_format_command_makes_no_changes(repo_with_file):
    result = guardrails.check_pre_pr_quality_gate("gh pr create", repo_with_file, _PASS, None, _PASS)
    assert result.allow is True
    assert (repo_with_file / "a.txt").read_text() == "original\n"
    assert _status(repo_with_file) == ""


# ---------------------------------------------------------------------------
# evaluate_bash_command -- reads test_command/lint_command/format_command from config.md
# ---------------------------------------------------------------------------


def test_evaluate_bash_command_denies_gh_pr_create_on_a_failing_configured_test_command(repo):
    (repo / "fail.py").write_text("import sys\nsys.exit(1)\n")
    (repo / ".tasks" / "config.md").write_text(
        "---\nworkflow_version: 1\ntest_command: python3 fail.py\n---\n"
    )
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "configure test_command"], cwd=repo)
    result = guardrails.evaluate_bash_command("gh pr create --title x --body y", repo)
    assert result.allow is False
    assert "test_command" in result.reason


def test_evaluate_bash_command_allows_gh_pr_create_when_everything_passes(repo):
    (repo / "ok.py").write_text("import sys\nsys.exit(0)\n")
    (repo / ".tasks" / "config.md").write_text(
        "---\nworkflow_version: 1\ntest_command: python3 ok.py\n---\n"
    )
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "configure test_command"], cwd=repo)
    result = guardrails.evaluate_bash_command("gh pr create --title x --body y", repo)
    assert result.allow is True


# ---------------------------------------------------------------------------
# The hook script itself, as a real subprocess
# ---------------------------------------------------------------------------


def _run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)], input=json.dumps(payload), capture_output=True, text=True
    )


def _bash_payload(command: str, cwd: str) -> dict:
    return {
        "session_id": "test-session", "cwd": cwd, "hook_event_name": "PreToolUse",
        "tool_name": "Bash", "tool_input": {"command": command},
    }


def test_hook_script_denies_gh_pr_create_on_sync_drift(repo):
    board = repo / ".tasks" / "BOARD.md"
    board.write_text(board.read_text().replace("1/2 done", "0/2 done"))
    result = _run_hook(_bash_payload("gh pr create --title x", str(repo)))
    assert result.returncode == 2
    assert "sync check" in result.stderr


def test_hook_script_allows_gh_pr_create_on_a_clean_repo(repo):
    result = _run_hook(_bash_payload("gh pr create --title x", str(repo)))
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_hook_script_never_writes_to_the_tree(repo):
    (repo / "a.txt").write_text("original\n")
    (repo / "format.py").write_text("open('a.txt', 'w').write('changed\\n')\n")
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "add a.txt and format.py"], cwd=repo)
    (repo / ".tasks" / "config.md").write_text(
        "---\nworkflow_version: 1\nformat_command: python3 format.py\n---\n"
    )
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "configure format_command"], cwd=repo)
    result = _run_hook(_bash_payload("gh pr create --title x", str(repo)))
    assert result.returncode == 2
    assert _status(repo) == ""
