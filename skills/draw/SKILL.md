---
name: draw
description: Draws or edits a diagram as an Excalidraw source plus a theme-aware SVG. Use when the developer asks to draw, add, or edit a diagram, or when a doc or README needs one.
allowed-tools: Bash(npx -y mcp-excalidraw-server@2.1.2 render *), Bash(python3 ${CLAUDE_PLUGIN_ROOT}/lib/svg_theme.py *)
model: opus
---

# draw

Produces one diagram as a `.excalidraw` source and an `.svg`, both under one base name, and places them in an Outline doc or a repo doc. The source stays a local file, so concurrent sessions never share shapes. The readability and placement rules are in the Diagrams section of `docs/guidelines/documentation-style.md`.

## Hard rules

- Never use the Excalidraw MCP server. Rendering is the `render` command below, run from a scratch directory outside the repo unless the files are going into a repo doc.
- Write the source in the agent format in `${CLAUDE_PLUGIN_ROOT}/skills/draw/format.md`. A shape's label is `"label": {"text": "..."}`.
- Keep the SVG's embedded fonts: never pass `--no-embed-fonts`.
- Publish only after you have looked at a PNG and it reads cleanly.

## Steps

1. **Source.** To draw, write `<name>.excalidraw`. To edit, load the existing source, from the repo or the Outline attachment, and change only what the request needs: keep the other shapes and their ids.
2. **PNG.** Render it, then look at the PNG. Fix crossings, long arrows, cramped labels, and missing labels or arrows, and render again until it reads cleanly.

   ```bash
   npx -y mcp-excalidraw-server@2.1.2 render <name>.excalidraw --out <name>.png
   ```

3. **SVG.** Render it with no background, then make it follow dark and light mode. The second command prints `{"ok": true, "file": ...}`.

   ```bash
   npx -y mcp-excalidraw-server@2.1.2 render <name>.excalidraw --out <name>.svg --no-background
   ```

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/lib/svg_theme.py <name>.svg
   ```

4. **Place.** Put the files where the Diagrams section says. In an Outline doc, upload both files as attachments, embed the SVG as an image, and put the `.excalidraw` link alone in a paragraph under it, written `[<name>.excalidraw <size in bytes>](<attachment url>)`. In a repo doc, save them as `docs/diagrams/excalidraw/<name>.excalidraw` and `docs/diagrams/svg/<name>.svg`, and reference only the SVG by a relative path. When editing an Outline diagram, replace the image and the source link, not add a second pair.
5. **Clean up.** Delete the scratch PNG.
