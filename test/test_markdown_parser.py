import unittest

from html import escape
from src.markdown_parser import convert_github_markdown_to_asana_xml


class TestConvertGithubMarkdownToAsanaXml(unittest.TestCase):
    def test_basic_markdown(self):
        md = """~~strike~~ **bold** _italic_ `code` [link](asana.com)"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            "<s>strike</s> <strong>bold</strong> <em>italic</em> <code>code</code> <a"
            ' href="asana.com">link</a>\n',
        )

    def test_ul_tag(self):
        md = """* bullet one\n* bullet two"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            """<ul>\n<li>bullet one</li>\n<li>bullet two</li>\n</ul>\n""",
        )

    def test_ol_tag(self):
        md = """1. bullet one\n2. bullet two"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            """<ol>\n<li>bullet one</li>\n<li>bullet two</li>\n</ol>\n""",
        )

    def test_paragraph(self):
        md = "we don't wrap random text in p tags"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(md + "\n", xml)

    def test_block_quote(self):
        md = "> block quote"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, "<em>&gt; block quote\n</em>")

    def test_horizontal_rule(self):
        # Asana doesn't support <hr /> tags, so we just ignore them
        md = "hello\n\n---\nworld\n"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, md)  # unchanged

    def test_auto_linking(self):
        md = "https://asana.com/ [still works](www.test.com)"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            '<a href="https://asana.com/">https://asana.com/</a> <a'
            ' href="www.test.com">still works</a>\n',
        )

    def test_link_to_non_asana_url(self):
        md = "hi [there](https://www.test.com)"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, 'hi <a href="https://www.test.com">there</a>\n')

    def test_link_to_asana_url_adds_data_asana_dynamic_false(self):
        md = "hi [there](https://app.asana.com/0/1)"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            'hi <a data-asana-dynamic="false" href="https://app.asana.com/0/1">there</a>\n',
        )

    def test_link_to_asana_url_with_no_vanity_text_does_not_add_data_asana_dynamic(
        self,
    ):
        md = "hi https://app.asana.com/0/1"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            'hi <a href="https://app.asana.com/0/1">https://app.asana.com/0/1</a>\n',
        )

    def test_link_with_title(self):
        md = 'hi [there](https://www.test.com "foo")'
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml, 'hi <a href="https://www.test.com" title="foo">there</a>\n'
        )

    def test_converts_headings_to_bold(self):
        md = "## heading"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, "\n<b>heading</b>\n")

    def test_nested_code_within_block_quote(self):
        md = "> abc `123`"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, "<em>&gt; abc <code>123</code>\n</em>")

    def test_removes_pre_tags_inline(self):
        md = """```test```"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, "<code>test</code>\n")

    def test_removes_pre_tags_block(self):
        md = """see:
```
function foo = () => null;
```
"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, "see:\n<code>function foo = () =&gt; null;\n</code>\n")

    def test_escapes_raw_html_mixed_with_markdown(self):
        md = """## <img href="link" />still here <h3>header</h3>"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            "\n<b>"
            + escape('<img href="link" />')
            + "still here "
            + escape("<h3>header</h3>")
            + "</b>\n",
        )

    def test_escapes_raw_html_on_own_lines(self):
        md = """## blah blah blah
<img href="link">
still here <h3>header</h3>"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            "\n<b>blah blah blah</b>\n"
            + escape('<img href="link">\n')
            + "still here "
            + escape("<h3>header</h3>"),
        )

    def test_escapes_raw_html(self):
        md = """<img href="link" />still here <h3>header</h3>"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            escape('<img href="link" />') + "still here " + escape("<h3>header</h3>\n"),
        )

    def test_removes_images(self):
        md = """![image](https://image.com)"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, '<a href="https://image.com">image</a>\n')


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
