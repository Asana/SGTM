import re
from html import escape, unescape
from typing import Match

import mistune  # type: ignore

# https://gist.github.com/gruber/8891611
URL_REGEX = r"""(?i)([^"\>\<\/\.]|^)\b((?:https?:(/{1,3}))(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))"""


class GithubToAsanaRenderer(mistune.HTMLRenderer):
    def paragraph(self, text) -> str:
        return text + "\n"

    def block_quote(self, text) -> str:
        return f"<em>&gt; {text}</em>"

    def strikethrough(self, text) -> str:
        return f"<s>{text}</s>"

    def heading(self, text, level) -> str:
        return f"\n<b>{text}</b>\n"

    def thematic_break(self) -> str:
        # Asana API doesn't support <hr />
        return "\n---\n"

    def inline_html(self, html) -> str:
        return escape(html)

    def block_html(self, html) -> str:
        return escape(html)

    def linebreak(self) -> str:
        return "\n"

    def codespan(self, text) -> str:
        return "<code>" + escape(text) + "</code>"

    def block_code(self, code, info=None):
        html = super().block_code(code, info=info)
        # the Asana API doesn't accept pre tags so we strip them
        return html.replace("<pre>", "").replace("</pre>", "")

    def text(self, text) -> str:
        text = escape(text, quote=False)

        def urlreplace(matchobj: Match[str]) -> str:
            url = unescape(matchobj.group(2))
            return matchobj.group(1) + f'<a href="{escape(url, quote=False)}">{url}</a>'

        return re.sub(URL_REGEX, urlreplace, text)

    def link(self, link, text=None, title=None):
        is_asana_vanity_link = link.startswith("https://app.asana.com") and text is not None
        if text is None:
            text = link

        asana_tags = 'data-asana-dynamic="false" ' if is_asana_vanity_link else ""
        s = '<a ' + asana_tags + 'href="' + self._safe_url(link) + '"'
        if title:
            s += ' title="' + mistune.escape_html(title) + '"'
        return s + '>' + (text or link) + '</a>'

    # Asana's API can't handle img tags
    def image(self, src, alt="", title=None) -> str:
        return self.link(src, text=alt, title=title)



def convert_github_markdown_to_asana_xml(text: str) -> str:
    markdown = mistune.create_markdown(
        renderer=GithubToAsanaRenderer(escape=False),
        plugins=["strikethrough"],
    )

    return markdown(text)
