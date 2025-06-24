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
from ginkgo.client import backtest_component_cli, backtest_result_cli, backtest_config_cli
from ginkgo.libs import GLOG
from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
from ginkgo.enums import ORDERSTATUS_TYPES


app = typer.Typer(
    help=":shark: Module for [bold medium_spring_green]BACKTEST[/]. [grey62]Build your own strategy and do backtest.[/grey62]",
    no_args_is_help=True,
)
app.add_typer(backtest_component_cli.app, name="component")
app.add_typer(backtest_result_cli.app, name="result")
app.add_typer(backtest_config_cli.app, name="config")
console = Console()


class ResultType(str, Enum):
    analyzer = "analyzer"
    order = "order"


def print_order_paganation(df, page: int):
    """
    Echo dataframe in TTY page by page.
    """
    if page > 0:
        data_length = df.shape[0]
        page_count = int(data_length / page) + 1
        for i in range(page_count):
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("DateTime", style="dim")
            table.add_column("Code", style="dim")
            table.add_column("Direction", style="dim")
            table.add_column("Price", style="dim")
            table.add_column("Volume", style="dim")
            table.add_column("FEE", style="dim")
            for i, r in df[i * page : (i + 1) * page].iterrows():
                table.add_row(
                    str(r["timestamp"]),
                    r["code"],
                    str(r["direction"]),
                    str(r["transaction_price"]),
                    str(r["volume"]),
                    str(r["fee"]),
                )
            console.print(table)
            go_next_page = Prompt.ask(f"Current: {(i+1)*page}/{data_length}, Conitnue? \\[y\\/N\\]")
            if go_next_page.upper() in quit_list:
                console.print("See you soon. :sunglasses:")
                raise typer.Abort()
    else:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("DateTime", style="dim")
        table.add_column("Code", style="dim")
        table.add_column("Direction", style="dim")
        table.add_column("Price", style="dim")
        table.add_column("Volume", style="dim")
        table.add_column("FEE", style="dim")
        for i, r in df.iterrows():
            table.add_row(
                str(r["timestamp"]),
                r["code"],
                str(r["direction"]),
                str(r["transaction_price"]),
                str(r["volume"]),
                str(r["fee"]),
            )
        console.print(table)


