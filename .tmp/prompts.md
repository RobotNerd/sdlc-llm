# prompts

<!-- Use @project-management-plan.md to create a PRD in @tasks/specs/. In addition to the tasks described in the document, add a way to track epics. I'm basing this off of my experience using Jira, a workflow I'm comfortable with. -->

<!-- Create stories using the PRD you created. I think they should all be grouped under an MVP epic unless you think otherwise. -->

<!-- We're dogfooding in this repository to define the workflow, so I don't have a clear understanding of it in my head yet. Can you describe your understanding of the workflow to me? What steps should you and I take now to start working on the tasks? Describe everything from start to finish, and note gaps (e.g. no automatic git commands because I'm doing those manually right now, but I may delgate them to you/the workflow later). -->

<!-- I merged it. Before you start working on the next task, try using the previous process of merging directly to main as a chore commit for cleaning up. -->

<!-- Question before working on TASK-020: will this GitHub Action workflow work on the free tier of GitHub that I'm using for personal projects? -->

<!-- Go ahead with TASK-020. -->

<!-- I merged it. Go ahead and clean up the branch, but don't start on the next task yet. -->

<!-- TODO: use add-task to create a new task for epic 001. It builds a python script using only stdlib as part of the init-project skill that offloads all of the deterministic behavior of the skill to code.

Use the add-task skill to add a new task to the board. This task is to refactor the init-project skill to move all deterministic behavior defined in the skill to a python script, built using only stdlib. Nearly all of the scaffolding can be done with code instead of the LLM. -->

<!-- TODO: use add-task to create a new refactoring task for epic 001

Use the add-task skill to create a new refactoring task in EPIC-001 that makes these changes to the `add-task` skill:
- move deterministic portions of the `add-task` skill to python script:
  - listing all open epics
  - 6.2 (creating the tasks.md file) can be split into 2 steps: 2a. code that creates the file from the template; 2b. where the LLM populates the new file contents
  - look for other deterministic steps that can be moved to the script
- clearly define parameters for the add-task skill in the skill definition -->

<!-- Make these updates to the project: -->

<!-- - Automatically perform git commands using the `gh` cli, which I just installed: pull latest from main, rebasing on main before creating a PR, create a new branch for a task, push changes to remote, create a PR. Recommend other git actions to include if you have any. -->
<!-- - Add/update existing tasks as necessary to account for automating git commands with `gh`. -->
<!-- - Note that I will manually review all PRs on github and squash & merge them myself. -->
<!-- - Make the changes you outlined in `Changes to make before TASK-001 starts` of @.tmp/workflow-plan.md. -->
<!-- - Update @CLAUDE.md. -->
<!-- - Add a note to yourself to ignore @.tmp/prompts.md. It's just a spot for me to write my prompts for you, so it's redundant from your perspective. -->

<!-- Additional notes/questions:
- I have already merged the previous PR into main as described in `Step 0 — prerequisite (you, manually)` in @.tmp/workflow-plan.md, and I created a new branch `feat/initial-workflow`. This new branch is for the last set of refinements I want to make to the initial plan before we tackle TASK-001. You can use `gh` now to push your changes and create a PR for this branch when you're ready.
- It looks like your plan only relies on pytest as a dependency at the moment and everything else is in stdlib. Should we use conda/uv for the sync script or is that overkill?
- I removed `tmp/` from .gitignore. I've decided to which to the `.tmp/` pattern and keep these files checked into the repo, knowing that I may manually remove them in the future. -->

<!-- Use the add-task skill to create a new refactoring task to clean up docs to remove redundant/deprecated information. This task should go at the bottom of the TODO list on the board. Some docs for cleanup that I've identified are:
- @./tasks/guidelines.md and @.claude/skills/init-project/templates/guidelines.md: some of these instructions are redundant now that they have been implemented in @.tasks/bin/sync.py.
- @CLAUDE.md
- Determine if anything in @.tmp/workflow-plan.md and @.tmp/project-management-plan.md is important information that needs to be kept. If so, find a better location for these details outside of .tmp.
- Add a `Example Usage` section to @README.md with an example step-by-step workflow that uses the skills defined in this repo. -->

<!-- I agree with your plan.

- Format: We'll do this as pure prose for now. After the implementation is done, I'll review and determine if I want a followup ticket to extract the deterministic behavior to a script.
- STOP semantics: You've been working more autonomously than I originally planned, and it's been going well. So let's keep that workflow.
- Good on the rest.

Go ahead with the implementation. -->

<!-- ---

TODO: Use the add-task skill to create a new refactoring task in EPIC-001 that makes these changes to the `implement-task` skill:
- move deterministic portions of the `implement-task` skill to python script:
  - step 0 and step 1 - most of these actions seem eligible for code
  - in general, most of the git actions seem like good candidates to be run in code
  - look for other deterministic steps that can be moved to the script -->

<!-- I merged it. Just like in previous steps, do the git clean up steps. Once you're done with the cleanup, use the add-task skill to create another task in EPIC-001 to automate the mechanical parts of the `refine-backlog` skill. Place the new task at the bottom of the TODO list on the board.

Include one additional work item as part of the new task. For step 3 with the stale-todo scan, I want a more sophisticated check then simply a created date > 30 days old. I'm designing this for use on my own personal projects, which I'll often have to drop and return to much later. One option is to account for the date of the last activity of the git repository, e.g. > 30 days older than the last commit date. I don't have a strong idea on the best way to do this, so part of the planning stage when implementing the task is to provide your analysis and suggestions on how best to adjust the stale-todo range. -->

<!-- I merged it. Just like in previous steps, do the git clean up steps. Once you're done with the cleanup, use the add-task skill to create another task in EPIC-001 to automate the mechanical parts of the `plan-feature` skill. Place the new task at the bottom of the TODO list on the board. -->

<!-- /add-task Remove references to details that are relevant only to this project, which can be found throughout many of the files in this project. One example: in the init-project skill, there is a reference to a task `(TASK-021)` included in the skill definition as well as comments in the associated scaffold script. This will be confusing to the agent when the skill is used in a different project, since it should have no reference to the inner workings of this repo, leading to a likely collision on task names. Focus only on the content that will be used in other projects, which is copied to the new project by the init-project skill @.claude/skills/init-project/. This goes at the bottom of the TODO list on the board. -->

<!-- /add-task New task in EPIC-001 at bottom of the TODO list. Modify the `init-project` skill so that it can be used to do an idempotent upgrade to an existing project where init-project has already been run. Like the current script implementation, behaviors should be implemented in the scaffold script where possible. Ensure that no existing spec/epic/task data is lost. The goal is to upgrade the skills and related process docs to keep them up-to-date with the latest changes in this repo. -->

<!-- /add-task Create a new task in EPIC-001 at the bottom of the TODO list. Add a new optional feature that includes an automatic code formatting tool if supported. Add an entry for it in @.tasks/config.md with null as the default value; it should be part of the interview questions to populate the value during the init-project skill. Update the implement-task to use the code formatter. Add a hook that ensure that the code formatter is run before creating a PR. -->

<!-- /plan-feature Create a new epic to move behavior to hooks. These hooks are included at the per-project level, so they are copied to a new repo as part of the init-project skill. I want you to identify what behaviors from the existing skills make sense to be turned into hooks. The goal is to ensure that the hook behaviors always occur and aren't left to probabilistic decisions. In addition to the existing skills and items I mention below, are there any new behaviors you would recommend adding as hooks?

My current ideas for hooks:
- Everything described in the `Guardrails` section of @.tasks/specs/SPEC-001-llm-sdlc-workflow.md.
- A script that checks for references to SPEC-NNN and TASK-NNN in the artifacts that will be copied to other repositories using the init-project skill (see TASK-027). Causes the agent to clean up these references before a PR can be opened for a task. This hook would only exist in the current repository and would be excluded from the list of artifacts copied by the init-project skill.
- The test_command is run before creating a PR and must pass.
- The lint_command is run before creating a PR and must pass.
- The code formatting tool is run before creating a PR (see TASK-031).
- Ensure that re-running init-project to upgrade a project doesn't modify the excluded files. -->

<!-- /plan-feature Create a new epic to refactor the `implement-task` skill to make it more automated. The tasks in this epic are placed at the bottom of the TODO list, and for now are planned to be implemented after all of the tasks in EPIC-002.

- The user can provide an epic, a task range, task list, or a stopping task and LLM works through all tasks autonomously:
  - epic provided: LLM attempts to implement all tasks in the epic
  - task range: implement all tasks from start to end in the range
  - task list: a list of individual tasks to work, which might not be in the same order as the TODO list on the board
  - stopping task: LLM starts with the first task at the top of the TODO section on the board and works all tasks in order from the TODO list until completing the stopping task
- before working, LLM must verify that the set of tasks provided by the user is valid; implement this as a script (or hook if that makes sense) to offload the decision making to be deterministic
- determine conditions when LLM should interrupt work and notify the user; these are my rough ideas, and I need suggestions/best practices from you
  - running into an issue the requires clarification from the user
  - running out of context; note that I need strategies to avoid this, which may need to be a separate epic itself
  - running into an unexpected blocker
  - using too many tokens; need strategies to keep token usage low, especially if we decide to start spawning additional worker agents
- creating follow up tasks: user can choose if they want the LLM to create additional tasks automatically or if the user needs to be notified; e.g. the LLM determines that a task is too big and needs to be split up; default to allowing new task creation, but add a configurable limiter to prevent task explosion
- switch to TDD: LLM should write test cases first, verify they fail, then implement and re-test until test cases pass -->

<!-- Merged, clean up then use /add-task to create a new task in EPIC-001 and place it at the top of the TODO list. Use TASK-023 as an example for creating a new skill to update the docs in this project. This will be invoked periodically by the human. Keep a list of docs in the config that should alwyas be reviewed and updated, as well as a list that should always be ignored. It looks like the sync script already looks for ignored_paths but I don't see it in the config, so maybe this needs to be fixed (include on this task if so). Determine what portions of this new skill are mechanical, if any; if so, add those to a paired scaffold script following the pattern of the existing skills. Ask for any clarification needed in the docs that can't be resolved automatically. -->

<!-- /add-task New task in EPIC-001 at top of todo list. Turn the work done in TASK-027 to strip project-specific references into a new skill `strip-project-references`. This new skill should only exist in this repository--it is excluded from the set of skills that are copied into other projects when running the init-project skill. Like with previous skill creation, determine what portions of this new skill are mechanical, if any; if so, add those to a paired scaffold script following the pattern of the existing skills. Ask for any clarification needed in the docs that can't be resolved automatically. -->

<!-- /add-task Create a new bug task in EPIC-001. Place at top of TODO list. This is a fix/refactor of the init-project skill coming out of TASK-029. Right now the skill only works within this repository, but it needs to be applied to a separate target git repo. I can think of two potential ways to handle it, but I'm open to suggestions if you can think of different/better approaches:

1. Clone this repo `sdlc-llm` as well as the target repo `T` where the init-project skill should be applied. Launch claude code in the `sdlc-llm` path. Invoke `init-project` and provide the local path to `T` as a parameter. The skill then applies everything to repo `T` at that path.

2. Make the `sdlc-llm` repo public on github. Clone the target repo `T` locally and launch a claude code session. Tell claude to use the init-project skill at the `sdlc-llm` github repo url and apply it to the local copy of `T`.

I think (2) isn't a very good approach, so I'm leaning towards (1).

Also add a small fix to the description in @.claude/skills/init-project/SKILL.md so that it renders properly in visual studio code. Here's the error that's showing up:

```
Failed to parse frontmatter
Nested mappings are not allowed in compact mappings at line 2, column 14:

description: Scaffold the "kanban in markdown" workflow into this repo — .tasks…
```

The problem appears to be the second `:` on line 3 in this spot `initialized, upgrade it: refresh`. -->

<!-- I changed my mind about this acceptance criteria:

- A managed file already present in the target is overwritten without prompting — the chosen behaviour; `run` still refuses only when the target already has `.tasks/`.

Change it so that it shows a diff and requires the human to rerun with `--force` to overwrite. I was confused and didn't realize `upgrade` was a separate action from `run`.

Please update TASK-049 to reflect this change. Note that I removed an acceptance criteria in TASK-049 for fixing the frontmatter on the `init-project` skill since it looks like you already fixed it. -->

<!-- There is an open PR for TASK-049 https://github.com/RobotNerd/sdlc-llm/pull/49. Before merging it, I tested init-project manually on another repo and there's one change I want you to make. When it prompts the user to populate config.md details, the prompt for the `docs_path` wasn't as user-friendly as I want. It should use phrasing like "which documents should be automatically updated in this repository when working on tasks?" -->

<!-- /add-task A new bug ticket at the top of the TODO list in EPIC-001. Earlier in this session I ran the /implement-task skill. My intention was to trigger you to pick the next task from the top of the TODO list, since there were no tasks in progress, no outstanding PRs waiting to be merged, and the most recent changes had been merged into main. But it didn't work, and you simply responded `Still nothing in progress — ready to start a new task. Auto-pick the top of TODO, or work a specific task?`. I want you to figure out why this happened, propose a fix, and create the new ticket to implement the fix. -->

---

<!-- /add-task A new task at the top of the TODO list in EPIC-001. Simplify and merge unit tests. Perform an analysis of all existing unit test looking for redundant tests, test cases that can be merged, and test cases that can be simplified. My suspicion is that we don't need all of the test cases that we currently have, and culling the ones we don't need will reduce context load in our working sessions. -->

---

<!-- I have some questions about EPIC-002: Once all the current tasks in this epic are implemented, will the file @.tasks/guidelines.md still serve any purpose, or will all of the details defined there have been successfully offloaded to skills and hooks? If not, identify which remaining parts, if any, can be moved to skills and/or hooks. Identify which portions of the doc can't be outsourced. Are the portions that can't be outsourced useful as instructions to the LLM for how to use these skills? If not, who is the intended target of this doc?

Ultimately, I'm trying to achieve these things:
- I want to understand if the LLM needs a broad overview like this guidelines doc that tells it how these skills should be used together and gives an overview of the spec/epic/task system.
- If the doc is needed/userful, where is the best place for that to live? Is the guidelines doc a good choice?
- If we keep the guidelines doc, then it will continue to be copied to a new repo when using the init-project skill. In this case, how would a claude code session started in the target repo know to load this guidelines doc as a reference, since we aren't modifying the existing CLAUDE.md in the target repo? -->

<!-- Read @.tasks/guidelines.md to gain context.

Then use the add-task skill to create a new task in EPIC-002 and place it at the top of the TODO list. The task is to implement the changes in the note added on @.tasks/archive/TASK-034-branch-dirty-tree-gate-hook.md:

```
- Follow-up candidate (not filed as a task, just noted): `implement-task/scaffold.py`'s own
  `dirty_files` could be migrated to call `guardrails.dirty_tree_violation` instead of keeping
  its own copy, per SPEC-002's "define guardrail logic once" goal -- out of this task's scope.
``` -->

<!-- > TODO: Come back to planning this later

/plan-feature Context/session management and multiple agents. Goes on board after all current epics, blocked by all current epics. The goal is to add the option to this workflow to run multiple agents.

- Session hand-off when context gets too full (configurable percentage threshold). Write a short hand-off doc, clear the session, and have LLM continue from the hand-off doc. (see TASK-043)
- Option to run multiple simultaneous "longish-lived" instances of claude code:
  - the orchestrator (e.g. opus, high effort)
  - the worker (e.g. sonnet, high effort)
  - the critic (haiku, ? effort, see TASK-045)
- model/effort for each is configurable
- configation options: disabled, only orchestrator and worker, all three
- each instance would stay live until hitting the threshold mentioned earlier (e.g. context too full, TASK-043), at which point it would do a session hand-off to a new instance of itself
- orchestrator focuses on planning tasks (e.g. creating tasks)
- the worker focus on implementation of each task
- if worker thinks planning is necessary, likes splitting up the current task, it passes that work back to the orchestrator
- at its discretion, the orchestrator can task the critic with reviewing PRs implemented by the worker agent, although this wouldn't necessarily happen for every task

These are my rough ideas, but I don't know the latest best practices for how to handle this type of multi-agent workflow. Keep in mind that I'm currently on the $20/month plan of claude code. I may ugrade to a more expensive plan later, but even when I do, I want to be smart about conserving tokens and context to support better scaling.

NOTE: Claude's initial analysis:

```
 On session hand-off: Claude Code already has native machinery for most of this — /compact (with custom preservation instructions, settable in CLAUDE.md), automatic compaction at a configurable context threshold, and — on Pro/Max
  specifically — an offer to "resume from a summary" when reopening a large session after a break. This is strikingly close to what .tmp/session-handoff.md already does by hand in this very repo. TASK-043 (EPIC-003) was explicitly built
  as a stopgap deferring "the real strategy" to a future epic — this is that epic, and it should upgrade TASK-043 rather than duplicate it, and it benefits every implement-task run, not just multi-instance ones.

  On multi-instance architecture — this is the important finding. Claude Code has two different primitives, and they're not equally suited to what you described:                                                                                                             No changes this session

  - Agent teams (experimental, opt-in via an env var): teammates share one session's lifetime — they're cleaned up when the lead session ends, can't be resumed after /resume, and Anthropic's own docs measure them at ~7x the token cost of
    a standard session when teammates plan first. Built for bounded parallel exploration (research, competing hypotheses), not standing, long-lived roles.
  - Cross-session messaging: lets genuinely independent, separately-launched Claude Code processes (interactive or headless -p) message each other by name, each with its own normal lifecycle — resumable, can /compact//clear on its own,
    can run indefinitely as a background worker.

  Your description — "each instance stays live until hitting the threshold, then hands off to a new instance of itself" — is exactly what cross-session messaging between independent processes supports, and exactly what agent teams don't
  (an in-process teammate can't survive a hand-off). So I'd steer this design away from agent teams entirely.

  On cost, plainly: a Pro plan's usage limit is one account-wide pool on a rolling 5-hour/weekly window, shared across everything you run. Three simultaneous long-lived instances don't triple your budget — they draw on the same pool
  three times as fast, so you'd hit the weekly ceiling sooner in wall-clock time for the same total spend. Worth designing the defaults around that reality rather than around "more instances = more capacity."
``` -->

<!-- /plan-feature Run multiple agents. This should go in a new epic that is placed at the bottom of the TODO list. It is blocked by EPIC-003.

- Orchestrator: A more powerful model that does the planning.
- Worker: A less powerful model that implements work planned by the orchestrator.
- Critic: A model that reviews changes implemented by the worker.
- All models and effort levels are configurable.

Behavior
- The orchestrator triggers the worker to start working on a task or a set of tasks.
- The orchestrator triggers the critic to review changes implemented by the worker.
- The critic reports its findings back to the orchestrator, and the orchestrator determines if the report requires a follow up action. Follow up actions can include: determine that no action is necessary and the current task can be completed, rework the current task to fix/improve issues based on the report feedback, create new tasks to address the critic's feedback later, stop work and ask the human user for clarification. I am open to your suggestions for additional follow up actions or changes to the ones I listed.
- Determine what level of capability you would recommend for each agent. The orchestrator should clearly be the smartest and most capable. How smart/capable do the worker and critic need to be in comparision.
- Is it possible to adjust the worker and critic effort level on the fly based on the difficultly level of the task? This would be decided by the orchestrator when delegating work to one of the other agents, and the adjustment to that agent's effort level one change before starting work, but only if this is an actual efficiency improvement.

Providers
- Each agent can optionally be outsourced to a model outside of the Anthropic ecosystem.
- The critic will be outsourced to a less expensive non-Anthropic model by default.
- Include an investigation while planning this feature to rank external models. Consider the latest ones from providers like qwen, deepseek, z.ai, gemini, kimi, and any others you find that are popular. Compare based on cost vs performance.
- Propose strategies to make this multi-agent process efficient. I want to avoid hitting the limits with claude/anthropic as well as keep costs reasonably low for openrouter/external model usage. For anthropic, I'm on the $20/month plan at the moment. I may upgrade later, but target this level of plan in your analysis for now.

Guardrails
- Guardrails are added to the critic-to-orchestrator feedback/rework loop to prevent it from getting stuck. If the critic kicks back the same task 3 times to the orchestrator to rework it, the orchestrator stops the automation and prompts the human user for clarification.
- Monitor available openrouter credits. Stop work and alert the user if the credits dip below a configurable threshold and/or the rate of credit consumption is greater than a configurable threshold (credit usage per request for the last 2 requests).
- I would like your suggestions for additional guardrails and/or changes to the ones I mentioned above.

Other
- Any deterministic behavior should be planned for implementation in a script.
- Implement behaviors in skills and hooks as appropriate.
- Propose any new skills and hooks that you would add for these features, if any. -->

<!-- It failed on step 4. The command ` gh pr create --title "scratch dry run" --body "throwaway - do not merge` was not denied as it should have been. Instead, it showed this output:

```
Warning: 6 uncommitted changes

Creating pull request for task-999-scratch-dryrun into main in RobotNerd/sdlc-llm

https://github.com/RobotNerd/sdlc-llm/pull/64
```

This the modified line from .tasks/config.md:

```
test_command: python3 -c "import sys; sys.exit(1)"
```

And I added a line with the text `trivial change` to README.md for step 2.

I cleaned up--PR deleted, scratch branch deleted. -->

<!-- /add-task New task in EPIC-004 at the bottom of the TODO list. I want a mechanism to automatically compact (or clear if that make more sense) the context for orchestrator and worker agents. Since these will be long-running agents, then I expect their context to eventually fill up and degrade performance.

One call out--I assume that the worker will be a long-running agent, but I need to verify that with you. The other possible workflow I can imagine is that the orchestrator would create a new instance of the worker for every task (sequentially). I'll defer to you to tell me which workflow is a more performant. -->

<!-- /add-task Put at top of TODO list. No epic. This is an enhancement to the init-project skill due to a gap that I noticed while testing manually. The target project that I applied init-project to wasn't using python, and the .gitignore did not include a __pycache__ entry (nor other python-related exclusions). Update the init-project skill so that it updates the .gitignore in the target repo to exclude all python-related artifacts that shouldn't be commited to the repo, if these entries don't already exist in the target repo's .gitignore. Do this programmatically with code. -->

<!-- PR merged.

Once you've finished the post-merge clean up, add a new task at the top of the board in EPIC-003. The range requirement I gave you for TASK-039 was wrong. The range doesn't account for the hand-ordered priority of the TODO list on the board. Change the behavior so that when I supply the starting and ending task ids, the range is taken from the existing ordering on the board starting with and ending with those tasks. -->

<!-- TODO: planning
- run /review-docs next
- Is there any way to programmatically enforce TDD with hooks? Right now it's prose-only and relies on the LLM model's decision. See recent implementation details in @.tasks/archive/TASK-040-tdd-mode.md -->

<!-- /add-task Add to EPIC-003 and place at the top of the TODO list. Address this note on @.tasks/archive/TASK-041-core-autonomous-loop.md:

```
No persistent batch-state file: ScheduleWakeup resumes the same session/conversation rather
than starting a fresh process, so the remaining task order and the outcomes accumulator survive
in context across a wait. Recovering batch progress from repo state alone after a lost session
is an open gap, not required by this task and not claimed by any of TASK-042/043/044/045 either.
```

The new task ensures that batch progress can be recovered from the repo state alone when starting a fresh session. -->

<!-- /add-task Analyze the content of @.claude/skills/implement-task/SKILL.md to determine if it can be simplified.
- Remove historical decisions that are unnecessary for the skill behavior, e.g. using phrasing like "unchanged".
- Remove steps that have been encoded in the python scripts associated with the skill.
- Determine if and steps can be merged.
- Determine if the wording of any steps can be simplified to improve clarity and reduce context without losing the meaning. -->

<!-- /add-task EPIC-003. Top of TODO list. Create a bug ticket for the problem you mentioned in the previous task:

Separate bug, not fixed: a stray .tasks/TASK-*.md without valid frontmatter makes sync crash with a traceback instead of a clear error. That could be its own task. -->

<!-- Approve. For each of your notes that need clarification:
1. OK
2. OK
3. OK
4. Change the behavior to bail out on rejection. This should end the batch and remove any artifacts. The summaryt should contain details about how many tasks were in the original batch, how many were completed, and which one fail to cause the batch to end prematurely.
5. List it as pending in the PR body. -->

<!-- It isn't working with my manual tests. I created a new epic `EPIC-002` with 3 tasks in another repository, and I used the prompt `/implement-task EPIC-002`. For the first run, I set `allow_auto_merge: false` in config.md, and that did I expected and stopped at the PR for the first task. I deleted the PR and branch, then set `allow_auto_merge: true`. When I ran the test a second time, I expected it to attempt to complete all three tasks, but it stopped again to wait for me to approve the PR for the first task. Am I missing anything in my test setup to enable automation for all 3 tasks without my intervention? -->

<!-- TODO: full rebuild of implement-task workflow
- resume? if so, jump to where you left off
- start task: pick next task and plan
- write tests
- implement task
- run tests; if tests fail, go back to `implement task` and make adjustments based on feedback; otherwise, proceed
- create pr
- spawn critic agent to review pr
- if critic rejects pr, go back to `implement task` and make adjustments based on feedback; otherwise, proceed
- merge PR, rebase main, do project management cleanup, merge directly to main; pick next task from batch and go to `start task`; if not more tasks in batch, proceed
- report: write summary report of the batch

- addendum: creating follow-up tasks
- addendum: interrupts
- addendum: bailut
- addendum: guardrails -->

> TODO: plan mode, Opus 5.5, xhigh effort
> TODO: create/find a guidelines doc for how to write a skill that keeps it short and clean

<!-- /plan-feature A full rewrite of the implement-task skill. All tasks for this new epic will be placed at the top of the board.

The implement-task skill @.claude/skills/implement-task/ in its current state is confusing. When I attempted to manually test the most recent change made in TASK-045, the automation behavior did not work. I reviewed the SKILL.md content, and it's clear to me that the failure occurs because of conflicting instructions.

I now have a better understanding of the skill requirements, and I want to create a completely new version of the skill from scratch. The new skill should be named `implement-task-v2` during development. Once the epic is complete and I'm satisified with the behavior, I will rename it to `implement-task` to replace the existing skill.

## Features

Some specific features of the new version that differ from the original:

- batch mode by default: The skill treats all task implementation as a batch of tasks. When implementing only one task--either a specific task requested by the user or the default task taken from the top of the TODO list--this is treated as a batch of one.
- critic agent enabled by default: A less expensive agent is spawned to review each PR, and the critic must approve the changes before merging is allowed. The allow_auto_merge config field is no longer needed.
- TDD: use test-driven development
- BDD: follow behavior-driven development
- Phase-naming for interruption recovery: In the original implementation, the batch-state used names like `phase1`, `phase2`, etc for the names of the phases where an interrupted batch could recover. In the new version, these should use the human-readable name of the corresponding step in the SKILLS.md file, e.g. `write tests` or `merge changes`.

## Parameters

- optional batch argument: "[tasks|range|stopping-task|epic]"

## Development process

- For the initial rewrite of the skill there will not be any associated python script automation--it will be prose-only in the `SKILLS.md` file. The delegation of a subset of behaviors to python scripts will be done in subsequent tasks. In order for the new version of the skill to run, the hooks defined in this repository may need to be disabled.
- All development can be done on a local branch per task. Once changes are reviewed and finalized, the local branch should be squashed and merged into main. At that point, the main branch should be pushed to remote.

## Creating follow-up tasks

- New tasks can be created at any point during a batch run
- The `autonomous_new_task_limit` from `.tasks/config.md` sets a hard limit for the number of tasks that can be automatically created
- see reference doc for creating follow-up tasks for more details

## Skill workflow

Here is the workflow I want the skill to follow in the order that it should occur:
- Ensure clean working repo
  - Stop immediately if any of the following states are discovered:
    - the `gh` cli tool is not installed
    - the git working tree is dirty
  - Pull the latest changes to main from remote
- Interrupted batch detection
  - Determine if the implement-task skill from a previous session was interrupted
  - If interrupted and the user provided a batch parameter, stop and get clarification from the user; determine if the user wants to delete the interrupted batch to start the new one, or if the interrupted batch should be resumed
  - If continuing an interrupted batch, recover the batch state and resume the batch where it left off
  - If not interrupted, go to the `Build batch` step
- Build batch
  - Build a batch of tasks to implement based on the arguments (if any) provided by the user
  - Building the batch list uses the TODO list defined in .tasks/BOARD.md
  - Batch types
    - no argument provided: choose the top task from TODO list on .tasks/BOARD.md by default if no argument provided by user, effectively making a batch of one task
    - specific list of tasks: a list of one or more tasks provided by the user; example prompts might be `/implement-task TASK-031 TASK-033` or `implement tasks 44, 45, and 47`
    - range: start with TASK-AAA and implement tasks up to and including TASK-BBB; all tasks between TASK-AAA and TASK-BBB are taken from the TODO section of the board in the order defined on the board
    - stop on task: basically the same as the range option, but with TASK-AAA automatically chosen as the very first task from the top of the TODO list
    - epic: implement all tasks from the TODO list assigned to the given epic
  - Batch validation: the list of tasks in the batch is validated before work begins; if the batch state is invalid, stop work and get clarification from the user
    - already implemented: the batch contains tasks that have already been implemented
    - task does not exist: the user listed a task the does not exist in the TODO list
    - task blocked: a task is blocked by another open task that is not part of the current batch
    - wrong order for range: the user provided a start/end task for a range where the ending task is prioritized higher on the board than the starting task
    - no stopping task: the stopping task provided for either the `range` or `stop on task` modes is invalid (doesn't exist, already completed, etc)
    - no tasks found: the generated batch is empty
- Start task
  - pick the next task from the batch and set it as the active task
  - create a new local git branch for the task; see reference doc for naming conventions
  - update the state of the task, its epic if it has one, and the board to reflect that the task is in progress
- Write tests
  - follow test-driven development
  - follow behavior-driven development
  - unit tests are not committed to the repository except for special cases; most unit test are considered throwaway
  - behavioral tests are committed to the repository
  - refer to the testing strategy reference document for full details of the testing strategy
- Implement task
  - make changes to the repository to meet the acceptance criteria of the task
- Run tests
  - verify that the entire test suite passes, including the newly written tests from the `Write tests` step above
  - if tests fail, return to the `Implement task` step to address the failures or to the `Write tests` step if the tests need to be modified
- Spawn critic
  - lauch a subagent using the Agent tool with `model: "haiku"`
  - see reference doc for `critic`
- Merge changes
  - NOTE: the previous implement-task skill created a PR on github for a human to review, but that is unnecessary now; the critic can perform that review using the details on the local branch; in this new workflow, the agent will not create PRs
  - perform the bookkeeping behaviors used in the previous version of the skill at this point: updating BOARD.md, archving the task file, updating the epic details, etc; all changes should be done on the local task branch
  - squash merge to main
  - push changes from main to remote
  - delete the local feature branch for the task
- Create summary report
  - create new file in `reports/` that contains a summary of the task
  - see reference doc that defines naming conventions
- Batch complete
  - reach this step when all tasks in the batch are complete or the batch bailed out early
  - write a new summary file in `reports/` following this python strftime pattern: `batch-%Y-%m-%d-%H-%M-%S.md`
  - see the reference doc for summary report

## Reference documents

All of the documents described below should be created in the `references/` subdirectory of the skill. The SKILL.md instructions should refer to these documents in the individual steps where this reference information is needed. The intent is to offload reference material out of the main skill description to keep it clean and only use reference docs when the agent needs additional details for a given step.

I have outlined some of the basic details for each of these reference documents. As part of the feature planning process, I would like you to further populate the content of each reference document using details that exist in the implement-task SKILL.md as well as the associated python scripts, batch_select.py and scaffold.py. Make changes as necessary where my instructions in this prompt diverge from the original version. I will review these reference docs once you have generated the proposed content of each doc in the spec for this epic.

### Reference doc: naming conventions
- use the same basic format for git branches and for per-task summary reports
- git branch: task-<NNN>-<slug>
- summary report: task-<NNN>-<slug>.md
- `NNN` and `slug` are taken from the `.tasks/TASK-*` file for the task being worked
- `NNN` is the numeric portion of the task from the task id
- `slug` is a kebab-case representation of the task title

### Reference doc: critic
- TODO: parse the guidelines for critic from the existing implement-task SKILL.md and python code
- ensure that and documentation changes are included in the review as well; documentation should be concise and clean
- check that lists and data structures in the code and documentation are sorted alphanumerically if the actual order doesn't matter

### Reference doc: summary report
- TODO: propose format for summary reports, both per-task and per-batch, based on the existing report structure
- Each summary report should include instructions for any manual tests that need to be run by the human user.
- the full batch summary report contains details about the entire batch, including tasks implemented, tasks not implemented, new tasks created, recommended tasks not yet created, manual testing steps if any, and reason for bailing out early if a bailout occurred

### Reference doc: testing strategy
- write throwaway unit tests; delete them once the branch for the task is squashed and merged into main
- committing unit tests to the repository is allowed in rare circumstances, e.g. testing a function that is likely to change often, code that is deemed likely to cause a regression
- commit behavioral tests
- the goal is to keep code that tests the surface area of the code rather than the internals--behavior-driven development (BDD)
- unit tests often go stale, making them a burden
- unit test counts can quickly balloon without providing much value per test, introducing unnecessary context bloat

### Reference doc: creating follow-up tasks
- Reasons for creating a new task:
  - An individual task is too large and needs to be split up
  - A new bug or necessary feature is discovered while working on a ticket and it is outside the scope of the current ticket
- New tasks are created using the add-task skill and added to the board at the bottom of the TODO list
- Assign the new task to an existing epic only if it's clear that it naturually fits into one. Otherwise, leave it as unassigned to an epic.
- The `autonomous_new_task_limit` from `.tasks/config.md` sets a hard limit for the number of tasks that can be automatically created while implementing a batch; once this limit is reached, new task recommendations are included in the summary reports generated for each task as well as the batch summary report
- Creating new tasks during a batch run is completely autonomous without any human involvement; the user will review new tasks after the batch run is complete

### Reference doc: interrupts and bailout

Situations where the agent determines that the batch must be paused and wait for a decision from the user.

- `needs_clarification` — the task is ambiguous, or its acceptance criteria contradict something discovered mid-implementation
- `unexpected_blocker` — something task-specific blocks progress
- `quality_gate_failure` — `test_command`/`lint_command`/`format_command`/`sync check` fails for the same reason multiple times in a row for a given task; `quality_gate_attempts` in .tasks/config.md sets the max allowed attempts
- `guardrail_denial` — the same `PreToolUse` hook denies a retry on a task multiple times in a row; `guardrail_denial_attempts` in .tasks/config.md sets the max allowed attempts
- `infra_failure` — `git`/`gh` itself is broken (auth expired, network failure, rate-limited, etc)
- `critic_rejection` — the critic rejects the change multiple times; `critic_rejection_attempts` in .tasks/config.md sets the max allowed attempts
- `context_usage_exceeded` / `token_budget_exceeded` — usage thresholds are exceeded; see the existing `check-usage-thresholds` implementation in .claude/skills/implement-task/scaffold.py for the behavior, which will need to be reimplemented in v2 of the skill

### Reference doc: guardrails
- NOTE: none of the guardrails listed in the implement-task skill apply for now; guardrails will be rebuilt from the ground up

## Additional updates

- Docs and the config.md need to be updated to reflect these changes.
- The spec includes any of the behaviors above that are candidates for automation. The initial implementation is prose-only in SKILL.md. Subsequent tasks will refactor SKILL.md and migrate those behaviors to an associated python script.
- Plan to reimplement the usage thresholds check from the original version of the skill. -->

<!-- Make these changes to the spec:
- Clarify that the task to update config.md removes deprecated keys that are only used by v1 and ignored by v2 of implement-task.
- Change the hook denial behavior. Since only one hook actually blocks v2, disable only that hook and keep the other two active.

Once those changes are made, go ahead and create the tasks. Also, move TASK-071 to wont-do as you suggested. -->

Some feedback on the tasks you created:

## TASK-073-v2-skeleton.md

Under `Testing strategy`, I would categorize the proposed test `tests/test_implement_task_v2_skill.py` as a throwaway unit test. As proposed, it's fragile and could easily fail if the number of step headings changes over time as we iterate on the skill, the order of steps could be adjusted, references change, etc. Same with the other criteria for this test case.

## TASK-074-v2-summary-reports.md

Under `Testing strategy`, the same note as above: `tests/test_implement_task_v2_skill.py` would be a throwaway unit test as described here.

---

> TODO: have LLM interview me on BDD

I would like to discuss BDD test criteria in more detail with you so that we can lock in a definition of it. We both need to be aligned on what I'm asking for out of behavioral tests before you begin implementing the tasks to build v2 of the skill.

Tthe manual test cases you added to the tasks in this epic are the behavioral tests. It's fine that we don't have any behavioral tests to check in for this epic. My gut feeling is that all behavioral tests will be manual and we will only be able to implement automated behavioral tests of implement-task-v2 once we start moving functionality into scripts.

Perform a web search on best practices for behavioral tests, and use that to define a list of clear, simple behavioral test rules that can be added to the testing strategy reference doc. Show them to me first, and interview me with questions about them so I can provide clarifications.

---

TODO: Update /add-task to include plans for comprehensive BDD test cases in each task; covers new test, changes to existing tests, and/or deprecations to existing tests; include expected inputs and outputs for each test case; clarify each test case as a either behavioral test or a throwaway unit test
TODO: Create a new EPIC for automating implement-task-v2.
TODO: Epic to rewrite existing `tests/`; find behavioral tests to keep and throw away the rest; write new tests to cover any missing behavioral test gaps

---

TODO: general
- prevent claude from inserting line breaks in markdown: https://mcpservers.org/agent-skills/prisma/markdown-no-artificial-line-wraps
- make a rewrite pass at README
- new skill: find shared code and move it to a shared library
- add linter; include prevention of large code files
- Add refactoring check for plan-feature and add-task
- Figure out the right way to choose model as orchestrator w/ different workers; ensure plan mode is always opus; make opus write the plan and tasks instead of switching to sonnet

---

TODO: remove stuff
- remove tdd_enforced from config.md and all references to it in the code; TDD is always followed
- remove workflow_version references from entire project

---

TODO: PLUGIN: group all skills as a plugin for namespacing
