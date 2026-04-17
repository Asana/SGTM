import re
import unittest

from src.markdown_parser import (
    convert_github_markdown_to_asana_xml,
    sanitize_html_for_asana,
)


class TestConvertGithubMarkdownToAsanaXml(unittest.TestCase):
    def test_basic_markdown(self):
        md = """~~strike~~ **bold** _italic_ `code` [link](https://www.asana.com)"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            "<s>strike</s> <strong>bold</strong> <em>italic</em> <code>code</code> <a"
            ' href="https://www.asana.com">link</a>\n',
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
        self.assertEqual(xml, "<blockquote>block quote\n</blockquote>")

    def test_horizontal_rule(self):
        md = "hello\n\n---\nworld\n"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, "hello\n<hr />world\n")

    def test_auto_linking(self):
        md = "https://asana.com/ [still works](https://www.test.com)"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            '<a href="https://asana.com/">https://asana.com/</a> <a'
            ' href="https://www.test.com">still works</a>\n',
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
            # title should get ignored
            xml,
            'hi <a href="https://www.test.com">there</a>\n',
        )

    def test_link_to_relative_url(self):
        md = "check out the [docs](README.md)"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            "check out the docs\n",
        )

    def test_converts_headings_to_bold(self):
        md = "## heading"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, "\n<b>heading</b>\n")

    def test_nested_code_within_block_quote(self):
        md = "> abc `123`"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, "<blockquote>abc <code>123</code>\n</blockquote>")

    def test_codespan(self):
        md = """```test```"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, "<code>test</code>\n")

    def test_sanitizes_raw_html_mixed_with_markdown(self):
        """Unsupported tags are stripped but content preserved inside markdown."""
        md = """## <img href="link" />still here <h3>header</h3>"""
        xml = convert_github_markdown_to_asana_xml(md)
        # <img> without src is stripped; <h3> tags stripped with block newline
        self.assertEqual(xml, "\n<b>still here header\n</b>\n")

    def test_sanitizes_raw_html_on_own_lines(self):
        """Block-level raw HTML is sanitized, not escaped."""
        md = """## blah blah blah
<img href="link">
still here <h3>header</h3>"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            xml,
            "\n<b>blah blah blah</b>\n" + "\n" + "still here header\n",
        )

    def test_sanitizes_raw_html(self):
        """Inline raw HTML tags are sanitized: unsupported stripped, content kept."""
        md = """<img href="link" />still here <h3>header</h3>"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, "still here header\n\n")

    def test_removes_images(self):
        md = """![image](https://image.com)"""
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(xml, '<a href="https://image.com">image</a>\n')


