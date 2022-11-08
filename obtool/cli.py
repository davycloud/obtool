import click

from obtool.obsidian import get_vaults_list, ObVault


@click.group()
def cli():
    pass


@click.command()
@click.argument('vault', default=None, required=False)
def ls(vault):
    if vault is None:
        for v in get_vaults_list():
            vault_name = v.path.name
            vault_path = v.path.parent
            click.echo(f'{vault_name}\n    {vault_path}')
    else:
        ob_vault = ObVault.open(vault)
        for f in ob_vault.iter_notes():
            click.echo(f'{f}')


cli.add_command(ls)


def main():
    cli()


if __name__ == '__main__':
    main()
