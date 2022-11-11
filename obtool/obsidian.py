"""
# 关于 Obsidian 的对象接口都在这里

"""

import os
import sys
import json
import warnings
from collections import deque, defaultdict
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, parse_qsl
from typing import Optional, Union, List, Dict, Set, Iterable

try:
    from rich import print
except ImportError:
    pass

import click
import pyperclip

from obtool.obmark import ObMarkdown

"""
https://help.obsidian.md/Advanced+topics/Accepted+file+formats

Obsidian recognizes the following file formats right now:

Markdown files: md;
Image files: png, jpg, jpeg, gif, bmp, svg;
Audio files: mp3, webm, wav, m4a, ogg, 3gp, flac;
Video files: mp4, webm, ogv, mov, mkv;
PDF files: pdf.
"""

NOTE_FORMATS = ['.md']
IMAGE_FORMATS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg']
AUDIO_FORMATS = ['.mp3', '.wav', '.m4a', '.ogg', '.3gp', '.flac']
VIDEO_FORMATS = ['.mp4', '.webm', '.ogv', '.mov', '.mkv']


class ObsidianNotFound(Exception):
    pass


class VaultNotFound(Exception):
    pass


class DuplicatedNameWarning(UserWarning):
    pass


class UseMarkdownLinkWarning(UserWarning):
    pass


def get_obsidian_system_config():
    """获取
    https://help.obsidian.md/Advanced+topics/How+Obsidian+stores+data

    on Mac, it's /Users/username/Library/Application Support/obsidian,
    on Windows %APPDATA%/Obsidian,
    on Linux $XDG_CONFIG_HOME/Obsidian/ or ~/.config/Obsidian/

    :return:
    """
    app_conf_dir = Path(click.get_app_dir('obsidian'))
    if not app_conf_dir.is_dir():
        raise ObsidianNotFound('没有找到Obsidian的配置目录。')
    cfg = app_conf_dir.joinpath('obsidian.json')
    if not cfg.exists():
        raise FileNotFoundError(f'没有找到 Obsidian 配置文件: {cfg}')
    return cfg


@dataclass
class ObVaultState:
    path: Path
    ts: int
    is_open: bool


@dataclass
class ObURI:
    url: str
    action: str
    params: dict


def get_vaults_list() -> List[ObVaultState]:
    ob_cfg = get_obsidian_system_config()
    ob_vaults = json.loads(ob_cfg.read_text(encoding='utf-8'))['vaults']
    return [ObVaultState(Path(v['path']), v['ts'], v.get('open', False))
            for v in ob_vaults.values()]


def find_vault(name_or_path: Union[str, Path]) -> ObVaultState:
    """Locate vault by name or path
    """
    if isinstance(name_or_path, str):
        name_or_path = name_or_path.replace('\\', '/')
        if '/' in name_or_path:  # 字符串格式的路径
            name_or_path = Path(name_or_path).absolute()
        else:
            # 通过 Obsidian URL 解析出来的库只有名字
            pass
    if isinstance(name_or_path, Path) and not name_or_path.is_dir():
        raise VaultNotFound()
    for vault in get_vaults_list():
        vault_path = Path(vault.path)
        if isinstance(name_or_path, Path):
            if name_or_path == vault_path:
                return vault
        else:
            if vault_path.name == name_or_path:
                return vault
    raise VaultNotFound(f'{name_or_path}')


def parse_obsidian_url(ob_url: str):
    """从 Obsidian URL 中获取仓库名和笔记相对路径

    https://help.obsidian.md/Advanced+topics/Using+obsidian+URI
    """
    if not ob_url.startswith('obsidian://'):
        raise ValueError(f'格式错误，"{ob_url[:20]}" 不是以 obsidian:// 开头。')
    u = urlparse(ob_url)
    parsed = parse_qsl(urlparse(ob_url).query)
    return ObURI(ob_url, u.netloc, dict(parsed))


def get_uri_from_clip():
    txt = pyperclip.paste()
    if txt.startswith('obsidian://'):
        return parse_obsidian_url(txt)


