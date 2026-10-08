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

* Every diagram in an Outline doc is a Mermaid code block (```` ```mermaid ````). Outline renders it natively.
* No ASCII-art diagrams.
* Keep diagrams small: one idea per diagram, and labels short enough to read on a phone.

### Layout

Outline uses Mermaid 11 with the ELK layout engine available.

| Diagram type | Layout |
|--------------|--------|
| `flowchart`, `stateDiagram-v2`, `classDiagram`, `erDiagram` | `layout: elk` |
| `sequenceDiagram`, `gantt`, `timeline`, `mindmap`, `pie`, `gitGraph`, `journey` | none; these have their own fixed layout |

Set the layout in frontmatter, at the top of the block:

```
---
config:
  layout: elk
---
flowchart LR
```

### Making graphs readable

* **Direction:** `LR` for flows and pipelines; `TB` for hierarchies. Inside a subgraph, set `direction TB` to stack its nodes.
* **Size:** about 12 nodes at most. Split a bigger diagram into two.
* **Labels:** one short title line, plus at most one detail line (`<br/>`). Details go in the text, not the box.
* **Edges:** draw only the edges that make the point. Fan out with `&` (`a --> b & c & d`). Avoid edges that run back against the main direction. Label an edge only when the label adds meaning.
* **Groups:** use subgraphs for real boundaries (a system, a repo), not for decoration.

### Checking the render

Never publish a diagram without looking at it.


1. Write the diagram to a `.mmd` file in a scratch directory.
2. Render it with the same Mermaid major version Outline uses:

   ```bash
   npx -y @mermaid-js/mermaid-cli@11 -i diagram.mmd -o diagram.png -b white -s 2
   ```
3. View the PNG. Fix crossings, long edges, and cramped labels, then render again.
4. Publish the block only when the PNG reads cleanly.

The local render uses Mermaid's default theme, so colors differ from Outline's. The layout is the same.
