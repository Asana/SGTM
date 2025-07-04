import re
from html import escape, unescape
from typing import Match
from urllib.parse import urlparse

import mistune  # type: ignore

# https://gist.github.com/gruber/8891611
URL_REGEX = r"""(?i)([^"\>\<\/\.]|^)\b((?:https?:(/{1,3}))(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))"""


class GithubToAsanaRenderer(mistune.HTMLRenderer):
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
        return escape(html)

    def block_html(self, html) -> str:
        return escape(html)

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

        def urlreplace(matchobj: Match[str]) -> str:
            url = unescape(matchobj.group(2))
            return matchobj.group(1) + f'<a href="{escape(url, quote=False)}">{url}</a>'

        return re.sub(URL_REGEX, urlreplace, text)

    def link(self, link, text=None, title=None):
        # the parser may pass in `title`, but Asana's API does not allow the
        # `title` attribute and is therefore ignored here.
        # https://developers.asana.com/docs/rich-text

        is_asana_vanity_link = link.startswith("https://app.asana.com") and text
        asana_tags = 'data-asana-dynamic="false" ' if is_asana_vanity_link else ""

        safe_url = self._safe_url(link)
        if self._is_valid_url(safe_url):
            return f'<a {asana_tags}href="{safe_url}">{text or safe_url}</a>'
        else:
            return escape(text or safe_url, quote=False)

    # Asana's API can't handle img tags
    def image(self, src, alt="", title=None) -> str:
        return self.link(src, text=alt, title=title)

    def _is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            # invalid URL
            return False


def convert_github_markdown_to_asana_xml(text: str) -> str:
    markdown = mistune.create_markdown(
        renderer=GithubToAsanaRenderer(escape=False),
        plugins=["strikethrough"],
    )

    return markdown(text)
