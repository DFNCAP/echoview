import click

from app.utils.app_info import AppInfo


@click.group
@click.version_option(version=AppInfo().app_version, prog_name="EchoView")
def cli() -> None:
    pass


if __name__ == "__main__":
    cli()
