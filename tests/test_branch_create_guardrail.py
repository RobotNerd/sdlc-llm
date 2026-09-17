"""Unit and hook-script tests for `.tasks/bin/guardrails.py`'s branch-creation gate
(TASK-034): dirty tree (minus `ignored_paths`) and non-conforming branch names.

Acceptance criteria this covers:
- a dirty tree (ignoring configured `ignored_paths`) denies branch creation
- a clean tree with a non-conforming branch name denies branch creation
- a clean tree with a conforming branch name is allowed
- `ignored_paths: []` (the default) makes any dirty file block branch creation
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
    """A real git repo (no remote needed -- branch creation is checked locally) with a
    `.tasks/config.md` setting `branch_prefix`/`ignored_paths`, committed clean.
    """
    work = tmp_path / "work"
    work.mkdir()
    _git(["init", "-q"], cwd=work)
    _git(["config", "user.email", "t@example.com"], cwd=work)
    _git(["config", "user.name", "Test"], cwd=work)
    (work / ".tasks").mkdir()
    (work / ".tasks" / "config.md").write_text(
        "---\nworkflow_version: 1\nbranch_prefix: task-\nignored_paths: [.tmp/prompts.md]\n---\n"
    )
    (work / "README.md").write_text("# scratch\n")
    _git(["add", "-A"], cwd=work)
    _git(["commit", "-q", "-m", "init"], cwd=work)
    _git(["branch", "-M", "main"], cwd=work)
    return work


# ---------------------------------------------------------------------------
# branch_name_violation -- pure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "branch",
    ["task-001-a-slug", "task-052-re-scope-guidelines-md", "task-999-x"],
    ids=["short-slug", "long-slug", "single-char-slug"],
)
def test_branch_name_violation_none_for_conforming_names(branch):
    assert guardrails.branch_name_violation(branch, "task-") is None


@pytest.mark.parametrize(
    "branch",
    ["task001-x", "task-1-x", "task-001", "task-001-", "task-001--x", "feature/task-001-x", "main"],
    ids=["missing-dash", "not-3-digits", "no-slug", "trailing-dash", "double-dash", "has-slash", "no-prefix"],
)
def test_branch_name_violation_flags_non_conforming_names(branch):
    assert guardrails.branch_name_violation(branch, "task-") is not None


def test_branch_name_violation_respects_a_different_prefix():
    assert guardrails.branch_name_violation("work-003-x", "work-") is None
    assert guardrails.branch_name_violation("task-003-x", "work-") is not None


# ---------------------------------------------------------------------------
# dirty_tree_violation -- real git status
# ---------------------------------------------------------------------------


def test_dirty_tree_violation_empty_on_a_clean_repo(repo):
    assert guardrails.dirty_tree_violation(repo, ()) == []


def test_dirty_tree_violation_reports_an_untracked_file(repo):
    (repo / "scratch.txt").write_text("dirty\n")
    assert guardrails.dirty_tree_violation(repo, ()) == ["scratch.txt"]


def test_dirty_tree_violation_excludes_ignored_paths(repo):
    (repo / ".tmp").mkdir()
    (repo / ".tmp" / "prompts.md").write_text("wip\n")
    (repo / "other.txt").write_text("also dirty\n")
    assert guardrails.dirty_tree_violation(repo, (".tmp/prompts.md",)) == ["other.txt"]


def test_dirty_tree_violation_with_no_ignored_paths_flags_everything(repo):
    (repo / ".tmp").mkdir()
    (repo / ".tmp" / "prompts.md").write_text("wip\n")
    assert guardrails.dirty_tree_violation(repo, ()) == [".tmp/prompts.md"]


# ---------------------------------------------------------------------------
# check_branch_create / evaluate_bash_command
# ---------------------------------------------------------------------------


def test_check_branch_create_allows_a_clean_conforming_checkout(repo):
    result = guardrails.check_branch_create(
        "git checkout -b task-035-x", repo, "task-", (".tmp/prompts.md",)
    )
    assert result.allow is True


def test_check_branch_create_allows_a_clean_conforming_switch(repo):
    result = guardrails.check_branch_create(
        "git switch -c task-035-x", repo, "task-", (".tmp/prompts.md",)
    )
    assert result.allow is True


def test_check_branch_create_denies_on_a_dirty_tree(repo):
    (repo / "scratch.txt").write_text("dirty\n")
    result = guardrails.check_branch_create(
        "git checkout -b task-035-x", repo, "task-", (".tmp/prompts.md",)
    )
    assert result.allow is False
    assert "scratch.txt" in result.reason


def test_check_branch_create_allows_when_only_ignored_paths_are_dirty(repo):
    (repo / ".tmp").mkdir()
    (repo / ".tmp" / "prompts.md").write_text("wip\n")
    result = guardrails.check_branch_create(
        "git checkout -b task-035-x", repo, "task-", (".tmp/prompts.md",)
    )
    assert result.allow is True


def test_check_branch_create_denies_a_non_conforming_name_on_a_clean_tree(repo):
    result = guardrails.check_branch_create(
        "git checkout -b my-random-branch", repo, "task-", (".tmp/prompts.md",)
    )
    assert result.allow is False
    assert "my-random-branch" in result.reason


def test_check_branch_create_default_ignored_paths_empty_flags_any_dirty_file(repo):
    (repo / "scratch.txt").write_text("dirty\n")
    result = guardrails.check_branch_create("git checkout -b task-035-x", repo, "task-", ())
    assert result.allow is False


def test_check_branch_create_ignores_unrelated_commands(repo):
    result = guardrails.check_branch_create("git status", repo, "task-", ())
    assert result.allow is True


def test_check_branch_create_ignores_a_plain_checkout_of_an_existing_branch(repo):
    result = guardrails.check_branch_create("git checkout main", repo, "task-", ())
    assert result.allow is True


def test_evaluate_bash_command_denies_dirty_tree_branch_creation(repo):
    (repo / "scratch.txt").write_text("dirty\n")
    result = guardrails.evaluate_bash_command("git checkout -b task-035-x", repo)
    assert result.allow is False


def test_evaluate_bash_command_allows_a_clean_conforming_branch_creation(repo):
    result = guardrails.evaluate_bash_command("git checkout -b task-035-x", repo)
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


def test_hook_script_allows_a_clean_conforming_branch_creation(repo):
    result = _run_hook(_bash_payload("git checkout -b task-035-x", str(repo)))
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_hook_script_denies_dirty_and_not_ignored(repo):
    (repo / "scratch.txt").write_text("dirty\n")
    result = _run_hook(_bash_payload("git checkout -b task-035-x", str(repo)))
    assert result.returncode == 2
    assert "scratch.txt" in result.stderr


def test_hook_script_allows_dirty_but_ignored(repo):
    (repo / ".tmp").mkdir()
    (repo / ".tmp" / "prompts.md").write_text("wip\n")
    result = _run_hook(_bash_payload("git switch -c task-035-x", str(repo)))
    assert result.returncode == 0


def test_hook_script_denies_a_clean_tree_with_a_bad_branch_name(repo):
    result = _run_hook(_bash_payload("git checkout -b whatever-i-want", str(repo)))
    assert result.returncode == 2
    assert "whatever-i-want" in result.stderr
