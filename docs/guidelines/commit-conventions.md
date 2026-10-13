# Commit conventions

How commits are named and written. `implement-task` reads this.

## Format

Conventional commits, with the task key as the scope:

```
<type>(<task key>): <summary>
```

* The summary is lowercase after the colon, imperative, under about 70 characters, with no trailing period.
* Commit messages are the only committed place a task key appears.

## Type

The squash commit's type comes from the task's type label:

| Task type | Commit type |
|-----------|-------------|
| `bug`     | `fix`       |
| `chore`   | `chore`     |
| `docs`    | `docs`      |
| `feature` | `feat`      |
| `refactor` | `refactor`  |

## Commits on a task branch

The branch is squash-merged, so these are working checkpoints. Each step that changes files ends with one:

```
wip(<task key>): <step name>
```

The step name is the skill step, for example `write tests` or `implement task`.

## The squash commit

* **Subject:** `<type>(<task key>): <task title, lowercased>`
* **Body:** the acceptance criteria met, as a list, and any follow-up tasks created, by key.

## Examples

`KEY` stands for the project's task-key prefix.

```
feat(KEY-42): reject batches whose blockers come later in the order

- A batch where a task's blocker is later in the order stops before any work.
- A batch where every blocker comes first starts normally.

Follow-ups: KEY-47
```

```
wip(KEY-42): write tests
```

```
fix(KEY-51): keep to-do order when a task is archived
```

## Don't

* Don't put more than one task in a commit.
* Don't write "update", "changes", or "misc" as the summary.
* Don't put a task key in code, docs, or test names. The branch name carries only the task number.
