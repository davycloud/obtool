"""
ObsidianInlineComment Extension for Python-Markdown
===================================================

This extension adds Obsidian Inline Comment to Python-Markdown.

For example:

Obsidian is great! %%Although I don't know why I need inline comment.%% You should use it.

"""

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor


class ObsidianInlineCommentExtension(Extension):

    def __init__(self, **kwargs):
        self.config = {
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        self.md = md
        # append to end of inline patterns
        COMMENT_RE = r'%%([^%]*%?[^%]*)%%'
        ob_inline_comment_pattern = ObCommentInlineProcessor(COMMENT_RE, self.getConfigs())
        ob_inline_comment_pattern.md = md
        md.inlinePatterns.register(ob_inline_comment_pattern, 'ob_comment_inline', 80)


class ObCommentInlineProcessor(InlineProcessor):
    def __init__(self, pattern, config):
        super().__init__(pattern)
        self.config = config

    def handleMatch(self, m, data):
        if m.group(1).strip():
            comment = m.group(1).strip()
            if not hasattr(self.md, 'ob_comments'):
                self.md.ob_comments = []
            self.md.ob_comments.append(comment)
        return '', m.start(0), m.end(0)


def makeExtension(**kwargs):  # pragma: no cover
    return ObsidianInlineCommentExtension(**kwargs)
