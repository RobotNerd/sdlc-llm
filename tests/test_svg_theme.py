"""The SVG theme script: an exported diagram follows the viewer's light or dark mode."""

import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "lib/svg_theme.py"
FIXTURE = ROOT / "tests/fixtures/render_export.svg"
SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"
DARK_FILTER = "filter: invert(93%) hue-rotate(180deg)"
DARK_QUERY = "@media (prefers-color-scheme: dark)"


@pytest.fixture
def diagram(tmp_path):
    copy = tmp_path / "diagram.svg"
    shutil.copy(FIXTURE, copy)
    return copy


def run_script(path):
    return subprocess.run([sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True, check=False)


def background_rectangles(root):
    return [child for child in root if child.tag == f"{SVG_NAMESPACE}rect" and child.get("width") == root.get("width")]


def theme_styles(root):
    return [element for element in root.iter(f"{SVG_NAMESPACE}style") if DARK_QUERY in (element.text or "")]


def describe(element, skip):
    """The element's tag, attributes, text and children, leaving out the elements `skip` picks."""
    return (
        element.tag,
        sorted(element.attrib.items()),
        element.text,
        [describe(child, skip) for child in element if not skip(child)],
    )


def test_background_removed_and_dark_rule_added_when_svg_exported(diagram):
    assert background_rectangles(ET.parse(diagram).getroot())

    result = run_script(diagram)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {"ok": True, "file": str(diagram.resolve())}
    root = ET.parse(diagram).getroot()
    assert not background_rectangles(root)
    styles = theme_styles(root)
    assert len(styles) == 1
    assert DARK_FILTER in styles[0].text


def test_nothing_else_changes_when_svg_exported(diagram):
    before = ET.parse(diagram).getroot()

    run_script(diagram)

    after = ET.parse(diagram).getroot()
    rectangles = background_rectangles(before)
    assert describe(after, lambda element: element in theme_styles(after)) == describe(
        before, lambda element: element in rectangles
    )


def test_bytes_unchanged_when_run_twice(diagram):
    run_script(diagram)
    first = diagram.read_bytes()

    result = run_script(diagram)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["ok"] is True
    assert diagram.read_bytes() == first


def test_refused_when_file_missing(tmp_path):
    missing = tmp_path / "missing.svg"

    result = run_script(missing)

    assert result.returncode != 0
    assert str(missing) in result.stderr
    assert not missing.exists()


def test_refused_when_file_not_svg(tmp_path):
    notes = tmp_path / "notes.svg"
    notes.write_text("just some text\n")

    result = run_script(notes)

    assert result.returncode != 0
    assert str(notes) in result.stderr
    assert notes.read_text() == "just some text\n"
