"""
Obsidian Block Comment Extension for Python Markdown
====================================================

This extension adds Obsidian Block Comment to Python-Markdown.

    %%
    These are
    comments
    in
    Obsidian
    %%

"""
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
import re


class ObsidianCommentExtension(Extension):
    def __init__(self, **kwargs):
        self.config = {
            'keep': [True, 'Reserve the comment for next process. Default: True']
        }
        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        """ Add FencedBlockPreprocessor to the Markdown instance. """
        md.registerExtension(self)
        md.preprocessors.register(ObsidianCommentPreprocessor(md, self.getConfigs()), 'ob_comment_block', 10)


class ObsidianCommentPreprocessor(Preprocessor):
    COMMENT_BLOCK_RE = re.compile(r'^%{2,}(?P<comment>.*?)%{2,}', re.MULTILINE | re.DOTALL)

    def __init__(self, md, config):
        super().__init__(md)
        self.config = config

    def run(self, lines):
        """ Match and store Obsidian block comment. """
        text = "\n".join(lines)
        while 1:
            m = self.COMMENT_BLOCK_RE.search(text)
            if m:
                comment = m.group('comment')
                # we may need this comment later.
                if not hasattr(self.md, 'ob_comments'):
                    self.md.ob_comments = []
                self.md.ob_comments.append(comment)
                if self.config['keep']:
                    c_begin = '<!-- obsidian comment begin -->'
                    c_end = '<!-- obsidian comment end -->'
                    content = f'{c_begin}\n{comment}\n{c_end}'
                else:
                    content = ''
                text = '{}\n{}\n{}'.format(text[:m.start()],
                                           content,
                                           text[m.end():])
            else:
                break
        return text.split("\n")


def makeExtension(**kwargs):  # noqa
    return ObsidianCommentExtension(**kwargs)