class ObVault:
    """
    """
    ignores = ['.obsidian']

    @classmethod
    def open(cls, name_or_path):
        vs = find_vault(name_or_path)
        return cls(vs.path)

    def __init__(self, path: Path):
        self.path = path
        self.name = self.path.name
        self._settings = self.load_settings()
        self.use_markdown_links = self._settings.get('useMarkdownLinks', False)
        if self.use_markdown_links:
            warnings.warn("当前库的链接格式没有启用 Wiki 链接格式，笔记无法准确解析。",
                          UseMarkdownLinkWarning)

        self._folders: List[Path] = []
        self._files: List[Path] = []
        self._tags: Dict[str, Set['ObNote']] = defaultdict(set)
        self._walk()
        self._map: Dict[str, ObFile] = {}
        self._same_names: Dict[str, List[ObFile]] = {}
        self._build_map()

    def __repr__(self):
        return f'<ObVault: {self.name}>'

    def load_settings(self):
        ob_setting_path = self.path.joinpath('.obsidian')
        if not ob_setting_path.exists():
            raise ValueError(f'.obsidian not exists, it is not a obsidian vault?')
        with open(ob_setting_path.joinpath('app.json'), 'r', encoding='utf-8') as f:
            _settings = json.load(f)
        return _settings

    def _walk(self):
        _folders = []
        for p in self.path.glob('*'):
            if p.name.startswith('.'):
                continue
            if p.is_dir():
                _folders.append(p)
            elif p.is_file():
                self._files.append(p)
        _queue = deque(_folders)
        while _queue:
            f = _queue.popleft()
            for p in f.glob('*'):
                if p.name.startswith('.'):
                    continue
                if p.is_dir():
                    _queue.append(p)
                    _folders.append(p)
                elif p.is_file():
                    self._files.append(p)
        self._folders = _folders

    def _build_map(self):
        for p in self._files:
            if p.suffix == '.md':
                ob_file = ObNote(p, self)
            else:
                ob_file = ObFile(p, self)

            key = ob_file.name

            if key in self._same_names:
                # 已经有重名记录了，说明这至少是第 3 个重名的了
                self._map[ob_file.long_name] = ob_file
                self._same_names[key].append(ob_file)
            elif key not in self._map:
                # 没有重名也没有记录，完美
                self._map[key] = ob_file
            else:
                # 没有重名但是有记录，说明这是刚发现的重名
                exist = self._map.pop(key)
                self._same_names[key] = [exist, ob_file]
                self._map[exist.long_name] = exist
                self._map[ob_file.long_name] = ob_file

    @property
    def moc(self):
        """map of contents"""
        return self._map

    @property
    def same_names(self) -> Dict[str, List['ObFile']]:
        """返回所有的同名文件组成的字典

        key 是文件名(如果是 `.md` 则不含后缀,其它文件包含后缀)
        value 是同名文件路径列表

        如果同名文件是同类型文件,则意味着它们要靠相对路径来区分

        但是请注意,由于笔记文件的名字去掉了 `.md` 后缀,可能有这样一种特殊情况:

        笔记文件名是 `X.png.md`, 则 Key 值是 `X.png`
        某图片文件名也是 `X.png` 则 Key 值也是 `X.png`

        'X.png': [Path('E:/Vault/../X.png'), Path('E:/Vault/.../X.png.md')]
        这种情况如果不是特意构造可能不会出现,但是一旦出现,逻辑无法处理
        """
        return self._same_names

    def get_file(self, name: str) -> Union['ObFile', List['ObFile']]:
        """根据笔记名获取笔记文件

        这里的 name 主要是从链接 [[]] 解析出来的值
        """
        input_name = name
        if name in self._map:
            if name in self._same_names:
                # 此时表示根目录下有重名笔记的情况出现，应该给与一定的提示
                # _sames = self.same_names[name]
                # print(f'{name} 还有同名笔记：{_sames}')
                pass
            return self._map[name]

        if name in self._same_names:
            # 直接报错貌似有点不够友好，返回重名列表？
            # raise ValueError(f'有重名,请用相对路径查找. {self._same_names[name]}')
            return self._same_names[name]

        if '/' in name:  # 相对路径
            # 注意，相对仓库的根路径
            pth = Path(name)
            if pth.is_absolute():
                try:
                    pth = pth.relative_to(self.path)
                except ValueError:
                    raise ValueError(f'仓库外的路径：{input_name}')
            pth = self.path.joinpath(pth).resolve()
            try:
                pth.relative_to(self.path)
            except ValueError:
                raise ValueError(f'仓库外的路径：{input_name}')

            name = pth.name
            p = self._map.get(name)
            if p:
                return p
            if name in self._same_names:
                # 确实重名了
                for e in self._same_names[name]:
                    #
                    if e.parent == pth.parent:
                        return e
            # 未创建，并且使用了相对路径
            return ObNote(None, self, input_name)
        # 所有找不到的都是未创建的笔记
        # Obsidian 中，
        # 如果名字没有带路径，则自动创建到笔记目录下，例如：
        #    假如笔记目录是 `Notes`，[[a_new_note]]
        #    创建到 `Notes/a_new_note.md`
        # 如果名字带有路径，则路径是相对仓库根目录来创建
        #    [[new_folder/new_note]]
        #    创建到 `new_folder/new_note.md`
        # 不存在的文件夹也是自动创建
        return ObNote(None, self, input_name)

    def iter_files(self, file_type='') -> Iterable["ObFile"]:
        """遍历所有笔记(.md)"""
        for ob_file in self._map.values():
            if (not file_type and not isinstance(ob_file, list)) \
                    or getattr(ob_file, 'file_type', None) == file_type \
                    or getattr(ob_file, 'suffix', None) == file_type:
                yield ob_file
            elif isinstance(ob_file, list):
                for f in ob_file:
                    if (not file_type) \
                            or getattr(f, 'file_type', None) == file_type \
                            or getattr(f, 'suffix', None) == file_type:
                        yield f

    def iter_notes(self) -> Iterable["ObNote"]:
        yield from self.iter_files('note')

    @property
    def notes(self):
        return list(self.iter_notes())

    @property
    def folders(self):
        return self._folders

    @property
    def files(self):
        return self._files

    @property
    def tags(self):
        return self._tags

    def count_by_suffix(self):
        """按后缀统计文件数量"""
        g = defaultdict(int)
        for file in self.iter_files():
            g[file.suffix] += 1
        return g


