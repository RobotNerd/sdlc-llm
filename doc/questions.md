# Open questions: PRD v2

Each question has a recommendation. Reply with the question number and "agree" or your answer.
Section numbers (§) refer to [PRD-v2.md](PRD-v2.md).

## Kaneo data model

**Q1. How should epics be modeled?** (§7.2) Kaneo has no native epics.
- A. **(Recommended)** A parent task labeled `epic`, kept in Planned. Children are linked with
  `subtask` relations, and Kaneo shows "n/m complete" on it. Epics stay off the board columns.
- B. The same as A, but epics sit in their own `epics` column, so they're visible on the board.
  This makes the board busier, and each epic's column position has no meaning.
- C. A separate Kaneo project that holds only epics, linked by relations across projects. The
  spike has to confirm that relations work across projects.
- D. A label per epic (`epic:auth-flow`). You get filtering, but no progress rollup, and
  workspace labels pile up.
> Answer: Option A

**Q2. Where do feature specs live?** (§7.2, §9.2)
- A. **(Recommended)** In the epic's Kaneo description. Durable decisions are copied into the
  architecture doc, with no tracker references. The spec goes stale in Kaneo, not in the repo.
- B. In the repo (`doc/specs/`), written without tracker references. They stay reviewable in
  diffs, but they're exactly the stale-artifact problem you're trying to remove.
