"""Unit tests for `.tasks/bin/sync`'s TODO merge (TASK-009) — the one
place `sync` merges instead of regenerating.

Acceptance criteria this covers:
- existing line order is preserved exactly, never sorted
- a line whose task left `todo` is removed
- a `todo` task not already listed is appended, in id order among the
  newly-added
- line format: dash, id, em-dash, title, two spaces, epic tag (omitted
  if none), ' ⛔ blocked_by ...' (ascending) when non-empty
- round-trip: parsing a rendered line back yields the same task id
- reorder attempt, status departure, new-task append, blocked-annotation
  add/remove
"""

from pathlib import Path

import pytest

from sync import Artifact, RegionError, apply_todo_merge, merge_todo, render_todo_line


def make_task(task_id, status="todo", title="x", epic=None, blocked_by=None):
    fields = {
        "id": task_id, "status": status, "title": title,
        "epic": epic, "blocked_by": blocked_by or [],
    }
    return Artifact(id=task_id, kind="task", path=Path(f"{task_id}.md"), fields=fields, order=list(fields), body="")


# ---------------------------------------------------------------------------
# render_todo_line
# ---------------------------------------------------------------------------


def test_render_todo_line_no_epic_no_blockers():
    task = make_task("TASK-002", title="Create templates")
    assert render_todo_line(task, {"TASK-002": task}) == "- TASK-002 — Create templates"


def test_render_todo_line_with_epic():
    task = make_task("TASK-006", title="do a thing", epic="EPIC-001")
    assert render_todo_line(task, {"TASK-006": task}) == "- TASK-006 — do a thing  `EPIC-001`"


def test_render_todo_line_with_epic_and_blocked_by_matches_real_format():
    blocker = make_task("TASK-009", status="in-progress")
    task = make_task("TASK-012", title="sync check", epic="EPIC-001", blocked_by=["TASK-009"])
    tasks = {"TASK-009": blocker, "TASK-012": task}
    assert render_todo_line(task, tasks) == "- TASK-012 — sync check  `EPIC-001` ⛔ blocked_by TASK-009"


def test_render_todo_line_blocked_by_ids_sorted_ascending():
    blockers = {f"TASK-{n:03d}": make_task(f"TASK-{n:03d}", status="todo") for n in (9, 11, 12)}
    task = make_task("TASK-013", epic="EPIC-001", blocked_by=["TASK-012", "TASK-009", "TASK-011"])
    tasks = {**blockers, "TASK-013": task}
    assert render_todo_line(task, tasks).endswith("⛔ blocked_by TASK-009, TASK-011, TASK-012")


def test_render_todo_line_omits_a_blocker_that_is_already_done():
    # blocked_by is a static declared list -- reconcile_blocks never prunes
    # it as blockers complete. The TODO line's marker must still drop a
    # satisfied blocker, computed at render time (this was a real bug: an
    # earlier version rendered the raw blocked_by field verbatim).
    done_blocker = make_task("TASK-004", status="done")
    still_open = make_task("TASK-008", status="todo")
    task = make_task("TASK-011", blocked_by=["TASK-004", "TASK-008"])
    tasks = {"TASK-004": done_blocker, "TASK-008": still_open, "TASK-011": task}
    assert render_todo_line(task, tasks) == "- TASK-011 — x ⛔ blocked_by TASK-008"


def test_render_todo_line_wont_do_blocker_also_counts_as_satisfied():
    blocker = make_task("TASK-004", status="wont-do")
    task = make_task("TASK-011", blocked_by=["TASK-004"])
    assert render_todo_line(task, {"TASK-004": blocker, "TASK-011": task}) == "- TASK-011 — x"


def test_render_todo_line_no_marker_once_every_blocker_is_satisfied():
    blockers = {tid: make_task(tid, status="done") for tid in ("TASK-004", "TASK-008")}
    task = make_task("TASK-011", blocked_by=["TASK-004", "TASK-008"])
    tasks = {**blockers, "TASK-011": task}
    assert "⛔" not in render_todo_line(task, tasks)


def test_render_todo_line_rejects_a_pipe_in_title():
    task = make_task("TASK-001", title="bad | title")
    with pytest.raises(RegionError, match=r"\|"):
        render_todo_line(task, {"TASK-001": task})


def test_render_todo_line_round_trip_yields_the_same_id():
    from sync import _TODO_LINE_RE

    blocker1 = make_task("TASK-001", status="todo")
    blocker2 = make_task("TASK-002", status="todo")
    for task in [
        make_task("TASK-002"),
        make_task("TASK-099", epic="EPIC-001", blocked_by=["TASK-001", "TASK-002"]),
    ]:
        tasks = {"TASK-001": blocker1, "TASK-002": blocker2, task.id: task}
        rendered = render_todo_line(task, tasks)
        match = _TODO_LINE_RE.match(rendered)
        assert match is not None
        assert match.group(1) == task.id


# ---------------------------------------------------------------------------
# merge_todo
# ---------------------------------------------------------------------------


def test_merge_todo_preserves_scrambled_order_exactly():
    # deliberately out of id order -- must not be sorted
    tasks = {t.id: t for t in [make_task("TASK-003"), make_task("TASK-001"), make_task("TASK-002")]}
    existing = ["- TASK-003 — x", "- TASK-001 — x", "- TASK-002 — x"]
    merged = merge_todo(existing, tasks)
    ids_in_order = [line.split(" — ")[0].removeprefix("- ") for line in merged]
    assert ids_in_order == ["TASK-003", "TASK-001", "TASK-002"]