@app.command()
def run(
    id: Annotated[str, typer.Option(..., "--id", "-id", case_sensitive=True, help="Backtest ID.")] = None,
    debug: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    :rocket: Run [bold medium_spring_green]BACKTEST[/].
    """
    from ginkgo.backtest.engines.engine_assembler_factory import assembler_backtest_engine
    from ginkgo.data.operations import get_engine, get_engines_page_filtered

    engine_df = get_engine(id)
    if engine_df.shape[0] == 0 or id is None:
        df = get_engines_page_filtered()
        msg = f"There is no engine [light_coral]{id}[/light_coral] in your database. " if id is None else ""
        msg += "You could choose another engine below."
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
    else:
        assembler_backtest_engine(id)


@app.command(name="list", no_args_is_help=True)
def list(
    engine: Annotated[bool, typer.Option(case_sensitive=False, help="List engines.")] = False,
    portfolio: Annotated[bool, typer.Option(case_sensitive=False, help="List portfolios.")] = False,
    file: Annotated[bool, typer.Option(case_sensitive=False, help="List files.")] = False,
    mapping: Annotated[bool, typer.Option(case_sensitive=False, help="List mappings.")] = False,
    param: Annotated[bool, typer.Option(case_sensitive=False, help="List params.")] = False,
    signal: Annotated[bool, typer.Option(case_sensitive=False, help="List signals.")] = False,
    order: Annotated[bool, typer.Option(case_sensitive=False, help="List orders.")] = False,
    position: Annotated[bool, typer.Option(case_sensitive=False, help="List positions.")] = False,
    filter: Annotated[str, typer.Option(case_sensitive=False, help="File filter.")] = None,
    a: Annotated[
        bool,
        typer.Option(case_sensitive=False, help="Show All Data, include removed file."),
    ] = False,
):
    """
    :open_file_folder: Show backtest components list.
    """
    from ginkgo.client.backtest_component_cli import ls as func

    return func(engine, portfolio, file, mapping, param, signal, order, position, filter, a)


def showorder(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID")] = "",
    page: Annotated[int, typer.Option(case_sensitive=False, help="Limit the number of output.")] = 0,
):
    """
    :one-piece_swimsuit: Show the backtest Orders.
    """
    from ginkgo.data.operatiy import get_backtest_list_df, get_order_df_by_portfolioid

    if id == "":
        raw = get_backtest_list_df()
        if raw.shape[0] == 0:
            console.print(
                f":sad_but_relieved_face: There is no [light_coral]backtest record[/light_coral] in database."
            )
            return
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Worth", style="dim")
        table.add_column("Start At")
        table.add_column("Finish At")
        rs = raw[["backtest_id", "profit", "start_at", "finish_at"]]
        for i, r in rs.iterrows():
            table.add_row(
                r["backtest_id"],
                f"${r['profit']}",
                f"{r['start_at']}",
                f"{r['finish_at']}",
            )
        console.print(table)
        return
    # Got backtest id
    orders = get_order_df_by_portfolioid(id)
    if orders.shape[0] == 0:
        console.print(f"There is no orders about Backtest: {id}")
        return

    orders = orders[orders["status"] == ORDERSTATUS_TYPES.FILLED]
    print_order_paganation(orders, page)


def showparams():
    pass


def showresult(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID")] = "",
    index: Annotated[
        typing_list[str],
        typer.Argument(
            case_sensitive=True,
            help="Type the analyzer_id to plot.",
        ),
    ] = None,
    compare: Annotated[
        str,
        typer.Option(case_sensitive=False, help="Do Compare with other backtest."),
    ] = "",
):
    """
    :one-piece_swimsuit: Show the backtest result.
    """
    from ginkgo.data.operations import get_backtest_list_df

    if id == "":
        raw = get_backtest_list_df()
        if raw.shape[0] == 0:
            console.print(
                f":sad_but_relieved_face: There is no [light_coral]backtest record[/light_coral] in database."
            )
            return
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Backtest", style="dim")
        table.add_column("Worth", style="dim")
        table.add_column("Start At")
        table.add_column("Finish At")
        rs = raw[["uuid", "backtest_id", "profit", "start_at", "finish_at"]]
        for i, r in rs.iterrows():
            table.add_row(
                r["uuid"],
                r["backtest_id"],
                f"${r['profit']}",
                f"{r['start_at']}",
                f"{r['finish_at']}",
            )
        console.print(table)
        return
    # Got backtest id
    record = get_backtest_record_by_backtest(id)
    print(record)
    if record is None:
        console.print(f":sad_but_relieved_face: Record {id} not exist. Please select one of follow.")
        print(get_backtest_list_df())
        return
    console.print(f":sunflower: Backtest [light_coral]{id}[/light_coral]  Worth: {record.profit}")
    console.print(f"You could use [green]ginkgo backtest res {id} analyzer_id1 analyzer_id2 ...[/green] to see detail.")

    import yaml

    if len(index) == 0:
        # get all the analyzer
        content = record.content
        analyzers = yaml.safe_load(content.decode("utf-8"))["analyzers"]
        if len(analyzers) == 0:
            console.print("No Analyzer.")
            return

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="dim")
        for i in analyzers:
            table.add_row(i["id"], i["parameters"][0])
        console.print(table)
        return

    from ginkgo.backtest.plots.result_plot import ResultPlot

    # Got analyzer id
    analyzer_ids = index
    content = record.content
    analyzers = yaml.safe_load(content.decode("utf-8"))["analyzers"]
    fig_data = []
    ids = [id]
    temp_data = {}
    for i in analyzer_ids:
        df = get_analyzer_df_by_backtest(id, i)
        if df.shape[0] == 0:
            continue
        analyzer_name = "TestName"
        for j in analyzers:
            if j["id"] == i:
                analyzer_name = j["parameters"][0]
                break
        temp_data[analyzer_name] = df
    fig_data.append(temp_data)
    if compare != "":
        temp_data = {}
        print("add compare")
        for i in analyzer_ids:
            df = get_analyzer_df_by_backtest(compare, i)
            if df.shape[0] == 0:
                continue
            analyzer_name = "TestName"
            for j in analyzers:
                if j["id"] == i:
                    analyzer_name = j["parameters"][0]
                    break
            temp_data[analyzer_name] = df
        ids.append(compare)
        fig_data.append(temp_data)
    plot = ResultPlot("Backtest")
    plot.update_data(id, fig_data, ids)
    plot.show()
