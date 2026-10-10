# Outline backend map

How a prose skill performs each DocStore operation through the Outline MCP server.

## Conventions

- **Values in angle brackets** come from `.sdlc/config.toml` (such as `<outline.collection_id>`) or from an earlier step.
- **Titles:** the title is its own field. A doc's text never starts with a top-level `#` heading.
- **Markdown:** Outline joins consecutive lines into one paragraph, pads table cells, and writes `*` list markers. Separate paragraphs with a blank line.
- **Diagrams:** Mermaid code blocks only.

## Operations

| Operation | Tools | Arguments and steps |
|-----------|-------|---------------------|
| `append_doc` | `mcp__plugin_sdlc-llm_outline__update_document`, `mcp__plugin_sdlc-llm_outline__fetch` | `id`, `editMode` `append`, and `text`, starting with a blank line. Fetch the doc afterwards and check the text is at the end. |
| `archive_doc` | `mcp__plugin_sdlc-llm_outline__delete_document` | `id`, and `archive` `true`. Without `archive`, the doc goes to the trash instead. |
| `create_doc` | `mcp__plugin_sdlc-llm_outline__create_document` | `title`, `text`, and `parentDocumentId`. For a doc at the top of the collection, pass `collectionId` `<outline.collection_id>` instead. |
| `find_doc` | `mcp__plugin_sdlc-llm_outline__list_collection_documents` | `collectionId` `<outline.collection_id>`. Walk the tree one title per path segment, such as `docs`, then `guidelines`, then `Code style`. Titles must match exactly. |
| `get_doc` | `mcp__plugin_sdlc-llm_outline__fetch` | `resource` `document`, and `id`. |
| `list_children` | `mcp__plugin_sdlc-llm_outline__list_collection_documents` | `collectionId` `<outline.collection_id>`. Find the doc in the tree, and take its direct children. |
| `search_docs` | `mcp__plugin_sdlc-llm_outline__list_documents` | `query`, and `collectionId` `<outline.collection_id>`. Archived docs are left out. |
| `update_doc` | `mcp__plugin_sdlc-llm_outline__update_document`, `mcp__plugin_sdlc-llm_outline__fetch` | `id`, `editMode` `patch`, `findText` copied verbatim from the fetched doc, and `text`. A patch that matches nothing can still succeed, so fetch the doc afterwards and check the change is there. If it isn't, retry with a different `findText`. One that starts at a numbered list item doesn't match. |
