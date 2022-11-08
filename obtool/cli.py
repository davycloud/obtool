from typing import Optional

import click

from obtool.obsidian import get_vaults_list, ObVault


@click.group()
@click.option('--vault', default=None, required=False)
@click.pass_context
def cli(ctx, vault):
    if vault:
        ctx.obj = ObVault.open(vault)


@click.command()
@click.pass_obj
def ls(vault: Optional[ObVault]):
    if vault is None:
        for v in get_vaults_list():
            vault_name = v.path.name
            vault_path = v.path.parent
            click.secho(f'{vault_name}', fg='cyan')
            click.secho(f'    {vault_path}')
    else:
        for f in vault.iter_notes():
            click.secho(f'{f.name}', fg='cyan')


cli.add_command(ls)


def main():
    cli()


if __name__ == '__main__':
    main()
