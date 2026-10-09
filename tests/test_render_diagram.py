"""The render-diagram script: a Mermaid file to a PNG, with the version Outline uses."""

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "lib/render_diagram.py"
ELK_FLOWCHART = """\
---
config:
  layout: elk
---
flowchart LR
  a --> b
"""
FAKE_NPX = f"""\
#!{sys.executable}
import json, os, sys
arguments = sys.argv[1:]
with open(os.environ["FAKE_NPX_LOG"], "w") as log:
    json.dump(arguments, log)
open(arguments[arguments.index("-o") + 1], "wb").write(b"png")
"""


def make_bin(tmp_path, with_npx=True):
    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    if with_npx:
        npx = bin_directory / "npx"
        npx.write_text(FAKE_NPX)
        npx.chmod(0o755)
    return bin_directory


def run_script(tmp_path, diagram_text, with_npx=True):
    diagram = tmp_path / "diagram.mmd"
    diagram.write_text(diagram_text)
    environment = {
        "FAKE_NPX_LOG": str(tmp_path / "npx-arguments.json"),
        "HOME": os.environ.get("HOME", str(tmp_path)),
        "PATH": str(make_bin(tmp_path, with_npx)),
    }
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(diagram)],
        capture_output=True,
        check=False,
        env=environment,
        text=True,
        timeout=30,
    )


def test_pinned_command_runs_and_png_path_is_printed_when_a_diagram_renders(tmp_path):
    result = run_script(tmp_path, ELK_FLOWCHART)

    assert result.returncode == 0, result.stderr
    arguments = json.loads((tmp_path / "npx-arguments.json").read_text())
    assert "@mermaid-js/mermaid-cli@11" in arguments
    assert arguments[arguments.index("-b") + 1] == "white"
    assert arguments[arguments.index("-s") + 1] == "2"
    assert arguments[arguments.index("-i") + 1] == str(tmp_path / "diagram.mmd")
    png = tmp_path / "diagram.png"
    assert json.loads(result.stdout)["png"] == str(png)
    assert png.is_file()
    assert result.stderr == ""


def test_warning_names_layout_elk_when_a_graph_diagram_has_no_frontmatter(tmp_path):
    result = run_script(tmp_path, "flowchart LR\n  a --> b\n")

    assert result.returncode == 0, result.stderr
    assert "layout: elk" in result.stderr


def test_every_graph_type_gets_the_warning_when_it_has_no_elk_layout(tmp_path):
    for diagram_type in ("classDiagram", "erDiagram", "stateDiagram-v2"):
        case = tmp_path / diagram_type
        case.mkdir()

        result = run_script(case, f"{diagram_type}\n")

        assert "layout: elk" in result.stderr, diagram_type


def test_no_warning_when_the_diagram_type_has_its_own_layout(tmp_path):
    result = run_script(tmp_path, "sequenceDiagram\n  a->>b: hi\n")

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""


def test_failure_names_nodejs_when_npx_is_missing(tmp_path):
    result = run_script(tmp_path, ELK_FLOWCHART, with_npx=False)

    assert result.returncode != 0
    assert "Node.js" in result.stderr
