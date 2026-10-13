# Code style

How code in this repo is written.

## Python

* Python ≥ 3.11, standard library only. `pytest` and `ruff` are the dev dependencies.
* Lint and format with ruff, configured in `pyproject.toml`: a line length of 120, and an explicit rule selection, so the result doesn't depend on ruff's defaults. `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .` must pass.
* A lint rule broken on purpose gets a `noqa` comment naming the rule and saying why, such as `# noqa: BLE001 - a failing hook must never block the turn from ending`.
* Match the surrounding code: its naming, idioms, and comment density.
* Names say what a thing is. No abbreviations a reader has to decode.
* Comments explain why, not what. No comments that restate the code. Keep comments at a minimum.
* No magic numbers. A constant or config default carries a comment saying why it has that value.
* Errors: handle the conditions you can, and fail with a specific message for the rest. Don't leave a bare exception for the agent to puzzle out.
* Use forward slashes in every path.

## Sorted order

Lists and data structures whose order doesn't matter are sorted alphanumerically:

* imports
* config keys
* set and dict literals

When order does carry meaning (steps, priority, a sequence), keep it, and don't sort.

## Prose in comments

* The code should be self-documenting. Write comments only when the meaning of a portion of the code is not straightforward.
* Short and plain. Short sentences, common words.
* No time-sensitive wording ("currently", "new", "recently").
