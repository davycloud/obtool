import functools
from typing import List, Iterable

from collections import OrderedDict

from rich.console import Console
from rich.text import Text
from rich.columns import Columns
from rich.progress import track

from .banner import print_banner
from .obsidian import ObVaultState, ObVault, ObFile, ObNote

console = Console()


def display_banner():
    """显示 Banner"""
    print_banner(console)


def display_vault_list(vault_list: Iterable[ObVaultState], show_detail=False):
    """显示笔记仓库列表"""
    for v in vault_list:
        vault_name = v.path.name
        vault_path = v.path.parent
        text = Text()
        text.append(f'{vault_name}', style="bold cyan")
        text.append(f'\n    📁 {vault_path}')
        if show_detail:
            if v.is_open:
                text.append(f'\n    🟢 已打开')
            else:
                text.append(f'\n    🔴 已关闭')
            created_time = v.created_time.isoformat(sep=' ')
            text.append(f'\n    📅 {created_time}')
        console.print(text)


def display_filenames(file_names: Iterable[str]):
    """展示文件名"""
    columns = Columns(file_names, equal=True, expand=True)
    console.print(columns)


def display_file_details(files):
    """展示文件详情"""
    pass


def display_vault_info(vault: ObVault, show_same_names, parse_all):
    info_dict = OrderedDict()
    info_dict['💼 仓库名称'] = vault.name
    info_dict['📁 文件夹数量'] = len(vault.folders)
    info_dict['📄 总文件数量'] = len(vault.files)
    info_dict['📝 总笔记数量'] = len(vault.notes)

    count_by_suffix = vault.count_by_suffix()
    for suffix, count in count_by_suffix.items():
        print(f' {suffix}：  {count}')
    same_names_count = len(vault.same_names)
    print(f'有 {same_names_count} 个文件重名。')
    if show_same_names:
        for name, files in vault.same_names.items():
            print(f'{name}: ')
            for f in files:
                print(f'  {f.path.as_posix()}')
    if parse_all:
        # parse_vault(vault)
        print(f'🏷 标签数量：{len(vault.tags)}')
        tags = list(vault.tags.items())
        tags.sort(key=lambda t: len(t[1]), reverse=True)
        for tag, tagged_notes in tags:
            print(f'  {tag}   {len(tagged_notes)}')
            for note in tagged_notes:
                print(f'        {note.name}')


def setup_vault(vault: ObVault):
    vault.progress_bar = functools.partial(track, description='解析中...')


# def parse_vault(vault: ObVault):
#     """解析整个仓库"""
#     # TODO: 应该让 vault 自己判断什么时候该解析所有
#     if not vault.all_parsed:
#         console.print('解析所有笔记，如果数量较多可能需要花费几秒钟。')
#         vault.parse_all(functools.partial(track, description='解析中...'))
    # for note in track(vault.notes, description='解析中...'):
    #     note.parse()
