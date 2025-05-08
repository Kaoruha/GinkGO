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
from ginkgo.client import backtest_update_cli, backtest_create_cli
from ginkgo.libs import GLOG
from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
from ginkgo.enums import ORDERSTATUS_TYPES


app = typer.Typer(
    help=":shark: Module for [bold medium_spring_green]BACKTEST[/]. [grey62]Build your own strategy and do backtest.[/grey62]",
    no_args_is_help=True,
)
app.add_typer(backtest_create_cli.app, name="create")
app.add_typer(backtest_update_cli.app, name="update")
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


@app.command(name="delete")
def delete(
    ids: Annotated[
        typing_list[str],
        typer.Argument(case_sensitive=True, help="File IDs"),
    ],
):
    """
    :boom: Delete [bold light_coral]FILE[/] or [bold light_coral]BACKTEST RECORD[/].
    """
    from ginkgo.data.operations import delete_file, delete_engine, delete_portfolio

    for i in ids:
        id = i
        # Try remove file
        result_file = delete_file(id)
        if result_file > 0:
            msg = f":zany_face: File [yellow]{id}[/yellow] delete."
            console.print(msg)
        # Try remove backtest engine
        result_back = delete_engine(id)
        if result_back > 0:
            msg = f":zany_face: Backtest Engine [light_coral]{id}[/light_coral] deleted."
            console.print(msg)
        # remove portfolios
        result_portfolio = delete_portfolio(id)
        if result_portfolio > 0:
            msg = f":zany_face: Portfolio [light_coral]{id}[/light_coral] deleted."
            console.print(msg)
        # remove backtest signals
        # remove backtest orders
        # remove backtest orders records
        # remove backtest analyzers
        # remove backtest positions
        # TODO Update delete functions
        continue
        # Remove order records and analyzers
        result_order = remove_orders(id)
        if result_order > 0:
            msg = f":zany_face: Orders about [light_coral]{id}[/light_coral] [yellow]{result_order}[/yellow] delete."
            console.print(msg)
        result_ana = remove_analyzers(id)
        if result_ana > 0:
            msg = f":zany_face: Analyzers about [light_coral]{id}[/light_coral] [yellow]{result_ana}[/yellow] delete."
            console.print(msg)

        result_pos = remove_positions(id)
        if result_pos > 0:
            msg = f":zany_face: Positions in backtest [light_coral]{id}[/light_coral] [yellow]{result_pos}[/yellow] delete."
            console.print(msg)

        if result_file == 0 and result_back == 0 and result_order == 0 and result_ana == 0 and result_pos == 0:
            console.print(
                f"There is no file or backtest record about [light_coral]{id}[/light_coral]. Please check id again."
            )


