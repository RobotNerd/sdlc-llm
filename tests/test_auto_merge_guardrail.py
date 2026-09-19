"""The auto-merge marker and the guardrail changes that honour it (TASK-045).

`check_gh_pr_merge` is unchanged in shape -- deny unless `marker_present` -- but the hook's
dispatcher (`evaluate_bash_command`) now computes `marker_present` from a real marker file: a
Bash `gh pr merge <N>` is allowed only when the project has set `allow_auto_merge: true` AND a
valid, unexpired marker for exactly PR <N> (and its head commit) exists. The marker is written
only by `implement-task`'s scripted `auto-merge` path, after its critic/cap gates, just before the
merge; the guardrails also deny any Bash command or Edit/Write that touches the marker file, so a
bare model decision can't conjure one. That last part is a speed bump for a cooperative agent, not
a security boundary -- same posture as every other guardrail in this module.

Everything that matters is exercised against the real hook scripts over stdin, too.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

import guardrails

REPO_ROOT = Path(__file__).resolve().parent.parent
BASH_HOOK = REPO_ROOT / ".claude" / "hooks" / "pretooluse_bash.py"
EDIT_WRITE_HOOK = REPO_ROOT / ".claude" / "hooks" / "pretooluse_edit_write.py"

SHA = "a" * 40
MERGE_CMD = f"gh pr merge 12 --squash --match-head-commit {SHA}"


def _project(tmp_path, allow_auto_merge):
    (tmp_path / ".tasks").mkdir()
    (tmp_path / ".tasks" / "config.md").write_text(
        f"---\nworkflow_version: 1\ndefault_branch: main\nbranch_prefix: task-\nremote: origin\n"
        f"allow_auto_merge: {'true' if allow_auto_merge else 'false'}\n---\n"
    )
    return tmp_path


@pytest.fixture
def project(tmp_path):
    return _project(tmp_path, allow_auto_merge=True)


def _config(project):
    return guardrails.load_project_config(project)


# ---------------------------------------------------------------------------
# marker file helpers
# ---------------------------------------------------------------------------


def test_marker_path_is_under_dot_tmp(project):
    assert guardrails.auto_merge_marker_path(project) == project / ".tmp" / "auto-merge-marker.json"


def test_write_then_clear_the_marker(project):
    path = guardrails.write_auto_merge_marker(project, pr=12, head_sha=SHA)

    assert path.is_file()
    assert guardrails.clear_auto_merge_marker(project) is True
    assert not path.exists()
    assert guardrails.clear_auto_merge_marker(project) is False


def test_a_valid_marker_lets_the_exact_merge_through(project):
    guardrails.write_auto_merge_marker(project, pr=12, head_sha=SHA)

    assert guardrails.auto_merge_marker_valid(MERGE_CMD, project, _config(project)) is True


@pytest.mark.parametrize("command", [
    f"gh pr merge 13 --squash --match-head-commit {SHA}",       # a different PR
    "gh pr merge --squash",                                     # no PR named
    "gh pr merge 12 --squash",                                  # not bound to the reviewed head
    f"gh pr merge 12 --squash --match-head-commit {'b' * 40}",  # bound to a different head
    "gh pr merge",
], ids=["other-pr", "no-pr", "no-head-binding", "other-head", "bare"])
def test_a_marker_only_covers_its_own_pr_and_head(project, command):
    guardrails.write_auto_merge_marker(project, pr=12, head_sha=SHA)

    assert guardrails.auto_merge_marker_valid(command, project, _config(project)) is False


def test_no_marker_means_not_valid(project):
    assert guardrails.auto_merge_marker_valid(MERGE_CMD, project, _config(project)) is False


def test_an_expired_marker_is_not_valid(project):
    guardrails.write_auto_merge_marker(project, pr=12, head_sha=SHA, ttl_seconds=60, now=time.time() - 3600)

    assert guardrails.auto_merge_marker_valid(MERGE_CMD, project, _config(project)) is False


def test_a_marker_is_never_valid_unless_the_project_opted_in(tmp_path):
    project = _project(tmp_path, allow_auto_merge=False)
    guardrails.write_auto_merge_marker(project, pr=12, head_sha=SHA)

    assert guardrails.auto_merge_marker_valid(MERGE_CMD, project, _config(project)) is False


@pytest.mark.parametrize("content", ["{not json", "[]", '{"pr": 12}', '{"pr": 12, "head_sha": "x"}'])
def test_a_corrupt_or_incomplete_marker_is_not_valid(project, content):
    path = guardrails.auto_merge_marker_path(project)
    path.parent.mkdir()
    path.write_text(content)

    assert guardrails.auto_merge_marker_valid(MERGE_CMD, project, _config(project)) is False


# ---------------------------------------------------------------------------
# the dispatcher: `evaluate_bash_command` / `evaluate_edit_write`
# ---------------------------------------------------------------------------


def test_dispatcher_allows_the_marked_merge(project):
    guardrails.write_auto_merge_marker(project, pr=12, head_sha=SHA)

    assert guardrails.evaluate_bash_command(MERGE_CMD, project).allow is True


def test_dispatcher_denies_the_same_merge_without_a_marker(project):
    result = guardrails.evaluate_bash_command(MERGE_CMD, project)

    assert result.allow is False
    assert "gh pr merge" in result.reason


def test_dispatcher_denies_a_marked_merge_when_auto_merge_is_off(tmp_path):
    project = _project(tmp_path, allow_auto_merge=False)
    guardrails.write_auto_merge_marker(project, pr=12, head_sha=SHA)

    assert guardrails.evaluate_bash_command(MERGE_CMD, project).allow is False


def test_dispatcher_denies_a_different_pr_while_a_marker_exists(project):
    guardrails.write_auto_merge_marker(project, pr=12, head_sha=SHA)

    assert guardrails.evaluate_bash_command(f"gh pr merge 99 --squash --match-head-commit {SHA}", project).allow is False


@pytest.mark.parametrize("command", [
    "cat .tmp/auto-merge-marker.json",
    'echo \'{"pr": 12}\' > .tmp/auto-merge-marker.json',
    "rm -f .tmp/auto-merge-marker.json",
    "python3 -c \"open('.tmp/auto-merge-marker.json','w')\"",
])
def test_dispatcher_denies_any_bash_command_touching_the_marker(project, command):
    result = guardrails.evaluate_bash_command(command, project)

    assert result.allow is False
    assert "marker" in result.reason


@pytest.mark.parametrize("tool", ["Write", "Edit"])
def test_edit_write_denies_touching_the_marker(project, tool):
    result = guardrails.evaluate_edit_write(
        tool, {"file_path": str(project / ".tmp" / "auto-merge-marker.json"), "content": "{}"}, project
    )

    assert result.allow is False
    assert "marker" in result.reason


def test_edit_write_still_allows_ordinary_files(project):
    result = guardrails.evaluate_edit_write("Write", {"file_path": str(project / "notes.txt"), "content": "x"}, project)

    assert result.allow is True


# ---------------------------------------------------------------------------
# the real hook scripts, over stdin -- "verified against the real hook, not just this task's code"
# ---------------------------------------------------------------------------


def _run_hook(script, project, payload):
    return subprocess.run(
        [sys.executable, str(script)], input=json.dumps({**payload, "cwd": str(project)}),
        capture_output=True, text=True,
    )


def _bash(project, command):
    return _run_hook(BASH_HOOK, project, {"tool_name": "Bash", "tool_input": {"command": command}})


def test_bash_hook_allows_a_marked_merge_and_denies_it_without_the_marker(project):
    denied = _bash(project, MERGE_CMD)
    assert denied.returncode == 2
    assert "gh pr merge" in denied.stderr

    guardrails.write_auto_merge_marker(project, pr=12, head_sha=SHA)
    allowed = _bash(project, MERGE_CMD)
    assert allowed.returncode == 0, allowed.stderr
    assert allowed.stdout == ""

    guardrails.clear_auto_merge_marker(project)
    assert _bash(project, MERGE_CMD).returncode == 2


def test_bash_hook_denies_touching_the_marker(project):
    result = _bash(project, "cat .tmp/auto-merge-marker.json")

    assert result.returncode == 2
    assert "marker" in result.stderr


def test_edit_write_hook_denies_writing_the_marker(project):
    result = _run_hook(EDIT_WRITE_HOOK, project, {
        "tool_name": "Write",
        "tool_input": {"file_path": str(project / ".tmp" / "auto-merge-marker.json"), "content": "{}"},
    })

    assert result.returncode == 2
    assert "marker" in result.stderr
