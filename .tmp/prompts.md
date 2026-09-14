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

Use the add-task skill to create a new refactoring task to clean up docs to remove redundant/deprecated information:
- @./tasks/guidelines.md and @.claude/skills/init-project/templates/guidelines.md: some of these instructions are redundant now that they have been implemented in @.tasks/bin/sync.py.
- @CLAUDE.md
- Determine if anything in @.tmp/workflow-plan.md and @.tmp/project-management-plan.md is important information that needs to be kept. If so, find a better location for these details outside of .tmp.
- Add a `Example Usage` section to @README.md with an example step-by-step workflow that uses the skills defined in this repo.