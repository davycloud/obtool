"""
ObsidianTags Extension for Python-Markdown
======================================

"""

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
import xml.etree.ElementTree as etree


def build_url(label, base, end):
    return '{}{}{}'.format(base, label, end)


class ObsidianTagExtension(Extension):

    def __init__(self, **kwargs):
        self.config = {
            'base_url': ['/tags/', 'String to append to beginning or URL.'],
            'end_url': ['/', 'String to append to end of URL.'],
            'html_class': ['tag', 'CSS hook. Leave blank for none.'],
            'build_url': [build_url, 'Callable formats URL from label.'],
        }

        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        self.md = md
        TAG_RE = r'\s?#([^#\s]+)'
        obsidian_tag_pattern = ObTagsInlineProcessor(TAG_RE, self.getConfigs())
        obsidian_tag_pattern.md = md
        md.inlinePatterns.register(obsidian_tag_pattern, 'ob_tag', 40)


class ObTagsInlineProcessor(InlineProcessor):
    def __init__(self, pattern, config):
        super().__init__(pattern)
        self.config = config

    def handleMatch(self, m, data):
        label = m.group(1).strip()
        if label:
            base_url, end_url, html_class = self._get_config()
            if '/' in label:
                # TODO: 也许不需要处理？
                pass
            url = self.config['build_url'](label, base_url, end_url)
            a = etree.Element('a')
            a.text = label
            a.set('href', url)
            if html_class:
                a.set('class', html_class)
            if m.group(0).startswith('!'):
                a.set('embed', 'true')
            if not hasattr(self.md, 'ob_tags'):
                self.md.ob_tags = []
            self.md.ob_tags.append(label)
        else:
            a = ''
        return a, m.start(0), m.end(0)

    def _get_config(self):
        """ Return meta data or config data. """
        base_url = self.config['base_url']
        end_url = self.config['end_url']
        html_class = self.config['html_class']
        return base_url, end_url, html_class


def makeExtension(**kwargs):  # pragma: no cover
    return ObsidianTagExtension(**kwargs)
