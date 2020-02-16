from typing import List
import asana
from src.config import ASANA_API_KEY


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

    def create_task(self, project_id: str) -> str:
        """
            Creates an Asana task in the specified project, returning the task_id
        """
        if project_id is None:
            raise ValueError("AsanaClient.create_task requires a project_id")
        response = self.asana_api_client.tasks.create({"projects": project_id})
        return response["gid"]
    
    def update_task(self, task_id: str, fields: dict):
        """
            Updates the specified Asana task, setting the provided fields
        """
        if task_id is None:
            raise ValueError("AsanaClient.update_task requires a task_id")
        if fields is None or not fields:
            raise ValueError("AsanaClient.update_task requires a collection of fields to upsert")
        self.asana_api_client.tasks.update(task_id, fields)
    
    def add_followers(self, task_id: str, followers: List[str]):
        """
            Adds followers to the specified task. The followers should be Asana domain-user ids.
        """
        if task_id is None:
            raise ValueError("AsanaClient.add_followers requires a task_id")
        if followers is None or not followers:
            raise ValueError("AsanaClient.add_followers requires a list of followers to add")
        self.asana_api_client.tasks.add_followers(task_id, {"followers": followers})
    
    def add_comment(self, task_id: str, comment_body: str) -> str:
        """
            Adds a html-formatted comment to the specified task. The comment will be posted on behalf of the SGTM
            user. Returns the object id of the comment
        """
        if task_id is None:
            raise ValueError("AsanaClient.add_comment requires a task_id")
        if comment_body is None or not comment_body:
            raise ValueError("AsanaClient.add_comment requires a comment body")
        response = self.asana_api_client.tasks.add_comment(task_id, {"html_text": comment_body})
        return response["gid"]


def create_task(project_id: str) -> str:
    """
        Creates an Asana task in the specified project, returning the task_id
    """
    return AsanaClient.singleton().create_task(project_id)


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
