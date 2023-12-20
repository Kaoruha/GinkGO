import typer
from typing import List as typing_list
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
    :poultry_leg: Run Backtest. [grey62]Duplication fo `ginkgo backtest run`.[/grey62]
    """
    from ginkgo.client.backtest_cli import run as backtest_run

    backtest_run(id, level)


@main_app.command()
def cat(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="File id.")],
):
    """
    :see_no_evil: Show File content. [grey62]Duplication of `ginkgo backtest cat`. [/grey62]
    """
    from ginkgo.client.backtest_cli import cat as backtest_cat

    backtest_cat(id)


@main_app.command()
def edit(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="File ID")],
):
    """
    :orange_book: Edit File. [grey62]Duplication of `ginkgo backtest edit`.[/grey62]
    """
    from ginkgo.client.backtest_cli import edit as backtest_edit

    backtest_edit(id)


@main_app.command()
def rm(
    ids: Annotated[
        typing_list[str],
        typer.Argument(case_sensitive=True, help="File ID"),
    ],
):
    """
    :boom: Delete [light_coral]FILE[/light_coral] or [light_coral]BACKTEST RECORD[/light_coral] in database. [grey62]Duplication of `ginkgo backtest rm`.[/grey62]
    """
    from ginkgo.client.backtest_cli import rm as backtest_rm

    backtest_rm(ids)


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
    :open_file_folder: Show backtest file summary. [grey62]Duplication of `ginkgo backtest ls`.[/grey62]
    """
    from ginkgo.client.backtest_cli import ls as backtest_ls

    backtest_ls(filter, a)


@main_app.command()
def res(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID")] = "",
    plt: Annotated[
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
    :one-piece_swimsuit: Show the backtest result. [grey62]Duplication of `ginkgo backtest res`.[/grey62]
    """
    from ginkgo.client.backtest_cli import res as backtest_res

    backtest_res(id, plt, order, analyzer)


@main_app.command()
def update(
    a: Annotated[
        bool, typer.Option(case_sensitive=False, help="Update StockInfo")
    ] = False,
    # data: Annotated[DataType, typer.Argument(case_sensitive=False)],
    stockinfo: Annotated[
        bool, typer.Option(case_sensitive=False, help="Update StockInfo")
    ] = False,
    calendar: Annotated[
        bool, typer.Option(case_sensitive=False, help="Update Calendar")
    ] = False,
    adjust: Annotated[
        bool, typer.Option(case_sensitive=False, help="Update adjustfactor")
    ] = False,
    day: Annotated[
        bool, typer.Option(case_sensitive=False, help="Update day bar")
    ] = False,
    tick: Annotated[
        bool, typer.Option(case_sensitive=False, help="Update tick data")
    ] = False,
    fast: Annotated[
        bool,
        typer.Option(
            case_sensitive=False, help="If set, ginkgo will try update in fast mode."
        ),
    ] = False,
    code: Annotated[
        str,
        typer.Argument(
            case_sensitive=False,
            help="If set,ginkgo will try to update the data of specific code.",
        ),
    ] = "",
    debug: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    :raccoon: Data Update. [grey62]Duplication of `ginkgo data update`. [/grey62]
    """
    from ginkgo.client.data_cli import update as data_update

    data_update(a, stockinfo, calendar, adjust, day, tick, fast, code, debug)


@main_app.command()
def rebuild(
    order: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Order Table")
    ] = False,
    record: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Backtest Record Table")
    ] = False,
    file: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild File Table")
    ] = False,
    backtest: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Backtest Table")
    ] = False,
    analyzer: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Analyzer Table")
    ] = False,
    stockinfo: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild StockInfo Table")
    ] = False,
    calendar: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Calendar Table")
    ] = False,
):
    """
    :fox_face: Rebuild [light_coral]TABLE[/light_coral] in database. [grey62]Duplication of `ginkgo data rebuild`. [/grey62]

    """
    from ginkgo.client.data_cli import rebuild as data_rebuild

    data_rebuild(order, record, file, backtest, analyzer, stockinfo, calendar)


if __name__ == "__main__":
    main_app()
