import typer
import os
from cmd import Cmd
from typing_extensions import Annotated
from rich.console import Console
from rich import print

from src.ginkgo.backtest.plots import CandlePlot
from src.ginkgo.client import data_cli
from src.ginkgo.client import backtest_cli
from src.ginkgo.client import unittest_cli
from src.ginkgo.client.interactive_cli import MyPrompt

main_app = typer.Typer(help="Usage: ginkgo [OPTIONS] COMMAND [ARGS]...")
main_app.add_typer(data_cli.app, name="data")
main_app.add_typer(backtest_cli.app, name="backtest")
main_app.add_typer(unittest_cli.app, name="unittest")

console = Console()


@main_app.command()
def status():
    """
    Check the module status.
    """
    from src.ginkgo.libs.ginkgo_conf import GCONF

    console.print(f"DEBUE: {GCONF.DEBUGMODE}")
    os.system("docker ps -a | grep ginkgo")


@main_app.command()
def version():
    """
    Ginkgo version.
    """
    from src.ginkgo.config.package import PACKAGENAME, VERSION

    print(
        f":sparkles: [bold medium_spring_green]{PACKAGENAME}[/bold medium_spring_green] [light_goldenrod2]{VERSION}[/light_goldenrod2]"
    )


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

    print(11)

    pass


if __name__ == "__main__":
    main_app()
