from typing import List, Iterator, Dict
import asana  # type: ignore
from src.config import ASANA_API_KEY

client = asana.Client.access_token(ASANA_API_KEY)
client.headers = {"Asana-Enable": "string_ids"}


def create_task(project: str) -> str:
    response = client.tasks.create({"projects": project})
    return response["gid"]


def update_task(task_id: str, fields: dict):
    client.tasks.update(task_id, fields)


def add_followers(task_id: str, followers: List[str]):
    client.tasks.add_followers(task_id, {"followers": followers})


def add_comment(task_id: str, comment_body: str) -> str:
    response = client.tasks.add_comment(task_id, {"html_text": comment_body})
    return response["gid"]


def get_project_custom_fields(project_id: str) -> Iterator[Dict]:
    return client.custom_field_settings.find_by_project(project_id)
