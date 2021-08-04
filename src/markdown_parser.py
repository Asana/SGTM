import re
from html import escape, unescape
from typing import Match

import mistune  # type: ignore

# https://gist.github.com/gruber/8891611
URL_REGEX = r"""(?i)([^"\>\<\/\.]|^)\b((?:https?:(/{1,3}))(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))"""


class GithubToAsanaRenderer(mistune.HTMLRenderer):
    def paragraph(self, text):
        return text + "\n"

    def block_quote(self, text):
        return f"<em>{escape('> ' + text, quote=False)}</em>"

    def strikethrough(self, text):
        return f"<s>{escape(text, quote=False)}</s>"

    def heading(self, text, level):
        return f"\n<b>{escape(text, quote=False)}</b>\n"

    def text(self, text):
        text = escape(text, quote=False)

        def urlreplace(matchobj: Match[str]) -> str:
            url = unescape(matchobj.group(2))
            return matchobj.group(1) + f'<a href="{escape(url, quote=False)}">{url}</a>'

        return re.sub(URL_REGEX, urlreplace, text)


def convert_github_markdown_to_asana_xml(text: str) -> str:
    markdown = mistune.create_markdown(
        renderer=GithubToAsanaRenderer(escape=False), plugins=["strikethrough"],
    )
    return _strip_pre_tags(markdown(text))


# the Asana API doesn't accept pre tags so we strip them
def _strip_pre_tags(text: str) -> str:
    return text.replace("<pre>", "").replace("</pre>", "")