- C. Both: drafted in the repo, then moved into Kaneo once approved.
> Answer: Store them in my self-hosted instance of [outline](https://www.getoutline.com/). Its MCP server is available at https://rainbow-flame.taila02055.ts.net:8445/. I have already connected claude code to the MCP server and verified that it works.

**Q11. Which columns?** (§7.2) The proposal: Planned (the backlog), `to-do`, `in-progress`,
`needs-human`, `done`, `wont-do`. Is `needs-human` (a paused batch, or a blocking manual test)
worth its own column? The alternative is a `needs-human` label on an `in-progress` task, but
only a status change fires Kaneo's default notifications. Should `wont-do` be a final column, or
should cancelled tasks be archived or deleted?
> Answer: Create a column for `needs-human`. No column for `wont-do`; archive them instead.

**Q12. Priority: drag order or Kaneo's priority field?** Recommendation: position in `to-do`
(drag order) is the only priority, and the `priority` field stays unset. v1 had one ordered list,
and a second priority signal would conflict with it.
> Answer: Agreed with your recommendation

**Q22. One Kaneo project per repo, all in one workspace?** Recommended. Say so if a repo should
span several projects, or the reverse.
> Answer: Agreed

## Repo artifacts and references

**Q3. Where does this PRD live once its tasks are in Kaneo?** It's a committed planning
artifact, so by your rule it goes stale. Options:
- A. Move it into Kaneo, as the description of a "v2" epic or a project description.
- B. Keep it in `doc/` until M1, then fold what lasts into the architecture doc and delete it.
  **(Recommended)**
> Answer: Option B, using outline.

Related: the PRD avoids v1 ids on purpose. Confirm that's the right call for docs written
during the transition too.
> Answer: Correct

**Q6. May commit messages cite Kaneo task keys?** (§8.3) Recommendation: yes, and only commit
messages, as `feat(KEY-NNN): title`. That's the one link from code history back to the tracker,
and `resume` relies on it (`git log --grep <key>`). Branch names include the task number too;
they're deleted after the merge.
> Answer: Yes, this is a good idea

**Q4. Where does the batch report go?** Per-task reports are Kaneo comments.
- A. **(Recommended)** A local gitignored file (`.sdlc/local/reports/`), with the headline also
  printed. It's cheap, private, and disposable.
- B. A comment on every task in the batch, which repeats the same text.
- C. A "Runs" project in Kaneo, with one task per batch. It's searchable, but adds clutter.
> Answer: Per-task reports as kaneo comments is fine. Write the epic reports to outline. For now, let's use the structure below to organize docs, and we'll iterate on it.

```
sdlc-llm
├── docs
├── spec
│   ├── SPEC-AAA: Title
│   └── SPEC-BBB: Title
└── reports
```

- docs: finalized documents; architecture, design, tutorials, etc
- spec: location of the specs (PRDs)
- reports: epic-level reports stored here

I'm open to suggestions to the above structure right now if you recommend any changes.

## Skills

**Q5. Where do autonomously created follow-up tasks go?** v1's plan put them at the end of
TODO. Recommendation: Planned (the backlog) with a `follow-up` label, so nothing the agent
invents enters the ready queue without your triage. The trade-off: a batch can't pick up its
own follow-ups.
> Answer: Agreed. The batch shouldn't automatically pick up its own follow-ups. I want a human-in-the-loop review of these for now, although we could revisit this later.

**Q10. Kaneo project setup: a skill, a script, or a doc?** (§9.6) It's a one-time job: create
the project, columns, labels, and the config file. Recommendation: a small `setup-project` skill
backed by a script, because column creation is REST-only and it's also useful when you add a new
repo. It doesn't copy any toolkit files, so it isn't `init-project` coming back. The alternative
is a setup doc.
> Answer: Agreed with your recommendation

**Q16. Keep a PR-based mode?** The v2 design dropped PRs for local squash merges gated by a
critic. Is that the only mode, or do you want an opt-in PR mode later (CI gating, Kaneo's GitHub
integration moving tasks on PR events)? Recommendation: local merge only, with PR mode listed as
deferred.
> Answer: Agreed with your recommendation 

**Q23. Does `refine-backlog` keep the active-days stale measure?** It flags a task by days with
commits since the task was created, not by calendar age. Recommendation: keep it, with the
threshold moved into config (`stale_active_days`).
> Answer: Agreed with your recommendation

## Packaging and architecture

**Q7. Config format and location.** The proposal is `.sdlc/config.toml`. TOML allows comments
(v1 relied on key notes), but reading it with the stdlib needs Python 3.11+ (`tomllib`). The
macOS system Python is 3.9. Options:
- A. **(Recommended)** TOML, with Python ≥ 3.11 as a stated requirement.
- B. JSON: works on any Python 3, but has no comments.
- C. A different location or name (for example, `sdlc.toml` at the repo root).
> Answer: Agreed with your recommendation

**Q8. How should skills share code?** `npx skills` installs one skill at a time, so shared code
(the Kaneo client, config loader, git helpers) has to be inside each skill.
- A. **(Recommended)** A single source in `lib/`, with a build script that copies it into each
  skill's `scripts/_shared/`. The copies are committed, and CI fails on drift.
- B. A pip-installable, stdlib-only CLI (`uvx sdlc-llm ...`) that the skills call. There's no
  duplication, but it adds an install step and breaks the "copy the skill and it works" model.
- C. Support the Claude Code plugin only, where skills can share files at the plugin root, and
  drop `npx skills`.
> Answer: Agreed with your recommendation.

**Q9. How portable across agents?** `implement-task` depends on Claude Code for its critic
subagent (`model: haiku`) and its usage valve (it reads Claude Code transcripts). Recommendation:
Claude Code is first-class. Other agents are best-effort and may lose the critic or the valve,
and the docs say so. Or should portability shape the design now?
> Answer: Focus on portability up front. I want to outsource the critic to an external agent in the future, most likely called by API (e.g. openrouter). For the prose-only initial version of implement-task-v2, it's fine to rely on a claude code only setup with haiku, but the subsequent task to make this scriptable implements it in a portable manner.

**Q15. Which guardrails matter?** (§11.1) v1's hooks mostly protected the markdown tracker. The
proposal: scripts enforce their own preconditions, and a few optional plugin hooks act as a
backstop. Which rules, if any, do you want hook-enforced from day one?
> Answer: Nothing from day one. Add hooks in follow up work.

**Q20. MCP transport and access in the prose-only phase.** Recommendation: prose-only skills
call the Kaneo MCP tools directly. Use the built-in HTTP endpoint (`/api/mcp`, OAuth), so the
stdio package's Node 24 requirement goes away. Confirm that, or say whether you'd rather use the
stdio package with an API key.
> Answer: Agreed with your recommendation.

## Scope and sequencing

**Q13. What happens to the current backlog and the legacy code?**
- The implement-task-v2 tasks: drop them, since M3 re-plans the same design against Kaneo?
  **(Recommended)**
- The multi-agent orchestrator/critic tasks: drop them, or import them into Kaneo's backlog as
  deferred?
- Legacy code: tag v1 and delete `.tasks/`, `sync`, hooks, v1 skills, and their tests at M1.
  **(Recommended)** Or keep v1 running until v2's `implement-task` works?
> Answer: Agreed with your recommendations. As for the multi-agent orchestrator/critic tasks, I want to keep this behavior (see my answer above regarding using the haiku critic). Don't re-import the existing tasks blindly. All of these tasks should be revisited while keeping the new workflow plan in mind, and these tasks should be rewritten from that fresh perspective. Add them to kaneo as deferred.

**Q14. Is the multi-agent orchestrator/worker/critic work still wanted?** It covers role
tiering, the OpenRouter critic, and budget guardrails. The PRD lists it as deferred. Keep it as
deferred, or drop it?
> Answer: Yes. See above.

**Q17. Who writes the guideline docs?** These are the architecture, testing strategy, code
style, task style guide, and commit conventions docs. Options:
- A. You write them.
- B. I draft each one from what's in the repo and your past feedback, and you edit.
  **(Recommended for the task style guide and commit conventions)**
- C. A mix. Also: is this set of five right, and is anything missing (a glossary, a security
  policy)?
> Answer: Agreed with your recommendation.

**Q19. Kaneo version policy.** Kaneo shipped six releases in about two days. Recommendation:
pin the Docker image tag, run the contract tests before each upgrade, and upgrade deliberately,
not automatically. Is running a Kaneo container in GitHub Actions for contract tests acceptable?
> Answer: Don't worry about upgrades for now. We'll keep kaneo pinned with the docker image tag for now. I will manage all self-hosted work in a separate project, which will leverage this sdlc-llm workflow. I'll define the kaneo upgrade project there with guardrails and validation.

## Environment

**Q18. Where will the agent run?** Kaneo is on your home network. Will sessions always run on a
machine on that network, or do you need remote access (Tailscale or a reverse proxy)? The PRD
treats cloud-hosted sessions, such as Claude Code on the web, as unsupported.
> Answer: Always on my machine and connected to my home network via tailscale.

**Q21. Task style guide content.** Before I draft it: do you have firm preferences for title
format, the maximum number of acceptance criteria, sentence style (the plain, short style of
your recent edits), or sizing rules? Or should I infer them from the tasks you've edited most
recently?
> Answer: Short and concise for all content. The plain, short style is preferred. No hard rule for the maximum number of acceptance criteria, although I may update that if I feel like tasks end up being too bulky.
