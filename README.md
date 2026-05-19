# Integration Asana Action

## Description
**Integration Asana Action** is a GitHub Action that creates and updates tasks in Asana. This action helps automate task management by integrating GitHub workflows with Asana projects.

## How It Works

The integration is **event-driven** — it reacts to specific GitHub events and does not perform continuous synchronization.

### Event: `opened`

When an issue or pull request is opened, the action checks whether the title starts with the prefix `Asana:`.

- **If the prefix is present**, a task is created in Asana inside the configured "To Do" section. The issue/PR body is used as the task description. After creation, the action automatically posts a comment on the GitHub issue/PR containing the generated Asana task ID (e.g., `Asana Task ID: 1234567890`). This comment is essential for the closing step to work.
- **If the prefix is absent**, nothing happens.

### Event: `edited`

When an issue or pull request title is edited and the new title starts with `Asana:`, the action creates the Asana task retroactively — as if the prefix had been present at creation. To avoid duplicates, the action first checks whether the issue/PR already has an `Asana Task ID:` comment and skips creation if one is found.

This allows teams to decide mid-lifecycle that an existing issue/PR should be tracked in Asana, without needing to close and reopen it.

### Event: `closed`

When an issue or pull request is closed, the action scans its comments looking for a comment that contains `Asana Task ID:`. If found, it moves the corresponding Asana task to the configured "Done" section.

### Manual trigger: `workflow_dispatch`

For issues or pull requests that were never sent to Asana and whose titles cannot be changed, the action supports a manual `workflow_dispatch` trigger. Provide the issue or PR number via the `ISSUE_NUMBER` input and the action will fetch the item from the GitHub API, create the Asana task, and post the tracking comment — exactly as if it had been opened with the `Asana:` prefix. Duplicate protection applies here as well.

### Behavior summary

| Trigger | Condition | Action taken in Asana |
|---|---|---|
| Issue/PR `opened` | Title starts with `Asana:` | Creates task in "To Do" and comments the task ID on GitHub |
| Issue/PR `opened` | Title does NOT start with `Asana:` | Nothing |
| Issue/PR `edited` | New title starts with `Asana:` and not yet synced | Creates task in "To Do" and comments the task ID on GitHub |
| Issue/PR `edited` | Already synced or no `Asana:` prefix | Nothing |
| Issue/PR `closed` | Comment with `Asana Task ID:` found | Moves task to the "Done" section |
| Issue/PR `closed` | No such comment found | Nothing |
| `workflow_dispatch` | `ISSUE_NUMBER` provided and not yet synced | Fetches issue/PR, creates task in "To Do", and comments the task ID |

### Known limitations

- **No continuous sync**: changes made to the issue/PR title or body after the initial sync are not reflected in Asana.
- **Partially implemented inputs**: the inputs `ASANA_SECTION_DOING`, `ASANA_CUSTOM_FIELD_STATUS_IN_PROGRESS_ID`, `ASANA_CUSTOM_FIELD_STATUS_ISSUE_ID`, and `ASANA_CUSTOM_FIELD_STATUS_RESOLVED_ID` are declared in `action.yml` but not yet used in the current implementation.

## Inputs

| Name | Description | Required |
|------|-------------|----------|
| `ASANA_PROJECT_ID` | Asana Project ID | ✅ Yes |
| `ASANA_SECTION_TO_DO` | Asana Section To Do ID | ✅ Yes |
| `ASANA_SECTION_DOING` | Asana Section Doing ID | ✅ Yes |
| `ASANA_WORKSPACE_ID` | Asana Workspace ID | ✅ Yes |
| `ASANA_CUSTOM_FIELD_STATUS_ID` | Asana Custom Field Status ID | ✅ Yes |
| `ASANA_CUSTOM_FIELD_STATUS_IN_PROGRESS_ID` | Asana Custom Field Status In Progress ID | ✅ Yes |
| `ASANA_CUSTOM_FIELD_STATUS_RESOLVED_ID` | Asana Custom Field Status Resolved ID | ✅ Yes |
| `ASANA_CUSTOM_FIELD_STATUS_ISSUE_ID` | Asana Custom Field Status Issue ID | ✅ Yes |
| `ISSUE_NUMBER` | GitHub Issue or PR number to sync retroactively (used with `workflow_dispatch`) | ❌ No |

