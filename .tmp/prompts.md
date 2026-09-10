# prompts

<!-- Use @project-management-plan.md to create a PRD in @tasks/specs/. In addition to the tasks described in the document, add a way to track epics. I'm basing this off of my experience using Jira, a workflow I'm comfortable with. -->

<!-- Create stories using the PRD you created. I think they should all be grouped under an MVP epic unless you think otherwise. -->

<!-- We're dogfooding in this repository to define the workflow, so I don't have a clear understanding of it in my head yet. Can you describe your understanding of the workflow to me? What steps should you and I take now to start working on the tasks? Describe everything from start to finish, and note gaps (e.g. no automatic git commands because I'm doing those manually right now, but I may delgate them to you/the workflow later). -->

Make these updates to the project:

- Automatically perform git commands using the `gh` cli, which I just installed: pull latest from main, rebasing on main before creating a PR, create a new branch for a task, push changes to remote, create a PR. Recommend other git actions to include if you have any.
- Add/update existing tasks as necessary to account for automating git commands with `gh`.
- Note that I will manually review all PRs on github and squash & merge them myself.
- Make the changes you outlined in `Changes to make before TASK-001 starts` of @.tmp/workflow-plan.md.
- Update @CLAUDE.md.
- Add a note to yourself to ignore @.tmp/prompts.md. It's just a spot for me to write my prompts for you, so it's redundant from your perspective.

Additional notes/questions:
- I have already merged the previous PR into main as described in `Step 0 — prerequisite (you, manually)` in @.tmp/workflow-plan.md, and I created a new branch `feat/initial-workflow`. This new branch is for the last set of refinements I want to make to the initial plan before we tackle TASK-001. You can use `gh` now to push your changes and create a PR for this branch when you're ready.
- It looks like your plan only relies on pytest as a dependency at the moment and everything else is in stdlib. Should we use conda/uv for the sync script or is that overkill?
- I removed `tmp/` from .gitignore. I've decided to which to the `.tmp/` pattern and keep these files checked into the repo, knowing that I may manually remove them in the future.