@app.command()
def edit(
    id: Annotated[str, typer.Option(..., "--id", "-id", case_sensitive=True, help="File ID")],
):
    """
    :orange_book: Edit [bold yellow]FILE[/].
    """

    def check_editor():
        editors = ["nvim", "vim"]
        for editor in editors:
            try:
                # 尝试运行编辑器，如果成功则说明可用
                result = subprocess.run([editor, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if result.returncode == 0:
                    return True, editor
            except FileNotFoundError:
                # 编辑器未安装或不在 PATH 中
                continue
        return False, None

    editor_res = check_editor()
    if not editor_res[0]:
        print("There is no editor in Systemt PATH.")
        return

    editor = editor_res[1]

    from ginkgo.libs.ginkgo_conf import GCONF
    from ginkgo.data.operations import get_file, update_file
    from ginkgo.enums import FILE_TYPES

    file_in_db = get_file(id)

    if file_in_db is None:
        console.print(
            f":sad_but_relieved_face: File [yellow]{id}[/yellow] not exists. Try [green]ginkgo backtest list[/green] first."
        )
    else:
        import uuid
        import shutil
        import os

        id = file_in_db.uuid
        name = file_in_db["name"]
        type = file_in_db.type
        if type is FILE_TYPES.ENGINE:
            file_format = "yml"
        else:
            file_format = "py"
        content = file_in_db.data
        temp_folder = f"{GCONF.WORKING_PATH}/{uuid.uuid4()}"
        Path(temp_folder).mkdir(parents=True, exist_ok=True)
        with open(f"{temp_folder}/{name}.{file_format}", "wb") as file:
            file.write(content)
        # TODO Support editor set, nvim,vim.vi,nano or vscode?
        edit_name = name.replace(" ", r"\ ") if " " in name else name
        os.system(f"{editor} {temp_folder}/{edit_name}.{file_format}")
        with open(f"{temp_folder}/{name}.{file_format}", "rb") as file:
            update_file(id, type, name, file.read())
            console.print(f":bear: [yellow]{type}[/yellow][green bold] {name}[/green bold] Updated.")
        # Remove the file and directory
        shutil.rmtree(temp_folder)


@app.command(name="cat")
def cat(
    id: Annotated[str, typer.Option(..., "--id", "-id", case_sensitive=True, help="File id.")],
):
    """
    :see_no_evil: Show [bold medium_spring_green]FILE[/] content.
    """
    from ginkgo.data.operations import get_file

    file = get_file(id)
    content = file.content
    console.print(content.decode("utf-8"))


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
    from ginkgo.enums import FILE_TYPES

    def intro_print(data_count: int, data_type: str):
        if filter is None:
            msg = f":ramen: There are {data_count} {data_type}. "
        else:
            msg = f":ramen: There are {data_count} {data_type} about [bold medium_spring_green]{filter}[/]. "
        console.print(msg)

    def print_engine(df):
        intro_print(df.shape[0], "engines")
        if df.shape[0] > 0:
            filtered_columns = ["uuid", "name", "is_live", "update_at"]
            rs = df[filtered_columns]
            table = Table(show_header=True, header_style="bold magenta")

            table.add_column("ID", style="dim")
            table.add_column("Name", style="dim")
            table.add_column("Live", style="dim")
            table.add_column("UpdateAt", style="dim")
            for i, r in rs.iterrows():
                table.add_row(r["uuid"], r["name"], str(r["is_live"]), str(r["update_at"]))
            console.print(table)

    def print_portfolio(df):
        intro_print(df.shape[0], "portfolios")
        if df.shape[0] > 0:
            filtered_columns = ["uuid", "name", "backtest_start_date", "backtest_end_date", "update_at"]
            rs = df[filtered_columns]
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim")
            table.add_column("Name", style="dim")
            table.add_column("Start", style="dim")
            table.add_column("End", style="dim")
            table.add_column("UpdateAt", style="dim")
            for i, r in rs.iterrows():
                table.add_row(
                    r["uuid"],
                    r["name"],
                    str(r["backtest_start_date"]),
                    str(r["backtest_end_date"]),
                    str(r["update_at"]),
                )
            console.print(table)

    def print_file(df):
        intro_print(df.shape[0], "files")
        if df.shape[0] > 0:
            filtered_columns = ["uuid", "name", "type", "update_at"]
            rs = df[filtered_columns]
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim")
            table.add_column("Name", style="dim")
            table.add_column("Type", style="dim")
            table.add_column("UpdateAt", style="dim")
            for i, r in rs.iterrows():
                table.add_row(r["uuid"], r["name"], str(r["type"]), str(r["update_at"]))
            console.print(table)

    def print_mapping(df):
        pass

    res = {}
    from ginkgo.data import (
        get_files_page_filtered,
        get_engines,
        get_orders_page_filtered,
        get_portfolios_page_filtered,
    )

    if engine:
        df = get_engines(name=filter, as_dataframe=True)
        res["engine"] = df
        print_engine(df)

    if portfolio:
        df = get_portfolios_page_filtered(name=filter)
        res["portfolio"] = df
        print_portfolio(df)

    if file:
        if filter is None:
            df = get_files_page_filtered()
        else:
            file_type = FILE_TYPES.enum_convert(filter)
            df1 = pd.DataFrame()
            if file_type:
                df1 = get_files_page_filtered(type=file_type)
            df = get_files_page_filtered(name=filter)
            if df1.shape[0] > 0:
                df = pd.concat([df1, df])
            df = df.drop_duplicates(subset=["uuid"])
        res["file"] = df
        print_file(df)
    if mapping:
        from ginkgo.data.operations import (
            get_engine_handler_mappings_page_filtered,
            get_engine_portfolio_mappings_page_filtered,
            get_portfolio_file_mappings_page_filtered,
        )

        if filter is None:
            df = get_engine_portfolio_mappings_page_filtered()
            intro_print(df.shape[0], "engine portfolio mappings")
            if df.shape[0] > 0:
                filtered_columns = ["uuid", "engine_id", "portfolio_id", "update_at"]
                rs = df[filtered_columns]
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("ID", style="dim")
                table.add_column("Engine", style="dim")
                table.add_column("Portfolio", style="dim")
                table.add_column("UpdateAt", style="dim")
                for i, r in rs.iterrows():
                    table.add_row(r["uuid"], r["engine_id"], r["portfolio_id"], str(r["update_at"]))
                console.print(table)
            df = get_engine_handler_mappings_page_filtered()
            intro_print(df.shape[0], "engine handler mappings")
            # TODO
            df = get_portfolio_file_mappings_page_filtered()
            intro_print(df.shape[0], "portfolio file mappings")
            if df.shape[0] > 0:
                filtered_columns = ["uuid", "portfolio_id", "file_id", "name", "type", "update_at"]
                rs = df[filtered_columns]
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("ID", style="dim")
                table.add_column("Name", style="dim")
                table.add_column("Type", style="dim")
                table.add_column("Portfolio", style="dim")
                table.add_column("File", style="dim")
                table.add_column("UpdateAt", style="dim")
                for i, r in rs.iterrows():
                    table.add_row(
                        r["uuid"], r["name"], str(r["type"]), r["portfolio_id"], r["file_id"], str(r["update_at"])
                    )
                console.print(table)
        else:
            df = get_engine_portfolio_mappings_page_filtered()
            if df.shape[0] > 0:
                df1 = df[df["engine_id"] == filter]
                df2 = df[df["portfolio_id"] == filter]
                df = pd.concat([df1, df2])
            intro_print(df.shape[0], "engine portfolio mappings")
            if df.shape[0] > 0:
                filtered_columns = ["uuid", "engine_id", "portfolio_id", "update_at"]
                rs = df[filtered_columns]
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("ID", style="dim")
                table.add_column("Engine", style="dim")
                table.add_column("Portfolio", style="dim")
                table.add_column("UpdateAt", style="dim")
                for i, r in rs.iterrows():
                    table.add_row(r["uuid"], r["engine_id"], r["portfolio_id"], str(r["update_at"]))
                console.print(table)
            df = get_engine_handler_mappings_page_filtered()
            if df.shape[0] > 0:
                df1 = df[df["engine_id"] == filter]
                df2 = df[df["handler_id"] == filter]
                df = pd.concat([df1, df2])
            intro_print(df.shape[0], "engine handler mappings")
            if df.shape[0] > 0:
                pass
            df = get_portfolio_file_mappings_page_filtered()
            if df.shape[0] > 0:
                df1 = df[df["portfolio_id"] == filter]
                df2 = df[df["file_id"] == filter]
                df = pd.concat([df1, df2])
            intro_print(df.shape[0], "portfolio file mappings")
            if df.shape[0] > 0:
                filtered_columns = ["uuid", "portfolio_id", "file_id", "name", "type", "update_at"]
                rs = df[filtered_columns]
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("ID", style="dim")
                table.add_column("Name", style="dim")
                table.add_column("Type", style="dim")
                table.add_column("Portfolio", style="dim")
                table.add_column("File", style="dim")
                table.add_column("UpdateAt", style="dim")
                for i, r in rs.iterrows():
                    table.add_row(
                        r["uuid"], r["name"], str(r["type"]), r["portfolio_id"], r["file_id"], str(r["update_at"])
                    )
                console.print(table)
    if param:
        from ginkgo.data.operations import get_params_page_filtered

        if filter is not None:
            df = get_params_page_filtered(source_id=filter)
        else:
            df = get_params_page_filtered()
        if df.shape[0] > 0:
            intro_print(df.shape[0], "mapping params")
            filtered_columns = ["uuid", "mapping_id", "index", "value", "update_at"]
            print(df)
            rs = df[filtered_columns]
            rs = rs.sort_values(by=["mapping_id", "index"], ascending=True)
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim")
            table.add_column("Mapping", style="dim")
            table.add_column("Index", style="dim")
            table.add_column("Value", style="dim")
            table.add_column("UpdateAt", style="dim")
            for i, r in rs.iterrows():
                table.add_row(r["uuid"], r["mapping_id"], str(r["index"]), r["value"], str(r["update_at"]))
            console.print(table)

    if signal:
        # Get signal
        # Filter engine
        # Filter portfolio
        # TODO
        pass
    if order:
        # Get Order
        # Filter engine
        # Filter portfolio
        # TODO
        pass
    if position:
        # Get Position
        # Filter engine
        # Filter portfolio
        # TODO
        pass


@app.command()
def run(
    id: Annotated[str, typer.Option(..., "--id", "-id", case_sensitive=True, help="Backtest ID.")] = None,
    debug: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    :open_file_folder: Run [bold medium_spring_green]BACKTEST[/].
    """
    from ginkgo.backtest.engines.engine_assembler_factory import assembler_backtest_engine
    from ginkgo.data import get_engine, get_engines

    engine_df = get_engine(id)
    if engine_df.shape[0] == 0 or id is None:
        df = get_engines()
        msg = f"There is no engine [light_coral]{id}[/light_coral] in your database" if id is None else ""
        msg += "You Cloud choose another engine below."
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


@app.command()
def recall(
    id: Annotated[str, typer.Option(..., "--id", "-id", case_sensitive=True, help="Backtest ID")],
    name: Annotated[str, typer.Option(case_sensitive=True, help="File Name")] = "",
):
    """
    :open_file_folder: Recall the backtest configuration from a completed backtest.
    """
    # TODO
    from ginkgo.data.operations import add_file, update_file, get_backtest_record
    from ginkgo.enums import FILE_TYPES
    import yaml
    import datetime

    backtest = get_backtest_record(id)
    if backtest is None:
        return
    content = backtest.content
    file_name = "Edo Tensei"
    try:
        file_name = name if name != "" else f"{yaml.safe_load(content)['name']}_recall"
    except Exception as e:
        print(e)
    file_id = add_file(FILE_TYPES.ENGINE, file_name)
    update_file(file_id, FILE_TYPES.ENGINE, file_name, content)
    console.print(
        f":dove:  Recall the configuration of backtest [light_coral]{id}[/light_coral] as [medium_spring_green]{file_name}[/medium_spring_green]"
    )


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


@app.command(name="init")
def init():
    """
    :ram: Init the basic file to database. Copy files from source.
    """
    from ginkgo.data import init_example_data as func

    func()
