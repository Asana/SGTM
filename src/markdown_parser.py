import re
from html import escape, unescape
from html.parser import HTMLParser
from typing import Match
from urllib.parse import urlparse

import mistune  # type: ignore

# https://gist.github.com/gruber/8891611
URL_REGEX = r"""(?i)([^"\>\<\/\.]|^)\b((?:https?:(/{1,3}))(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))"""


# Tags that Asana's rich text API supports.
# https://developers.asana.com/docs/rich-text
_ASANA_SUPPORTED_TAGS = frozenset(
    {
        "a",
        "b",
        "strong",
        "em",
        "i",
        "s",
        "u",
        "code",
        "pre",
        "ol",
        "ul",
        "li",
        "blockquote",
    }
)

# Per-tag allowlist of HTML attributes that Asana accepts.
_ASANA_ALLOWED_ATTRS = {
    "a": frozenset({"href", "data-asana-gid", "data-asana-dynamic"}),
}

# URL schemes considered safe for href/src attributes.
_SAFE_URL_SCHEMES = frozenset({"http", "https", "mailto"})

# Table cell/row tags get special treatment: " | " between cells, "\n" at row
# boundaries, so stripped table text doesn't run together.
_TABLE_CELL_TAGS = frozenset({"td", "th"})
_TABLE_ROW_TAG = "tr"

# Block-level HTML elements that should emit a newline when their closing tag
# is stripped, so adjacent blocks don't run together (e.g. "TitleBody" → "Title\nBody").
_BLOCK_LEVEL_TAGS = frozenset(
    {
        "p",
        "div",
        "section",
        "summary",
        "details",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "footer",
        "nav",
        "article",
        "aside",
        "figure",
        "figcaption",
    }
)

def _urlreplace(matchobj: Match[str]) -> str:
    """Replace a bare URL match with an <a> tag. Used by both the markdown
    renderer's text() method and the HTML sanitizer's handle_data()."""
    url = unescape(matchobj.group(2))
    return matchobj.group(1) + f'<a href="{escape(url, quote=False)}">{url}</a>'


def _is_safe_url(url: str) -> bool:
    """Check that a URL uses a safe scheme (http, https, mailto)."""
    try:
        parsed = urlparse(url)
        return parsed.scheme.lower() in _SAFE_URL_SCHEMES
    except Exception:
        return False


class _AsanaHTMLSanitizer(HTMLParser):
    """Sanitizes raw HTML for Asana's rich text API.

    - Passes through Asana-supported tags with sanitized attributes
    - Strips unsupported wrapper tags but preserves their text content
    - Converts <img> tags to <a> links using src/alt attributes
    - Converts <br> to newlines
    - Passes through <hr />
    - Removes HTML comments entirely
    - Validates URL schemes (only http/https/mailto allowed)
    - Flattens nested <a> tags — keeping only the outermost — because
      Asana's rich text parser rejects invalid nested anchors.  The
      caller may seed anchor_depth so tracking carries across sanitizer
      invocations (e.g. per-tag inline_html calls within one document).
    """

    def __init__(self, anchor_depth: int = 0) -> None:
        super().__init__(convert_charrefs=False)
        self._parts: list = []
        self._cell_count_in_row = 0  # tracks cell position within a <tr>
        self.anchor_depth = anchor_depth  # nested <a> depth; public for cross-call carry

    def handle_starttag(self, tag: str, attrs: list) -> None:
        tag_lower = tag.lower()
        # Table structure: insert separators so cell text doesn't run together.
        if tag_lower in _TABLE_CELL_TAGS:
            if self._cell_count_in_row > 0:
                self._parts.append(" | ")
            self._cell_count_in_row += 1
            return
        if tag_lower == _TABLE_ROW_TAG:
            self._cell_count_in_row = 0
            return
        if tag_lower in _ASANA_SUPPORTED_TAGS:
            if tag_lower == "a":
                self.anchor_depth += 1
                if self.anchor_depth > 1:
                    return  # Suppress nested <a>; keep only the outermost
            allowed = _ASANA_ALLOWED_ATTRS.get(tag_lower, frozenset())
            safe_attrs = []
            seen_keys = set()
            for k, v in attrs:
                k_lower = k.lower()
                if k_lower in allowed and k_lower not in seen_keys and v is not None:
                    # Validate URL attributes against safe schemes
                    if k_lower == "href" and not _is_safe_url(v):
                        continue
                    safe_attrs.append(f'{k}="{escape(v)}"')
                    seen_keys.add(k_lower)
            attr_str = (" " + " ".join(safe_attrs)) if safe_attrs else ""
            self._parts.append(f"<{tag_lower}{attr_str}>")
        elif tag_lower == "img":
            attrs_dict = dict(attrs)
            src = attrs_dict.get("src", "")
            alt = attrs_dict.get("alt", "")
            if self.anchor_depth > 0:
                # Already inside an <a>; emit alt text only (no wrapping anchor)
                # to avoid producing nested anchors.
                if alt:
                    self._parts.append(escape(alt, quote=False))
            elif src and _is_safe_url(src):
                self._parts.append(
                    f'<a href="{escape(src)}">{escape(alt or src)}</a>'
                )
        elif tag_lower == "br":
            self._parts.append("\n")
        elif tag_lower == "hr":
            self._parts.append("<hr />")
        # All other tags (details, summary, div, table, h1-h6, etc.):
        # silently strip the tag; text content is preserved via handle_data.

    def handle_endtag(self, tag: str) -> None:
        tag_lower = tag.lower()
        if tag_lower == _TABLE_ROW_TAG:
            self._parts.append("\n")
            self._cell_count_in_row = 0
            return
        if tag_lower in _TABLE_CELL_TAGS:
            return  # closing </td>/</th> needs no output
        if tag_lower in _ASANA_SUPPORTED_TAGS:
            if tag_lower == "a" and self.anchor_depth > 0:
                self.anchor_depth -= 1
                if self.anchor_depth > 0:
                    return  # Inner </a>; the outer <a> is still open
            # If anchor_depth is already 0, this </a> may pair with an <a>
            # emitted by a previous inline_html() call, so emit it anyway.
            self._parts.append(f"</{tag_lower}>")
        elif tag_lower in _BLOCK_LEVEL_TAGS:
            # Avoid consecutive newlines from deeply nested block elements
            # (e.g. </p></div></div> should not emit three newlines).
            if not self._parts or not self._parts[-1].endswith("\n"):
                self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        text = escape(data, quote=False)
        # Auto-link bare URLs, matching the behavior of the markdown
        # renderer's text() method — but skip when we're already inside an
        # <a> element, otherwise we'd wrap a URL inside another anchor and
        # produce invalid nested <a><a>...</a></a>.
        if self.anchor_depth == 0:
            text = re.sub(URL_REGEX, _urlreplace, text)
        self._parts.append(text)

    def handle_entityref(self, name: str) -> None:
        self._parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self._parts.append(f"&#{name};")

    def handle_comment(self, data: str) -> None:
        pass  # Strip HTML comments entirely

    def get_result(self) -> str:
        return "".join(self._parts)


