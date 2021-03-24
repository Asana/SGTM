from unittest.mock import patch, Mock
from test.impl.builders import builder, build
from test.impl.base_test_case_class import BaseClass
from src.asana import logic as asana_logic


class TestShouldAutocompleteTasksOnMerge(BaseClass):
    @patch("src.asana.logic.SGTM_FEATURE__AUTOCOMPLETE_ENABLED", False)
    def test_false_if_feature_not_enabled(self):
        pull_request = build(
            builder.pull_request()
            .merged(True)
            .label(
                builder.label().name(
                    asana_logic.AutocompleteLabel.COMPLETE_ON_MERGE.value
                )
            )
        )
        self.assertFalse(asana_logic.should_autocomplete_tasks_on_merge(pull_request))

    @patch("src.asana.logic.SGTM_FEATURE__AUTOCOMPLETE_ENABLED", True)
    def test_false_if_pull_request_is_not_merged(self):
        pull_request = build(
            builder.pull_request()
            .merged(False)
            .label(
                builder.label().name(
                    asana_logic.AutocompleteLabel.COMPLETE_ON_MERGE.value
                )
            )
        )
        self.assertFalse(asana_logic.should_autocomplete_tasks_on_merge(pull_request))

    @patch("src.asana.logic.SGTM_FEATURE__AUTOCOMPLETE_ENABLED", True)
    def test_false_if_pull_request_does_not_have_autocomplete_label(self):
        pull_request = build(builder.pull_request().merged(True))
        self.assertFalse(asana_logic.should_autocomplete_tasks_on_merge(pull_request))

    @patch("src.asana.logic.SGTM_FEATURE__AUTOCOMPLETE_ENABLED", True)
    def test_true_if_should_autocomplete(self):
        pull_request = build(
            builder.pull_request()
            .merged(True)
            .label(
                builder.label().name(
                    asana_logic.AutocompleteLabel.COMPLETE_ON_MERGE.value
                )
            )
        )
        self.assertTrue(asana_logic.should_autocomplete_tasks_on_merge(pull_request))


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
