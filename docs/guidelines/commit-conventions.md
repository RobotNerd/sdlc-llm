# Commit conventions

How commits and pull requests are named and written. `work` follows this for each task it commits.

## Format

Conventional commits, with the task key as the scope:

```
<type>(<task key>): <summary>
```

* The summary is lowercase after the colon, imperative, under about 70 characters, with no trailing period.
* Commit messages and pull request titles are the only committed places a task key appears.

## Type

The commit's type comes from the task's type label:

| Task type | Commit type |
|-----------|-------------|
| `bug`     | `fix`       |
| `chore`   | `chore`     |
| `docs`    | `docs`      |
| `feature` | `feat`      |
| `refactor` | `refactor`  |

## One commit per task

A batch branch has one commit per task, in the batch's order:

* **Subject:** `<type>(<task key>): <task title, lowercased>`
* **Body:** what changed, as a list, and any follow-up tasks created, by key.

A fix after review is a new commit with the same scope, on the same branch.

## The pull request

`work` opens one pull request per batch, and the developer squash-merges it on GitHub.

* **Title:** for one task, the task's commit subject. For several, `<type>: <what the batch does>`, with the type of most of its tasks.
* **Body:** each task's key and title, with a line on what changed.
* **On merge:** the squash commit on the default branch takes the pull request's title as its subject, and GitHub lists each branch commit's message in its body. That's how every task key in a batch reaches the default branch. Keep that list when merging.

## Examples

`KEY` stands for the project's task-key prefix.

```
feat(KEY-42): reject batches whose blockers come later in the order

- A batch where a task's blocker is later in the order stops before any work.
- A batch where every blocker comes first starts normally.

Follow-ups: KEY-47
```

```
fix(KEY-51): keep to-do order when a task is archived
```

## Don't

* Don't put more than one task in a commit.
* Don't write "update", "changes", or "misc" as the summary.
* Don't put a task key in code, docs, or test names. The branch name carries only the first task's number.