def sanitize_html_for_asana(html: str) -> str:
    """Sanitize raw HTML for Asana's rich text API.

    Converts a block of raw HTML (e.g. from a GitHub bot comment) into
    Asana-compatible markup by keeping supported tags, stripping unsupported
    wrapper tags while preserving their text, and removing HTML comments.
    """
    sanitizer = _AsanaHTMLSanitizer()
    sanitizer.feed(html)
    return sanitizer.get_result()


class GithubToAsanaRenderer(mistune.HTMLRenderer):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Mistune's inline parser splits inline HTML into one inline_html()
        # call per tag (e.g. <a>, <img>, </a> are three separate calls).  To
        # flatten nested anchors that span those calls (Graphite stack
        # comments and Cursor Bugbot "Fix in Cursor" buttons both produce
        # <a href="..."><img src="..."/></a> in list items / paragraphs),
        # we carry anchor depth across sanitize invocations on this renderer.
        self._inline_anchor_depth = 0

    def paragraph(self, text) -> str:
        return text + "\n"

    def block_quote(self, text) -> str:
        return f"<blockquote>{text}</blockquote>"

    def strikethrough(self, text) -> str:
        return f"<s>{text}</s>"

    def heading(self, text, level) -> str:
        return f"\n<b>{text}</b>\n"

    def thematic_break(self) -> str:
        return "<hr />"

    def inline_html(self, html) -> str:
        # Use the sanitizer class directly (not the simple helper) so we can
        # thread anchor_depth across successive inline_html() calls.
        sanitizer = _AsanaHTMLSanitizer(anchor_depth=self._inline_anchor_depth)
        sanitizer.feed(html)
        self._inline_anchor_depth = sanitizer.anchor_depth
        return sanitizer.get_result()

    def block_html(self, html) -> str:
        # Block HTML is handled as a complete unit — a fresh sanitizer is
        # fine since everything between the opening and closing tags of the
        # block is passed as one string.
        return sanitize_html_for_asana(html)

    def linebreak(self) -> str:
        return "\n"

    def codespan(self, text) -> str:
        return "<code>" + escape(text) + "</code>"

    def block_code(self, code, info=None):
        #  Strip the '\r\n' from the end of the code text that Github automatically adds
        code = code.rstrip("\r\n")
        return "<pre>" + escape(code) + "</pre>"

    def text(self, text) -> str:
        text = escape(text, quote=False)
        # Skip bare-URL auto-linking when we're inside an <a> emitted by a
        # previous inline_html() call — otherwise the URL would be wrapped
        # in a second <a>, producing invalid nested anchors.
        if self._inline_anchor_depth == 0:
            text = re.sub(URL_REGEX, _urlreplace, text)
        return text

    def link(self, link, text=None, title=None):
        # the parser may pass in `title`, but Asana's API does not allow the
        # `title` attribute and is therefore ignored here.
        # https://developers.asana.com/docs/rich-text

        is_asana_vanity_link = link.startswith("https://app.asana.com") and text
        asana_tags = 'data-asana-dynamic="false" ' if is_asana_vanity_link else ""

        safe_url = self._safe_url(link)
        if _is_safe_url(safe_url):
            return f'<a {asana_tags}href="{safe_url}">{text or safe_url}</a>'
        else:
            return escape(text or safe_url, quote=False)

    # Asana's API can't handle img tags
    def image(self, src, alt="", title=None) -> str:
        return self.link(src, text=alt, title=title)


def convert_github_markdown_to_asana_xml(text: str) -> str:
    markdown = mistune.create_markdown(
        renderer=GithubToAsanaRenderer(escape=False),
        plugins=["strikethrough"],
    )

    return markdown(text)
