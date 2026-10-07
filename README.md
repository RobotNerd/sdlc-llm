# sdlc-llm

Agent skills for a solo developer who builds software with an LLM. The skills plan features,
write tasks, groom the backlog, review docs, and implement batches of tasks, from branch to
merge.

Work items live in [Kaneo](https://kaneo.app), a self-hosted tracker. Specs, guideline docs,
and reports live in [Outline](https://www.getoutline.com), a self-hosted wiki. Notifications
for anything that needs the developer go to Discord, with Telegram as a fallback. The repo
holds only code, tests, evals, and config.

## Status

Version 2 is in development: it's being rebuilt as a single Claude Code plugin on top of
Kaneo and Outline. Version 1 kept the tracker inside each repo as markdown files. It's
preserved at the `v1-final` tag:

```bash
git checkout v1-final
```

## Development

Python 3.11 or later, standard library only. `pytest` is the one dev dependency:

```bash
pip install -e '.[dev]'
```

```bash
python3 -m pytest
```
