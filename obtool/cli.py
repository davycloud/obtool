from typing import Optional
import pickle
from pathlib import Path

# import click
import rich_click as click

from obtool.obsidian import get_vaults_list, ObVault, get_uri_from_clip, ObFile
from obtool import views


APP_DIR = Path(click.get_app_dir('obtool'))
if not APP_DIR.exists():
    APP_DIR.mkdir()


def save_cache(vault):
    pickle_file = APP_DIR.joinpath(f'{vault.name}.pickle')
    with open(pickle_file, 'wb') as f:
        # Pickle the 'data' dictionary using the highest protocol available.
        pickle.dump(vault, f, pickle.HIGHEST_PROTOCOL)


def clear_cache(vault_name: str):
    pickle_file = APP_DIR.joinpath(f'{vault_name}.pickle')
    if pickle_file.exists():
        pickle_file.unlink()


def load_cache(vault_name: str):
    pickle_file = APP_DIR.joinpath(f'{vault_name}.pickle')
    if pickle_file.exists():
        with open(pickle_file, 'rb') as f:
            return pickle.load(f)


@click.group()
@click.option('--vault', 'vault_name', default=None, required=False, help='仓库名称')
@click.option('--cache', 'use_cache', is_flag=True, help='是否使用缓存来避免重复解析')
@click.pass_context
def cli(click_ctx, vault_name, use_cache):
    """
    快速分析 Obsidian 笔记仓库
    """
    click_ctx.ensure_object(dict)
    uri = get_uri_from_clip()
    if uri and 'vault' in uri.params:
        vault_from_clip = uri.params['vault']
        file_from_clip = uri.params.get('file')
        click.echo(f'📋 检测到剪切板中的 Obsidian 链接')
        click.echo(f'动作：  {uri.action}')
        click.echo(f'仓库：  {vault_from_clip}')
        click.echo(f'文件：  {file_from_clip}')

        if vault_name and vault_name != vault_from_clip:
            click.echo(f'--vault 选项指定的仓库和剪切板中的不一致，忽略剪切板中内容。')
        elif not vault_name:
            click.echo(f'未指定仓库，将直接使用以上信息： {vault_from_clip}')
            vault_name = vault_from_clip
    if vault_name:
        if not use_cache:
            clear_cache(vault_name)
            v = ObVault.open(vault_name)
            views.setup_vault(v)
        else:
            v = load_cache(vault_name) or ObVault.open(vault_name)

        click_ctx.obj['vault'] = v
        click_ctx.obj['use_cache'] = use_cache
        if uri and 'file' in uri.params:
            click_ctx.obj['file'] = v.get_file(uri.params['file'])


@click.command()
@click.option('--suffix', '-s', default='', required=False, help='按文件名后缀查询，如 .png')
@click.option('-a', '--all', 'show_all', is_flag=True, help='当展示仓库列表时，显示更多内容；当展示仓库内文件时，显示全部文件')
@click.option('-l', '--long', 'long_name', is_flag=True, help='是否展示笔记文件的相对路径')
@click.option('--tag', '-t', 'tags', multiple=True, help='按标签查询，可多次使用')
@click.option('--or-tag', 'union_result', is_flag=True, help='默认使用多个标签查询时，显示的是交集，使用该选项显示并集')
@click.pass_obj
def ls(ctx, suffix, show_all, long_name, tags, union_result: bool):
    """显示笔记（库）列表

    未使用 --vault 指定笔记库时，列出笔记仓库；

    使用 --vault 指定笔记库时，列出库中的文件，缺省情况下只列出所有笔记（即 .md 文件）
    """
    vault = ctx.get('vault')
    if vault is None:
        views.display_vault_list(get_vaults_list(), show_detail=show_all)
    else:
        if show_all or suffix:
            if tags:
                print('--tag 选项在显示所有文件时无效，忽略。')
            data = vault.iter_files(file_type=suffix)
        elif tags:
            vault.ensure_all_parsed()
            op = 'OR' if union_result else 'AND'
            data = vault.find_notes_by_tags(tags, op=op)
        else:
            data = vault.iter_notes()

        if not long_name:
            views.display_filenames(f.name for f in data)

    if ctx.get('use_cache', False):
        save_cache(vault)


@click.command()
@click.option('--name', default='', required=False, help='笔记/文件名称')
@click.option('--show-same-names', is_flag=True)
@click.option('-a', '--all', 'parse_all', is_flag=True)
@click.pass_obj
def info(ctx, name, show_same_names, parse_all):
    vault: Optional[ObVault] = ctx.get('vault')
    if vault is None:
        click.secho(f'使用 --vault 指定仓库', fg='red')
        return
    if not name:
        show_vault_info(vault, show_same_names, parse_all)
    else:
        show_file_info(vault, name, parse_all)

    file: Optional[ObFile] = ctx.get('file')
    if file:
        print(file)

    if ctx.get('use_cache', False):
        save_cache(vault)


def show_vault_info(vault, show_same_names, parse_all):
    click.echo(f'💼 仓库： {vault.name}')
    print(f'📁 文件夹数量： {len(vault.folders)}')
    print(f'📄 总文件数量： {len(vault.files)}')
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
        vault.ensure_all_parsed()
        # parse_vault(vault)
        # views.parse_vault(vault)
        print(f'🏷 标签数量：{len(vault.tags)}')
        tags = list(vault.tags.items())
        tags.sort(key=lambda t: len(t[1]), reverse=True)
        for tag, tagged_notes in tags:
            print(f'  {tag}   {len(tagged_notes)}')
            for note in tagged_notes:
                print(f'        {note.name}')


def show_file_info(vault, name, parse_all):
    ob_file = vault.get_file(name)
    if not ob_file.exists:
        print('该文件还不存在')
        return

    # if parse_all:
    #     parse_vault(vault)
    print(ob_file.name)
    print(ob_file.path)
    if ob_file.is_note():
        ob_file.parse()
        print(ob_file.tags)
        print(ob_file.links)


@click.command()
def cmd():
    import sys
    from obtool.cmdapp import App
    c = App()
    sys.exit(c.cmdloop())


cli.add_command(ls)
cli.add_command(info)
cli.add_command(cmd)


def click_main():
    import sys
    if len(sys.argv) == 1 or '--help' in sys.argv:
        # don't show too much ...
        views.display_banner()
    cli()



if __name__ == '__main__':
    click_main()
