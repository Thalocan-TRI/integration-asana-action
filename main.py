import os
import sys

from clients.asana_client import AsanaClient
from clients.github_client import GitHubClient
from services.sync_service import SyncService

_REQUIRED_ENV_VARS = [
    "ASANA_PAT",
    "GITHUB_TOKEN",
    "INPUT_ASANA_PROJECT_ID",
    "INPUT_ASANA_SECTION_TO_DO",
    "INPUT_ASANA_SECTION_DONE",
    "GITHUB_EVENT_NAME",
]


def _validate_env() -> None:
    missing = [var for var in _REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        print(f"Missing required environment variables: {', '.join(missing)}")
        sys.exit(1)


def run():
    _validate_env()
    asana_client = AsanaClient(os.getenv("ASANA_PAT"))
    github_client = GitHubClient(os.getenv("GITHUB_TOKEN"))
    service = SyncService(
        asana_client=asana_client,
        github_client=github_client,
        project_id=os.getenv("INPUT_ASANA_PROJECT_ID"),
        section_to_do=os.getenv("INPUT_ASANA_SECTION_TO_DO"),
        section_done=os.getenv("INPUT_ASANA_SECTION_DONE"),
    )
    service.run(
        event_name=os.getenv("GITHUB_EVENT_NAME"),
        event_path=os.getenv("GITHUB_EVENT_PATH", "/github/workflow/event.json"),
        github_repository=os.getenv("GITHUB_REPOSITORY"),
        issue_number=os.getenv("INPUT_ISSUE_NUMBER"),
    )


if __name__ == "__main__":
    run()
