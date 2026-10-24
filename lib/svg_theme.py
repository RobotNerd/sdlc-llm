"""Make an SVG exported by `mcp-excalidraw-server render` follow the viewer's color scheme.

Removes the background rectangle, and adds a style rule that applies Excalidraw's own dark filter
when the viewer prefers a dark color scheme. Rewrites the file in place, and prints
{"ok": true, "file": "<absolute path>"}. Running it again on its own output changes nothing.
"""

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NAMESPACE = "{http://www.w3.org/2000/svg}"
STYLE_CLASS = "svg-theme"
DARK_STYLE = (
    f'<style class="{STYLE_CLASS}">'
    "@media (prefers-color-scheme: dark) { svg { filter: invert(93%) hue-rotate(180deg); } }"
    "</style>"
)
# The export draws the background as a rect, as wide and high as the drawing, ahead of everything else.
BACKGROUND_RECTANGLE = re.compile(r"<rect\b[^>]*/>")
OPENING_TAG = re.compile(r"<svg\b[^>]*>")
NOT_DRAWN = (f"{SVG_NAMESPACE}defs", f"{SVG_NAMESPACE}metadata", f"{SVG_NAMESPACE}style")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path, help="the SVG to rewrite in place")
    arguments = parser.parse_args(argv)
    path = arguments.file

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        return fail(f"{path}: unreadable: {error.strerror}")
    except UnicodeDecodeError:
        return fail(f"{path}: not an SVG: not UTF-8 text")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as error:
        return fail(f"{path}: not an SVG: {error}")
    if root.tag != f"{SVG_NAMESPACE}svg":
        return fail(f"{path}: not an SVG: the root element is {root.tag}, not svg")

    themed = remove_background(text, root)
    if f'class="{STYLE_CLASS}"' not in themed:
        opening = OPENING_TAG.search(themed)
        themed = themed[: opening.end()] + DARK_STYLE + themed[opening.end() :]
    if themed != text:
        path.write_text(themed, encoding="utf-8")
    print(json.dumps({"ok": True, "file": str(path.resolve())}))
    return 0


def remove_background(text, root):
    drawn = [child for child in root if child.tag not in NOT_DRAWN]
    if not drawn or drawn[0].tag != f"{SVG_NAMESPACE}rect":
        return text
    first = drawn[0]
    if (first.get("width"), first.get("height")) != (root.get("width"), root.get("height")):
        return text
    # Search after the defs, so a rect inside them is never taken for the background.
    start = text.find("</defs>") + len("</defs>") if "</defs>" in text else 0
    match = BACKGROUND_RECTANGLE.search(text, start)
    return text[: match.start()] + text[match.end() :] if match else text


def fail(message):
    print(message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
