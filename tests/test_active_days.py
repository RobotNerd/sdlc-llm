"""Active days: days with commits to the default branch since a task was created."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "lib/active_days.py"
CONFIG = """\
config_version = 1
default_branch = "main"
remote = "origin"

[docs]
backend = "outline"

[tracker]
backend = "kaneo"
"""


def make_repo(tmp_path, commit_times):
    subprocess.run(["git", "init", "--quiet", "--initial-branch=main"], cwd=tmp_path, check=True)
    (tmp_path / ".sdlc").mkdir()
    (tmp_path / ".sdlc/config.toml").write_text(CONFIG)
    for number, when in enumerate(commit_times):
        (tmp_path / "file.txt").write_text(str(number))
        environment = {**os.environ, "GIT_AUTHOR_DATE": when, "GIT_COMMITTER_DATE": when}
        subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
        subprocess.run(
            ["git", "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "--quiet", "-m", "x"],
            cwd=tmp_path,
            check=True,
            env=environment,
        )
    return tmp_path


def run_script(repo, *created_at):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *created_at], capture_output=True, check=False, cwd=repo, text=True, timeout=30
    )


def test_each_day_with_commits_after_the_creation_time_counts_once(tmp_path):
    repo = make_repo(
        tmp_path,
        ["2026-09-01T10:00:00Z", "2026-09-02T10:00:00Z", "2026-09-02T15:00:00Z", "2026-09-05T10:00:00Z"],
    )

    result = run_script(repo, "2026-08-01T00:00:00Z", "2026-09-02T12:00:00Z", "2026-10-01T00:00:00Z")

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "2026-08-01T00:00:00Z": 3,
        "2026-09-02T12:00:00Z": 2,
        "2026-10-01T00:00:00Z": 0,
    }


def test_commits_off_the_default_branch_are_not_counted(tmp_path):
    repo = make_repo(tmp_path, ["2026-09-01T10:00:00Z"])
    subprocess.run(["git", "checkout", "--quiet", "-b", "feature"], cwd=repo, check=True)
    environment = {
        **os.environ,
        "GIT_AUTHOR_DATE": "2026-09-03T10:00:00Z",
        "GIT_COMMITTER_DATE": "2026-09-03T10:00:00Z",
    }
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "--quiet", "--allow-empty", "-m", "y"],
        cwd=repo,
        check=True,
        env=environment,
    )

    result = run_script(repo, "2026-08-01T00:00:00Z")

    assert json.loads(result.stdout) == {"2026-08-01T00:00:00Z": 1}


def test_a_missing_config_is_reported_with_exit_2(tmp_path):
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)

    result = run_script(tmp_path, "2026-08-01T00:00:00Z")

    assert result.returncode == 2
    assert "active days:" in result.stderr
