"""Unit and hook-script tests for `.tasks/bin/guardrails.py` and the `PreToolUse`/`Bash` hook
that calls it (TASK-032).

Acceptance criteria this covers:
- each of the three guardrails has a unit test on its pure function
- each has a hook-script test: representative `PreToolUse` stdin JSON in, `deny` for a
  violating `tool_input.command`, `allow` (no output) for everything else
- the vendored copies of `guardrails.py` and the hook script stay byte-identical to their
  canonical sources, and `.claude/settings.json` stays identical to its portable template
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import guardrails

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_SCRIPT = REPO_ROOT / ".claude" / "hooks" / "pretooluse_bash.py"


def _git(args, cwd, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


@pytest.fixture
def repo(tmp_path):
    """A bare `origin` + clone (`work`), with a minimal `.tasks/` already committed and
    pushed to `origin/main`: `config.md` (default_branch=main, remote=origin,
    branch_prefix=task-), `BOARD.md`, and one `done` task (`TASK-001`).
    """
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(origin)], check=True)
    work = tmp_path / "work"
    _git(["clone", "-q", str(origin), str(work)], cwd=tmp_path)
    _git(["config", "user.email", "t@example.com"], cwd=work)
    _git(["config", "user.name", "Test"], cwd=work)

    (work / ".tasks").mkdir()
    (work / ".tasks" / "config.md").write_text(
        "---\nworkflow_version: 1\ndefault_branch: main\nbranch_prefix: task-\nremote: origin\n---\n"
    )
    (work / ".tasks" / "BOARD.md").write_text("# Board\n")
    (work / ".tasks" / "TASK-001-x.md").write_text(
        "---\nid: TASK-001\ntitle: a\nstatus: done\nepic: null\nbranch: null\npr: null\n"
        "merge_commit: null\nblocked_by: []\nblocks: []\n---\n"
    )
    (work / "README.md").write_text("# scratch\n")
    _git(["add", "-A"], cwd=work)
    _git(["commit", "-q", "-m", "init"], cwd=work)
    _git(["branch", "-M", "main"], cwd=work)
    _git(["push", "-u", "origin", "main"], cwd=work)
    return work


# ---------------------------------------------------------------------------
# Guardrail 1: `gh pr merge`
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    ["gh pr merge", "gh pr merge 123 --squash", "git status && gh pr merge --auto"],
    ids=["bare", "with-args", "chained"],
)
def test_check_gh_pr_merge_denies_without_a_marker(command):
    result = guardrails.check_gh_pr_merge(command)
    assert result.allow is False
    assert "gh pr merge" in result.reason


def test_check_gh_pr_merge_allows_when_marker_present():
    result = guardrails.check_gh_pr_merge("gh pr merge", marker_present=True)
    assert result.allow is True


def test_check_gh_pr_merge_ignores_unrelated_commands():
    assert guardrails.check_gh_pr_merge("gh pr create --title x").allow is True
    assert guardrails.check_gh_pr_merge("ls -la").allow is True


# ---------------------------------------------------------------------------
# Guardrail 2: pushing task work to `default_branch`
# ---------------------------------------------------------------------------


def test_check_push_to_default_branch_allows_non_push_commands():
    result = guardrails.check_push_to_default_branch(
        "git status", Path("/nonexistent"), default_branch="main", remote="origin"
    )
    assert result.allow is True


def test_check_push_to_default_branch_allows_push_to_a_task_branch():
    result = guardrails.check_push_to_default_branch(
        "git push origin task-001-x", Path("/nonexistent"), default_branch="main", remote="origin"
    )
    assert result.allow is True


def test_check_push_to_default_branch_allows_pure_bookkeeping_push(repo):
    board = repo / ".tasks" / "BOARD.md"
    board.write_text(board.read_text() + "\nsome update\n")
    task = repo / ".tasks" / "TASK-001-x.md"
    task.write_text(task.read_text().replace("merge_commit: null", "merge_commit: abc123"))
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "bookkeeping"], cwd=repo)

    result = guardrails.check_push_to_default_branch(
        "git push origin main", repo, default_branch="main", remote="origin"
    )
    assert result.allow is True, result.reason


def test_check_push_to_default_branch_denies_a_non_board_change(repo):
    (repo / "README.md").write_text("# scratch\nreal work\n")
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "real work"], cwd=repo)

    result = guardrails.check_push_to_default_branch(
        "git push origin main", repo, default_branch="main", remote="origin"
    )
    assert result.allow is False
    assert "README.md" in result.reason


def test_check_push_to_default_branch_denies_a_non_bookkeeping_task_field_change(repo):
    task = repo / ".tasks" / "TASK-001-x.md"
    task.write_text(task.read_text().replace("title: a", "title: a different title"))
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "sneaky title change"], cwd=repo)

    result = guardrails.check_push_to_default_branch(
        "git push origin main", repo, default_branch="main", remote="origin"
    )
    assert result.allow is False
    assert "TASK-001" in result.reason


def test_check_push_to_default_branch_allows_an_archive_move(repo):
    task = repo / ".tasks" / "TASK-001-x.md"
    text = task.read_text().replace("status: done", "status: wont-do")
    task.unlink()
    archive_dir = repo / ".tasks" / "archive"
    archive_dir.mkdir()
    (archive_dir / "TASK-001-x.md").write_text(text)
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "archive"], cwd=repo)

    result = guardrails.check_push_to_default_branch(
        "git push origin main", repo, default_branch="main", remote="origin"
    )
    assert result.allow is True, result.reason


# ---------------------------------------------------------------------------
# Guardrail 3: force-push misuse
# ---------------------------------------------------------------------------


def test_check_force_push_allows_a_plain_push():
    result = guardrails.check_force_push(
        "git push origin task-001-x", Path("/nonexistent"), branch_prefix="task-"
    )
    assert result.allow is True


def test_check_force_push_denies_bare_force():
    result = guardrails.check_force_push(
        "git push --force origin task-001-x", Path("/nonexistent"), branch_prefix="task-"
    )
    assert result.allow is False
    assert "--force-with-lease" in result.reason


def test_check_force_push_allows_lease_on_the_in_progress_task_branch(repo):
    task = repo / ".tasks" / "TASK-001-x.md"
    task.write_text(
        task.read_text().replace("status: done", "status: in-progress").replace(
            "branch: null", "branch: task-001-x"
        )
    )
    result = guardrails.check_force_push(
        "git push --force-with-lease origin task-001-x", repo, branch_prefix="task-"
    )
    assert result.allow is True, result.reason


def test_check_force_push_denies_lease_on_a_branch_that_is_not_in_progress(repo):
    # TASK-001 is `done`, not `in-progress`, with no branch set -- nothing makes
    # `task-001-x` the current task's own branch.
    result = guardrails.check_force_push(
        "git push --force-with-lease origin task-001-x", repo, branch_prefix="task-"
    )
    assert result.allow is False
    assert "task-001-x" in result.reason


def test_check_force_push_denies_lease_on_default_branch(repo):
    result = guardrails.check_force_push(
        "git push --force-with-lease origin main", repo, branch_prefix="task-"
    )
    assert result.allow is False


# ---------------------------------------------------------------------------
# evaluate_bash_command -- the dispatcher the hook script calls
# ---------------------------------------------------------------------------


def test_evaluate_bash_command_allows_an_ordinary_command(repo):
    result = guardrails.evaluate_bash_command("git status", repo)
    assert result.allow is True


def test_evaluate_bash_command_denies_gh_pr_merge(repo):
    result = guardrails.evaluate_bash_command("gh pr merge", repo)
    assert result.allow is False


def test_evaluate_bash_command_denies_a_non_board_push_to_default_branch(repo):
    (repo / "README.md").write_text("# scratch\nreal work\n")
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "real work"], cwd=repo)
    result = guardrails.evaluate_bash_command("git push origin main", repo)
    assert result.allow is False


# ---------------------------------------------------------------------------
# The hook script itself, as a real subprocess -- the documented `PreToolUse` stdin shape
# ---------------------------------------------------------------------------


def _run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK_SCRIPT)], input=json.dumps(payload), capture_output=True, text=True
    )


def _bash_payload(command: str, cwd: str) -> dict:
    return {
        "session_id": "test-session",
        "cwd": cwd,
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }


def test_hook_script_denies_gh_pr_merge(repo):
    result = _run_hook(_bash_payload("gh pr merge", str(repo)))
    assert result.returncode == 2
    assert "gh pr merge" in result.stderr


def test_hook_script_denies_a_default_branch_push_with_non_board_changes(repo):
    (repo / "README.md").write_text("# scratch\nreal work\n")
    _git(["add", "-A"], cwd=repo)
    _git(["commit", "-q", "-m", "real work"], cwd=repo)
    result = _run_hook(_bash_payload("git push origin main", str(repo)))
    assert result.returncode == 2
    assert "README.md" in result.stderr


def test_hook_script_denies_bare_force_push():
    result = _run_hook(_bash_payload("git push --force origin task-001-x", "/nonexistent"))
    assert result.returncode == 2
    assert "--force-with-lease" in result.stderr


def test_hook_script_denies_force_with_lease_on_the_wrong_branch(repo):
    result = _run_hook(_bash_payload("git push --force-with-lease origin main", str(repo)))
    assert result.returncode == 2


def test_hook_script_allows_an_ordinary_command_with_no_output(repo):
    result = _run_hook(_bash_payload("git status", str(repo)))
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_hook_script_ignores_non_bash_tool_calls():
    payload = {
        "session_id": "test-session", "cwd": "/nonexistent", "hook_event_name": "PreToolUse",
        "tool_name": "Read", "tool_input": {"file_path": "/etc/hosts"},
    }
    result = _run_hook(payload)
    assert result.returncode == 0
    assert result.stdout == ""


# ---------------------------------------------------------------------------
# Vendoring: the shipped copies must never silently drift from their canonical sources
# ---------------------------------------------------------------------------


def test_vendored_guardrails_is_byte_identical_to_tasks_bin_guardrails():
    vendored = REPO_ROOT / ".claude" / "skills" / "init-project" / "vendored-guardrails"
    canonical = REPO_ROOT / ".tasks" / "bin" / "guardrails.py"
    assert vendored.read_bytes() == canonical.read_bytes()


def test_vendored_hook_script_is_byte_identical_to_the_canonical_one():
    vendored = REPO_ROOT / ".claude" / "skills" / "init-project" / "vendored-hooks" / "pretooluse_bash.py"
    assert vendored.read_bytes() == HOOK_SCRIPT.read_bytes()


def test_settings_json_template_is_byte_identical_to_this_repos_own():
    template = REPO_ROOT / ".claude" / "skills" / "init-project" / "templates" / "settings.json"
    canonical = REPO_ROOT / ".claude" / "settings.json"
    assert template.read_bytes() == canonical.read_bytes()
