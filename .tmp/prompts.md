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

/plan-feature Create a new epic to move behavior to hooks. I want you to identify what behaviors from the existing skills make sense to be turned into hooks. The goal is to ensure that the hook behaviors always occur and aren't left to probabilistic decisions. In addition to the existing skills, are there any new behaviors you would recommend adding as hooks?

My current ideas for hooks:
- A script that checks for references to SPEC-NNN and TASK-NNN in the artifacts that will be copied to other repositories using the init-project skill (see TASK-027). Causes the agent to clean up these references before a PR can be opened for a task. This hook would only exist in the current repository and would be excluded from the list of artifacts copied by the init-project skill.
- The test_command is run before creating a PR and must pass.
- The lint_command is run before creating a PR and must pass.
- The code formatting tool is run before creating a PR.
- Ensure that re-running init-project to upgrade a project doesn't modify the excluded files.

---

/plan-feature Create a new epic to refactor the `implement-task` skill to be more automated:
- user provides an epic, a task range, task list, or a stopping task and LLM works through all tasks autonomously
  - epic provided: LLM attempts to implement all tasks in the epic
  - task range: implement all tasks from start to end in the range
  - task list: a list of individual tasks to work, which might not be in the same order as the TODO list on the board
  - stopping task: LLM starts with the first task at the top of the TODO section on the board and works all tasks in order from the TODO list until completing the stopping task
- before working, LLM must verify that the set of tasks provided by the user is valid; implement this as a script to offload the decision making from the LLM
- determine conditions when LLM should interrupt work and notify the user; these are my rough ideas, and I need suggestions/best practices from you
  - running into an issue the requires clarification from the user
  - running out of context; need strategies to avoid this
  - running into an unexpected blocker
  - using too many tokens; need strategies to keep token usage low, especially if spawning additional worker agents
- creating follow up tasks: user can choose if they want the LLM to create additional tasks automatically or if the user needs to be notified; e.g. the LLM determines that a task is too big and needs to be split up; default to allowing new task creation, but add a limiter to prevent task explosion
- switch to TDD: LLM should write test cases first, verify they fail, then implement and re-test until test cases pass

---

TODO: /add-task use higher model (e.g. Opus) as the orchestrator and spin off lower models (e.g. Sonnet) to implement the tasks; each model and its effort level is configurable; how to balance context and token usage to keep the process efficient?