class ObFile:
    """Obsidian 笔记库中的文件"""

    def __init__(self, path: Optional[Path], vault: ObVault, name: str = ''):
        if not path and not name:
            raise ValueError(f'path 和 name 不可以都为空。')
        if path is None:
            path = vault.path.joinpath(name + '.md')
        self.path = path
        self.vault = vault
        self._input_name = name
        if self.exists:
            self.name = self._short_name()
        else:
            self.name = self._input_name

    def _short_name(self):
        if self.path.suffix == '.md':
            return self.path.stem
        else:
            return self.path.name

    @property
    def long_name(self):
        rel_path = self.path.relative_to(self.vault.path).as_posix()
        # return rel_path.removesuffix('.md')   # need python 3.9
        if rel_path.endswith('.md'):
            return rel_path[:-3]
        else:
            return rel_path

    def __repr__(self):
        info = self.path.as_posix()
        if not self.exists:
            info += ' (未创建)'
        return f'<{self.__class__.__name__}: {self.name} [{info}]>'

    @property
    def parent(self):
        # FIXME: 这里缺省应该是笔记配置路径
        return self.path.parent if self.path else self.vault.path

    @property
    def exists(self):
        return self.path and self.path.is_file()

    @property
    def suffix(self):
        # 还不存在的文件默认是笔记,所以后缀是 `.md`
        return self.path.suffix if self.path else '.md'

    @property
    def file_type(self):
        if self.suffix == '.md':
            return 'note'
        elif self.suffix in IMAGE_FORMATS:
            return 'image'
        elif self.suffix == '.pdf':
            return 'pdf'
        elif self.suffix in VIDEO_FORMATS:
            return 'video'
        elif self.suffix in AUDIO_FORMATS:
            return 'audio'
        else:
            return self.suffix


class ObNote(ObFile):
    def __init__(self, path: Optional[Path], vault: ObVault, name=None):
        super().__init__(path, vault, name)
        self._marks = None
        self._parsed = False

    def parse(self):
        if self.vault.use_markdown_links:
            raise ValueError("Obsidian 仓库的链接设置没有开启 Wiki 链接而是使用标准 MD 语法。")
        if self.exists:
            marks = self._marks = ObMarkdown().parse(self.path)
            tags = marks.tags[:]
            tags_in_meta = marks.meta.get('tags', [])
            if isinstance(tags_in_meta, str):
                tags_in_meta = tags_in_meta.split(',')
            tags.extend(tags_in_meta)

            for tag in tags:
                self.vault.tags[tag].add(self)
                if '/' in tag:
                    i = 0
                    while True:
                        i = tag.find('/', i)
                        if i < 0:
                            break
                        self.vault.tags[tag[:i]].add(self)
                        i += 1

    def info(self):
        return self._marks


def main():
    print(get_vaults_list())


if __name__ == '__main__':
    main()
