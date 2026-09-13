"""Unit tests for `.tasks/bin/sync archive` (TASK-011).

Acceptance criteria this covers:
- done/wont-do task files move to .tasks/archive/, preserving filename
- a one-line reference remains discoverable with title + pr (satisfied by
  the moved file itself plus BOARD.md's existing done column -- see the
  Worklog and archive()'s docstring for why no separate index is built)
- archived files still count for sync next-id (verified in TASK-010)
- should_auto_archive() reads config.md's archive_done key
- moving is idempotent
- fixture repo with one done, one wont-do, one todo task
"""

from pathlib import Path

from sync import archive, find_archivable, next_id, should_auto_archive


def _write(path: Path, art_id: str, status: str, pr=None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pr_line = f"\npr: {pr}" if pr else "\npr: null"
    path.write_text(
        f"---\nid: {art_id}\ntitle: x{pr_line}\nstatus: {status}\n"
        "blocked_by: []\nblocks: []\n---\nbody\n"
    )


def _fixture_repo(root: Path) -> None:
    _write(root / "TASK-001-x.md", "TASK-001", "done", pr="https://x/pr/1")
    _write(root / "TASK-002-x.md", "TASK-002", "wont-do")
    _write(root / "TASK-003-x.md", "TASK-003", "todo")


# ---------------------------------------------------------------------------
# find_archivable / archive
# ---------------------------------------------------------------------------


def test_find_archivable_selects_done_and_wont_do_only(tmp_path):
    _fixture_repo(tmp_path)
    assert set(find_archivable(tmp_path)) == {"TASK-001", "TASK-002"}


def test_archive_moves_done_and_wont_do_preserving_filename(tmp_path):
    _fixture_repo(tmp_path)
    moved = archive(tmp_path)
    assert {p.name for p in moved} == {"TASK-001-x.md", "TASK-002-x.md"}
    assert (tmp_path / "archive" / "TASK-001-x.md").is_file()
    assert (tmp_path / "archive" / "TASK-002-x.md").is_file()
    assert not (tmp_path / "TASK-001-x.md").exists()
    assert not (tmp_path / "TASK-002-x.md").exists()


def test_archive_leaves_todo_tasks_in_place(tmp_path):
    _fixture_repo(tmp_path)
    archive(tmp_path)
    assert (tmp_path / "TASK-003-x.md").is_file()
    assert not (tmp_path / "archive" / "TASK-003-x.md").exists()


def test_archive_preserves_frontmatter_untouched(tmp_path):
    _fixture_repo(tmp_path)
    original = (tmp_path / "TASK-001-x.md").read_text()
    archive(tmp_path)
    assert (tmp_path / "archive" / "TASK-001-x.md").read_text() == original


def test_archive_reference_still_carries_title_and_pr(tmp_path):
    # AC #2: title + pr remain discoverable -- via the moved file itself
    _fixture_repo(tmp_path)
    archive(tmp_path)
    from sync import discover

    art = discover(tmp_path)["TASK-001"]
    assert art.fields["title"] == "x"
    assert art.fields["pr"] == "https://x/pr/1"
    assert art.path == tmp_path / "archive" / "TASK-001-x.md"


def test_archive_is_idempotent(tmp_path):
    _fixture_repo(tmp_path)
    first = archive(tmp_path)
    second = archive(tmp_path)
    assert len(first) == 2
    assert second == []


def test_archive_with_nothing_to_archive_moves_nothing(tmp_path):
    _write(tmp_path / "TASK-001-x.md", "TASK-001", "todo")
    assert archive(tmp_path) == []


# ---------------------------------------------------------------------------
# archived files still count for next-id (cross-check with TASK-010)
# ---------------------------------------------------------------------------


def test_archived_files_still_count_for_next_id(tmp_path):
    _fixture_repo(tmp_path)
    archive(tmp_path)
    # TASK-001 and TASK-002 are now in .tasks/archive/; next id must be 004
    assert next_id(tmp_path, "task") == "TASK-004"


# ---------------------------------------------------------------------------
# should_auto_archive
# ---------------------------------------------------------------------------


def test_should_auto_archive_true_by_default():
    assert should_auto_archive({}) is True


def test_should_auto_archive_respects_explicit_true_and_false():
    assert should_auto_archive({"archive_done": True}) is True
    assert should_auto_archive({"archive_done": False}) is False
