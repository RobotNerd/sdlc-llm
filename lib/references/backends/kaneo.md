# Kaneo backend map

How a prose skill performs each Tracker operation through the Kaneo MCP server.

## Conventions

- **Values in angle brackets** come from `.sdlc/config.toml` (such as `<kaneo.project_id>`) or from an earlier step.
- **Task ids:** every tool takes Kaneo's internal task id, not the `KEY-NNN` key. To turn a key into an id, list the project's tasks and match on `number`.
- **Not found:** an unknown task id fails with 400 `Workspace ID could not be determined`, not 404. Treat that error as "no such task".
- **Updates:** `update_task` reads the task and merges the fields you pass. Pass only the fields you mean to change.
- **Paging:** `list_tasks` returns 50 tasks by default and 100 at most. Pass `limit` 100, and read every page up to `pagination.totalPages`. When `pagination.relatedTotalPages` is more than 1, read every `relatedPage` too; labels come from there.
- **Status values:** a column's slug (`to-do`, `in-progress`, `needs-human`, `done`), `planned` for the backlog, or `archived`.

## Operations

| Operation | Tools | Arguments and steps |
|-----------|-------|---------------------|
| `add_comment` | `mcp__plugin_sdlc-llm_kaneo__create_task_comment` | `taskId`, and `content` in markdown. |
| `add_label` | `mcp__plugin_sdlc-llm_kaneo__list_workspace_labels`, `mcp__plugin_sdlc-llm_kaneo__attach_label_to_task` | List the labels of workspace `<kaneo.workspace_id>`, and take the `id` of the one whose `name` matches and whose `taskId` is `null`. The list also holds each task's own copy of its labels, which have a `taskId`; never attach one of those. Skip the attach when the task already has a label with that name. Otherwise attach it with `labelId` and `taskId`. |
| `add_relation` | `mcp__plugin_sdlc-llm_kaneo__create_task_relation` | `sourceTaskId`, `targetTaskId`, and `relationType`. For `blocks`, the source is the blocker. For `subtask`, the source is the epic. |
| `archive_task` | `mcp__plugin_sdlc-llm_kaneo__update_task_status` | `taskId`, and `status` `archived`. To cancel a task, first add the `wont-do` label and a comment giving the reason. |
| `create_task` | `mcp__plugin_sdlc-llm_kaneo__create_task` | `projectId` `<kaneo.project_id>`, `title`, `description`, `priority` `no-priority`, and `status`. Then add the task's type label, and place it when its status is `to-do`. |
| `get_task` | `mcp__plugin_sdlc-llm_kaneo__get_task` | `taskId`. The result has no labels; read them from `list_tasks` when they matter. |
| `list_column` | `mcp__plugin_sdlc-llm_kaneo__list_tasks` | `projectId` `<kaneo.project_id>`, `status`, `sortBy` `position`, `sortOrder` `asc`, `limit` 100, every page. The tasks are under `data.columns[].tasks`, or `data.plannedTasks` and `data.archivedTasks`. Order them by `position`, then by `number`, so a tie never makes the order ambiguous. |
| `list_relations` | `mcp__plugin_sdlc-llm_kaneo__get_task_relations` | `taskId`. |
| `place_task` | `mcp__plugin_sdlc-llm_kaneo__list_tasks`, `mcp__plugin_sdlc-llm_kaneo__update_task` | Kaneo has no insert call, and setting one task's `position` leaves the others alone, so placing a task renumbers its column. 1. Read the column in order, as in `list_column`. 2. Take the task out of the list, then insert it at the top, at the end, or right after the anchor task. 3. For each task whose list index differs from its `position`, call `update_task` with `taskId` and `position` set to the index, counting from 0. Set the task's status before placing it. |
| `remove_label` | `mcp__plugin_sdlc-llm_kaneo__list_tasks`, `mcp__plugin_sdlc-llm_kaneo__detach_label_from_task` | Each task holds its own copy of a label, with its own `id`. Find the task in `list_tasks`, take the `id` of its label entry whose `name` matches, and detach it with `labelId`. Never pass a workspace label's id. |
| `remove_relation` | `mcp__plugin_sdlc-llm_kaneo__get_task_relations`, `mcp__plugin_sdlc-llm_kaneo__delete_task_relation` | List the source task's relations, take the `id` of the one with the matching target and type, and delete it with `id`. |
| `search_tasks` | `mcp__plugin_sdlc-llm_kaneo__search` | `q`, `workspaceId` `<kaneo.workspace_id>`, and `type` `tasks`. Keep only the results whose `projectId` is `<kaneo.project_id>`. Don't pass `projectId`: Kaneo rejects it with `Workspace ID could not be determined`. Each result has `taskNumber` and `status`. |
| `set_status` | `mcp__plugin_sdlc-llm_kaneo__update_task_status` | `taskId`, and `status`. |
| `update_description` | `mcp__plugin_sdlc-llm_kaneo__update_task` | `taskId`, and `description`. |
