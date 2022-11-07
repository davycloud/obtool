"""
Obsidian Header Extension for Python-Markdown
======================================

The original Header ignore the space between # and header text.

In Obsidian, when there is no space, it's a tag.

"""

from markdown.extensions import Extension
from markdown.blockprocessors import HashHeaderProcessor
import re


class ObsidianHeaderExtension(Extension):
    def extendMarkdown(self, md):
        md.parser.blockprocessors.register(ObHashHeaderProcessor(md.parser), 'hashheader', 70)


class ObHashHeaderProcessor(HashHeaderProcessor):
    # there must be at least one space after #{1,6}
    RE = re.compile(r'(?:^|\n)(?P<level>#{1,6}) +(?P<header>(?:\\.|[^\\])*?)#*(?:\n|$)')


def makeExtension(**kwargs):  # pragma: no cover
    return ObsidianHeaderExtension(**kwargs)
