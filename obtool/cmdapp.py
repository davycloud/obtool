import sys
from typing import List, Optional, Any

import cmd2
from cmd2 import Cmd2ArgumentParser, with_argparser, with_category, Fg, ansi

from obtool.obsidian import get_vaults_list, ObVault, get_uri_from_clip, ObFile
from obtool import views
from obtool.banner import get_banner


from rich import print, get_console


class App(cmd2.Cmd):
    """ Obsidian 笔记助手"""
    def __init__(self):
        super().__init__()
        self.name = 'ObTool'
        self.console = get_console()
        self.default_category = '系统命令'
        self.vault: Optional[ObVault] = None
        self.vault_list = get_vaults_list()
        self._vault_cache = {}
        self.aliases['cls'] = '!cls'
        self.aliases['exit'] = 'quit'

    def poutput(self, msg: Any = '', *, end: str = '\n') -> None:
        if isinstance(msg, str) and ansi.ANSI_STYLE_RE.match(msg):
            super().poutput(msg, end=end)
        else:
            self.console.print(msg, end=end)

    def preloop(self) -> None:
        self.console.print(get_banner())

    @property
    def prompt(self):
        appname = ansi.style(self.name, fg=Fg.MAGENTA)
        arrow = ansi.style('> ', fg=Fg.WHITE)
        if not self.vault:
            return appname + arrow
        else:
            vault_name = ansi.style(f' [{self.vault.name}]', fg=Fg.CYAN)
            return appname + vault_name + arrow

    @staticmethod
    def _kwargs(args):
        kwargs = vars(args)
        kwargs.pop('cmd2_statement')
        kwargs.pop('cmd2_handler')
        return kwargs

    ls_parser = Cmd2ArgumentParser()
    ls_parser.add_argument('-a', '--all', action='store_true', dest='show_all', help='展示详情')
    ls_parser.add_argument('-s', '--suffix', help='指定文件后缀，如 .png')
    ls_parser.add_argument('-t', '--tag', action='append', dest='tags', help='指定笔记标签，可多次使用')
    ls_parser.add_argument('folder', nargs='?', help='指定文件夹')

    @with_argparser(ls_parser)
    @with_category('ObTool 命令')
    def do_ls(self, args):
        """显示笔记（库）列表
        - 未指定笔记仓库时，列出笔记仓库；
        - 指定笔记库时，列出库中的文件，缺省情况下只列出所有笔记（即 .md 文件）
        """
        vault = self.vault
        if vault is None:
            views.display_vault_list(self.vault_list,
                                     show_detail=args.show_all)
        else:
            self.list_vault_files(**self._kwargs(args))

    def list_vault_files(self, show_all=False, suffix=None, tags=None, **kwargs):
        if not self.vault:
            return
        if show_all or suffix:
            if tags:
                print('--tag 选项在显示所有文件时无效，忽略。')
            data = self.vault.iter_files(file_type=suffix)
        elif tags:
            self.vault.ensure_all_parsed()
            # op = 'OR' if union_result else 'AND'
            op = 'AND'
            data = self.vault.find_notes_by_tags(tags, op=op)
        else:
            data = self.vault.iter_notes()

        views.display_filenames(f.name for f in data)

    def get_vault(self, vault_name):
        if vault_name not in self._vault_cache:
            vault = ObVault.open(vault_name)
            views.setup_vault(vault)
            self._vault_cache[vault_name] = vault
        return self._vault_cache[vault_name]

    vault_parser = Cmd2ArgumentParser()
    vault_parser.add_argument('vault_name', nargs='?', help='仓库名称')

    @with_argparser(vault_parser)
    @with_category('ObTool 命令')
    def do_vault(self, args):
        """选择一个笔记仓库"""
        vault_name_list = [v.path.name for v in self.vault_list]
        vault_name = args.vault_name
        if not vault_name:
            vault_name = self.select(vault_name_list, '请选择：')
        if vault_name not in vault_name_list:
            self.poutput(f'笔记仓库 {vault_name} 不存在。')
            return

        self.vault = self.get_vault(vault_name)

    def complete_vault(self, text, line, begidx, endidx) -> List[str]:
        """Completion function for do_vault"""
        vault_name_list = [v.path.name for v in self.vault_list]
        return self.basic_complete(text, line, begidx, endidx,
                                   match_against=vault_name_list)

    def note_names(self) -> List[str]:
        if not self.vault:
            return []
        return list(self.vault.moc.keys())

    info_parser = Cmd2ArgumentParser()
    info_parser.add_argument('--name', nargs='?', choices_provider=note_names, help='笔记/文件名称')
    info_parser.add_argument('--same-names', action='store_true', help='显示同名文件')
    info_parser.add_argument('--tags', action='store_true', help='统计标签数量')
    info_parser.add_argument('--back-links', action='store_true', help='统计反链（指定文件名有效）')

    @with_argparser(info_parser)
    @with_category('ObTool 命令')
    def do_stat(self, args):
        """统计笔记数量"""
        if self.vault is None:
            print(f'先使用 vault 指定仓库')
            return
        if not args.name:
            views.display_vault_stat(self.vault,
                                     show_tags=args.tags,
                                     show_same_names=args.same_names)
        else:
            views.display_file_stat(self.vault,
                                    name=args.name,
                                    show_back_links=args.back_links
                                    )


def main():
    c = App()
    sys.exit(c.cmdloop())


if __name__ == '__main__':
    main()
