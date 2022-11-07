
"""
The original Python-Markdown autolink require a pair of < >

    AUTOLINK_RE = r'<((?:[Ff]|[Hh][Tt])[Tt][Pp][Ss]?://[^<>]*)>'

Let's make it optional.

use the same name and priority to overwrite it :

    inlinePatterns.register(AutolinkInlineProcessor(AUTOLINK_RE, md), 'autolink', 120)

"""


from markdown.extensions import Extension
from markdown.inlinepatterns import AutolinkInlineProcessor


AUTOLINK_RE = r'<?((?:[Ff]|[Hh][Tt])[Tt][Pp][Ss]?://[^<>]*)>?'


class ObsidianAutoLinkExtension(Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(AutolinkInlineProcessor(AUTOLINK_RE, md), 'autolink', 120)


def makeExtension(**kwargs):  # noqa
    return ObsidianAutoLinkExtension(**kwargs)
