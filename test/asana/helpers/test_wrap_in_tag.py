from src.asana.helpers import _wrap_in_tag
from test.impl.base_test_case_class import BaseClass
from test.impl.builders import builder, build


class TestWrapInTag(BaseClass):

    def test_no_attrs_and_empty_text(self):
        actual = _wrap_in_tag("body")("")
        self.assertEqual(actual, "<body></body>")

    def test_including_plain_text(self):
        actual = _wrap_in_tag("h1")("Hi! My name is SGTM!")
        self.assertEqual(actual, "<h1>Hi! My name is SGTM!</h1>")

    def test_nested_tags(self):
        actual = _wrap_in_tag("body")(
            _wrap_in_tag("p")("The Force will be with you. Always.")
        )
        self.assertEqual(actual, "<body><p>The Force will be with you. Always.</p></body>")

    def test_one_attribute(self):
        actual = _wrap_in_tag("h1", {"class": "im-a-class"})("Hi! My name is SGTM!")
        self.assertEqual(actual, '<h1 class="im-a-class">Hi! My name is SGTM!</h1>')

    def test_multiple_attributes(self):
        actual = _wrap_in_tag("h1", {"class": "im-a-class", "id": "123"})("Hi! My name is SGTM!")
        self.assertEqual(actual, '<h1 class="im-a-class" id="123">Hi! My name is SGTM!</h1>')

    def test_attr_value_that_contains_quote(self):
        actual = _wrap_in_tag("h1", {"id": '1"23'})("Hi! My name is SGTM!")
        self.assertEqual(actual, '<h1 id="1&quot;23">Hi! My name is SGTM!</h1>')

    def test_text_contains_emoji(self):
        actual = _wrap_in_tag("li")("👍")
        self.assertEqual(actual, '<li>👍</li>')

    def test_attribute_value_contains_emoji(self):
        actual = _wrap_in_tag("li", {'reaction': "👍"})("Happy to see it!")
        self.assertEqual(actual, '<li reaction="👍">Happy to see it!</li>')


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
