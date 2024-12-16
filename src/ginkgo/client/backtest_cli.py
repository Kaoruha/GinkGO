import typer
from ginkgo.data.ginkgo_data import GDATA
from tabulate import tabulate
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
    help=":shark: Module for [bold medium_spring_green]BACKTEST[/]. [grey62]Build your own strategy and do backtest.[/grey62]"
)
console = Console()


class ResourceType(str, Enum):
    backtest = "backtest"
    strategy = "strategy"
    selector = "selector"
    sizer = "sizer"
    risk_manager = "riskmanager"
    portfolio = "portfolio"
    analyzer = "analyzer"
    plot = "plot"


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
def init():
    """
    :ram: Init the basic file to database. Copy files from source.
    """
    from ginkgo.data import init_example_data as func
    func()


@app.command()
def cat(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="File id.")],
):
    """
    :see_no_evil: Show [bold medium_spring_green]FILE[/] content.
    """
    from ginkgo.data.ginkgo_data import GDATA

    file = GDATA.get_file(id)
    content = file.content
    console.print(content.decode("utf-8"))


@app.command()
def ls(
    filter: Annotated[str, typer.Option(case_sensitive=False, help="File filter")] = None,
    a: Annotated[
        bool,
        typer.Option(case_sensitive=False, help="Show All Data, include removed file."),
    ] = False,
):
    """
    :open_file_folder: Show backtest file summary.
    """
    from ginkgo.data import get_files
    from ginkgo.data.ginkgo_data import GDATA

    if filter is None:
        # If filter is None, show all files.
        raw = get_files()
    else:
        from ginkgo.enums import FILE_TYPES

        file_type = FILE_TYPES.enum_convert(filter)
        raw = get_files(type=file_type)
    if raw.shape[0] > 0:
        # If there is file in database.
        # Show the file list.
        rs = raw[["uuid", "name", "type", "update_at"]]
        msg = ""
        if filter is None:
            msg = f":ramen: There are {raw.shape[0]} files. "
        else:
            msg = f":ramen: There are {raw.shape[0]} files about {filter}. "
        console.print(msg)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="dim")
        table.add_column("Type", style="dim")
        table.add_column("Update", style="dim")
        for i, r in rs.iterrows():
            table.add_row(r["uuid"], r["name"], str(r["type"]), str(r["update_at"]))
        console.print(table)
    else:
        # If there is no file in database.
        console.print(
            f"There is no [light_coral]{filter}[/light_coral] in database. You could run [medium_spring_green]ginkgo backtest init[/medium_spring_green] or [medium_spring_green]ginkgo backtest new [FileType][/medium_spring_green]"
        )


@app.command()
def run(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID.")],
    debug: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    from ginkgo.backtest.engines.engine_assembler_factory import assembler_backtest_engine
    from ginkgo.data import get_engine, get_engines
    engine_df = get_engine(id)
    if engine_df.shape[0] == 0:
        df = get_engines()
        console.print(f"ENGINE [light_coral]{id}[/light_coral] not exist. You Cloud choose another engine below.")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="dim")
        table.add_column("Description", style="dim")
        table.add_column("Update At", style="dim")
        for i, r in df.iterrows():
            table.add_row(
                    r['uuid'],
                    r['name'],
                    r['desc'],
                    str(r['update_at']),
            )
        console.print(table)
        return
    else:
        assembler_backtest_engine(id)



@app.command()
def edit(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="File ID")],
):
    """
    :orange_book: Edit File.
    """
    from ginkgo.data.ginkgo_data import GDATA
    from ginkgo.libs.ginkgo_conf import GCONF
    from ginkgo.enums import FILE_TYPES

    file_in_db = GDATA.get_file(id)

    if file_in_db is None:
        console.print(
            f":sad_but_relieved_face: File [yellow]{id}[/yellow] not exists. Try [green]ginkgo backtest list[/green] first."
        )
    else:
        import uuid
        import shutil
        import os

        id = file_in_db.uuid
        name = file_in_db.file_name
        type = file_in_db.type
        if type is FILE_TYPES.ENGINE:
            file_format = "yml"
        else:
            file_format = "py"
        content = file_in_db.content
        temp_folder = f"{GCONF.WORKING_PATH}/{uuid.uuid4()}"
        Path(temp_folder).mkdir(parents=True, exist_ok=True)
        with open(f"{temp_folder}/{name}.{file_format}", "wb") as file:
            file.write(content)
        # TODO Support editor set, nvim,vim.vi,nano or vscode?
        edit_name = name.replace(" ", r"\ ") if " " in name else name
        os.system(f"nvim {temp_folder}/{edit_name}.{file_format}")
        with open(f"{temp_folder}/{name}.{file_format}", "rb") as file:
            GDATA.update_file(id, type, name, file.read())
            console.print(f":bear: [yellow]{type}[/yellow][green bold] {name}[/green bold] Updated.")
        # Remove the file and directory
        shutil.rmtree(temp_folder)

