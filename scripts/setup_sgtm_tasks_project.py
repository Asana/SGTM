#!/usr/bin/env python3

import argparse
from dataclasses import dataclass
from typing import List

import asana  # type: ignore
import sys


@dataclass
class EnumOption:
    name: str
    color: str


@dataclass
class CustomField:
    name: str

    def resource_subtype(self):
        raise NotImplementedError(
            "resource_subtype not implemented in " + self.__class__.__name__
        )

    def additional_custom_field_data(self):
        return {}


@dataclass
class EnumCustomField(CustomField):
    enum_options: List[EnumOption]

    def resource_subtype(self):
        return "enum"

    def additional_custom_field_data(self):
        enum_options = [
            {
                "name": enum_option.name,
                "color": enum_option.color,
                "enabled": True,
            }
            for enum_option in self.enum_options
        ]
        return {"enum_options": enum_options}


@dataclass
class PeopleCustomField(CustomField):
    def resource_subtype(self):
        return "people"


# If adding a new option, ensure that the color you're selecting is part of this list of colors:
# "none" | "red" | "orange" | "yellow-orange" | "yellow" | "yellow-green" | "green" | "blue-green" |
# "aqua" | "blue" | "indigo" | "purple" | "magenta" | "hot-pink" | "pink" | "cool-gray"
# TODO: Replace this list with a link to public documentation once available
CUSTOM_FIELDS = [
    EnumCustomField(
        name="PR Status",
        enum_options=[
            EnumOption(name="Open", color="green"),
            EnumOption(name="Draft", color="cool-gray"),
            EnumOption(name="Merged", color="purple"),
            EnumOption(name="Closed", color="red"),
        ],
    ),
    EnumCustomField(
        name="Build",
        enum_options=[
            EnumOption(name="Success", color="green"),
            EnumOption(name="Failure", color="red"),
        ],
    ),
    PeopleCustomField(name="Author (SGTM)"),
    EnumCustomField(
        name="Review Status",
        enum_options=[
            EnumOption(name="Needs Review", color="yellow"),
            EnumOption(name="Changes Requested", color="red"),
            EnumOption(name="Approved", color="green"),
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

    subparsers = parser.add_subparsers(title="Sub-commands")

    parser_create = subparsers.add_parser(
        "create",
        help="""Use this option if you want to set up a new project from scratch""",
    )

    parser_create.add_argument(
        "-n",
        "--new_project_name",
        help="""The Asana Project name""",
        type=str,
        required=True,
    )

    parser_create.add_argument(
        "-t",
        "--team_id",
        help="""This is the global ID of the team that you want to share the project with. You can find this in the URL
        by navigating to the desired team in Asana
		""",
        type=str,
        required=True,
    )

    parser_create.set_defaults(func=setup_new_project)

    parser_update = subparsers.add_parser(
        "update",
        help="""Use this option if you have an existing Asana Project that you want to use to sync
        SGTM tasks""",
    )

    parser_update.add_argument(
        "-e",
        "--existing_project_id",
        help="""The global ID of an existing Asana Project. You can find this in the URL by navigating to the project in Asana""",
        type=str,
        required=True,
    )

    parser_update.set_defaults(func=setup_existing_project)

    return parser.parse_args()


def setup_new_project(args) -> None:
    client = AsanaClient(args.personal_access_token)
    project_id = client.create_project(args.new_project_name, args.team_id)
    client.setup_custom_fields(project_id)
    print(
        f"The ID of your newly created project '{args.new_project_name}' is"
        f" {project_id}"
    )


def setup_existing_project(args) -> None:
    client = AsanaClient(args.personal_access_token)
    client.setup_custom_fields(args.existing_project_id)
    client.add_user_to_project(args.existing_project_id)


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
        if len(pat_user["workspaces"]) == 1:
            return pat_user["workspaces"][0]["gid"]
        else:
            workspaces = pat_user["workspaces"]
            workspace_list = [
                (workspace["name"], workspace["gid"]) for workspace in workspaces
            ]

            for i, (workspace_name, workspace_id) in enumerate(workspace_list):
                print(f"{i + 1}. {workspace_name}, {workspace_id}")

            index = int(
                input(
                    "Please select the workspace you want to create the SGTM"
                    " project/the SGTM project exists in. - Enter a number between 1"
                    f" and {len(workspace_list)}: "
                )
            )

            try:
                workspace = workspace_list[index - 1]
                return workspace[1]
            except IndexError as e:
                print("Invalid selection - please try again.")
                sys.exit(0)

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
                "resource_subtype": custom_field.resource_subtype(),
                "is_global_to_workspace": False,
                **custom_field.additional_custom_field_data(),
            }

            try:
                self.client.projects.add_custom_field_setting(
                    project_id,
                    {"custom_field": custom_field_data},
                )
            except asana.error.PremiumOnlyError:
                print(
                    "Custom Fields are not available for free users or guests. If"
                    " you're using Asana Basic, you can continue setting up SGTM"
                    " without setting up the custom fields. If you're on Asana Premium,"
                    " please verify that the PAT you passed in does not correspond to a"
                    " guest and try again."
                )
                return

    def add_user_to_project(self, project_id: str) -> None:
        """
        Add the PAT user as a follower to the given project
        """
        user_id = self._get_user_id()
        self.client.projects.add_followers(project_id, {"followers": user_id})


if __name__ == "__main__":
    args = parse_args()
    args.func(args)
