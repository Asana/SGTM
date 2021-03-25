#!/usr/bin/env python3

import argparse
from dataclasses import dataclass

import asana
import sys


@dataclass
class EnumOption:
    name: str
    color: str


@dataclass
class CustomField:
    name: str
    enum_options: [EnumOption]


CUSTOM_FIELDS = [
    CustomField(
        name="PR Status",
        enum_options=[
            EnumOption(name="Open", color="green"),
            EnumOption(name="Merged", color="purple"),
            EnumOption(name="Closed", color="red"),
        ],
    ),
    CustomField(
        name="Build",
        enum_options=[
            EnumOption(name="Success", color="green"),
            EnumOption(name="Failure", color="red"),
        ],
    ),
]


def parse_args():
    parser = argparse.ArgumentParser(
        description="""A helper script to set up an SGTM tasks Asana project with the suggested custom fields
		"""
    )

    parser.add_argument(
        "-p",
        "--personal_access_token",
        help="""The Asana Personal Access Token that will be used to set up the Asana project. If you do not already have one,
		follow the instructions at https://developers.asana.com/docs/personal-access-token
		""",
        type=str,
        required=True,
    )

    parser.add_argument(
        "-n",
        "--new_project_name",
        help="""The Asana Project name - use this if you want to set up a project from scratch
		""",
        type=str,
        required=False,
    )

    parser.add_argument(
        "-t",
        "--team_id",
        help="""Only required if you are creating a new project - this is the global ID of the team that
		you want to share the project with
		""",
        type=str,
        required=False,
    )

    parser.add_argument(
        "-e",
        "--existing_project_id",
        help="""The global ID of an existing Asana Project - use this if you have an existing Asana project that you want to use 
		to sync SGTM tasks
		""",
        type=str,
        required=False,
    )

    return parser.parse_args()


def setup_new_project(project_name: str, team_id: str, pat: str) -> None:
    client = AsanaClient(pat)
    project_id = client.create_project(project_name, team_id)
    client.setup_custom_fields(project_id)


def setup_existing_project(project_id: str, pat: str) -> None:
    client = AsanaClient(pat)
    client.setup_custom_fields(project_id)
    client.add_user_to_project(project_id)


class AsanaClient(object):
    def __init__(self, personal_access_token: str):
        self.client = asana.Client.access_token(personal_access_token)
        self.client.headers = {"Asana-Enable": "string_ids"}
        self.workspace_id = self._get_workspace_id()

    def _get_workspace_id(self) -> str:
        """
        Get the workspace ID that the user who created the PAT is a part of
        """
        pat_user = self.client.users.me()
        return pat_user["workspaces"][0]["gid"]

    def _get_user_id(self) -> str:
        """
        Get the user ID for the user that created the PAT
        """
        pat_user = self.client.users.me()
        return pat_user["gid"]

    def create_project(self, project_name: str, team_id: str) -> str:
        """
        Create a project with the given name, shared with the provided team in the workspace
        """
        create_project_data = {
            "name": project_name,
            "public": True,
            "team": team_id,
        }
        response = self.client.projects.create_project(create_project_data)
        return response["gid"]

    def setup_custom_fields(self, project_id: str) -> None:
        """
        Create the custom fields that SGTM requires and add them to the given project
        """
        for custom_field in CUSTOM_FIELDS:
            custom_field_data = {
                "name": custom_field.name,
                "enabled": True,
                "workspace": self.workspace_id,
                "resource_subtype": "enum",
                "enum_options": [],
            }

            for enum_option in custom_field.enum_options:
                custom_field_data["enum_options"].append(
                    {
                        "name": enum_option.name,
                        "color": enum_option.color,
                        "enabled": True,
                    }
                )

            response = self.client.custom_fields.create_custom_field(custom_field_data)
            custom_field_gid = response["gid"]

            self.client.projects.add_custom_field_setting_for_project(
                project_id,
                {
                    "custom_field": custom_field_gid,
                },
            )

    def add_user_to_project(self, project_id: str) -> None:
        """
        Add the PAT user as a follower to the given project
        """
        user_id = self._get_user_id()
        self.client.projects.add_followers_for_project(
            project_id, {"followers": user_id}
        )


if __name__ == "__main__":
    args = parse_args()

    if args.new_project_name and args.existing_project_id:
        print(
            "Cannot select both an existing project and a new project, please try again"
        )
        sys.exit(0)

    if args.new_project_name:
        if not args.team_id:
            print(
                "A project needs to be associated with a team, please provide the team ID and try again"
            )
            sys.exit(0)

        setup_new_project(
            args.new_project_name, args.team_id, args.personal_access_token
        )

    if args.existing_project_id:
        setup_existing_project(args.existing_project_id, args.personal_access_token)
