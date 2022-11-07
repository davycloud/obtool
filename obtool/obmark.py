"""解析 Obsidian 的 Markdown 文件
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path
import frontmatter
from markdown import Markdown

from obtool.mdextensions.oblinks import ObsidianLinkExtension
from obtool.mdextensions.obcomments import ObsidianCommentExtension
from obtool.mdextensions.obinlinecomment import ObsidianInlineCommentExtension
from obtool.mdextensions.obtags import ObsidianTagExtension
from obtool.mdextensions.obheader import ObsidianHeaderExtension
from obtool.mdextensions.obautolink import ObsidianAutoLinkExtension


@dataclass
class ObMarks:
    path: Path
    content: str = field(repr=False)    # 正文内容
    meta: dict          # Frontmatter 元数据
    tags: list          # 标签（只包含正文中的）
    links: list         # 内部链接
    # blocks: list        # 块
    comments: list      # 注释内容
    html: str = field(repr=False)


@dataclass
class ObLink:
    """表示 Obsidian 的链接

    基础链接
    [[note_name]]

    链接标题
    [[note_name#topic_a]]

    别名
    [[note_name|another_name]]

    块链接
    [[note_name#^block_id]]


    """
    target: str
    alias: str
    section: str
    block: str
    image_size: str
    embedded: bool


def parse_link(link):
    """

    A full link could be: [[target#block|alias]]
    :param link:
    :return:
    """
    block = alias = ''
    if '|' in link:
        target, alias = link.split('|', maxsplit=1)
    else:
        target = link
    if '#' in target:
        target, block = target.split('#', maxsplit=1)
        if not alias:
            alias = block
    return target, block, alias


class ObMarkdown:

    def __init__(self, ignore_comment=False):
        self.extensions = ['extra',
                           ObsidianTagExtension(),
                           ObsidianLinkExtension(),
                           ObsidianCommentExtension(keep=not ignore_comment),
                           ObsidianHeaderExtension(),
                           ObsidianAutoLinkExtension(),
                           ObsidianInlineCommentExtension()]

    def parse(self, md_file):
        if not isinstance(md_file, Path):
            md_file = Path(md_file)
        if not (md_file.exists() and md_file.is_file()):
            raise ValueError(f'File {md_file} not exists.')
        with open(md_file, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            md = Markdown(extensions=self.extensions)
            html = md.convert(post.content)
            ob_comments = getattr(md, 'ob_comments', [])
            ob_links = getattr(md, 'ob_links', [])
            ob_tags = getattr(md, 'ob_tags', [])
            # if ob_comments:
            #     print(ob_comments)

        return ObMarks(md_file, post.content, post.metadata,
                       ob_tags, ob_links, ob_comments, html)


if __name__ == '__main__':
    parser = ObMarkdown()
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.is_file() and p.suffix == '.md':
            print(parser.parse(p))
