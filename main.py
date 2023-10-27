import typer
import os
from cmd import Cmd
from typing_extensions import Annotated
from rich.console import Console

from src.ginkgo.backtest.plots import CandlePlot
from src.ginkgo.client import data_cli
from src.ginkgo.client import backtest_cli
from src.ginkgo.client import unittest_cli
from src.ginkgo.client.interactive_cli import MyPrompt

main_app = typer.Typer(help="Usage: ginkgo [OPTIONS] COMMAND [ARGS]...")
main_app.add_typer(data_cli.app, name="data")
main_app.add_typer(backtest_cli.app, name="backtest")
main_app.add_typer(unittest_cli.app, name="unittest")


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
    from src.ginkgo.config.package import PACKAGENAME, VERSION

    print(f"{PACKAGENAME} {VERSION}")


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
    from src.ginkgo.libs.ginkgo_conf import GCONF

    pass


if __name__ == "__main__":
    main_app()
