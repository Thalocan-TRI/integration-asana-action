import asana


class AsanaClient:
    def __init__(self, access_token: str):
        configuration = asana.Configuration()
        configuration.access_token = access_token
        self._api_client = asana.ApiClient(configuration)

    def create_task(
        self,
        section_id: str,
        project_id: str,
        name: str,
        notes: str | None = None,
    ) -> dict:
        api_task_client = asana.TasksApi(self._api_client)

        body = {"data": {"name": name, "projects": [project_id]}}

        if notes is not None:
            body["data"]["notes"] = notes

        task = api_task_client.create_task(body, {})
        task_id = task["gid"]

        api_section_client = asana.SectionsApi(self._api_client)
        api_section_client.add_task_for_section(
            section_id, {"body": {"data": {"task": task_id}}}
        )
        return task

    def move_task_to_section(self, task_id: str, section_id: str) -> None:
        api_section_client = asana.SectionsApi(self._api_client)
        api_section_client.add_task_for_section(
            section_id, {"body": {"data": {"task": task_id}}}
        )
