"""
ObsidianLinks Extension for Python-Markdown
===========================================

Code are basically copied from WikiLinks extension.

Converts [[WikiLinks]] to relative links.

See <https://Python-Markdown.github.io/extensions/wikilinks>
for documentation.

Original code Copyright [Waylan Limberg](http://achinghead.com/).

All changes Copyright The Python Markdown Project

License: [BSD](https://opensource.org/licenses/bsd-license.php)

"""

from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.util import STX, ETX, INLINE_PLACEHOLDER_PREFIX
import xml.etree.ElementTree as etree
import re


def build_url(label, base, end):
    """ Build an url from the label, a base, and an end. """
    clean_label = re.sub(r'([ ]+_)|(_[ ]+)|([ ]+)', '_', label)
    return '{}{}{}'.format(base, clean_label, end)


class ObsidianLinkExtension(Extension):

    def __init__(self, **kwargs):
        self.config = {
            'base_url': ['/', 'String to append to beginning or URL.'],
            'end_url': ['/', 'String to append to end of URL.'],
            'html_class': ['link', 'CSS hook. Leave blank for none.'],
            'build_url': [build_url, 'Callable formats URL from label.'],
        }

        super().__init__(**kwargs)

    def extendMarkdown(self, md):
        self.md = md
        # append to end of inline patterns
        # WIKILINK_RE = r'!?\[\[([\w0-9_ -\|]+)\]\]'
        WIKILINK_RE = r'!?\[\[(.*?)\]\]'
        wikilinkPattern = ObLinksInlineProcessor(WIKILINK_RE, self.getConfigs())
        wikilinkPattern.md = md
        md.inlinePatterns.register(wikilinkPattern, 'ob_link', 175)


class ObLinksInlineProcessor(InlineProcessor):
    def __init__(self, pattern, config):
        super().__init__(pattern)
        self.config = config

    def handleMatch(self, m, data):
        if m.group(1).strip():
            base_url, end_url, html_class = self._getMeta()
            label = m.group(1).strip()
            # [target#block|alias]
            block = alias = ''
            if '|' in label:
                target, alias = label.split('|', maxsplit=1)
            elif INLINE_PLACEHOLDER_PREFIX in label:  # has escaped \|
                target = label.split(STX)[0]
                alias = label.split(ETX)[-1]
                label = f'{target}|{alias}'
            else:
                target = label
            if '#' in target:
                target, block = target.split('#', maxsplit=1)
                if not alias:
                    alias = block
            if block:
                # TODO: url add escaped block
                end_url = end_url + '#' + block
            url = self.config['build_url'](target, base_url, end_url)
            a = etree.Element('a')
            if alias:
                a.text = alias
            else:
                a.text = target
            a.set('href', url)
            if html_class:
                a.set('class', html_class)
            if m.group(0).startswith('!'):
                a.set('embed', 'true')
            if not hasattr(self.md, 'ob_links'):
                self.md.ob_links = []
            self.md.ob_links.append(label)
        else:
            a = ''
        return a, m.start(0), m.end(0)

    def _getMeta(self):
        """ Return meta data or config data. """
        base_url = self.config['base_url']
        end_url = self.config['end_url']
        html_class = self.config['html_class']
        if hasattr(self.md, 'Meta'):
            if 'wiki_base_url' in self.md.Meta:
                base_url = self.md.Meta['wiki_base_url'][0]
            if 'wiki_end_url' in self.md.Meta:
                end_url = self.md.Meta['wiki_end_url'][0]
            if 'wiki_html_class' in self.md.Meta:
                html_class = self.md.Meta['wiki_html_class'][0]
        return base_url, end_url, html_class


def makeExtension(**kwargs):  # pragma: no cover
    return ObsidianLinkExtension(**kwargs)
