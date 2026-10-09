"""Render a Mermaid file to a PNG, with the Mermaid major version Outline uses.

Prints {"png": <path>} on stdout. Layout warnings go to stderr and don't stop the render.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Outline renders with Mermaid 11. The same major version gives the same layout.
MERMAID_CLI = "@mermaid-js/mermaid-cli@11"
BACKGROUND = "white"
# Twice the default resolution, so small labels stay readable when the PNG is viewed.
SCALE = "2"
GRAPH_TYPES = ("classDiagram", "erDiagram", "flowchart", "graph", "stateDiagram", "stateDiagram-v2")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
ELK_LAYOUT = re.compile(r"^\s*layout:\s*elk\s*$", re.MULTILINE)
ELK_FIX = "---\nconfig:\n  layout: elk\n---"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("input", type=Path, help="the .mmd file")
    parser.add_argument("-o", "--output", type=Path, help="defaults to the input path with .png")
    arguments = parser.parse_args(argv)
    output = arguments.output or arguments.input.with_suffix(".png")

    try:
        source = arguments.input.read_text()
    except OSError as error:
        return fail(f"can't read {arguments.input}: {error.strerror}")

    warning = layout_warning(source)
    if warning:
        print(f"warning: {warning}", file=sys.stderr)

    npx = shutil.which("npx")
    if npx is None:
        return fail("npx not found; rendering Mermaid needs Node.js, which includes npx (https://nodejs.org)")
    command = [npx, "-y", MERMAID_CLI, "-i", str(arguments.input), "-o", str(output), "-b", BACKGROUND, "-s", SCALE]
    result = subprocess.run(command, capture_output=True, check=False, text=True)
    if result.returncode != 0 or not output.is_file():
        return fail(f"mermaid-cli failed (exit {result.returncode}):\n{result.stderr.strip()}")

    print(json.dumps({"png": str(output)}))
    return 0


def layout_warning(source):
    frontmatter = FRONTMATTER.match(source)
    body = source[frontmatter.end() :] if frontmatter else source
    diagram_type = next(
        (line.split()[0] for line in body.splitlines() if line.strip() and not line.strip().startswith("%%")),
        None,
    )
    if diagram_type not in GRAPH_TYPES:
        return None
    if frontmatter and ELK_LAYOUT.search(frontmatter.group(1)):
        return None
    return f"{diagram_type} diagrams use `layout: elk`. Start the diagram with:\n{ELK_FIX}"


def fail(message):
    print(f"error: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
