import unittest

from src.markdown_parser import convert_github_markdown_to_asana_xml


class TestConvertGithubMarkdownToAsanaXml(unittest.TestCase):
    def test_basic_markdown(self):
        md = """~~strike~~ **bold** _italic_ `code` [link](asana.com)"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            '<s>strike</s> <strong>bold</strong> <em>italic</em> <code>code</code> <a href="asana.com">link</a>\n',
        )

    def test_ul_tag(self):
        md = """* bullet one\n* bullet two"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml, """<ul>\n<li>bullet one</li>\n<li>bullet two</li>\n</ul>\n""",
        )

    def test_ol_tag(self):
        md = """1. bullet one\n2. bullet two"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml, """<ol>\n<li>bullet one</li>\n<li>bullet two</li>\n</ol>\n""",
        )

    def test_paragraph(self):
        md = "we don't wrap random text in p tags"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(md + "\n", xml)

    def test_block_quote(self):
        md = "> block quote"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, "<em>> block quote\n</em>")

    def test_auto_linking(self):
        md = "https://asana.com/ [still works](www.test.com)"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            '<a href="https://asana.com/">https://asana.com/</a> <a href="www.test.com">still works</a>\n',
        )

    def test_converts_headings_to_bold(self):
        md = "## heading"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, "\n<b>heading</b>\n")


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
