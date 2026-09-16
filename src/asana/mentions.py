"""Small Asana rich-text helpers shared by task descriptions and comments."""
from html import escape
from typing import Optional

import src.aws.s3_client as s3_client


def task_url_from_task_id(task_id: str) -> str:
    if not task_id:
        raise ValueError("task_url_from_task_id requires a task_id")
    return f"https://app.asana.com/0/0/{task_id}"


def asana_user_link_for_github_login(github_handle: str) -> Optional[str]:
    """An Asana @-mention (`<a data-asana-gid=...>`) for the mapped user, or None."""
    user_id = s3_client.get_asana_domain_user_id_from_github_handle(github_handle)
    if user_id is None:
        return None
    return (
        f'<A data-asana-gid="{escape(user_id)}"'
        f' href="https://github.com/{escape(github_handle)}">{escape(github_handle)}</A>'
    )


def asana_mention_for_github_login(github_handle: str) -> str:
    """
    An Asana @-mention of the user mapped to this GitHub login, which notifies them,
    or the bare login when SGTM does not know their Asana account.
    """
    return asana_user_link_for_github_login(github_handle) or escape(github_handle)


def asana_task_link(task_id: str, text: str) -> str:
    """An Asana-rendered link to a task, shown with the given text."""
    return (
        f'<A data-asana-gid="{escape(task_id)}"'
        f' href="{task_url_from_task_id(task_id)}">{escape(text)}</A>'
    )
