import typer
import os
from cmd import Cmd
from typing_extensions import Annotated
from rich.console import Console
from rich import print

from enum import Enum
from ginkgo.backtest.plots import CandlePlot
from ginkgo.client import data_cli
from ginkgo.client import backtest_cli
from ginkgo.client import unittest_cli
from ginkgo.client.interactive_cli import MyPrompt

main_app = typer.Typer(help="Usage: ginkgo [OPTIONS] COMMAND [ARGS]...")
main_app.add_typer(data_cli.app, name="data")
main_app.add_typer(backtest_cli.app, name="backtest")
main_app.add_typer(unittest_cli.app, name="unittest")

console = Console()


class DEBUG_TYPE(str, Enum):
    ON = "on"
    OFF = "off"


@main_app.command()
def status():
    """
    Check the module status.
    """
    from ginkgo.libs.ginkgo_conf import GCONF

    console.print(f"DEBUE: {GCONF.DEBUGMODE}")
    console.print(f"CPU RATIO: {GCONF.CPURATIO*100}%")
    os.system(
        "docker stats redis_master clickhouse_master mysql_master clickhouse_test mysql_test --no-stream"
    )


@main_app.command()
def version():
    """
    Ginkgo version.
    """
    from ginkgo.config.package import PACKAGENAME, VERSION

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
def configure(
    cpu: Annotated[float, typer.Option(case_sensitive=False)] = None,
    debug: Annotated[DEBUG_TYPE, typer.Option(case_sensitive=False)] = None,
):
    """
    Configure Ginkgo.
    """
    if cpu is None and debug is None:
        console.print(
            "You could set cpu usage by --cpu, switch the debug mode by --debug."
        )

    from ginkgo.libs.ginkgo_conf import GCONF

    if cpu is not None:
        if isinstance(cpu, float):
            GCONF.set_cpu_ratio(cpu)
        console.print(f"CPU RATIO: {GCONF.CPURATIO*100}%")

    if debug is not None:
        if debug == DEBUG_TYPE.ON:
            GCONF.set_debug(True)
        elif debug == DEBUG_TYPE.OFF:
            GCONF.set_debug(False)
        console.print(f"DEBUE: {GCONF.DEBUGMODE}")


if __name__ == "__main__":
    main_app()
