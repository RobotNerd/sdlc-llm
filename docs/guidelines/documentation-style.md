# Documentation style

How documentation in this repo is written.

## Sorted order

Lists whose order doesn't matter are sorted alphanumerically. When order does carry meaning (steps, priority, a sequence), keep it, and don't sort.

## Prose

* Short and plain. Short sentences, common words.
* One term per concept. "Task", never "ticket" or "story".
* No time-sensitive wording ("currently", "new", "recently").
* No tracker references in committed files: no task keys, epic keys, or spec ids.
* State rules directly. No hedging or filler.

## Formatting for the reader

These rules apply to every doc: guidelines, specs, reports, task text, and comments. The reader often copies from a doc into a shell, a UI, or an agent prompt. Make that one click.

* **Commands go in their own code block.** Never put a command the reader runs inline in a sentence. Outline shows a copy button on every code block. Use one block per action, with the shell language (`bash`) set.
* **Values the reader types or pastes stand apart from the sentence.**
  * One value (a key name, a collection name): its own code block.
  * Several values (labels, columns, slugs): a bulleted list, one value per line, each in inline code. Sort it unless the order matters.
  * A before-and-after edit: two bullets, `From:` and `To:`.
* **Files the reader creates:** give the file name in its own code block, then the full content in a second block with its language set, then the command that uses or checks it. Don't wrap the content in a heredoc or a clipboard command such as `pbpaste`; the reader creates the file in an editor.
* **Agent prompts the reader sends go in their own code block,** with language set as `Plain text`.
* **Commands are paste-ready.** Save ids and other output into shell variables, so later commands use the variables and need no editing. When a placeholder can't be avoided, say just above the block what replaces it.
* **Inside a numbered step,** indent the code block or list under the step, with a blank line before it, so the numbering continues.
* **Inline code inside a sentence is for names the reader only reads:** a file, a field, a function, a column the text refers to.
* **Consecutive lines merge.** Outline joins lines that aren't separated by a blank line into one paragraph. Lines that must stay separate, such as Given / When / Then, are bullets.

## Diagrams

Every diagram is drawn in Excalidraw, with the `draw` skill. No ASCII-art diagrams.

### Workflow

The `draw` skill has the steps. It keeps the source as a local `.excalidraw` file, looks at a PNG before anything is published, and renders the SVG from the source. The files share one base name: `<name>.excalidraw` and `<name>.svg`. To edit a diagram, load its `.excalidraw` source and keep the shapes that are not part of the change.

### Where the files go

* **Outline doc:** embed the SVG as an image attachment. Attach the `.excalidraw` file, and put a link to it alone in its own paragraph under the image, written as below. The name and size are the ones given to `create_attachment`.

  ```
  [<name>.excalidraw <size in bytes>](<attachment url>)
  ```

  The link text is never a label such as "Source". Outline reads the last word of the text as the file size and the rest as the title.
* **Repo doc:** store the files at these paths. Markdown references only the SVG, by a relative path from the doc.
  * `docs/diagrams/excalidraw/<name>.excalidraw`
  * `docs/diagrams/svg/<name>.svg`

### Making diagrams readable

* **One idea per diagram.**
* **Size:** about 12 shapes at most. Split a bigger diagram into two.
* **Labels:** short, so they read on a phone. Details go in the text, not the shape.
* **Direction:** left to right for flows.
* **Arrows:** draw only the ones that make the point. Avoid arrows that run back against the main direction.

### Existing Mermaid diagrams

An existing Mermaid diagram is redrawn in Excalidraw only when it is edited.
