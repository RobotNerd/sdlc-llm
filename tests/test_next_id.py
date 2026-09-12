"""Unit tests for `.tasks/bin/sync next-id` (TASK-010).

Acceptance criteria this covers:
- next-id task -> TASK-021 given TASK-001..020
- next-id epic -> EPIC-002; next-id spec -> SPEC-002
- archived files are included in the max -- an id is never reused
- an unknown type exits non-zero with a usage message
- output is exactly the id plus a newline
"""

import subprocess
import sys
from pathlib import Path

import pytest

from sync import next_id

SYNC_PATH = Path(__file__).resolve().parent.parent / ".tasks" / "bin" / "sync"


def _write(path: Path, art_id: str, kind_prefix: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    extra = "\nstatus: todo\nblocked_by: []\nblocks: []" if kind_prefix == "TASK" else ""
    path.write_text(f"---\nid: {art_id}\ntitle: x{extra}\n---\n")


# ---------------------------------------------------------------------------
# next_id (library function)
# ---------------------------------------------------------------------------


def test_next_id_task_given_twenty_existing(tmp_path):
    for i in range(1, 21):
        _write(tmp_path / f"TASK-{i:03d}-x.md", f"TASK-{i:03d}", "TASK")
    assert next_id(tmp_path, "task") == "TASK-021"


def test_next_id_each_kind_is_independent(tmp_path):
    _write(tmp_path / "TASK-001-x.md", "TASK-001", "TASK")
    _write(tmp_path / "EPIC-001-x.md", "EPIC-001", "EPIC")
    _write(tmp_path / "specs" / "SPEC-001-x.md", "SPEC-001", "SPEC")
    assert next_id(tmp_path, "task") == "TASK-002"
    assert next_id(tmp_path, "epic") == "EPIC-002"
    assert next_id(tmp_path, "spec") == "SPEC-002"


def test_next_id_with_no_existing_artifacts_starts_at_one(tmp_path):
    assert next_id(tmp_path, "task") == "TASK-001"


def test_next_id_archived_files_count_toward_the_max(tmp_path):
    for i in range(1, 21):
        _write(tmp_path / f"TASK-{i:03d}-x.md", f"TASK-{i:03d}", "TASK")
    _write(tmp_path / "archive" / "TASK-050-x.md", "TASK-050", "TASK")
    assert next_id(tmp_path, "task") == "TASK-051"


def test_next_id_unknown_type_raises_value_error(tmp_path):
    with pytest.raises(ValueError, match="unknown id type"):
        next_id(tmp_path, "bogus")


def test_next_id_zero_padded_to_three_digits_even_past_999(tmp_path):
    _write(tmp_path / "TASK-999-x.md", "TASK-999", "TASK")
    assert next_id(tmp_path, "task") == "TASK-1000"  # not truncated -- just no longer padded


# ---------------------------------------------------------------------------
# CLI: exact output, exit codes (subprocess, exercising main() for real)
# ---------------------------------------------------------------------------


def _run(*args: str) -> subprocess.CompletedProcess:
    # main() resolves tasks_root from the script's own location (parent.parent
    # of .tasks/bin/sync), so these run against the real repo's .tasks/ --
    # the CLI wiring is a thin wrapper over next_id(), which is fully covered
    # against isolated fixtures above; this just exercises argv parsing.
    return subprocess.run(
        [sys.executable, str(SYNC_PATH), *args], capture_output=True, text=True
    )


def test_cli_next_id_task_output_is_exactly_the_id_and_a_newline():
    result = _run("next-id", "task")
    assert result.returncode == 0
    assert result.stdout.endswith("\n")
    assert result.stdout.count("\n") == 1
    assert result.stdout.strip().startswith("TASK-")
    assert result.stderr == ""


def test_cli_next_id_unknown_type_exits_non_zero_with_usage_message():
    result = _run("next-id", "bogus")
    assert result.returncode != 0
    assert "bogus" in result.stderr


def test_cli_next_id_missing_type_argument_exits_non_zero():
    result = _run("next-id")
    assert result.returncode != 0
