import typer
import pandas as pd
import subprocess

from enum import Enum
from typing import List as typing_list, Optional
from typing_extensions import Annotated
from rich.prompt import Prompt
from rich.table import Column, Table
from rich.console import Console
from pathlib import Path

from ginkgo.client.unittest_cli import LogLevelType
from ginkgo.libs import GLOG
from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
from ginkgo.enums import ORDERSTATUS_TYPES

app = typer.Typer(
    help=":roll_of_paper: Manage [bold medium_spring_green]RESULT[/]. [grey62][/]",
    no_args_is_help=True,
)
console = Console()


@app.command(name="list")
def ls():
    print("list results")


@app.command(name="show")
def show(
    engine_id: Annotated[str, typer.Option(..., "--engine", "-engine", case_sensitive=True, help="Engine ID.")] = None,
    portfolio_id: Annotated[
        str, typer.Option(..., "--portfolio", "-portfolio", case_sensitive=True, help="Portfolio ID.")
    ] = None,
    analyzer_id: Annotated[
        str, typer.Option(..., "--analyzer", "-analyzer", case_sensitive=True, help="Analyzer ID.")
    ] = None,
    output: Annotated[str, typer.Option(..., "--output", "-output", case_sensitive=True, help="Plot output.")] = None,
):
    """
    :open_file_folder: Analyze [bold medium_spring_green]BACKTEST[/] with plot.
    """
    from ginkgo.data.operations import (
        get_engines_page_filtered,
        get_portfolio_file_mappings_page_filtered,
        get_analyzer_records_page_filtered,
    )
    from ginkgo.data import get_engine_portfolio_mappings
    from ginkgo.enums import FILE_TYPES

    if engine_id is None:
        df = get_engines_page_filtered()
        msg = "You could choose engine below with param --engine"
        console.print(msg)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="dim")
        table.add_column("Description", style="dim")
        table.add_column("Update At", style="dim")
        for i, r in df.iterrows():
            table.add_row(
                r["uuid"],
                r["name"],
                r["desc"],
                str(r["update_at"]),
            )
        console.print(table)
        return
    if portfolio_id is None:
        df = get_engine_portfolio_mappings(engine_id)
        msg = "You could choose portfolio below with param --portfolio"
        console.print(msg)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="dim")
        table.add_column("Update At", style="dim")
        for i, r in df.iterrows():
            table.add_row(
                r["portfolio_id"],
                r["portfolio_name"],
                str(r["update_at"]),
            )
        console.print(table)
        return

    if analyzer_id is None:
        df = get_portfolio_file_mappings_page_filtered(portfolio_id=portfolio_id, type=FILE_TYPES.ANALYZER)
        msg = "You could choose analyzer below with param --analyzer"
        console.print(msg)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="dim")
        table.add_column("Update At", style="dim")
        for i, r in df.iterrows():
            table.add_row(
                r["file_id"],
                r["name"],
                str(r["update_at"]),
            )
        console.print(table)
        return

    result = get_analyzer_records_page_filtered(portfolio_id=portfolio_id, engine_id=engine_id, analyzer_id=analyzer_id)
    from ginkgo.backtest.plots.terminal_line import TerminalLine

    if result.shape[0] == 0:
        console.print("There is no data. Please run backtest first.")
        return

    TerminalLine(data=result, title=result.iloc[0]["name"]).show()
    if output is not None:
        pass


@app.command(name="export")
def export():
    print("export results")


@app.command(name="remove")
def remove():
    print("remove results")
