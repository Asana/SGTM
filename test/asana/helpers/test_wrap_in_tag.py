from src.asana.helpers import _wrap_in_tag
from test.impl.base_test_case_class import BaseClass
from test.impl.builders import builder, build


class TestWrapInTag(BaseClass):
    def test_no_attrs_and_empty_text(self):
        actual = _wrap_in_tag("movie")("")
        self.assertEqual(actual, "<movie></movie>")

    def test_basic_usage(self):
        actual = _wrap_in_tag("movie")("A long time ago in a galaxy far, far away...")
        self.assertEqual(
            actual, "<movie>A long time ago in a galaxy far, far away...</movie>"
        )

    def test_nested_tags(self):
        actual = _wrap_in_tag("p")(
            "No. " + _wrap_in_tag("strong")("I") + " am your father."
        )
        self.assertEqual(actual, "<p>No. <strong>I</strong> am your father.</p>")

    def test_attribute_with_text(self):
        actual = _wrap_in_tag("p", {"force": "enabled"})(
            "These aren't the droids you're looking for."
        )
        self.assertEqual(
            actual,
            "<p force=\"enabled\">These aren't the droids you're looking for.</p>",
        )

    def test_multiple_attributes(self):
        actual = _wrap_in_tag("p", {"by": "leia", "with": "snark"})(
            "Why you stuck-up, half-witted, scruffy-looking nerf herder."
        )
        self.assertEqual(
            actual,
            '<p by="leia" with="snark">Why you stuck-up, half-witted, scruffy-looking nerf herder.</p>',
        )

    def test_attr_value_that_contains_special_characters(self):
        actual = _wrap_in_tag("clone", {"cloned": "<clone></clone>"})("")
        self.assertEqual(actual, '<clone cloned="&lt;clone&gt;&lt;/clone&gt;"></clone>')

    def test_text_contains_emoji(self):
        actual = _wrap_in_tag("li")(
            "...the ship that made the Kessel Run in less than twelve parsecs...🚀"
        )
        self.assertEqual(
            actual,
            "<li>...the ship that made the Kessel Run in less than twelve parsecs...🚀</li>",
        )

    def test_attribute_value_contains_emoji(self):
        actual = _wrap_in_tag("p", {"reaction": "👍👍👍👍👍"})("Five stars! Bravo!")
        self.assertEqual(actual, '<p reaction="👍👍👍👍👍">Five stars! Bravo!</p>')


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
