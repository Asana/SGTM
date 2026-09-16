import importlib.util
import pathlib
from argparse import Namespace
from unittest.mock import MagicMock, patch

from test.impl.base_test_case_class import BaseClass

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2]
    / "scripts"
    / "setup_sgtm_tasks_project.py"
)


def load_script():
    spec = importlib.util.spec_from_file_location("setup_sgtm_tasks_project", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


script = load_script()


class TestFieldSelection(BaseClass):
    def test_plain_sgtm_tasks_project(self):
        args = Namespace(codeowner_project=False, with_codeowner_fields=False)
        names = [f.name for f in script.fields_for(args)]
        self.assertEqual(
            names,
            [
                "PR Status",
                "Build",
                "Author (SGTM)",
                "Review Status",
                "Branch Name (SGTM)",
            ],
        )
        self.assertEqual(script.extra_enum_options_for(args), {})

    def test_sgtm_tasks_project_with_codeowner_fields(self):
        args = Namespace(codeowner_project=False, with_codeowner_fields=True)
        fields = {f.name: f for f in script.fields_for(args)}
        self.assertIn("Codeowner Review (SGTM)", fields)
        self.assertIn("Codeowners Pending (SGTM)", fields)
        # A fresh "Review Status" field carries the new option from the start...
        self.assertIn(
            "Needs Codeowner Approval",
            [o.name for o in fields["Review Status"].enum_options],
        )
        # ...and the original definition is untouched.
        self.assertNotIn(
            "Needs Codeowner Approval",
            [o.name for o in script.REVIEW_STATUS_FIELD.enum_options],
        )
        extra = script.extra_enum_options_for(args)
        self.assertEqual(
            [o.name for o in extra["Review Status"]], ["Needs Codeowner Approval"]
        )

    def test_codeowner_project(self):
        args = Namespace(codeowner_project=True, with_codeowner_fields=False)
        fields = {f.name: f for f in script.fields_for(args)}
        self.assertEqual(
            sorted(fields),
            [
                "Author (SGTM)",
                "Branch Name (SGTM)",
                "Codeowner Approval (SGTM)",
                "Codeowners (SGTM)",
                "PR Status",
            ],
        )
        self.assertEqual(
            [o.name for o in fields["Codeowner Approval (SGTM)"].enum_options],
            [
                "Needed",
                "Approved",
                "Approval Stale",
                "Changes Requested",
                "No Longer Required",
                "Merged with Bypass",
            ],
        )

    def test_enum_option_colors_are_valid(self):
        valid = {
            "none", "red", "orange", "yellow-orange", "yellow", "yellow-green",
            "green", "blue-green", "aqua", "blue", "indigo", "purple", "magenta",
            "hot-pink", "pink", "cool-gray",
        }  # fmt: skip
        for field in (
            script.CUSTOM_FIELDS
            + script.CODEOWNER_PR_TASK_FIELDS
            + script.CODEOWNER_PROJECT_FIELDS
        ):
            for option in getattr(field, "enum_options", []):
                self.assertIn(option.color, valid, f"{field.name}: {option.name}")
        self.assertIn(script.REVIEW_STATUS_CODEOWNER_OPTION.color, valid)


class TestSetupCustomFields(BaseClass):
    def client(self, existing_settings):
        with patch.object(script.asana.Client, "access_token") as access_token:
            api = MagicMock()
            api.users.me.return_value = {"gid": "me", "workspaces": [{"gid": "ws-1"}]}
            api.custom_field_settings.find_by_project.return_value = existing_settings
            access_token.return_value = api
            client = script.AsanaClient("pat")
        return client, api

    def test_skips_existing_fields_and_adds_missing_enum_options(self):
        client, api = self.client(
            [
                {
                    "custom_field": {
                        "gid": "cf-review",
                        "name": "Review Status",
                        "enum_options": [{"name": "Needs Review"}],
                    }
                },
                {"custom_field": {"gid": "cf-pr", "name": "PR Status"}},
            ]
        )
        args = Namespace(codeowner_project=False, with_codeowner_fields=True)
        client.setup_custom_fields(
            "project-1", script.fields_for(args), script.extra_enum_options_for(args)
        )

        created = [
            call.args[1]["custom_field"]["name"]
            for call in api.projects.add_custom_field_setting.call_args_list
        ]
        self.assertNotIn("Review Status", created)
        self.assertNotIn("PR Status", created)
        self.assertIn("Codeowner Review (SGTM)", created)
        self.assertIn("Codeowners Pending (SGTM)", created)
        api.custom_fields.create_enum_option.assert_called_once_with(
            "cf-review", {"name": "Needs Codeowner Approval", "color": "orange"}
        )

    def test_existing_option_is_not_added_twice(self):
        client, api = self.client(
            [
                {
                    "custom_field": {
                        "gid": "cf-review",
                        "name": "Review Status",
                        "enum_options": [{"name": "Needs Codeowner Approval"}],
                    }
                }
            ]
        )
        args = Namespace(codeowner_project=False, with_codeowner_fields=True)
        client.setup_custom_fields(
            "project-1", script.fields_for(args), script.extra_enum_options_for(args)
        )
        api.custom_fields.create_enum_option.assert_not_called()

    def test_codeowner_project_gets_its_own_fields(self):
        client, api = self.client([])
        args = Namespace(codeowner_project=True, with_codeowner_fields=False)
        client.setup_custom_fields("project-2", script.fields_for(args), {})
        created = [
            call.args[1]["custom_field"]
            for call in api.projects.add_custom_field_setting.call_args_list
        ]
        by_name = {field["name"]: field for field in created}
        self.assertIn("Codeowner Approval (SGTM)", by_name)
        self.assertEqual(by_name["Codeowners (SGTM)"]["resource_subtype"], "text")
        self.assertEqual(by_name["Author (SGTM)"]["resource_subtype"], "people")
        self.assertTrue(
            all(field["workspace"] == "ws-1" for field in created),
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
