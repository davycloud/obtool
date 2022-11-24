import functools
from typing import List, Iterable, cast

from rich import get_console, print
from rich.text import Text
from rich.columns import Columns
from rich.table import Table
from rich.progress import track

from .banner import print_banner
from .obsidian import ObVaultState, ObVault, ObFile, ObNote

console = get_console()


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


def display_file_stat(vault: ObVault, name: str, show_back_links=False):
    """展示文件详情"""
    print()
    ob_file = vault.get_file(name)
    if not ob_file.exists:
        print('该文件还不存在。')
        return
    table = Table(title="", box=None,
                  show_header=False, show_edge=False)
    table.add_row('名称', str(ob_file.name))
    table.add_row('路径', str(ob_file.path))
    if ob_file.is_note():
        ob_file = cast(ObNote, ob_file)
        ob_file.parse()
        table.add_row('标签', ','.join(ob_file.tags))
        table.add_row('链接', '\n'.join(ob_file.links))
        if show_back_links:
            vault.ensure_all_parsed()
            back_links = [note.name for note in vault.get_back_links(name)]
            table.add_row('反链', '\n'.join(back_links))
    console.print(table)


def display_vault_stat(vault: ObVault, show_tags=False, show_same_names=False):
    print()
    table = Table(title="", box=None,
                  show_header=False, show_edge=False)
    table.add_column()
    table.add_column(justify="right", style="cyan")
    table.add_row('💼 仓库名称', str(vault.name))
    table.add_row('📁 文件夹数量', str(len(vault.folders)))
    table.add_row('📄 总文件数量', str(len(vault.files)))
    table.add_row('📝 总笔记数量', str(len(vault.notes)))
    console.print(table)

    print()
    table = Table(title="按文件后缀统计数量", box=None, show_edge=False)
    table.add_column("文件后缀")
    table.add_column("文件数量", justify="right", style="cyan")
    count_by_suffix = vault.count_by_suffix()
    for suffix, count in count_by_suffix.items():
        table.add_row(f' {suffix}', f'{count}')
    console.print(table)

    print()
    same_names_count = len(vault.same_names)
    if same_names_count > 0:
        print(f'有 {same_names_count} 个文件重名。')
        if show_same_names:
            for name, files in vault.same_names.items():
                print(f'{name}: ')
                for f in files:
                    print(f'  {f.path.as_posix()}')
        else:
            print(f'使用 [cyan]--show-same-names[/] 选项显示重名文件信息\n')
    else:
        print('没有重名文件。\n')

    if show_tags:
        vault.ensure_all_parsed()

        print(f'🏷 标签数量：{len(vault.tags)}')
        tags_table = Table(title="", show_edge=False)
        tags_table.add_column("标签")
        tags_table.add_column("数量", justify="center", style="cyan")
        tags = list(vault.tags.items())
        tags.sort(key=lambda t: len(t[1]), reverse=True)
        for tag, tagged_notes in tags:
            tags_table.add_row(f'{tag}', f'{len(tagged_notes)}')
        print(tags_table)


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
