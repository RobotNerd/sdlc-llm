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

<!-- Some feedback below on the tasks you created. Please update the tasks to reflec these notes.

## TASK-073-v2-skeleton.md

Under `Testing strategy`, I would categorize the proposed test `tests/test_implement_task_v2_skill.py` as a throwaway unit test. As proposed, it's fragile and could easily fail if the number of step headings changes over time as we iterate on the skill, the order of steps could be adjusted, references change, etc. Same with the other criteria for this test case.

## TASK-074-v2-summary-reports.md

Under `Testing strategy`, the same note as above: `tests/test_implement_task_v2_skill.py` would be a throwaway unit test as described here. -->

<!-- I would like to discuss BDD test criteria in more detail with you so that we can lock in a definition of it. We both need to be aligned on what I'm asking for out of behavioral tests before you begin implementing the tasks to build v2 of the skill.

Tthe manual test cases you added to the tasks in this epic are the behavioral tests. It's fine that we don't have any behavioral tests to check in for this epic. My gut feeling is that all behavioral tests will be manual and we will only be able to implement automated behavioral tests of implement-task-v2 once we start moving functionality into scripts.

Perform a web search on best practices for behavioral tests, and use your findings to define a list of clear, simple behavioral test rules that can be added to the testing strategy reference doc. Show them to me first, and interview me with questions about them so I can provide clarifications. -->

<!-- My answers to your questions:

1. It counts as observable behavior.
2. The testing section should start with a short simplified summary that uses the labels Given: / When: / Then: followed by the numbered steps that describe the details of the propsed test procedure.Manual testing steps follow the same pattern and are included in the task description after the automated testing plan.
3. Task files and reports are enough for now.
4. Some manual tests can be marked as "must pass before merge" and this should be done during the planning stage when I review the tasks that you generated. When the implement-task skill is invoked, it should check all tasks in the batch for these blocking manual tests. If any are found, ask the user if they want to proceed or if they want to adjust the batch.
5. Faking is acceptable for now.
6. This is good as is.

Given that feedback, create a new document @doc/testing-strategy.md with plan. -->

<!-- Notes on the additional decisions:

1. Agreed
2. On pass it merged. On failure, it stops the batch.
3. Agreed
4. Agreed

Keep doc/testing-strategy.md as the master copy for right now. I'll revisit this later.

Don't implement the steps that you outlined in `Plan: applying this strategy to EPIC-005` yet. I have something else I want to do first. -->

---

<!-- I've spent some time reconsidering my design of this system. My main conclusion is that managing epics and tasks as part of each project is a bad design decision. It's overly cumbersome, reinvents the wheel, and it leaves a lot of unnecessary stale data in the project as archived files. I want to use these lessons to rethink the design.