class TestSanitizeHtmlForAsana(unittest.TestCase):
    """Tests for the HTML sanitizer that converts raw HTML to Asana-compatible markup."""

    # --- Asana-supported tags pass through ---

    def test_preserves_anchor_tag_with_href(self):
        html = '<a href="https://example.com">click here</a>'
        self.assertEqual(
            sanitize_html_for_asana(html),
            '<a href="https://example.com">click here</a>',
        )

    def test_strips_unsupported_attrs_from_anchor(self):
        html = '<a href="https://example.com" target="_blank" rel="noopener">link</a>'
        self.assertEqual(
            sanitize_html_for_asana(html),
            '<a href="https://example.com">link</a>',
        )

    def test_preserves_bold_tags(self):
        self.assertEqual(
            sanitize_html_for_asana("<b>bold</b>"),
            "<b>bold</b>",
        )
        self.assertEqual(
            sanitize_html_for_asana("<strong>bold</strong>"),
            "<strong>bold</strong>",
        )

    def test_preserves_emphasis_tags(self):
        self.assertEqual(
            sanitize_html_for_asana("<em>italic</em>"),
            "<em>italic</em>",
        )
        self.assertEqual(
            sanitize_html_for_asana("<i>italic</i>"),
            "<i>italic</i>",
        )

    def test_preserves_list_tags(self):
        html = "<ul><li>one</li><li>two</li></ul>"
        self.assertEqual(sanitize_html_for_asana(html), html)

    def test_preserves_code_tags(self):
        self.assertEqual(
            sanitize_html_for_asana("<code>foo()</code>"),
            "<code>foo()</code>",
        )
        self.assertEqual(
            sanitize_html_for_asana("<pre>block</pre>"),
            "<pre>block</pre>",
        )

    def test_preserves_strikethrough_and_underline(self):
        self.assertEqual(sanitize_html_for_asana("<s>old</s>"), "<s>old</s>")
        self.assertEqual(sanitize_html_for_asana("<u>new</u>"), "<u>new</u>")

    def test_preserves_blockquote(self):
        self.assertEqual(
            sanitize_html_for_asana("<blockquote>quoted</blockquote>"),
            "<blockquote>quoted</blockquote>",
        )

    # --- Unsupported tags stripped, content preserved ---

    def test_strips_details_summary_with_newlines(self):
        html = "<details><summary>Click to expand</summary>Hidden content</details>"
        self.assertEqual(
            sanitize_html_for_asana(html),
            "Click to expand\nHidden content\n",
        )

    def test_strips_div_with_newline(self):
        html = '<div class="wrapper"><span>text</span></div>'
        self.assertEqual(sanitize_html_for_asana(html), "text\n")

    def test_strips_heading_tags_with_newlines(self):
        for level in range(1, 7):
            html = f"<h{level}>Heading</h{level}>"
            self.assertEqual(sanitize_html_for_asana(html), "Heading\n")

    def test_strips_table_tags_preserves_text_with_separators(self):
        html = "<table><tr><th>Name</th><th>Status</th></tr><tr><td>foo</td><td>OK</td></tr></table>"
        self.assertEqual(
            sanitize_html_for_asana(html), "Name | Status\nfoo | OK\n"
        )

    def test_single_cell_row_has_no_leading_separator(self):
        html = "<table><tr><td>only cell</td></tr></table>"
        self.assertEqual(sanitize_html_for_asana(html), "only cell\n")

    def test_three_column_table(self):
        html = "<table><tr><td>A</td><td>B</td><td>C</td></tr></table>"
        self.assertEqual(sanitize_html_for_asana(html), "A | B | C\n")

    def test_strips_p_tags_with_newline(self):
        html = "<p>paragraph text</p>"
        self.assertEqual(sanitize_html_for_asana(html), "paragraph text\n")

    # --- Special tag conversions ---

    def test_converts_img_with_src_to_link(self):
        html = '<img src="https://example.com/image.png" alt="Logo" />'
        self.assertEqual(
            sanitize_html_for_asana(html),
            '<a href="https://example.com/image.png">Logo</a>',
        )

    def test_converts_img_without_alt_uses_src(self):
        html = '<img src="https://example.com/pic.png" />'
        self.assertEqual(
            sanitize_html_for_asana(html),
            '<a href="https://example.com/pic.png">https://example.com/pic.png</a>',
        )

    def test_strips_img_without_src(self):
        html = '<img alt="no source" />'
        self.assertEqual(sanitize_html_for_asana(html), "")

    def test_converts_br_to_newline(self):
        self.assertEqual(sanitize_html_for_asana("line1<br>line2"), "line1\nline2")
        self.assertEqual(sanitize_html_for_asana("line1<br />line2"), "line1\nline2")

    def test_passes_through_hr(self):
        self.assertEqual(sanitize_html_for_asana("<hr>"), "<hr />")
        self.assertEqual(sanitize_html_for_asana("<hr />"), "<hr />")

    # --- HTML comments ---

    def test_strips_html_comments(self):
        html = "<!-- this is a comment -->visible text"
        self.assertEqual(sanitize_html_for_asana(html), "visible text")

    def test_strips_multiline_html_comments(self):
        html = "before<!-- multi\nline\ncomment -->after"
        self.assertEqual(sanitize_html_for_asana(html), "beforeafter")

    # --- URL scheme validation ---

    def test_blocks_javascript_url_in_href(self):
        html = '<a href="javascript:alert(1)">click</a>'
        result = sanitize_html_for_asana(html)
        self.assertNotIn("javascript:", result)
        # Tag still emitted but without href
        self.assertIn("<a>", result)

    def test_blocks_data_url_in_href(self):
        html = '<a href="data:text/html,payload">click</a>'
        result = sanitize_html_for_asana(html)
        self.assertNotIn("data:", result)

    def test_blocks_javascript_url_in_img_src(self):
        html = '<img src="javascript:alert(1)" alt="xss" />'
        result = sanitize_html_for_asana(html)
        self.assertNotIn("javascript:", result)
        self.assertEqual(result, "")

    def test_allows_https_url_in_href(self):
        html = '<a href="https://example.com">link</a>'
        self.assertEqual(
            sanitize_html_for_asana(html),
            '<a href="https://example.com">link</a>',
        )

    def test_allows_mailto_url_in_href(self):
        html = '<a href="mailto:user@example.com">email</a>'
        self.assertEqual(
            sanitize_html_for_asana(html),
            '<a href="mailto:user@example.com">email</a>',
        )

    def test_deduplicates_href_attributes(self):
        """Only the first href is kept if an element has duplicates."""
        html = '<a href="https://first.com" href="https://second.com">link</a>'
        result = sanitize_html_for_asana(html)
        self.assertIn("https://first.com", result)
        self.assertNotIn("https://second.com", result)

    # --- Text escaping ---

    def test_escapes_special_chars_in_text(self):
        html = "<div>1 < 2 & 3 > 0</div>"
        result = sanitize_html_for_asana(html)
        self.assertIn("1 &lt; 2 &amp; 3 &gt; 0", result)

    def test_preserves_entity_refs(self):
        html = "&amp; &lt; &gt;"
        self.assertEqual(sanitize_html_for_asana(html), "&amp; &lt; &gt;")

    # --- Real-world bot comment patterns ---

    def test_spacelift_comment(self):
        """Spacelift-style collapsible status with nested list and links."""
        html = (
            "<!-- spacelift_id -->"
            "Commit: abc123\n"
            "<details><summary>Stacks affected:</summary>"
            '<ul><li>stack-a: <a href="https://spacelift.io/a">link</a></li></ul>'
            "</details>"
        )
        result = sanitize_html_for_asana(html)
        self.assertNotIn("<!--", result)
        self.assertNotIn("<details>", result)
        self.assertNotIn("<summary>", result)
        self.assertIn("Commit: abc123", result)
        self.assertIn("Stacks affected:", result)
        self.assertIn("<ul>", result)
        self.assertIn("<li>", result)
        self.assertIn('<a href="https://spacelift.io/a">link</a>', result)

    def test_graphite_comment(self):
        """Graphite-style comment with images and styled links."""
        html = (
            '<a href="https://graphite.dev" target="_blank">'
            '<img src="https://graphite.dev/logo.png" alt="Graphite" width="10" />'
            "</a> "
            '<a href="https://graphite.dev"><b>Graphite</b></a>'
        )
        result = sanitize_html_for_asana(html)
        self.assertNotIn("target=", result)
        self.assertNotIn("<img", result)
        self.assertIn('<a href="https://graphite.dev">', result)
        self.assertIn("<b>Graphite</b>", result)

    def test_cursor_agent_badges(self):
        """Cursor agent badge HTML with picture/source/div elements."""
        html = (
            '<div><a href="https://cursor.com/agent">'
            "<picture>"
            '<source media="(prefers-color-scheme: dark)" srcset="dark.png">'
            '<img alt="Open" src="light.png">'
            "</picture></a></div>"
        )
        result = sanitize_html_for_asana(html)
        self.assertNotIn("<div>", result)
        self.assertNotIn("<picture>", result)
        self.assertNotIn("<source", result)
        self.assertIn('<a href="https://cursor.com/agent">', result)

    # --- End-to-end through the markdown parser ---

    def test_markdown_with_details_block(self):
        """GitHub markdown containing a <details> block renders cleanly."""
        md = "Summary\n\n<details><summary>Details</summary>\n\nHidden\n\n</details>"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertNotIn("&lt;details&gt;", xml)
        self.assertNotIn("&lt;summary&gt;", xml)
        self.assertIn("Summary", xml)
        self.assertIn("Details", xml)
        self.assertIn("Hidden", xml)

    def test_markdown_with_html_comment(self):
        """HTML comments in markdown are stripped entirely."""
        md = "<!-- hidden -->visible text"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertNotIn("<!--", xml)
        self.assertNotIn("hidden", xml)
        self.assertIn("visible text", xml)

    def test_markdown_with_inline_html_link(self):
        """Raw <a> tags in markdown pass through with sanitized attributes."""
        md = 'Click <a href="https://example.com" target="_blank">here</a> now'
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertIn('<a href="https://example.com">here</a>', xml)
        self.assertNotIn("target=", xml)

    def test_fenced_code_block_preserves_html_as_code(self):
        """Fenced code blocks remain as <pre> with HTML escaped — unchanged mistune default."""
        md = '```html\n<div>example</div>\n```'
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertIn("<pre>", xml)
        self.assertIn("&lt;div&gt;", xml)

    def test_indented_code_stays_as_code(self):
        """Plain indented code remains as <pre> — unchanged mistune default."""
        md = "    x = 1\n    y = 2\n"
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertIn("<pre>", xml)
        self.assertIn("x = 1", xml)

    def test_bare_urls_in_block_html_are_autolinked(self):
        """Bare URLs inside block-level HTML should become clickable links."""
        html = "<details><summary>Links</summary>Visit https://example.com for info</details>"
        xml = convert_github_markdown_to_asana_xml(html)
        self.assertIn('<a href="https://example.com">', xml)

    def test_markdown_link_with_javascript_url_is_escaped(self):
        """Markdown [text](javascript:...) links should be escaped, not rendered."""
        md = '[click](javascript:alert(1))'
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertNotIn("javascript:", xml)
        self.assertIn("click", xml)


