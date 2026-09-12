"""Unit tests for `.tasks/bin/sync`'s BOARD.md epics panel and status
column renderers (TASK-008).

Acceptance criteria this covers:
- epics panel: header incl. Progress, one row per epic not done/wont-do,
  ordered by id
- column header `| Task | Title | Epic | Ref |`; Ref = branch for
  in-progress, pr (falling back to branch) otherwise; no epic -> "—"
- done column capped at the most recent N rows
- every empty region renders `_(none)_` (via the region engine)
- composes with replace_region; running twice is a no-op
- an empty board, and a board with a task in each status
"""

from pathlib import Path

import pytest

from sync import (
    Artifact,
    RegionError,
    ensure_region,
    render_board_column,
    render_board_epics_panel,
)


def make_epic(epic_id: str, status: str, title: str = "MVP") -> Artifact:
    fields = {"id": epic_id, "title": title, "status": status}
    return Artifact(id=epic_id, kind="epic", path=Path(f"{epic_id}.md"), fields=fields, order=list(fields), body="")


def make_task(task_id, status, title="x", epic=None, branch=None, pr=None) -> Artifact:
    fields = {"id": task_id, "status": status, "title": title, "epic": epic, "branch": branch, "pr": pr}
    return Artifact(id=task_id, kind="task", path=Path(f"{task_id}.md"), fields=fields, order=list(fields), body="")


# ---------------------------------------------------------------------------
# render_board_epics_panel
# ---------------------------------------------------------------------------


def test_epics_panel_empty_board_is_empty_string():
    assert render_board_epics_panel([]) == ""


def test_epics_panel_excludes_done_and_wont_do_epics():
    done_epic = make_epic("EPIC-001", "done")
    active_epic = make_epic("EPIC-002", "in-progress")
    wontdo_epic = make_epic("EPIC-003", "wont-do")
    result = render_board_epics_panel(
        [(done_epic, []), (active_epic, []), (wontdo_epic, [])]
    )
    assert "EPIC-001" not in result
    assert "EPIC-003" not in result
    assert "EPIC-002" in result


def test_epics_panel_matches_spec_001_worked_example():
    epic_a = make_epic("EPIC-002", "in-progress")
    children_a = [make_task(f"TASK-{i:03d}", "done" if i < 3 else "todo") for i in range(7)]
    epic_b = make_epic("EPIC-003", "todo")
    children_b = [make_task("TASK-100", "todo"), make_task("TASK-101", "todo")]
    result = render_board_epics_panel([(epic_a, children_a), (epic_b, children_b)])
    assert result == (
        "| Epic | Status | Progress |\n"
        "|---|---|---|\n"
        "| EPIC-002 | in-progress | 3/7 done |\n"
        "| EPIC-003 | todo | 0/2 done |"
    )


# ---------------------------------------------------------------------------
# render_board_column
# ---------------------------------------------------------------------------


def test_column_empty_board_all_columns_empty():
    for status in ("in-progress", "in-review", "blocked", "done"):
        assert render_board_column([], status) == ""


def test_column_one_task_in_each_status_lands_in_the_right_column():
    tasks = [
        make_task("TASK-001", "in-progress", "a", epic="EPIC-001", branch="task-001-a"),
        make_task("TASK-002", "in-review", "b", epic="EPIC-001", pr="https://x/pr/2"),
        make_task("TASK-003", "blocked", "c", epic="EPIC-001"),
        make_task("TASK-004", "done", "d", epic="EPIC-001", pr="https://x/pr/4"),
        make_task("TASK-005", "todo", "e"),  # not in any column
    ]
    for status, task_id in [
        ("in-progress", "TASK-001"),
        ("in-review", "TASK-002"),
        ("done", "TASK-004"),
    ]:
        result = render_board_column(tasks, status)
        assert task_id in result
        for other in ("TASK-001", "TASK-002", "TASK-003", "TASK-004", "TASK-005"):
            if other != task_id:
                assert other not in result

    blocked_result = render_board_column(tasks, "blocked")
    assert "TASK-003" in blocked_result
    assert "TASK-005" not in blocked_result  # todo tasks never appear in a status column


def test_column_ref_is_branch_for_in_progress():
    tasks = [make_task("TASK-001", "in-progress", "a", branch="task-001-a", pr="https://x/pr/1")]
    result = render_board_column(tasks, "in-progress")
    assert "task-001-a" in result
    assert "https://x/pr/1" not in result  # branch wins for in-progress, even if pr is set


def test_column_ref_is_pr_for_in_review_and_done():
    for status in ("in-review", "done"):
        tasks = [make_task("TASK-001", status, "a", branch="task-001-a", pr="https://x/pr/1")]
        result = render_board_column(tasks, status)
        assert "https://x/pr/1" in result
        assert "task-001-a" not in result


def test_column_ref_falls_back_to_branch_when_no_pr_yet():
    tasks = [make_task("TASK-001", "blocked", "a", branch="task-001-a", pr=None)]
    result = render_board_column(tasks, "blocked")
    assert "task-001-a" in result


def test_column_ref_and_epic_dash_when_absent():
    tasks = [make_task("TASK-001", "blocked", "a")]  # no epic, no branch, no pr
    result = render_board_column(tasks, "blocked")
    assert "| TASK-001 | a | — | — |" in result


def test_column_rows_ordered_by_id():
    tasks = [make_task("TASK-010", "done", "b", pr="x"), make_task("TASK-002", "done", "a", pr="y")]
    result = render_board_column(tasks, "done")
    assert result.index("TASK-002") < result.index("TASK-010")


def test_column_done_is_capped_at_most_recent_n():
    tasks = [make_task(f"TASK-{i:03d}", "done", "x", pr=f"pr{i}") for i in range(1, 26)]
    result = render_board_column(tasks, "done", cap=20)
    for i in range(1, 6):
        assert f"TASK-{i:03d}" not in result  # oldest 5 dropped
    for i in range(6, 26):
        assert f"TASK-{i:03d}" in result  # most recent 20 kept


def test_column_no_cap_when_cap_is_none():
    tasks = [make_task(f"TASK-{i:03d}", "done", "x", pr=f"pr{i}") for i in range(1, 26)]
    result = render_board_column(tasks, "done")
    assert "TASK-001" in result and "TASK-025" in result


def test_column_rejects_a_pipe_in_a_title():
    tasks = [make_task("TASK-001", "blocked", "bad | title")]
    with pytest.raises(RegionError, match=r"\|"):
        render_board_column(tasks, "blocked")


def test_column_composes_with_region_engine_and_none_marker():
    result = ensure_region("# Board\n", "blocked", render_board_column([], "blocked"))
    assert "_(none)_" in result


def test_column_running_twice_is_a_no_op():
    tasks = [make_task("TASK-001", "in-progress", "a", branch="task-001-a")]
    once = ensure_region("# Board\n", "in-progress", render_board_column(tasks, "in-progress"))
    twice = ensure_region(once, "in-progress", render_board_column(tasks, "in-progress"))
    assert twice == once
