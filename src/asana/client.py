from typing import List, Iterator, Dict, Optional
import asana  # type: ignore
from src.config import ASANA_API_KEY


def validate_object_id(object_id: str, message: str):
    """
        Validates that object_id seems to be a valid Asana object-id, raising a ValueError with the message 'message'
        if this is not the case
    """
    if (
        object_id is None
        or not object_id
        or not isinstance(object_id, str)
        or not object_id.strip()
    ):
        raise ValueError(message)


class AsanaClient(object):
    """
        Encapsulates the Asana client interface, as exposed to the world. There is a single (singleton) instance of
        the Asana client in the process, which is lazily created upon the first request. This pattern supports test code
        that does not require Asana.
    """

    # the singleton instance of AsanaClient
    _singleton = None

    def __init__(self):
        client = asana.Client.access_token(ASANA_API_KEY)
        client.headers = {"Asana-Enable": "string_ids"}
        self.asana_api_client = client

    # getter for the singleton
    @classmethod
    def singleton(cls):
        """
        Getter for the AsanaClient singleton
        """
        if cls._singleton is None:
            cls._singleton = AsanaClient()
        return cls._singleton

    def create_task(self, project_id: str, due_date_str: str = None) -> str:
        """
            Creates an Asana task in the specified project, returning the task_id
        """
        validate_object_id(project_id, "AsanaClient.create_task requires a project_id")

        create_task_params = {"projects": project_id}
        if due_date_str:
            create_task_params["due_on"] = due_date_str
        response = self.asana_api_client.tasks.create(create_task_params)
        return response["gid"]

    def update_task(self, task_id: str, fields: dict):
        """
            Updates the specified Asana task, setting the provided fields
        """
        validate_object_id(task_id, "AsanaClient.update_task requires a task_id")
        if fields is None or not fields:
            raise ValueError(
                "AsanaClient.update_task requires a collection of fields to upsert"
            )
        self.asana_api_client.tasks.update(task_id, fields)

    def add_followers(self, task_id: str, followers: List[str]):
        """
            Adds followers to the specified task. The followers should be Asana domain-user ids.
        """
        validate_object_id(task_id, "AsanaClient.add_followers requires a task_id")
        if followers is None or not followers:
            raise ValueError(
                "AsanaClient.add_followers requires a list of followers to add"
            )
        for follower in followers:
            validate_object_id(follower, "Followers should be Asana domain-user-ids")
        self.asana_api_client.tasks.add_followers(task_id, {"followers": followers})

    def add_comment(self, task_id: str, comment_body: str) -> str:
        """
            Adds a html-formatted comment to the specified task. The comment will be posted on behalf of the SGTM
            user. Returns the object id of the comment
        """
        validate_object_id(task_id, "AsanaClient.add_comment requires a task_id")
        if comment_body is None or not comment_body:
            raise ValueError("AsanaClient.add_comment requires a comment body")
        response = self.asana_api_client.tasks.add_comment(
            task_id, {"html_text": comment_body}
        )
        return response["gid"]

    def update_comment(self, comment_id: str, comment_body: str) -> None:
        validate_object_id(
            comment_id, "AsanaClient.update_comment requires a comment_id"
        )
        if not comment_body:
            raise ValueError("AsanaClient.update_comment requires a comment body")
        self.asana_api_client.stories.update(comment_id, {"html_text": comment_body})

    def delete_comment(self, comment_id: str) -> None:
        validate_object_id(
            comment_id, "AsanaClient.update_comment requires a comment_id"
        )
        self.asana_api_client.stories.delete(comment_id)

    def get_project_custom_fields(self, project_id: str) -> Iterator[Dict]:
        return self.asana_api_client.custom_field_settings.find_by_project(project_id)

    def find_all_tasks_for_project(
        self, project_id: str, opt_fields: Optional[List[str]]
    ) -> Iterator[Dict]:
        return self.asana_api_client.tasks.find_all(
            project=project_id, completed_since="now", opt_fields=opt_fields
        )


def create_task(project_id: str, due_date_str: str = None) -> str:
    """
        Creates an Asana task in the specified project, returning the task_id
    """
    return AsanaClient.singleton().create_task(project_id, due_date_str=due_date_str)


def update_task(task_id: str, fields: dict):
    """
        Updates the specified Asana task, setting the provided fields
    """
    return AsanaClient.singleton().update_task(task_id, fields)


def add_followers(task_id: str, followers: List[str]):
    """
        Adds followers to the specified task. The followers should be Asana domain-user ids.
    """
    return AsanaClient.singleton().add_followers(task_id, followers)


def add_comment(task_id: str, comment_body: str) -> str:
    """
        Adds a html-formatted comment to the specified task. The comment will be posted on behalf of the SGTM
        user. Returns the object id of the comment
    """
    return AsanaClient.singleton().add_comment(task_id, comment_body)


def get_project_custom_fields(project_id: str) -> Iterator[Dict]:
    """
        Retrieve's the custom fields in the specified project.
    """
    return AsanaClient.singleton().get_project_custom_fields(project_id)


def update_comment(comment_id: str, comment_body: str):
    AsanaClient.singleton().update_comment(comment_id, comment_body)


def delete_comment(comment_id: str):
    AsanaClient.singleton().delete_comment(comment_id)


def find_all_tasks_for_project(
    self, project_id: str, opt_fields: Optional[List[str]] = None
) -> Iterator[Dict]:
    AsanaClient.singleton().find_all_tasks_for_project(project_id, opt_fields)