def test_merge_todo_drops_a_line_whose_task_left_todo():
    tasks = {
        "TASK-001": make_task("TASK-001", status="in-progress"),
        "TASK-002": make_task("TASK-002", status="todo"),
    }
    existing = ["- TASK-001 — x", "- TASK-002 — x"]
    merged = merge_todo(existing, tasks)
    assert len(merged) == 1
    assert merged[0].startswith("- TASK-002 —")


def test_merge_todo_drops_a_line_for_a_task_that_no_longer_exists():
    tasks = {"TASK-002": make_task("TASK-002")}
    existing = ["- TASK-001 — gone now", "- TASK-002 — x"]
    merged = merge_todo(existing, tasks)
    assert len(merged) == 1
    assert merged[0].startswith("- TASK-002 —")


def test_merge_todo_appends_new_todo_tasks_at_the_end_in_id_order():
    tasks = {
        "TASK-005": make_task("TASK-005"),
        "TASK-003": make_task("TASK-003"),  # new, not in existing
        "TASK-001": make_task("TASK-001"),  # new, not in existing
    }
    existing = ["- TASK-005 — x"]
    merged = merge_todo(existing, tasks)
    ids = [line.split(" — ")[0].removeprefix("- ") for line in merged]
    assert ids == ["TASK-005", "TASK-001", "TASK-003"]  # existing first, then new ones by id


def test_merge_todo_refreshes_annotations_on_kept_lines():
    # the line text in `existing` is stale; merge_todo re-renders from current fields
    tasks = {"TASK-001": make_task("TASK-001", title="new title", epic="EPIC-002")}
    existing = ["- TASK-001 — old stale title"]
    merged = merge_todo(existing, tasks)
    assert merged == ["- TASK-001 — new title  `EPIC-002`"]


def test_merge_todo_blocked_annotation_can_appear_and_disappear():
    tasks = {"TASK-001": make_task("TASK-001", blocked_by=["TASK-002"])}
    existing = ["- TASK-001 — x"]  # previously unblocked
    merged = merge_todo(existing, tasks)
    assert "⛔ blocked_by TASK-002" in merged[0]

    tasks["TASK-001"] = make_task("TASK-001", blocked_by=[])  # now unblocked
    merged2 = merge_todo(existing, tasks)
    assert "⛔" not in merged2[0]


def test_merge_todo_ignores_non_task_lines():
    tasks = {"TASK-001": make_task("TASK-001")}
    existing = ["", "not a task line", "- TASK-001 — x"]
    merged = merge_todo(existing, tasks)
    assert merged == ["- TASK-001 — x"]


def test_merge_todo_empty_input_and_no_todo_tasks():
    assert merge_todo([], {}) == []


# ---------------------------------------------------------------------------
# apply_todo_merge
# ---------------------------------------------------------------------------


BOARD_FIXTURE = (
    "# Board\n\n"
    "## Epics\n\n_(none)_\n\n"
    "## TODO\n\n"
    "- TASK-002 — b  `EPIC-001`\n"
    "- TASK-001 — a  `EPIC-001`\n"
    "\n"
    "## In Progress\n\n_(none)_\n"
)


def test_apply_todo_merge_touches_only_the_todo_section():
    tasks = {
        "TASK-002": make_task("TASK-002", title="b", epic="EPIC-001"),
        "TASK-001": make_task("TASK-001", title="a", epic="EPIC-001"),
    }
    result = apply_todo_merge(BOARD_FIXTURE, tasks)
    assert result == BOARD_FIXTURE  # unchanged data -> true no-op
    assert "## Epics" in result and "## In Progress" in result


def test_apply_todo_merge_preserves_order_drops_and_appends():
    tasks = {
        "TASK-002": make_task("TASK-002", title="b", status="done", epic="EPIC-001"),  # left todo
        "TASK-001": make_task("TASK-001", title="a", epic="EPIC-001"),  # kept
        "TASK-003": make_task("TASK-003", title="c"),  # new
    }
    result = apply_todo_merge(BOARD_FIXTURE, tasks)
    todo_section = result[result.index("## TODO"):result.index("## In Progress")]
    assert "TASK-002" not in todo_section
    lines = [l for l in todo_section.splitlines() if l.startswith("- ")]
    assert lines == ["- TASK-001 — a  `EPIC-001`", "- TASK-003 — c"]


def test_apply_todo_merge_is_idempotent():
    tasks = {
        "TASK-002": make_task("TASK-002", title="b", epic="EPIC-001"),
        "TASK-001": make_task("TASK-001", title="a", epic="EPIC-001"),
    }
    once = apply_todo_merge(BOARD_FIXTURE, tasks)
    twice = apply_todo_merge(once, tasks)
    assert twice == once


def test_apply_todo_merge_raises_without_a_todo_heading():
    with pytest.raises(RegionError, match="TODO"):
        apply_todo_merge("# Board\n\nno todo section here\n", {})


def test_apply_todo_merge_handles_todo_as_the_last_section():
    text = "# Board\n\n## TODO\n\n- TASK-001 — a\n"
    tasks = {"TASK-001": make_task("TASK-001", title="a")}
    result = apply_todo_merge(text, tasks)
    assert result == text