## Environment Variables

| Name | Description | Required |
|------|-------------|----------|
| `ASANA_PAT` | Personal Access Token for Asana API authentication | ✅ Yes |
| `GITHUB_TOKEN` | GitHub Token for GitHub Repo API authentication | ✅ Yes |

## Usage

### Automatic sync (opened, edited, closed)

Add `edited` alongside `opened` and `closed` to also trigger task creation when a title is updated with the `Asana:` prefix:

```yaml
name: Sync Asana task

on:
  issues:
    types: [opened, edited, closed]

jobs:
    create_update_asana_task:
        runs-on: ubuntu-latest
        permissions:
          issues: write
          pull-requests: write
          contents: read
        steps:
            - uses: actions/checkout@v3
            - uses: Thalocan-TRI/integration-asana-action@v1
              with:
                ASANA_WORKSPACE_ID: 'XXXXXXXXXXXXXXXX'
                ASANA_PROJECT_ID: 'XXXXXXXXXXXXXXXX'
                ASANA_SECTION_TO_DO: 'XXXXXXXXXXXXXXXX'
                ASANA_SECTION_DOING: 'XXXXXXXXXXXXXXXX'
                ASANA_CUSTOM_FIELD_STATUS_ID: 'XXXXXXXXXXXXXXXX'
                ASANA_CUSTOM_FIELD_STATUS_IN_PROGRESS_ID: 'XXXXXXXXXXXXXXXX'
                ASANA_CUSTOM_FIELD_STATUS_RESOLVED_ID:  'XXXXXXXXXXXXXXXX'
                ASANA_CUSTOM_FIELD_STATUS_ISSUE_ID: 'XXXXXXXXXXXXXXXX'
              env:
                ASANA_PAT: ${{ secrets.ASANA_PAT }}
                GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### Manual retroactive sync (workflow_dispatch)

To send an existing issue or PR that was never synced to Asana, add a `workflow_dispatch` trigger with an `issue_number` input:

```yaml
name: Sync Asana task

on:
  issues:
    types: [opened, edited, closed]
  workflow_dispatch:
    inputs:
      issue_number:
        description: 'Issue or PR number to sync retroactively to Asana'
        required: true

jobs:
    create_update_asana_task:
        runs-on: ubuntu-latest
        permissions:
          issues: write
          pull-requests: write
          contents: read
        steps:
            - uses: actions/checkout@v3
            - uses: Thalocan-TRI/integration-asana-action@v1
              with:
                ASANA_WORKSPACE_ID: 'XXXXXXXXXXXXXXXX'
                ASANA_PROJECT_ID: 'XXXXXXXXXXXXXXXX'
                ASANA_SECTION_TO_DO: 'XXXXXXXXXXXXXXXX'
                ASANA_SECTION_DOING: 'XXXXXXXXXXXXXXXX'
                ASANA_CUSTOM_FIELD_STATUS_ID: 'XXXXXXXXXXXXXXXX'
                ASANA_CUSTOM_FIELD_STATUS_IN_PROGRESS_ID: 'XXXXXXXXXXXXXXXX'
                ASANA_CUSTOM_FIELD_STATUS_RESOLVED_ID:  'XXXXXXXXXXXXXXXX'
                ASANA_CUSTOM_FIELD_STATUS_ISSUE_ID: 'XXXXXXXXXXXXXXXX'
                ISSUE_NUMBER: ${{ github.event.inputs.issue_number }}
              env:
                ASANA_PAT: ${{ secrets.ASANA_PAT }}
                GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

With this configuration, you can go to **Actions → Sync Asana task → Run workflow**, enter the issue/PR number, and the action will create the Asana task and post the tracking comment automatically.

## Generating Asana Inputs
In the utils file, you can generate all necessary Asana inputs to populate the workflow variables. This script requires the user to provide ASANA_PAT and will automatically retrieve all required information.

## Secrets
It is recommended to store sensitive data such as Asana PAT as GitHub Secrets.

## License
...

## Contributions
Contributions are welcome! Feel free to open an issue or submit a pull request.

## Support
For any issues or feature requests, please open an [issue](https://github.com/Thalocan-TRI/integration-asana-action/issues).
