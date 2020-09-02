from src.asana.helpers import convert_urls_to_links

from test.impl.base_test_case_class import BaseClass


class TestConvertUrlsToLinks(BaseClass):
    def test_no_urls_returns_original(self):
        self.assertEqual("foo", convert_urls_to_links("foo"))

    def test_wrap_url_in_a_tag(self):
        input_text = "Hey check out https://www.asana.com to work together effortlessly"
        expected_output = 'Hey check out <A href="https://www.asana.com">https://www.asana.com</A> to work together effortlessly'
        self.assertEqual(expected_output, convert_urls_to_links(input_text))

    def test_wrap_prefix_url_in_a_tag(self):
        input_text = "https://www.asana.com is our website"
        expected_output = (
            '<A href="https://www.asana.com">https://www.asana.com</A> is our website'
        )
        self.assertEqual(expected_output, convert_urls_to_links(input_text))

    def test_wrap_suffix_url_in_a_tag(self):
        input_text = "Our website is https://www.asana.com"
        expected_output = (
            'Our website is <A href="https://www.asana.com">https://www.asana.com</A>'
        )
        self.assertEqual(expected_output, convert_urls_to_links(input_text))

    def test_wrap_multiple_urls_in_a_tag(self):
        input_text = "Hey check out https://www.asana.com to work together effortlessly. We're hiring at https://asana.com/jobs"
        expected_output = 'Hey check out <A href="https://www.asana.com">https://www.asana.com</A> to work together effortlessly. We\'re hiring at <A href="https://asana.com/jobs">https://asana.com/jobs</A>'
        self.assertEqual(expected_output, convert_urls_to_links(input_text))

    def test_dont_wrap_urls_that_already_are_wrapped_in_a_tag(self):
        input_text = 'Hey check out <A href="https://www.asana.com">https://www.asana.com</A> to work together effortlessly'
        self.assertEqual(input_text, convert_urls_to_links(input_text))

    def test_markdown_wraped_urls_still_get_converted(self):
        url = "https://app.asana.com/0/0/12345"
        input_text = "Pull Request synchronized with [Asana task]({})".format(url)
        self.assertEqual(
            'Pull Request synchronized with [Asana task](<A href="{}">{}</A>)'.format(
                url, url
            ),
            convert_urls_to_links(input_text),
        )


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
