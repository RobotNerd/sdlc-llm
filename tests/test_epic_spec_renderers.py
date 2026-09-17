"""Unit tests for `.tasks/bin/sync`'s epic `children` and spec `epics`
region renderers (TASK-007).

Acceptance criteria this covers:
- epic children region: header, rows ordered by id, blank line, Progress
  line (done counts done+wont-do)
- spec epics region: header incl. Progress, rows ordered by id, status
  from derivation
- an epic with no children / a spec with no epics renders `_(none)_`
  (via the region engine's empty-body handling)
- renderers compose with replace_region
- exact bytes for zero-child, one-child, and many-child epics
"""

from pathlib import Path

from sync import ensure_region, render_epic_children, render_spec_epics


def make_epic(epic_id: str, status: str, title: str = "MVP") -> "Artifact":
    from sync import Artifact

    fields = {"id": epic_id, "title": title, "status": status}
    return Artifact(id=epic_id, kind="epic", path=Path(f"{epic_id}.md"), fields=fields, order=list(fields), body="")


def make_task(task_id: str, status: str, title: str) -> "Artifact":
    from sync import Artifact

    fields = {"id": task_id, "status": status, "title": title}
    return Artifact(id=task_id, kind="task", path=Path(f"{task_id}.md"), fields=fields, order=list(fields), body="")


# ---------------------------------------------------------------------------
# render_epic_children
# ---------------------------------------------------------------------------


def test_render_epic_children_zero_children_is_empty_string():
    epic = make_epic("EPIC-001", "todo")
    assert render_epic_children(epic, []) == ""


def test_render_epic_children_one_child_exact_bytes():
    epic = make_epic("EPIC-001", "todo")
    children = [make_task("TASK-011", "done", "Use API to request current weather")]
    result = render_epic_children(epic, children)
    assert result == (
        "| Task | Status | Title |\n"
        "|---|---|---|\n"
        "| TASK-011 | done | Use API to request current weather |\n"
        "\n"
        "Progress: 1/1 done"
    )


def test_render_epic_children_many_children_matches_spec_001_example():
    # the exact worked example from SPEC-001 §'Generated regions'
    epic = make_epic("EPIC-001", "in-progress")
    children = [
        make_task("TASK-011", "done", "Use API to request current weather"),
        make_task("TASK-012", "todo", "Cache weather responses"),
    ]
    result = render_epic_children(epic, children)
    assert result == (
        "| Task | Status | Title |\n"
        "|---|---|---|\n"
        "| TASK-011 | done | Use API to request current weather |\n"
        "| TASK-012 | todo | Cache weather responses |\n"
        "\n"
        "Progress: 1/2 done"
    )


def test_render_epic_children_rows_ordered_by_id_regardless_of_input_order():
    epic = make_epic("EPIC-001", "todo")
    children = [
        make_task("TASK-012", "todo", "second"),
        make_task("TASK-002", "todo", "first"),
    ]
    result = render_epic_children(epic, children)
    assert result.index("TASK-002") < result.index("TASK-012")


def test_render_epic_children_progress_counts_wont_do_as_done():
    epic = make_epic("EPIC-001", "todo")
    children = [
        make_task("TASK-001", "done", "a"),
        make_task("TASK-002", "wont-do", "b"),
        make_task("TASK-003", "todo", "c"),
    ]
    result = render_epic_children(epic, children)
    assert result.endswith("Progress: 2/3 done")


def test_render_epic_children_composes_with_region_engine_and_none_marker():
    text = "# Doc\n"
    epic = make_epic("EPIC-001", "todo")
    result = ensure_region(text, "children", render_epic_children(epic, []))
    assert "_(none)_" in result


# ---------------------------------------------------------------------------
# render_spec_epics
# ---------------------------------------------------------------------------


def test_render_spec_epics_zero_epics_is_empty_string():
    assert render_spec_epics([]) == ""


def test_render_spec_epics_one_epic_exact_bytes():
    epic = make_epic("EPIC-002", "in-progress", title="Board sync tooling")
    children = [make_task("TASK-001", "done", "a"), make_task("TASK-002", "todo", "b")]
    result = render_spec_epics([(epic, children)])
    assert result == "| Epic | Status | Progress |\n|---|---|---|\n| EPIC-002 | in-progress | 1/2 done |"


def test_render_spec_epics_many_epics_matches_board_panel_shape():
    # mirrors SPEC-001's board `epics` panel worked example
    epic_a = make_epic("EPIC-002", "in-progress")
    children_a = [make_task(f"TASK-{i:03d}", "done" if i < 3 else "todo", "x") for i in range(7)]
    epic_b = make_epic("EPIC-003", "todo")
    children_b = [make_task("TASK-100", "todo", "y"), make_task("TASK-101", "todo", "z")]
    result = render_spec_epics([(epic_b, children_b), (epic_a, children_a)])  # deliberately out of order
    assert result == (
        "| Epic | Status | Progress |\n"
        "|---|---|---|\n"
        "| EPIC-002 | in-progress | 3/7 done |\n"
        "| EPIC-003 | todo | 0/2 done |"
    )


def test_render_spec_epics_status_comes_from_the_epic_record_as_given():
    # render_spec_epics does not re-derive status -- it trusts the caller
    # already ran derive_epic_status; a stale/human status is rendered verbatim
    epic = make_epic("EPIC-002", "wont-do")
    result = render_spec_epics([(epic, [make_task("TASK-001", "done", "a")])])
    assert "| EPIC-002 | wont-do | 1/1 done |" in result

