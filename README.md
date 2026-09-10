# LLM-based SDLC toolkit

Current status: this is a new repository that was split off from another one. The file @project-management-plan.md is an analysis of the original plan and a set of recommendations on how it should be improved.

A personalized workflow for software development leveraging LLMs. It implements "kanban in markdown" method for keeping track of action items within a project repository, geared toward solo development.

- .tasks/ - stores all task-related files
- .tasks/BOARD.md - Main list of tasks grouped by their current statuses.
- .tasks/TASK-*.md - Details of each individual task.

## Task description

Each .tasks/TASK-*.md file contains the following components:

- Header: task identifier and title
- Type: Listed directly under the ticket header, it describes the category of ticket. Available values: [Feature, Bug]
- Description: Details about the purpose of the ticket and relevant context needed to implement it.
- Acceptance criteria: List of features/requirements that must be met for the ticket to be complete.
- Testing strategy: High-level steps to test and verify the functionality. Note that these test steps differ from unit tests, becaue they are intended to verify the full behavior (e.g. making actual API calls, verifying that the feature works within the context of the larger application, etc).
- Additional notes: Any additional information that provide useful context, e.g. related tickets, libraries that might be helpful, references to relevant documentation, etc.

Example:

```markdown
# TASK-011: Use API to request current weather

Type: Feature

## Descripiton
Write a Python script that uses the AccuWeather API to retrieve local weather forecast.

## Acceptance Criteria
- [ ] A REST call to the AccuWeather API is made to retrieve the weather forecast.
- [ ] A zip code is sent as part of the API request.
- [ ] Unit tests are written that mock the AccuWeather API.

## Testing strategy

Run the testing steps for the following zip codes: 98117, 29014, 44113.

1. Run the script, passing in a zip code.
2. Verify that the request returns successfully.
3. Verify that the payload contains the expected weather data.

## Additional notes
- Blocked by Task-008.
- Blocks Task-012.
- This ticket only covers implementing the script to make API requests
```