Here are my current thoughts on how I want to change things up:
- Use [kaneo](https://kaneo.app) for project management. It handles all task management, the kanban board, etc. It appears to come with an MCP server for agent connectivity. Leverage as many of its features as possible for task management rather than the agent doing the work. I plan to self-host it on my home network. As part of this planning phase, I want you to evaluate kaneo to ensure that it will meet all of the needs for what I want to accomplish with this project.
- I still want to keep the functionality of most skills. They need to work with kaneo instead of repo-managed tasks. I'm open to changing they way skills are organized, i.e. we don't have to keep exact same grouping of behavior by skill if something else makes more sense (new skills, splitting up skills, merging skills, etc). These tasks have behavior I want to keep: add-task, implement-task, plan-feature, refine-backlog, review-docs
- Drop the init-project skill. Users can install skills as a plugin or manually per-skill, which seems to be industry best practice. Also consider making these installble using vercel labs npx skills, which I think is a way to share skills across multiple agent platforms.
- The goal is still to automate the process of implementing batches of tasks. This means that building implement-task-v2 will still happen mostly as designed. It will be most complex skill.
- Skill behavior should continue to be offloaded to deterministic scripts wherever possible. Keep the iterative development process where the first round is prose-only, and then behavior is offloaded in small testable chunks.
- I noticed that what we've built so far feels more unstructured than I would like. I think the correct way to resolve this is a combination of multiple changes I should make: more upfront planning on my part of testing procedures and architecture direction in my prompts, defining style guide documents (architecture, testing strategy, linting rules, etc), and providing a solid style guide of how I want the tasks you generate to be formatted and worded.
- Guideline reference docs, like @doc/testing-strategy.md, should be independent of the tasks managed by the project. For example, right now the testing strategy doc includes references to things like implement-task-v2 and EPIC-005. These types of references should be limited only to the tasks stored in kaneo and not exist in any of the generated artifiacts that are committed to the repo.

Given this new direction, I want you to start by performing a full analysis of the project in its current state. Compile a new spec document/PRD that captures the features the new version should implement, and write it to @doc/PRD-v2.md. Take into account existing features, planned features (in current specs, epics, and tasks in @.tasks/), and the changes I mentioned above. Fill in any gaps you notice with your suggestions. Finally, put any questions you need me to clarify in a new file @doc/questions.md.

We'll iterate on the new PRD document. -->

<!-- TODO: self-hosted tmp
- write step-by-step plan to deploy obsidian, kaneo, and sparkyfitness
- make notes about what I've already tried and problems I ran into
- keep doc around as a reference so it can be used to migrate data for these services later when I finalize my home network -->

<!-- Write up an installation plan for me in a new file @doc/tmp-self-hosted.md that provides step-by-step instructions to install each of the following services:

- [obsidian](https://obsidian.md/)
- [kaneo](https://kaneo.app)
- [sparkyfitness](https://github.com/CodeWithCJ/SparkyFitness)

## Goals
- I'm installing kaneo and obsidian to unblock progress on the sdlc-llm project, since I want to use both services as part of this workflow.
- The sparkyfitness service is already running on that machine and I want to keep using it, but it's conflicting with the other services I'm trying to host (more details below).
- I'm working on a more comprehensive plan for my self-hosted home network, and these services will likely need to be migrated to another host machine. The output document should include all the details necessary to know how and where these services are installed to make it easier to know what needs to be migrated in the future.
- For obsidian, I want to install the LiveSync plugin to keep data synced between the hosted service and the obsidian mobile app on my phone.

## Platform
- OS: Ubuntu 24.04
- Machine name: rainbow-flame
- Networking: tailscale
  - MagicDNS url: rainbow-flame.taila02055.ts.net
  - IP: 100.105.75.3

## Background
I initially installed sparkyfitness on rainbow-flame. To make it accessible from my other devices on the tailscale network, I enabled MagicDNS and ran `sudo tailscale serve --bg 3004`. The problems started later when I tried to install kaneo on the same machine. I tried running these commands:

```
sudo tailscale serve reset
sudo tailscale serve --bg --set-path=/kaneo http://127.0.0.1:5173
sudo tailscale serve --bg --set-path=/sparkyfitness http://127.0.0.1:3004
```

When I try to access either of the above URLs, I get a blank screen in the browser. In the browser dev tools console, there are a bunch of disallowed MIME type errors, like this: `Loading module from “https://rainbow-flame.taila02055.ts.net/assets/useSearch-BSm_91uI.js” was blocked because of a disallowed MIME type (“text/plain”).`. My guess is that neither of these services are playing nice with the paths where I'm trying to serve them. I've installed obsidian on rainbow-flame, but I haven't tried to configure it yet until I can resolve the serving issue. -->

<!-- Make adjustments to the document given this feedback:
- Modify sparkyfitness to be served on port 3004 externally instead of defaulting to port 443.
- The path to sparkyfitness: `$HOME/app/sparkyfitness` (full path `/home/mib/app/sparkyfitness`)
- I installed obsidian with the `apt` package manager. Make sure the docs include instructions to install it using docker since I'll need to reinstall. -->

<!-- I'm following the sparkyfitness setup. I tried accessing it from my macbook, which I hadn't done before. It's showing me the error: `Authentication Failed Invalid Origin`. I'm also getting the same error when trying to reach it from the mobile app. I see these errors in the debug console:

```
[Auth Client] Error: 
Object { response: Response, responseText: '{"message":"Invalid origin","code":"INVALID_ORIGIN"}', request: {…}, error: {…} }
auth-client-BStSoeHw.js:1:236
[ERROR] Mutation Error:  
Object { message: "Invalid origin", code: "INVALID_ORIGIN", status: 403, statusText: "" }
api-BQ-8BZLf.js:1:1359
[ERROR] Auth: Sign in failed: 
Object { message: "Invalid origin", code: "INVALID_ORIGIN", status: 403, statusText: "" }
api-BQ-8BZLf.js:1:1359
```

Give me instructions to resolve this issue and update the document to include the steps. -->

<!-- I got obsidian running...and I think I hate it. It seems to be the hot new documentation tool for self-hosting that everyone is using alongside AI agents, but I do not like the UX. The setup process was not streamlined, which makes me worry about the longetivity of this product.

Here are the features I'm looking for in a self-hosted documentation tool:
- Acts as the source of truth for documentation: docs for multiple projects like sdlc, my personal notes, etc.
- Has a WYSIWYG in-browser editor.
- Can be used from a desktop browser or mobile.
- Ideally has a mobile app that connects to my self-hosted server, but I'm willing to use mobile-web if the UX is solid.
- Easy for an LLM agent to interact with it, e.g. MCP.
- Stable
- There's an active community.
- Nice to have: supports plugins/extensions.
- Similar services I've used and liked: Notion, Confluence.

Perform an analysis of popular documentation tools to compare and contrast them on these features. Include Obsidian in the analysis. -->

<!-- I reviewed those options and decided to give AFFiNE a try. It seems stable enough, and the mobile app makes it worth a shot. The miro-style canvas seems like it could come in handy. If it doesn't work out, I can try falling back to other options, like Outline, Docmost, or BookStack, which all look good.

Update @doc/tmp-self-hosted.md:
- Remove obsidian.
- Add AFFiNE install instructions.
- Add a section capturing your comparison of documentation tools. Include a note that if AFFiNE falls through, I will try Outline, Docmost, and/or BookStack. -->

<!-- Make some updates to @doc/tmp-self-hosted.md.

First of all, the command `curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3010/` when setting up affine will return a 302. This is because it redirects you to create the initial user account when first accessing the site. I was able to reach the URL in the browser and configure it just fine.

The bigger change: I want you to add step-by-step instructions for setting up an MCP server along with steps to test and verify it via claude code. This is a critical feature for me, because I want the LLM agent to read and write (create, update) docs in affine. I want to know if this will work now so that I can pivot to another tool if it doesn't.

Create two sets of instructions for using AFFiNE MCP:
1. Using the built-in MCP server. I tried enabling AI support in the AFFiNE settings under the `AI BYOK` section, but I'm not sure what exactly I need to configure. This section references `Settings > Integrations` but I don't see that section anywhere in the AFFiNE settings.
2. Using this MCP server: https://github.com/DAWNCR0W/affine-mcp-server. It looks like a community plugin to me, so I'm hoping it gets around the need to sign up with a provider in the AFFiNE configuration in order to enable MCP access.

Also perform a web search to determine if there are any other options for setting up AFFiNE MCP beyond the two approaches I listed above. -->

<!-- Update the document to include a section with in similar instructions for Outline: installing, configuring, enabling MCP, and testing MCP. I'd like to play with it now just in case I like it better, considering that it requires fewer workarounds than AFFiNE for my use case. I noticed from their official docs that the recommended way to use it on mobile is with [PWA](https://docs.getoutline.com/s/guide/doc/mobile-Ez4bmY6VDD). This might be acceptable for my mobile usage and I will test it. -->

<!-- The outline install is failing on step 6c. 4. I see the error when checking the docker logs with `docker compose logs -f outline`:

```shell
outline-1  | {"error":"password authentication failed for user \"outline\"","level":"error","message":"Failed to connect to database","stack":"SequelizeConnectionError: password authentication failed for user \"outline\"\n    at Client._connectionCallback (/opt/outline/node_modules/sequelize/lib/dialects/postgres/connection-manager.js:145:24)\n    at Client._handleErrorWhileConnecting (/opt/outline/node_modules/pg/lib/client.js:379:19)\n    at Client._handleErrorMessage (/opt/outline/node_modules/pg/lib/client.js:399:19)\n    at Connection.emit (node:events:509:20)\n    at /opt/outline/node_modules/pg/lib/connection.js:115:12\n    at Parser.parse (/opt/outline/node_modules/pg-protocol/dist/parser.js:38:17)\n    at Socket.<anonymous> (/opt/outline/node_modules/pg-protocol/dist/index.js:11:42)\n    at Socket.emit (node:events:509:20)\n    at addChunk (node:internal/streams/readable:568:12)\n    at readableAddChunkPushByteMode (node:internal/streams/readable:519:3)"}
```

And the docker containers from `docker compose ps`:

```shell
NAME                 IMAGE                                              COMMAND                  SERVICE    CREATED         STATUS                          PORTS
outline-outline-1    docker.getoutline.com/outlinewiki/outline:1.10.1   "docker-entrypoint.s…"   outline    6 minutes ago   Restarting (1) 34 seconds ago   
outline-postgres-1   postgres:16                                        "docker-entrypoint.s…"   postgres   6 minutes ago   Up 6 minutes (healthy)          5432/tcp
outline-redis-1      redis:7 
``` -->

<!-- It's failing on step 6c. 5 when I navigate to https://rainbow-flame.taila02055.ts.net:8445/ and it's redirected to the URL https://rainbow-flame.taila02055.ts.net:8446/interaction/error?error=You+are+not+allowed+to+access+this+service. I ran `docker compose logs outline` and don't see any errors.

Also a slight variation to your instructions: I'm using 1password. I saved the passkey there instead of the icloud keychain. -->

<!-- The outline MCP commands are working very well. Outline seems to meet my needs, as you originally recommended. Update the document to deprecate the affine installation instructions and add step-by-step instructions to remove the existing affine install.

When testing the MCP commands in claude code, I was prompted to allow the MCP requests. How can I allow all MCP requests to the outline server in claude code? -->

<!-- I successfully uninstalled affine and committed all changes to git. Update @doc/tmp-self-hosted.md to meet these criteria:
- Remove all references to affine.
- Remove all references to obsidian.
- Remove the documentation tool comparisions appendix. Outline should work just fine, and if I ever need to return to this analysis, I can find it in the git history.

The goal of this update is to make the document contain only the details that describe the current state of the self-hosted services and to not include any historical decisions. -->

---

<!-- I added my answers to @doc/questions.md.

These are my responses to your suggestions in @doc/PRD-v2.md that aren't already answered in the questions doc:
- Section 4. I agree with this: `Keep the tracker calls behind one client module anyway, so a second backend stays possible.`.
- Section 6. Agreed: `The core data model (§7) uses only features that the MCP server exposes, so prose-only skills never hit a wall. Only the one-time project setup needs REST or the web UI.`
- Section 7.1 Notify the human: Agreed. I'm not familiar with mattermost, but it sounds like a good option since it's self-hosted. The other option I was considering is signal, which might work better in cases where I'm remote and might have disconnected my phone from tailscale. I think this warrants further analysis of messaging options so I can determine which platform (or maybe multiple platforms) I want to support.
- 8.1 commit conventions: Agreed
- 9.1 the two STOP conditions and the ASK: only do these when the human triggers the add-task skill; when the agent invokes the add-task skill once the spec is finalized (via the plan-feature task), it should automatically create the epic and multiple tasks within that epic without human interaction; human review of all generated tasks comes after those are created
- 9.1 3 duplicate check: Agreed
- 9.2 2 architecture check: agreed; note that the wording should change to remove the reference to commtting the doc changes, since the agent will automatically make those changes in the outline app
- 9.3 2 blocked-order problems: agreed
- 9.3 5 ready check: agreed
- 9.5: Agreed on `The code-style and architecture docs are part of the critic's input [suggestion].`.
- 9.5: Agreed on `placed in Planned [suggestion] (not at the end of to-do; Q5)`
- 9.6: Agreed
- 11. repo layout: agreed, except for the `scripts/_shared` folder; see response to Q8
- 11. versioning: agreed on semver
- 11.1 guardrails: agreed on `A SessionStart hook that prints the Kaneo tasks that are in-progress or needs-human [suggestion]: the replacement for v1's board-context hook.`.
- 12 Contract tests: Agreed
- 13 3: `[suggestion] A step is ready to extract once it has passed its manual test in at least two runs with no prose change in between.` It's a good guideline, which I'll determine manually. No need for the agent to keep track of this.
- 13 4 extraction order: looks good for now

Other specific notes:
- 7.3: A self-hosted kaneo instance is running on my local network and available over tailscale at https://rainbow-flame.taila02055.ts.net:8443/. I have not connected its mcp server to claude code yet, but we can do that and then you can run all of the tests you describe in this section. I'd say we run this outside of the official workflow, since we're moving to tasks that would require kaneo.
- Section 9 `plan-feature`: epic stays in kaneo, spec moves to outline
- Using kaneo and outline: When we start replacing portions of the skills with scripts, the calls to these external tools should be abstracted using an interface. The goal is to hopefully make it easier to swap out backend tools in the future if necessary. I'm not sure if it's really possible to do this within the prose content of the skill, but if so, let's word the skill to act this way as well.
- I want to integrate an optional external messaging tool for notifying me on STOP and ASK conditions, which you mentioned in Section 7.1. Whenever one of these events occurs, the notification is always displayed in the claude code terminal. If the messaging tool is enabled (set in config.md), then a short, concise version of the notification is sent on that messaging channel. We'll choose an initial messaging tool in the beginning, but I may want the option to support multiple messaging tools/channels in the future.
- Is it possible to use a `.env` file in this repo for storing secrets. For example, it could hold the `KANEO_API_KEY` secret you refer to in section 10.

Update the PRD given this feedback. If you have any additional questions, add them at the bottom of the questions doc.
Since you have access to outline, copy @doc/PRD-v2.md to outline once you've made the above changes locally. Likewise, move @doc/questions.md to outline but with a better name, like `PRD-v2-questions`. For the next round of changes to these docs, we'll try to use only the versions in outline. -->

<!-- Round 2 feedback.

I added my answers to @doc/questions.md.

Responses to your suggestions in the PRD:
- 6.1 in prose: agreed
- 7.2 outline: agreed
- 7.2 <project> > docs > guidelines: agreed on this location
- 7.2 spec titles: agreed
- 7.3 cancelled tasks: agreed
- 7.3 labels: agreed
- 7.4 outline: agreed
- 8: message shape: agreed
- 8: how it's sent: agreed
- 8 Later (two-way replies): agreed
- 9.3 outline docs: agreed
- 10.1 needs-refinement comment: agreed
- 10.2 5 tasks in planned: agreed
- 10.5 critic safety: agreed
- 11 claude code .env deny settings: agreed

Other notes:
- For the guideline docs, section 9.1: Keeping these in outline is good for now. Later, I think these should be moved to their own github repo. Since I'm making the skills public, the guidelines docs they rely on should be public as well--outline is self-hosted and I won't open it to the public. The docs can be placed in a separate public git repo, and it can allow mix-and-match guidelines (e.g. separate code style docs for multiple languages) that the consuming repository can choose to use. Don't worry about planning this out now, but make a note of it in the PRD.
- Section 10.2: Interviews should be conducted using the `questions` document pattern like we're using for the planning of this PRD. Create the questions doc in the appropriate location in outline. Once the user updates the docs with answers, they will notify the agent of that so the skill workflow can resume. -->

<!-- I answered the round 3 questions in outline.

Responses to your suggestions in the PRD:
- 7.2 reports paths: agreed
- 7.4 archving: agreed
- 8. avoid duplicate notifications: agreed
- 10.2 resuming: agreed
- 10.5 step #10, outline epic reports path: agreed
- 10.5 critic floor interrupt: agreed

Additional Notes:
- Go ahead and delete the local PRD-v2 doc now that we're using outline
- I came across two official claude code guides that seem relevant here. Read both guides and then compare to the PRD. Are there any changes you would recommend making to the PRD based on these guides?
  - [Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
  - [AI-native SDLC playbook](https://academy.claude.com/courses/ai-native-sdlc-playbook) -->

<!-- I updated the questions doc with answers for Round 4.

Responses to your suggestions in the PRD:
- 10.1 question doc location: agreed

Additional notes:
- When adding questions to the question docs, insert a new line with `> Answer: TODO` after each new question to be answered.
- As for the course I referenced, signing in is optional. Try checking it again. In case you can't get past the sign-in gate, I included direct links to each part of the course below.

AI Native course - all pages in order:
- Intro: https://academy.claude.com/courses/ai-native-sdlc-playbook/introduction
- Intent: https://academy.claude.com/courses/ai-native-sdlc-playbook/capture-intent
- Requirements/design: https://academy.claude.com/courses/ai-native-sdlc-playbook/requirements-and-design
- Plan: https://academy.claude.com/courses/ai-native-sdlc-playbook/plan-mode
- CLAUDE.md: https://academy.claude.com/courses/ai-native-sdlc-playbook/claude-md
- Skills: https://academy.claude.com/courses/ai-native-sdlc-playbook/skills-as-institutional-knowledge
- Sessions/subagents: https://academy.claude.com/courses/ai-native-sdlc-playbook/parallel-sessions-and-subagents
- Feedback loop: https://academy.claude.com/courses/ai-native-sdlc-playbook/give-claude-a-feedback-loop
- CI: https://academy.claude.com/courses/ai-native-sdlc-playbook/continuous-evals-in-ci
- PR review: https://academy.claude.com/courses/ai-native-sdlc-playbook/ai-in-the-pr-review-loop
- Hooks: https://academy.claude.com/courses/ai-native-sdlc-playbook/hooks-as-approval-gates
- CICD: https://academy.claude.com/courses/ai-native-sdlc-playbook/ci-cd-integration-and-deployment
- Metrics: https://academy.claude.com/courses/ai-native-sdlc-playbook/closing-the-loop-on-metrics
- Closing: https://academy.claude.com/courses/ai-native-sdlc-playbook/closing-thoughts-and-resources -->

<!-- My feedback on your suggestions in the PRD:
- 9.1 things claude gets wrong: agreed
- 10.3 6 deferred review: agreed
- 10.4 3 things claude gets wrong: agreed
- 16 deferred, kaneo as single record: agreed -->

<!-- The PRD document looks good. Change its status (currently "draft"), and then write step-by-step instructions that I can follow to manually implement the verification spike. Format the instructions as you would if you were writing it as a kaneo task. For now, put the task in outline nested under `PRD v2: sdlc-llm`. We can delete the doc once done.

While I'm working on that spike, go ahead and write the draft versions of the guideline docs. -->

<!-- The file @doc/tmp-self-hosted.md contains a set of instructions that I used to install self-hosted apps that are needed for the current project, sdlc-llm. I want to add one additional self-hosted tool: excalidraw.
- the agent will use excalidraw to create diagrams when it needs one for documentation
- the agent will use the excalidraw mcp
- the instructions should follow a similar pattern to the step-by-step instructions provided in the doc for other tools
- the instructions should include a short set of prompts for testing that direct the agent to use the mcp; it should create a diagram from scratch, make an edit to that same diagram, then export it as an image to a file saved locally in the current directory
- [self-hosting instructions](https://docs.excalidraw.com/docs/introduction/development#self-hosting)

Ask me any clarifying questions you have before starting. -->

<!-- As an aside while I work on that task, can you modify the PRD in outline. I want you to replace the architecture diagram at the beginning of section 6 with a mermaind diagram. Outline supports mermaid natively.

If this is successful, I want to modify the PRD to include this a guideline for docs--use mermaid to create diagrams when needed. -->

<!-- Agreed with your addition, which should make the diagrams cleaner.

One bit of feedback on the diagram you created in the PRD--it was visually messy. I edited it myself to explicitly add a layout at the top of the mermaid definition, like this:

```mermaid
---
config:
  layout: elk
---
```

This was me tinkering--there may be an even better layout available. Update the PRD and guideline docs to include this. Since you can't see the rendered page, make a best guess of which layout should be used depending on the diagram type. If possible, we should come up with a way for you to see the rendered page so that you won't need a human in the loop to create clean diagrams. Or find another way to generate diagrams other than mermaid in outline. -->

<!-- I'm working through the first manual task. Update the outline document `Verify the Kaneo and Outline behavior the v2 data model relies on` to use formatting that's easier for me to use, as described below. Also update the formatting guidelines for all documentation, not just tasks, to take these changes into account.

Friction points
- Terminal commands for me to run that are displayed inline in a paragraph are slower for me to copy/paste because I have to highlight them with the mouse. Displaying them in a dedicated code block makes it much easier, since outline automatically shows a copy button to copy the command with a single click.
- Displaying non-command values that I have to copy/paste inline in a paragraph also makes it slower for me to read and understand. For example, in Setup > Step 4, the workflow columns are listed inline. It would be easier for me to understand them, as well as copy/paste, if they were displayed as a bulleted list.

## Example 1: Command to run

### Current
2. Kaneo API key. In Kaneo: Settings → Account → API Keys → create `sdlc-spike`. Then `read -s KANEO_API_KEY && export KANEO_API_KEY` and paste it.

### Preferred
2. Kaneo API key. In Kaneo: Settings → Account → API Keys → create
```
sdlc-spike
```

Then
```
read -s KANEO_API_KEY && export KANEO_API_KEY
```
and paste it.

## Example 2: label values

### Current
5. Kaneo labels. In the UI, create workspace labels `epic`, `deferred`, and `wont-do`.

### Preferred
5. Kaneo labels. In the UI, create workspace labels:
- `epic`
- `deferred`
- `wont-do` -->

<!-- I finished running the manual tests in the document `Verify the Kaneo and Outline behavior the v2 data model relies on`. Note that I cut the backend findings from the architecture guideline docs, since that did was not a good place for the testing outcome. Instead I nested it in a new document under the test procedure document and named it `backend findings`. It's an ephemeral doc and will be removed once we're done with it.

There were a few deviations found. The most significant one was when trying to reorder kaneo tasks using the API. Setting `position: 0` doesn't automatically reorder other tasks in the same column. I put this as a "maybe" for breaking the PRD. I'm not sure if the PRD calls for using the API specifically to reorder tasks or if it's loose enough to support MCP as a replacement. There may also be a workaround you can discover with the API that will reorder tasks properly.

Feedback on other steps included as well. -->

<!-- I will clean up the docs in outline manually.

Right now I'm reviewing the guideline doc drafts you wrote. While I'm doing that, I want you to read the file @.tmp/anthropic-email.eml. It's an announcment about recent updates to the claude code ecosystem, and I think some of them may be applicable to what we're building in this project. Go ahead and read the content of the linked documents for full details. Summarize any recommendations you have about how any of these features/tools might fit in the sdlc-llm project. It's ok if none of them are relevant, or if they would only provide marginal benefits. Call that out if so. -->

<!-- I have finished reviewing the guideline docs in outline. My feedback:

- The `Code style` doc mixed concerns: it included guidelines for writing code along with those for writing documentation. I split out the documentation portion and moved it to a new document alongside the existing one named `Documentation style`. There is some overlap with the `Task style` guide; skills that refer to the tasks style guide should also refer to `Documentation style`.
- In the review policy doc, I changed the nit limit to 10.
- I updated a reference in the `Skill authoring` doc to the `Documentation style` doc.
- The `Task style` guide might violate the rule of nested references. For example, it refers to both the `Code Style` and `Testing strategy` docs. I'm not sure if just referring to them by name counts as a nested reference, so it might be fine in its current state.

Make updates as necessary. -->

<!-- I'm working on the messaging ticket and I noticed a change to make to the documentation and task guidelines. When the manual instructions I have to follow involve creating a file, you're currently using `pbpaste` like this example from the document `Pick the notification channel for STOP and ASK messages`:

```bash
pbpaste > notify_check.py && python3 -m py_compile notify_check.py && echo ok
```

I would prefer instead that you tell me the name of the file to create along with its contents as the first step, skipping the `pbpaste` portion of the statement. I can create the file in my editor. So this example would become something like:

Create a file
```
notify_check.py
```

with this content:
```python
# Sends one test message with the standard library, the way the M1 notify script will.
import json, os, sys, urllib.error, urllib.request

channel = sys.argv[1]
# ...
```

Next run:
```bash
python3 -m py_compile notify_check.py && echo ok
``` -->

<!-- I completed the messaging task and the results are in outline. Short answer: discord as primary with telegram as a failover option in case of service outage. -->

<!-- Everything passed. I manually cleaned up following your instructions, and I've merged the PR. Clean up and start SDLC-4. -->

<!-- Discord properly showed a tappable link in step 3.

Discord failed as expected in step 4, but telegram then failed with a 400. I added TELEGRAM_BOT_TOKEN to the .env file, and I thought I used the same one I successfully used in our manual tests from M0. Walk me through troubleshooting it. -->

<!-- The telegram message is received as expected and the tappable link works. One last thing. I pasted the output of the test command below. Is the `unknown webhook` error expected here?

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/0/broken python3 lib/notify.py --skill implement-task --kind ASK --task SDLC-6 --text "manual test, Discord broken" --link https://github.com/RobotNerd/sdlc-llm/pull/97
warning: notification not sent: sent to telegram after discord: HTTP 404: Unknown Webhook
{"sent_to": "telegram", "warning": "sent to telegram after discord: HTTP 404: Unknown Webhook"}
``` -->

<!-- Merged. Make a note in SLC-11 or SDLC-12 (wherever it fits best) to remove the "Skill evals" section via setup-project, then clean up and start SDLC-11. -->

<!-- The manual test worked as expected. The extra columns for kaneo shows this:

```json
"extra_columns": [
  "in-review"
]
```

Update provision to remove this column for new projects. -->

<!-- It's failing on step 2, saying that the MCP servers aren't connected. I verified that they are connected with the prompts `list all collections in outline` and `list all projects in kaneo`, which each returned the expected data. Here's the output with th error:

```
STOP: the plugin's MCP servers aren't connected. I stopped before asking any interview questions.

- Plugin tools missing: step 2 needs mcp__plugin_sdlc-llm_kaneo__list_workspaces, and no mcp__plugin_sdlc-llm_* tool exists in this session. The only Kaneo and Outline tools here come from separate servers named kaneo and outline (mcp__kaneo__*, mcp__outline__*).
- Why I didn't use those instead: the other skills call only the plugin's tool names. So do the permissions setup writes to .claude/settings.json, and the step 7 check. Running setup against the other servers would still leave every later skill broken.
- URLs not filled in: the skill shows the default Kaneo and Outline URLs as ${user_config.kaneo_url} and ${user_config.outline_url}, not real addresses. The plugin's settings, which hold those URLs, look unset or not loaded.

To fix:
1. Run /mcp to see whether the plugin's kaneo and outline servers are listed and why they failed. Check that the sdlc-llm plugin is installed and enabled, and that its settings include kaneo_url and outline_url.
2. Restart Claude Code, then run /sdlc-llm:setup-project again. It will start over from step 1.

.env is already at the repo root. I didn't read it, as the skill requires.
``` -->

<!-- Everything works now as expected. I squashed and merged the PR, and you can clean up the board.

Before we move on, I have a question about the current repo. Is there a step in any of the upcoming milestones to start dogfooding on the current repo, which we tried in v1? Or have we not planned that yet and/or are actively avoiding it? -->

<!-- Is there a reason that the new setup-project skill is defined in `skills/` instead of `.claude/skills`? -->

<!-- TODO: run it on this repo -->

<!-- Yes, make the first M2 task running setup-project on this repo. I signed into the kaneo mcp, so you should have access to it now. Once you finish cleaning that up, it looks like we're ready to move to M2.

Going forward, here are some changes I want you to make:
- The milestones in Section `15. Roadmap` of the PRD v2 doc should be represented as epics in kaneo. The tasks created in each milestone are assigned to that epic.
- The manual test instructions in kaneo should be written out step-by-step with all the details I need to run them directly on the task itself. So far, you've been writing these instructions out to the console, which makes it more difficult for me to copy/paste commands to run in the terminal. If you can't fully determine all manual test steps needed before actually implementing the ticket, another option is to include the full test instructions as a comment on the kaneo ticket. Tell me which one you chose in the output in the claude code cli. -->

<!-- Feedback on SDLC-22 107:

Simplify the skill description in @skills/add-task/SKILL.md. The description should be treated as a trigger, acting as a guide that lets the agent know when to invoke the skill. Remove any additional details from the description that don't help achieve this goal, like in this case, portions of the description that describe details of what it's doing internally. Add this a guideline to the PRD so that it's included when authoring upcoming skills. -->

<!-- On the editing problem in auto mode: I updated my user-level claude settings in ~/.claude/setting.json. However, in this project I also have .claude/settings.json and .claude/settings.local.json, both of which contain permissions settings. Is there something I can change in either or both of these files to resolve the editing issue? -->

<!-- Before I try that, I'm going to end this sessions and start a new one. I saved your instructions above, and I will try them if the fresh session fails to fix the problem.

Before I start the fresh sessions, I want to make sure that the new session can pick up right where we left off. Is there anything special I need to add as a prompt, or will the session be able to pick up everything from what's available in the repo and its access to kaneo/outline? -->

<!-- Here are some more details about the session where the error is happening.
- The session is running in this path: /Users/marshallbowles/dev/sdlc-llm
- It attempted to edit four files; three failed and one edit succeeded.
- This is a fresh session, but it's still happening.
- The file `.claude/settings.json` in that directory was successfully edited in auto mode.
- Edit attempts were made to these files in that directory, but they failed: tests/test_plugin_layout.py, .claude-plugin/plugin.json, and CLAUDE.md.

First, try making ten separate edits to README.md in this repository, since it could be an intermittent error. If that passes, please to a deep dive into the other repository I mentioned above to see if you can spot anything locally that could be causing the problem. -->

<!-- More details. I first disabled the kaneo mcp server, and the edits still failed. That session's output:

```
All three edits were blocked again with the Kaneo MCP server disabled, with the same "no verdict" error. So Kaneo probably isn't the cause.

This session also showed a pattern:
- Went through: the Edit to .claude/settings.json, and Edits to files in the memory directory.
- Blocked: .claude-plugin/plugin.json, tests/test_plugin_layout.py and CLAUDE.md.

I've added this result to the auto-mode memory.

The three blocked edits are unchanged from the earlier list. Switch to accept-edits mode for pass 2. Re-enable the Kaneo server too: after the edits I need it to move the task to needs-human and post the report comment.
```

Then I disabled the outline mcp server, tried again, and the edits still failed. The session output:

```
All three edits were blocked again, with both the Kaneo and Outline servers disabled. So neither MCP server is the cause. The result is in the auto-mode memory.

One clue: the .claude/settings.json edit went through in the same parallel batch where the plugin.json edit was blocked. Whatever triggers it varies by file, not by session state. I don't know why.

To finish the task:
1. Switch to accept-edits mode for the three edits (plugin.json, tests/test_plugin_layout.py, CLAUDE.md).
2. Re-enable both MCP servers.
3. Tell me to continue. I'll then commit, push, test the update command against the branch, open the PR, and update Kaneo.
```

One other bit of info: I ran the session with the command `claude --plugin-dir ~/dev/sdlc-llm` since I'm installing the plugin from another repo while testing. The plugin is what includes the kaneo and outline mcp servers. The current task I'm working on is to switch to installing the plugin from the repo in github instad of the local machine. Is it possible that installing from a local directory is causing the issue? -->

<!-- Figured out the root cause in another session. It's because I'm invoking this session with the `--plugin-dir ~/dev/sdlc-llm` flag; that means we're editing the exact plugin files we're referencing from the installed plugin, which is why it's getting blocked. The current ticket *should* fix that problem once it's finished, since we'll be installing the plugin files from the github repo.

One question before I enable accept edit mode so you can finish the last edits. The skills you created are in `./skills`, but to use them as a plugin, I thought they were supposed to be installed in `.claude/skills`. Will installing them as a plugin create the skills files under the `.claude/` directory? How is this all supposed to work? -->

<!-- > claude --plugin-dir ~/dev/sdlc-llm -->

<!-- I'm running through the manual test `Plain claude in this repo` on SDLC-38. It failed on step 2. The session did not prompt me to add the sdlc-llm marketplace. I used the `/plugin` command, and the sdlc-llm plugin shows an error: `Plugin "sdlc-llm" not cached at /Users/marshallbowles/.claude/plugins/marketplaces/sdlc-llm`. -->

---

<!-- Before starting work on the next task in this project, I want to make sure we're aligned on the manual testing strategy. My ultimate goal is to have you compete an epic on your own, and the manual tasks will be the human-run validation phase at the end.

- Manual tests are only written when you absolutely can't test the behavior automatically.
- If manual tests aren't blocking, try to plan for them to be conducted at the end of an epic.
- When adding a task and defining manual tests, include a short/simple explanation on the task (at the top of the manual test block) of what exact behavior is being tested that you can't conduct automatically, and why you can't automatically check that behavior. This allows me to review the test during the planning phase, at which point I can determine if it should be a blocking manual test that occurs before its task can be completed or if I am willing to defer it until later (i.e. end of the epic/batch).
- I know that we're planning to implement batches that aren't necessarily the same as a full epic. In this case, I still want the manual tasks at the end of the epic if possible, which would be decided before the batch execution anyway (in the planning phase).
- For the implement-task skill, I want to make sure we're accounting for blocking manual tests when choosing the batch. A batch should always run to completion without human interaction, barring an actual error. If one of the tasks in the middle of the batch includes a blocking manual test, I want you to alert me about that before beginning any of the tasks in the batch. The batch ending ticket will be automatically selected by the skill as the first task in the batch with the blocking manual test, making the batch shorter than what I requested when triggering the skill. When you prompt me about this, I can choose to continue or cancel the batch request.

Make sure the docs and existing skills fully reflect these guidelines (as well as any other docs I missed), and ensure that you're following this approach if you aren't already. Also look through the upcoming tasks in kaneo for any manual test cases that are shown as manual but could be automated. -->

---

TODO: general
- update CLAUDE.md to make sure unnecessary line breaks aren't added to generated markdown; maybe this skill https://mcpservers.org/agent-skills/prisma/markdown-no-artificial-line-wraps
- make a rewrite pass at README
- new skill: find shared code and move it to a shared library
- create separate git repo with all guideline docs for coding projects: linter rules for every language, testing strategy, document writing style guide, etc; projects can then directly reference those docs from the git repo so they don't have to be stored in sdlc-llm and copied alongside the skills
- potentially install a self-hosted instance of excalidash; only needed if I want to manually create diagrams
- (self-hosted project): fork [outline](https://github.com/outline/outline) and add password authentication; will be simpler for self-hosting and allows me to remove the dependency on pocket id
- add linter and formatter; probably [ruff](https://docs.astral.sh/ruff/) for both, unless you strongly recommend something else; update related docs: code style guide
- projects to pull ideas from:
  - [agent-skills](https://github.com/addyosmani/agent-skills) by addyosmani
  - [superpowers](https://github.com/obra/superpowers) by obra
  - [skills](https://github.com/mattpocock/skills) by mattpocock
  - [pstack](https://github.com/cursor/plugins/tree/main/pstack) by poteto
  - create a new skill: review these repos (and any others added to the list); have they introduced any new ideas since the last check; if so, are those changes useful to include in this repo; user periodically triggers this skill manually
- Consider integrating Jev into the workflow where it makes sense
- Remove the local mermaid rendering step. It's overkill.
- Investigate switching to excalidraw for diagrams.
- Add the telegram chat id to the .env file. It isn't a secret, but it's a good place to keep track of it.
- In addition to the critic, investigate existing hostile reviewers and recommended best practices. Find ones for architecture, code, and documentation.
- Outline doesn't automatically sort it's tree entries at any given level. Update the review-docs skill to check the tree for unsorted entries and sort them ascending.
- Create a new user account in kaneo for the LLM with the same permissions I have. Replace the existing API key with one from this account. Might need to set `ALLOW_REGISTRATION=true` in the compose.yml file and run `docker compose up -d --force-recreate kaneo`. Double check all of this so it doesn't kill my existing instance. If that works, try registering via the UI as the bot; credentials already in 1password.
- Adding new tools to the workflow: Investigate [mypy](https://mypy-lang.org/) for python static code analysis. Also add categories for security analysis (e.g. [bandit](https://bandit.readthedocs.io/en/latest/) in python), dead code checks (e.g. [vulture](https://github.com/jendrikseipp/vulture)), complexity analysis (e.g. [radon](https://radon.readthedocs.io/en/latest/index.html) and/or [mccabe](https://github.com/PyCQA/mccabe)). This will require rethinking how we list the tools. For python, these features are split between multiple single-responsibility tools. In other languages, the features may split in different ways across different tools, or a single tool may exist that implements all of these features. So we need a smart way to define it in the config and its usage in skills/hooks so that it can be used to support the language being used in the repository. We should also support the case where a single repository contains code written in multiple languages.
- Investigate how to add [graphify](https://github.com/Graphify-Labs/graphify) and similar tools to the workflow. The goal is to create a knowledge graph of the code to support the agent in understanding how the system works. At what point in the development/progress of a project's development should this tool or similar tools be added?
- Test strategy update: the validation task (last one in an epic); in addition to the deferred manual tests from individual tasks, this task should include manual user acceptance tests. I will use these to manually verify the new features implemented in the epic. Keep them relatively simply, focusing on happy path testing.
