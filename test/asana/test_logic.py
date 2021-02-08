from unittest.mock import patch, Mock
from test.impl.builders import builder, build
from test.impl.base_test_case_class import BaseClass
from src.asana import logic as asana_logic


@patch("os.getenv", return_value="true")
class TestShouldAutocompleteTasksOnMerge(BaseClass):
    def test_false_if_feature_not_enabled(self, get_env_mock):
        get_env_mock.return_value = None
        pull_request = build(
            builder.pull_request()
            .merged(True)
            .label(
                builder.label().name(asana_logic.AutocompleteLabel.COMPLETE_ON_MERGE)
            )
        )
        self.assertFalse(asana_logic.should_autocomplete_tasks_on_merge(pull_request))

    def test_false_if_pull_request_is_not_merged(self, get_env_mock):
        pull_request = build(
            builder.pull_request()
            .merged(False)
            .label(
                builder.label().name(asana_logic.AutocompleteLabel.COMPLETE_ON_MERGE)
            )
        )
        self.assertFalse(asana_logic.should_autocomplete_tasks_on_merge(pull_request))

    def test_false_if_pull_request_does_not_have_autocomplete_label(self, get_env_mock):
        pull_request = build(builder.pull_request().merged(True))
        self.assertFalse(asana_logic.should_autocomplete_tasks_on_merge(pull_request))

    def test_true_if_should_autocomplete(self, get_env_mock):
        pull_request = build(
            builder.pull_request()
            .merged(True)
            .label(
                builder.label().name(asana_logic.AutocompleteLabel.COMPLETE_ON_MERGE)
            )
        )
        self.assertTrue(asana_logic.should_autocomplete_tasks_on_merge(pull_request))


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
