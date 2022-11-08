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
from typing import Optional, Union, List, Dict

try:
    from rich import print
except ImportError:
    pass

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
    if sys.platform == 'win32':
        cfg = Path(os.environ['APPDATA']).joinpath('obsidian/obsidian.json')
    elif sys.platform == 'linux':
        cfg = Path(os.environ['HOME']).joinpath('.config/Obsidian/obsidian.json')
    elif sys.platform == 'darwin':
        cfg = Path(os.environ['HOME']).joinpath('Library/Application Support/obsidian/obsidian.json')
    else:
        raise NotImplemented(f'当前操作系统不支持')

    if not cfg.exists():
        raise FileNotFoundError(f'没有找到 Obsidian 配置文件: {cfg}')
    return cfg


@dataclass
class ObVaultStat:
    path: Path
    ts: int
    is_open: bool


@dataclass
class ObURI:
    action: str
    params: dict


def get_vaults_list() -> List[ObVaultStat]:
    ob_cfg = get_obsidian_system_config()
    ob_vaults = json.loads(ob_cfg.read_text(encoding='utf-8'))['vaults']
    return [ObVaultStat(Path(v['path']), v['ts'], v.get('open', False))
            for v in ob_vaults.values()]


def find_vault(name_or_path: Union[str, Path]) -> ObVaultStat:
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
    return ObURI(u.path, dict(parsed))


class Obsidian:
    """Obsidian App"""

    @staticmethod
    def open_vault(name: str):
        pass


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
        self._walk()
        print(len(self._files))
        self._map: Dict[str, Union[List[ObFile], ObFile]] = {}
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
                key = p.stem
                ob_file = ObNote(key, p, self)
            else:
                key = p.name
                ob_file = ObFile(key, p, self)

            if key not in self._map:
                self._map[key] = ob_file
            else:
                # warnings.warn("重复文件", DuplicatedNameWarning)
                exist = self._map[key]
                if not isinstance(exist, list):
                    self._map[key] = [exist]
                self._map[key].append(ob_file)

    @property
    def same_names(self) -> Dict[str, List[Path]]:
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
        same_names_map = {k: v for k, v in self._map.items() if isinstance(v, list)}
        for p_list in same_names_map.values():
            names = set([p.name for p in p_list])
            assert len(names) == 1, f"无法处理的文件名冲突: {p_list}"
        return same_names_map

    def get_ob_file(self, name: str):
        """根据笔记名获取笔记文件

        这里的 name 主要是从链接 [[]] 解析出来的值
        """
        if name in self._map:  # pure name, without .md suffix
            p = self._map[name]
            if isinstance(p, list):
                raise ValueError(f'有重名,请用相对路径查找. {p}')
            return p
        elif '/' in name:  # 相对路径
            # 这里的问题是无法判断它是笔记还是其它文件
            # 例如笔记 `x.png.md` 的名字是 `x.png`
            # 所以不能直接拼路径,还是得查一次
            folder, name = name.rsplit('/', 1)

            # 注意, 出现相对路径不代表一定有重名,
            # 有两种可能:
            # 1. 链接创建的时候是重名的,但是重名文件后来没有了,链接没有同步更新
            # 2. 有人偏爱设置了 基于当前笔记的相对路径
            # 对第 2 种情况,如果没有重名也是可以正确返回的,但是一旦重名就乱套了
            # 必须提醒注意
            p = self._map.get(name)
            if isinstance(p, ObFile):
                return p
            elif isinstance(p, list):
                # 确实重名了
                parent = self.path.joinpath(folder)
                for e in p:
                    if e.parent == parent:
                        return e
                else:
                    # 不可能出现
                    raise ValueError("")
        return ObNote(name, None, self)

    def iter_files(self, file_type=''):
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

    def iter_notes(self):
        yield from self.iter_files('note')

    @property
    def notes(self):
        return list(self.iter_notes())

    def info(self):
        print(f'文件夹数量：{len(self._folders)}')
        print(f'文件数量：{len(self._files)}')

        group_by_suffix = defaultdict(int)
        for file in self.iter_files():
            group_by_suffix[file.suffix] += 1
        print(group_by_suffix)

        duplicated = self.same_names
        if duplicated:
            print(f'存在重名的文件：\n{duplicated}')


class ObFile:
    """Obsidian 笔记库中的文件"""

    def __init__(self, name, path: Optional[Path], vault: ObVault):
        self.path = path
        self.vault = vault
        self.name = name

    def __repr__(self):
        if self.exists:
            info = self.path.as_posix()
        else:
            info = '未创建'
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
    def __init__(self, name, path: Optional[Path], vault: ObVault):
        super().__init__(name, path, vault)
        self._marks = None

    def parse(self):
        if self.vault.use_markdown_links:
            raise ValueError("Obsidian 仓库的链接设置没有开启 Wiki 链接而是使用标准 MD 语法。")
        if self.exists:
            self._marks = ObMarkdown().parse(self.path)

    def info(self):
        return self._marks


def main():
    print(get_vaults_list())


if __name__ == '__main__':
    main()
