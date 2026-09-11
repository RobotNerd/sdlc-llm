"""Unit tests for `.tasks/bin/sync`'s frontmatter parser/renderer and loader.

TASK-004's acceptance criteria this covers:
- parser handles quoted/bare scalars, null, true/false, integers, [a, b, c] lists,
  and ignores trailing '# comment' text
- parser rejects anything outside that subset with a specific error
- loader discovers SPEC-*.md / EPIC-*.md / TASK-*.md under .tasks/, .tasks/specs/,
  and .tasks/archive/, keyed by id
- writing a record back produces byte-identical frontmatter for the supported subset
"""

from pathlib import Path

import pytest

import sync
from sync import Artifact, FrontmatterError, discover, parse_frontmatter, render_frontmatter


# ---------------------------------------------------------------------------
# parse_frontmatter: the supported subset
# ---------------------------------------------------------------------------


def test_parses_bare_and_quoted_scalars():
    text = '---\nid: TASK-001\ntitle: "sync: a title with a colon"\nstatus: todo\n---\nbody\n'
    fields, body, order = parse_frontmatter(text)
    assert fields == {"id": "TASK-001", "title": "sync: a title with a colon", "status": "todo"}
    assert order == ["id", "title", "status"]
    assert body == "body\n"


def test_parses_null_bool_and_int():
    text = "---\npr: null\nallow_auto_merge: false\nrebase_before_pr: true\nworkflow_version: 1\n---\n"
    fields, _, _ = parse_frontmatter(text)
    assert fields == {
        "pr": None,
        "allow_auto_merge": False,
        "rebase_before_pr": True,
        "workflow_version": 1,
    }
    assert fields["workflow_version"] is not True  # int, not bool


def test_parses_negative_int():
    fields, _, _ = parse_frontmatter("---\nn: -3\n---\n")
    assert fields == {"n": -3}


def test_parses_empty_and_populated_lists():
    text = "---\nblocked_by: []\nblocks: [TASK-006, TASK-010, TASK-011]\n---\n"
    fields, _, _ = parse_frontmatter(text)
    assert fields == {"blocked_by": [], "blocks": ["TASK-006", "TASK-010", "TASK-011"]}


def test_list_items_parsed_as_scalars_not_just_strings():
    fields, _, _ = parse_frontmatter("---\nflags: [true, false, null, 1, plain]\n---\n")
    assert fields == {"flags": [True, False, None, 1, "plain"]}


def test_trailing_comment_is_ignored():
    fields, _, _ = parse_frontmatter("---\nstatus: draft            # draft | approved | superseded\n---\n")
    assert fields == {"status": "draft"}


def test_hash_inside_quotes_is_not_a_comment():
    fields, _, _ = parse_frontmatter('---\ntitle: "issue #3 in the title"\n---\n')
    assert fields == {"title": "issue #3 in the title"}


def test_blank_lines_in_frontmatter_are_skipped():
    fields, _, order = parse_frontmatter("---\nid: TASK-001\n\ntitle: x\n---\n")
    assert fields == {"id": "TASK-001", "title": "x"}
    assert order == ["id", "title"]


def test_body_after_frontmatter_is_preserved():
    text = "---\nid: TASK-001\n---\n\n# heading\n\nsome body text\n"
    _, body, _ = parse_frontmatter(text)
    assert body == "\n# heading\n\nsome body text\n"


# ---------------------------------------------------------------------------
# parse_frontmatter: rejections (outside the supported subset)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,match",
    [
        ("no frontmatter here\n", "does not start with"),
        ("---\nid: TASK-001\nno closing marker\n", "not closed"),
        ("---\n  nested: map\n---\n", "indentation"),
        ("---\n\tid: TASK-001\n---\n", "indentation"),
        ("---\nnot-a-key-line\n---\n", "not a 'key: value'"),
        ("---\nid: TASK-001\nid: TASK-002\n---\n", "duplicate key"),
        ("---\nblocked_by: [TASK-001\n---\n", "unterminated list"),
        ("---\ntitle: \"unterminated\n---\n", "unterminated quoted"),
        ("---\ntitle: 'single quoted'\n---\n", "single-quoted"),
        ("---\nnotes: |\n  block scalar\n---\n", "unsupported YAML feature"),
        ("---\nblocked_by: [[nested], list]\n---\n", "nested lists"),
        ("---\nid:\n---\n", "missing value"),
    ],
)
def test_rejects_unsupported_input(text, match):
    with pytest.raises(FrontmatterError, match=match):
        parse_frontmatter(text)


def test_error_message_names_the_line_number():
    text = "---\nid: TASK-001\n  bad: line\n---\n"
    with pytest.raises(FrontmatterError, match=r"line 2"):
        parse_frontmatter(text)


# ---------------------------------------------------------------------------
# render_frontmatter / round-trip
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        # a TASK-file-shaped frontmatter block
        "---\n"
        "id: TASK-004\n"
        'title: "sync: stdlib frontmatter parser and artifact loader"\n'
        "type: feature\n"
        "status: in-progress\n"
        "epic: EPIC-001\n"
        "created: 2026-09-10\n"
        "branch: task-004-sync-frontmatter-parser\n"
        "pr: null\n"
        "merge_commit: null\n"
        "blocked_by: []\n"
        "blocks: [TASK-006, TASK-010, TASK-011]\n"
        "---\n",
        # a config.md-shaped frontmatter block (booleans, an int, dotted paths)
        "---\n"
        "workflow_version: 1\n"
        "test_command: pytest\n"
        "lint_command: null\n"
        "docs_paths: [README.md, CLAUDE.md, .tmp/workflow-plan.md]\n"
        "rebase_before_pr: true\n"
        "allow_auto_merge: false\n"
        "ci_checks: [test]\n"
        "---\n",
        # an EPIC-file-shaped frontmatter block
        "---\nid: EPIC-001\ntitle: MVP\nspec: SPEC-001\nstatus: in-progress\ncreated: 2026-09-10\n---\n",
    ],
)
def test_round_trip_is_byte_identical(text):
    fields, body, order = parse_frontmatter(text)
    rendered = render_frontmatter(fields, order)
    assert rendered == text
    # running it twice is a no-op — the idempotent-replace case
    fields2, _, order2 = parse_frontmatter(rendered)
    assert render_frontmatter(fields2, order2) == rendered