@app.command()
def create_engine():
    pass


@app.command()
def show():
    pass

@app.command()
def create_file(
    type: Annotated[ResourceType, typer.Argument(case_sensitive=False, help="File Type")],
    name: Annotated[str, typer.Argument(case_sensitive=True, help="File Name")],
    source: Annotated[str, typer.Option(case_sensitive=True, help="Copy from Target")] = "",
):
    """
    :ramen: Create file in database.
    """
    from ginkgo.data.ginkgo_data import GDATA
    from ginkgo.enums import FILE_TYPES

    resource = FILE_TYPES.enum_convert(type)
    if resource in FILE_TYPES:
        if source == "":
            GDATA.add_file(resource, name)
            console.print(f"Create file [yellow]{name}[/yellow].")
        else:
            r = GDATA.copy_file(resource, name, source)
            if r is None:
                console.print(f"Copy file [yellow]{name}[/yellow] Failed.")
            else:
                console.print(f"Copy file [yellow]{name}[/yellow] Done.")
    else:
        print(f"File type not support.")


@app.command()
def rm(
    ids: Annotated[
        typing_list[str],
        typer.Argument(case_sensitive=True, help="File ID"),
    ],
):
    """
    :boom: Delete [light_coral]FILE[/light_coral] or [light_coral]BACKTEST RECORD[/light_coral] in database.
    """
    from ginkgo.data.ginkgo_data import GDATA

    for i in ids:
        id = i

        # Try remove file
        result_file = GDATA.remove_file(id)
        if result_file:
            msg = f":zany_face: File [yellow]{id}[/yellow] delete."
            console.print(msg)
        # Try remove backtest records
        result_back = GDATA.remove_backtest(id)
        if result_back:
            msg = f":zany_face: Backtest Record [light_coral]{id}[/light_coral] delete."
            console.print(msg)
        # Remove order records and analyzers
        result_order = GDATA.remove_orders(id)
        if result_order > 0:
            msg = f":zany_face: Orders about [light_coral]{id}[/light_coral] [yellow]{result_order}[/yellow] delete."
            console.print(msg)
        result_ana = GDATA.remove_analyzers(id)
        if result_ana > 0:
            msg = f":zany_face: Analyzers about [light_coral]{id}[/light_coral] [yellow]{result_ana}[/yellow] delete."
            console.print(msg)

        result_pos = GDATA.remove_positions(id)
        if result_pos > 0:
            msg = f":zany_face: Positions in backtest [light_coral]{id}[/light_coral] [yellow]{result_pos}[/yellow] delete."
            console.print(msg)

        if not result_file and not result_back and result_order == 0 and result_ana == 0 and result_pos == 0:
            console.print(
                f"There is no file or backtest record about [light_coral]{id}[/light_coral]. Please check id again."
            )


@app.command()
def recall(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID")],
    name: Annotated[str, typer.Option(case_sensitive=True, help="File Name")] = "",
):
    """
    Recall the Backtest config from a complete backtest.
    """
    from ginkgo.data.ginkgo_data import GDATA
    from ginkgo.enums import FILE_TYPES
    import yaml
    import datetime

    backtest = GDATA.get_backtest_record(id)
    if backtest is None:
        return
    content = backtest.content
    file_name = "Edo Tensei"
    try:
        file_name = name if name != "" else f"{yaml.safe_load(content)['name']}_recall"
    except Exception as e:
        print(e)
    file_id = GDATA.add_file(FILE_TYPES.ENGINE, file_name)
    GDATA.update_file(file_id, FILE_TYPES.ENGINE, file_name, content)
    console.print(
        f":dove:  Recall the configuration of backtest [light_coral]{id}[/light_coral] as [medium_spring_green]{file_name}[/medium_spring_green]"
    )


@app.command()
def order(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID")] = "",
    page: Annotated[int, typer.Option(case_sensitive=False, help="Limit the number of output.")] = 0,
):
    """
    :one-piece_swimsuit: Show the backtest Orders.
    """
    if id == "":
        raw = GDATA.get_backtest_list_df()
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
    orders = GDATA.get_order_df_by_portfolioid(id)
    if orders.shape[0] == 0:
        console.print(f"There is no orders about Backtest: {id}")
        return

    orders = orders[orders["status"] == ORDERSTATUS_TYPES.FILLED]
    print_order_paganation(orders, page)


@app.command()
def res(
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

    if id == "":
        raw = GDATA.get_backtest_list_df()
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
    record = GDATA.get_backtest_record_by_backtest(id)
    print(record)
    if record is None:
        console.print(f":sad_but_relieved_face: Record {id} not exist. Please select one of follow.")
        print(GDATA.get_backtest_list_df())
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
        df = GDATA.get_analyzer_df_by_backtest(id, i)
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
            df = GDATA.get_analyzer_df_by_backtest(compare, i)
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
