import typer
import click
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
from ginkgo.client.backtest_cli import LogLevelType


main_app = typer.Typer(
    help="Usage: ginkgo [OPTIONS] COMMAND [ARGS]...", rich_markup_mode="rich"
)
main_app.add_typer(data_cli.app, name="data")
main_app.add_typer(backtest_cli.app, name="backtest")
main_app.add_typer(unittest_cli.app, name="unittest")

console = Console()


class DEBUG_TYPE(str, Enum):
    ON = "on"
    OFF = "off"


@main_app.command()
def status(
    stream: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    :bullet_train: Check the module status.
    """
    from ginkgo.libs.ginkgo_conf import GCONF

    console.print(f"DEBUE: {GCONF.DEBUGMODE}")
    console.print(f"CPU RATIO: {GCONF.CPURATIO*100}%")
    if stream:
        os.system(
            "docker stats redis_master clickhouse_master mysql_master clickhouse_test mysql_test"
        )
    else:
        os.system(
            "docker stats redis_master clickhouse_master mysql_master clickhouse_test mysql_test --no-stream"
        )


@main_app.command()
def version():
    """
    :sheep: Show the version of Local Ginkgo Client.
    """
    from ginkgo.config.package import PACKAGENAME, VERSION

    print(
        f":sparkles: [bold medium_spring_green]{PACKAGENAME}[/bold medium_spring_green] [light_goldenrod2]{VERSION}[/light_goldenrod2]"
    )


@main_app.command()
def interactive():
    """
    :robot: Active interactive mode.
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
    :wrench: Configure Ginkgo.
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


@main_app.command()
def run(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID.")],
    level: Annotated[
        LogLevelType, typer.Option(case_sensitive=False, help="DEBUG Level")
    ] = "INFO",
):
    """
    :poultry_leg: Run Backtest. [yellow]Duplication fo `ginkgo backtest run`.[/yellow]
    """
    from ginkgo.client.backtest_cli import run as backtest_run

    backtest_run(id, level)


@main_app.command()
def cat(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="File id.")],
):
    """
    :see_no_evil: Show File content. [yellow]Duplication of `ginkgo backtest cat`. [/yellow]
    """
    from ginkgo.client.backtest_cli import cat as backtest_cat

    backtest_cat(id)


@main_app.command()
def edit(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="File ID")],
):
    """
    :orange_book: Edit File resources. [yellow]Duplication of `ginkgo backtest edit`.[/yellow]
    """
    from ginkgo.client.backtest_cli import edit as backtest_edit

    backtest_edit(id)


@main_app.command()
def rm(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="File ID")],
):
    """
    :boom: Delete file in database. [yellow]Duplication of `ginkgo backtest rm`.[/yellow]
    """
    from ginkgo.client.backtest_cli import rm as backtest_rm

    backtest_rm(id)


@main_app.command()
def ls(
    filter: Annotated[
        str, typer.Option(case_sensitive=False, help="File filter")
    ] = None,
    a: Annotated[
        bool,
        typer.Option(case_sensitive=False, help="Show All Data, include removed file."),
    ] = False,
):
    """
    :open_file_folder: Show backtest file summary. [yellow]Duplication of `ginkgo backtest ls`.[/yellow]
    """
    from ginkgo.client.backtest_cli import ls as backtest_ls

    backtest_ls(filter, a)


@main_app.command()
def res(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID")] = "",
    plot: Annotated[
        bool,
        typer.Option(case_sensitive=False, help="Show Result in charts."),
    ] = False,
    order: Annotated[
        bool,
        typer.Option(case_sensitive=False, help="Show Order Result."),
    ] = False,
    analyzer: Annotated[
        bool,
        typer.Option(case_sensitive=False, help="Show Anaylzer Result."),
    ] = False,
):
    """
    :one-piece_swimsuit: Show the backtest result. [yellow]Duplication of `ginkgo backtest res`.[/yellow]
    """
    from ginkgo.client.backtest_cli import res as backtest_res

    backtest_res(id, plot, order, analyzer)


if __name__ == "__main__":
    main_app()
