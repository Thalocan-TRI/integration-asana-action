# Integration Asana Action

## Description
**Integration Asana Action** is a GitHub Action that creates and updates tasks in Asana. This action helps automate task management by integrating GitHub workflows with Asana projects.

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

## Usage

To use this action, add the following step to your GitHub Actions workflow:

```yaml
name: Example Workflow - Create and Update Asana task

on:
  issues:
    types: [opened, closed]

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
                ASANA_WORKSPACE_ID: '1205703551806704'
                ASANA_PROJECT_ID: '1205880144741880'
                ASANA_SECTION_TO_DO: '1208647756867715'
                ASANA_SECTION_DOING: '1206013198716545'
                ASANA_CUSTOM_FIELD_STATUS_ID: '1205880144741940'
                ASANA_CUSTOM_FIELD_STATUS_IN_PROGRESS_ID: '1205880144741943'
                ASANA_CUSTOM_FIELD_STATUS_RESOLVED_ID:  '1205880144741941'
                ASANA_CUSTOM_FIELD_STATUS_ISSUE_ID: '1205880144741942'

              env:
                ASANA_PAT: ${{ secrets.ASANA_PAT }}
                GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

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

