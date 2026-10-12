"""The reference check: committed files never cite tracker items."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "lib/reference_check.py"
CONFIG = """\
config_version = 1

[docs]
backend = "outline"

[kaneo]
project_slug = "EX"

[reference_check]
allow = ["KEY-NNN", "EX-0"]

[tracker]
backend = "kaneo"
"""


def make_repo(tmp_path, files):
    subprocess.run(["git", "init", "--quiet"], cwd=tmp_path, check=True)
    (tmp_path / ".sdlc").mkdir()
    (tmp_path / ".sdlc/config.toml").write_text(CONFIG)
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    return tmp_path


def run_check(repo):
    return subprocess.run(
        [sys.executable, str(SCRIPT)], capture_output=True, check=False, cwd=repo, text=True, timeout=30
    )


def test_a_committed_task_key_is_reported_with_its_path_and_line(tmp_path):
    repo = make_repo(tmp_path, {"docs/notes.md": "Intro.\nFixed in EX-12, see the PR.\n"})

    result = run_check(repo)

    assert result.returncode == 1
    assert result.stdout == "docs/notes.md:2: EX-12\n"


def test_a_legacy_id_is_reported(tmp_path):
    repo = make_repo(tmp_path, {"a.py": "# From TASK-7.\n", "b.md": "EPIC-001 and SPEC-3\n"})

    result = run_check(repo)

    assert result.returncode == 1
    assert result.stdout.splitlines() == ["a.py:1: TASK-7", "b.md:1: EPIC-001", "b.md:1: SPEC-3"]


def test_an_allowed_placeholder_passes(tmp_path):
    repo = make_repo(tmp_path, {"guide.md": "Cite a task as KEY-NNN, or EX-0 in examples.\n"})

    result = run_check(repo)

    assert result.returncode == 0, result.stdout
    assert result.stdout == ""


def test_an_untracked_file_is_never_reported(tmp_path):
    repo = make_repo(tmp_path, {"clean.md": "Nothing here.\n"})
    (repo / "scratch.md").write_text("EX-12\n")

    result = run_check(repo)

    assert result.returncode == 0, result.stdout
    assert result.stdout == ""


def test_a_clean_repo_prints_nothing_and_exits_0(tmp_path):
    repo = make_repo(tmp_path, {"README.md": "A project. EXTRA-12 and ex-12 aren't task keys.\n"})

    result = run_check(repo)

    assert result.returncode == 0, result.stdout
    assert result.stdout == ""
    assert result.stderr == ""


def test_a_binary_file_is_skipped(tmp_path):
    repo = make_repo(tmp_path, {})
    (repo / "image.png").write_bytes(b"\x89PNG\x00EX-12")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)

    result = run_check(repo)

    assert result.returncode == 0, result.stdout


def test_ci_runs_the_check():
    workflow = (ROOT / ".github/workflows/ci.yml").read_text()

    assert "python lib/reference_check.py" in workflow
