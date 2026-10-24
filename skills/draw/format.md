# Agent format

A `.excalidraw` source is a JSON object with an `elements` list. The `render` command accepts this format and native Excalidraw elements.

```json
{
  "elements": [
    {"id": "plan", "type": "rectangle", "x": 0, "y": 0, "width": 160, "height": 80, "label": {"text": "plan"}},
    {"id": "work", "type": "rectangle", "x": 300, "y": 0, "width": 160, "height": 80, "label": {"text": "work"}},
    {"id": "plan-to-work", "type": "arrow", "x": 160, "y": 40, "width": 140, "height": 0, "startElementId": "plan", "endElementId": "work"}
  ]
}
```

- **Shapes:** `rectangle`, `ellipse`, and `diamond`, each with `id`, `x`, `y`, `width`, and `height`.
- **Labels:** write a shape's label as `"label": {"text": "..."}`. A `"text"` field on the shape renders no label.
- **Arrows:** `type` is `arrow`. `startElementId` and `endElementId` are the `id`s of the shapes it joins, and the arrow's `x` and `y` are where it leaves the first shape.
- **Layout:** left to right, with about 140 px between shapes.
