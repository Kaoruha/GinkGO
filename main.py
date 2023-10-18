import typer
import os
from cmd import Cmd
from typing_extensions import Annotated
from rich.console import Console

from ginkgo.backtest.plots import CandlePlot
from ginkgo.client import data_cli
from ginkgo.client.interactive_cli import MyPrompt

main_app = typer.Typer(help="Usage: ginkgocli [OPTIONS] COMMAND [ARGS]...")
main_app.add_typer(data_cli.app, name="data")


@main_app.command()
def status():
    """
    Check the module status.
    """
    os.system("docker ps -a | grep ginkgo")


@main_app.command()
def version():
    """
    Ginkgo version.
    """
    print(f"Ginkgo version: 2.1")


@main_app.command()
def interactive():
    """
    Active interactive mode.
    """
    os.system("clear")
    p = MyPrompt()
    p.cmdloop()


@main_app.command()
def configure():
    """
    Configure Ginkgo.
    """
    from ginkgo.config.ginkgo_config import GCONF

    pass


if __name__ == "__main__":
    main_app()