def test_render_without_explicit_order_uses_dict_order():
    fields = {"b": 1, "a": 2}
    assert render_frontmatter(fields) == "---\nb: 1\na: 2\n---\n"


def test_render_rejects_mismatched_order():
    with pytest.raises(FrontmatterError, match="order"):
        render_frontmatter({"a": 1}, order=["a", "b"])


def test_render_quotes_values_that_would_otherwise_misparse():
    # a bare string that looks like null/true/an int/a list must round-trip quoted
    for value in ("null", "true", "false", "42", "[x]"):
        rendered = render_frontmatter({"v": value}, order=["v"])
        fields, _, _ = parse_frontmatter(rendered)
        assert fields["v"] == value, rendered


# ---------------------------------------------------------------------------
# discover(): the loader
# ---------------------------------------------------------------------------


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_discover_finds_spec_epic_and_task_across_all_three_dirs(tmp_path):
    _write(tmp_path / "specs" / "SPEC-001-x.md", "---\nid: SPEC-001\ntitle: x\n---\n")
    _write(tmp_path / "EPIC-001-x.md", "---\nid: EPIC-001\ntitle: x\n---\n")
    _write(tmp_path / "TASK-001-x.md", "---\nid: TASK-001\ntitle: x\nstatus: todo\n---\n")
    _write(tmp_path / "archive" / "TASK-002-x.md", "---\nid: TASK-002\ntitle: x\nstatus: done\n---\n")

    artifacts = discover(tmp_path)

    assert set(artifacts) == {"SPEC-001", "EPIC-001", "TASK-001", "TASK-002"}
    assert artifacts["SPEC-001"].kind == "spec"
    assert artifacts["EPIC-001"].kind == "epic"
    assert artifacts["TASK-002"].kind == "task"
    assert artifacts["TASK-002"].fields["status"] == "done"


def test_discover_ignores_non_artifact_markdown_files(tmp_path):
    _write(tmp_path / "TASK-001-x.md", "---\nid: TASK-001\n---\n")
    _write(tmp_path / "BOARD.md", "# not frontmatter at all")
    _write(tmp_path / "config.md", "---\nworkflow_version: 1\n---\n")
    _write(tmp_path / "guidelines.md", "---\nworkflow_version: 1\n---\n")

    artifacts = discover(tmp_path)

    assert set(artifacts) == {"TASK-001"}


def test_discover_rejects_duplicate_ids(tmp_path):
    _write(tmp_path / "TASK-001-a.md", "---\nid: TASK-001\n---\n")
    _write(tmp_path / "archive" / "TASK-001-b.md", "---\nid: TASK-001\n---\n")

    with pytest.raises(FrontmatterError, match="duplicate id"):
        discover(tmp_path)


def test_discover_missing_directories_is_not_an_error(tmp_path):
    # no specs/ or archive/ subdirectory exists yet
    _write(tmp_path / "TASK-001-x.md", "---\nid: TASK-001\n---\n")
    assert set(discover(tmp_path)) == {"TASK-001"}


def test_discover_names_the_offending_file_on_a_parse_error(tmp_path):
    bad = tmp_path / "TASK-001-x.md"
    _write(bad, "---\n  bad: indent\n---\n")
    with pytest.raises(FrontmatterError, match=str(bad)):
        discover(tmp_path)


def test_artifact_write_round_trips(tmp_path):
    path = tmp_path / "TASK-001-x.md"
    original = "---\nid: TASK-001\nstatus: todo\n---\nbody text\n"
    _write(path, original)
    artifacts = discover(tmp_path)
    art = artifacts["TASK-001"]

    art.fields["status"] = "in-progress"
    art.write()

    assert path.read_text() == "---\nid: TASK-001\nstatus: in-progress\n---\nbody text\n"


# ---------------------------------------------------------------------------
# Integration: every real artifact in this repo parses correctly
# ---------------------------------------------------------------------------


def test_discover_over_the_real_repo_tasks_directory():
    """SPEC-001/EPIC-001/TASK-* committed in this repo all parse with the right types."""
    artifacts = discover(sync.__file__ and Path(sync.__file__).resolve().parent.parent)

    by_kind = {"spec": 0, "epic": 0, "task": 0}
    for art in artifacts.values():
        by_kind[art.kind] += 1
        assert isinstance(art.fields.get("id"), str) and art.fields["id"] == art.id
        assert isinstance(art.fields.get("title"), str) and art.fields["title"]
        if art.kind == "task":
            assert art.fields["status"] in {
                "todo", "in-progress", "blocked", "in-review", "done", "wont-do",
            }
            assert isinstance(art.fields["blocked_by"], list)
            assert isinstance(art.fields["blocks"], list)

    assert by_kind["spec"] >= 1
    assert by_kind["epic"] >= 1
    assert by_kind["task"] >= 1