class TestAnchorFlatteningAcrossInlineCalls(unittest.TestCase):
    """Nested <a> tags must be flattened regardless of whether the tags are
    tokenized by mistune as one block or split into per-tag inline_html calls."""

    def test_graphite_stack_list_item_flattens_nested_anchors(self):
        """Real Graphite stack source: list item with <a href><img></a>.

        Mistune tokenizes this as per-tag inline_html calls (one call each
        for <a>, <img>, </a>).  Without renderer-level anchor tracking the
        <img> would convert to a second <a> nested inside the outer one.
        """
        # Exact source pulled from GitHub (issue comment 4270446033)
        md = (
            '* **#389656** '
            '<a href="https://app.graphite.com/github/pr/Asana/codez/389656" target="_blank">'
            '<img src="https://static.graphite.dev/graphite-32x32-black.png" alt="Graphite" width="10px" height="10px"/>'
            '</a>'
            ' 👈 '
            '<a href="https://app.graphite.com/github/pr/Asana/codez/389656?utm_source=stack-comment-view-in-graphite" target="_blank">(View in Graphite)</a>\n'
            '* `next-master`\n'
        )
        xml = convert_github_markdown_to_asana_xml(md)

        # Assert: no nested <a> — the critical property
        nested = re.findall(r'<a[^>]*>(?:(?!</a>).)*<a\b', xml, flags=re.DOTALL)
        self.assertEqual(
            nested, [], f"Unexpected nested anchors in output:\n{xml}"
        )
        # Outer anchor should still be present with its Graphite label text
        self.assertIn(
            '<a href="https://app.graphite.com/github/pr/Asana/codez/389656">Graphite</a>',
            xml,
        )
        # Second (text) link unchanged
        self.assertIn("(View in Graphite)</a>", xml)

    def test_cursor_bugbot_fix_button_in_paragraph_flattens_nested_anchors(self):
        """Real Cursor Bugbot pattern: <a href><picture><source><img></picture></a>
        as a paragraph of per-tag inline_html calls."""
        md = (
            '<!-- BUGBOT_FIX_ALL -->\n'
            '<a href="https://cursor.com/open?data=JWT" target="_blank" rel="noopener noreferrer">'
            '<picture>'
            '<source media="(prefers-color-scheme: dark)" srcset="https://cursor.com/fix-dark.png">'
            '<source media="(prefers-color-scheme: light)" srcset="https://cursor.com/fix-light.png">'
            '<img alt="Fix All in Cursor" width="115" height="28" src="https://cursor.com/fix-dark.png">'
            '</picture></a>\n'
            '<!-- /BUGBOT_FIX_ALL -->\n'
        )
        xml = convert_github_markdown_to_asana_xml(md)
        nested = re.findall(r'<a[^>]*>(?:(?!</a>).)*<a\b', xml, flags=re.DOTALL)
        self.assertEqual(
            nested, [], f"Unexpected nested anchors in output:\n{xml}"
        )
        # Outer Cursor link preserved with alt text as the label
        self.assertIn('<a href="https://cursor.com/open?data=JWT">', xml)
        self.assertIn("Fix All in Cursor", xml)

    def test_anchor_depth_resets_between_top_level_renders(self):
        """Two separate convert_github_markdown_to_asana_xml() calls must not
        share anchor depth — each should start fresh."""
        # First call leaves depth at 0 (balanced)
        xml1 = convert_github_markdown_to_asana_xml('<a href="https://a.com">one</a>')
        # Second call should render a standalone link normally
        xml2 = convert_github_markdown_to_asana_xml('<a href="https://b.com">two</a>')
        self.assertIn('<a href="https://a.com">one</a>', xml1)
        self.assertIn('<a href="https://b.com">two</a>', xml2)

    def test_bare_url_inside_anchor_is_not_auto_linked(self):
        """A bare URL as the text content of an <a> must NOT be re-wrapped
        in another <a> by the URL auto-linker — that produces nested anchors.
        Real-world trigger: Spacelift's <a href='URL'>URL</a> inside <details>
        and Graphite-style inline tags with a URL between them."""
        # Case 1: url inside inline <a> (mistune's text() path)
        md = '<a href="https://example.com">visit https://example.com/path</a>'
        xml = convert_github_markdown_to_asana_xml(md)
        self.assertEqual(
            0, len(re.findall(r'<a[^>]*>(?:(?!</a>).)*<a\b', xml, flags=re.DOTALL)),
            f"nested anchors in: {xml}",
        )

        # Case 2: url inside <a> in block HTML (sanitizer's handle_data path)
        md2 = "<div><a href='https://example.com'>https://example.com</a></div>"
        xml2 = convert_github_markdown_to_asana_xml(md2)
        self.assertEqual(
            0, len(re.findall(r'<a[^>]*>(?:(?!</a>).)*<a\b', xml2, flags=re.DOTALL)),
            f"nested anchors in: {xml2}",
        )

        # Sanity: bare URL outside any anchor still auto-links
        md3 = "See https://example.com for info"
        xml3 = convert_github_markdown_to_asana_xml(md3)
        self.assertIn('<a href="https://example.com">https://example.com</a>', xml3)


if __name__ == "__main__":
    from unittest import main as run_tests

    run_tests()
