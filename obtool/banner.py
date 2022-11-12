from rich.align import Align
from rich.panel import Panel
from rich.text import Text

from os import get_terminal_size
from platform import system


def get_terminal_width() -> int:
    try:
        width, _ = get_terminal_size()
    except OSError:
        width = 80

    if system().lower() == "windows":
        width -= 1

    return width


# https://textpaint.net/
def print_banner(console) -> None:
    width = get_terminal_width()
    height = 8
    banner = """\
╔═══╗╔╗  ╔════╗        ╔╗
║╔═╗║║║  ║╔╗╔╗║        ║║
║║ ║║║╚═╗╚╝║║╚╝╔══╗╔══╗║║
║║ ║║║╔╗║  ║║  ║╔╗║║╔╗║║║
║╚═╝║║╚╝║ ╔╝╚╗ ║╚╝║║╚╝║║╚╗
╚═══╝╚══╝ ╚══╝ ╚══╝╚══╝╚═╝
"""

    panel = Panel(
        Align(
            Text(banner, justify="center", style="#7b67d3"),
            vertical="middle",
            align="center",
        ),
        width=width,
        height=height,
        subtitle="by davy (https://davycloud.com)",
    )
    console.print(panel)


if __name__ == '__main__':
    from rich.console import Console
    print_banner(Console())
