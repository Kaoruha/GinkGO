import typer
from ginkgo.data.ginkgo_data import GDATA
from tabulate import tabulate
from enum import Enum
from typing import List as typing_list, Optional
from typing_extensions import Annotated
from rich.prompt import Prompt
from rich.table import Column, Table
from rich.console import Console
from ginkgo.client.unittest_cli import LogLevelType
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
from ginkgo.enums import ORDERSTATUS_TYPES


app = typer.Typer(
    help=":shark: Module for BACKTEST. [grey62]Build your own strategy and do backtest.[/grey62]"
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
            go_next_page = Prompt.ask(
                f"Current: {(i+1)*page}/{data_length}, Conitnue? \[y/N]"
            )
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
    from ginkgo.data.ginkgo_data import GDATA

    GDATA.init_file()


@app.command()
def cat(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="File id.")],
):
    """
    :see_no_evil: Show File content.
    """
    from ginkgo.data.ginkgo_data import GDATA

    file = GDATA.get_file(id)
    content = file.content
    console.print(content.decode("utf-8"))


@app.command()
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
    :open_file_folder: Show backtest file summary.
    """
    from ginkgo.data.ginkgo_data import GDATA

    if filter is None:
        # If filter is None, show all files.
        raw = GDATA.get_file_list_df(None)
    else:
        # If filter is not None, show files by filter.
        # Try convert filter to enum.
        # If Failed try with fuzzy search. TODO
        from ginkgo.enums import FILE_TYPES

        file_type = FILE_TYPES.enum_convert(filter)
        if file_type is None:
            raw = GDATA.get_file_list_df_fuzzy(filter)
        else:
            raw = GDATA.get_file_list_df(file_type)

    if raw.shape[0] > 0:
        # If there is file in database.
        # Show the file list.
        rs = raw[["uuid", "file_name", "type", "update"]]
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
            table.add_row(r["uuid"], r["file_name"], str(r["type"]), str(r["update"]))
        console.print(table)
    else:
        # If there is no file in database.
        console.print(
            f"There is no [light_coral]{filter}[/light_coral] in database. You could run [steel_blue1]ginkgo backtest init[/steel_blue1] or [steel_blue1]ginkgo backtest new [FileType][/steel_blue1]"
        )


@app.command()
def run(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID.")],
    debug: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    :poultry_leg: Run Backtest.
    """
    import uuid
    import importlib
    import inspect
    import os
    import shutil
    import yaml
    import time
    import datetime
    import sys
    from ginkgo.libs.ginkgo_conf import GCONF
    from ginkgo.data.ginkgo_data import GDATA
    from ginkgo.backtest.engines import EventEngine
    from ginkgo.enums import EVENT_TYPES
    from ginkgo.backtest.matchmakings import MatchMakingSim
    from ginkgo.backtest.feeds import BacktestFeed
    from ginkgo.backtest.events import EventNextPhase
    from ginkgo.backtest.portfolios import PortfolioT1Backtest
    from ginkgo.libs import datetime_normalize

    if debug:
        GLOG.set_level("DEBUG")
    else:
        GLOG.set_level("INFO")

    def get_class_from_id(father_directory: str, file_id: str):
        model = GDATA.get_file(file_id)
        path = f"{GCONF.WORKING_PATH}/{father_directory}/{file_id}.py"
        if model is None:
            GLOG.ERROR(f"{file_id} not exist.")
            return None
        with open(path, "wb") as file:
            file.write(model.content)
            file.flush()  # Flush the data to the disk
            os.fsync(file.fileno())  # ensure the changes are permanent
        module = None
        try_time = 0
        while True:
            try:
                module = importlib.import_module(f"{father_directory}.{file_id}")
                break
            except Exception as e:
                with open(path, "wb") as file:
                    file.write(model.content)
                    file.flush()  # Flush the data to the disk
                    os.fsync(file.fileno())  # ensure the changes are permanent
                print(e)
                try_time += 1
                if try_time > 5:
                    break
                time.sleep(2)
        if module is None:
            return None
        classes = inspect.getmembers(module, inspect.isclass)
        filtelight_coral_classes = []
        for name, cls in classes:
            if hasattr(cls, "__abstract__"):
                filtelight_coral_classes.append(cls)
        # TODO Check the length
        if len(filtelight_coral_classes) == 1:
            return filtelight_coral_classes[0]
        else:
            # TODO Raise Exception
            return None

    backtest_config_file_id = id

    # 1. Create a temp folder.

    random_id = uuid.uuid4().hex
    temp_folder = f"{GCONF.WORKING_PATH}/{random_id}"
    os.mkdir(temp_folder)

    # 2 Read config from database.
    backtest_config_model = GDATA.get_file(id)
    if backtest_config_model is None:
        print(f"Backtest {id} not exsit.")
        shutil.rmtree(temp_folder)
        return

    # 2. Read the id, Get backtest config from database. Write to local temp
    content = backtest_config_model.content

    with open(f"{temp_folder}/{id}.yml", "wb") as file:
        file.write(content)

    # Read local file
    backtest_config = None
    try:
        with open(f"{temp_folder}/{id}.yml", "r") as file:
            backtest_config = yaml.safe_load(file)
    except Exception as e:
        print(e)
        shutil.rmtree(temp_folder)
        return

    if backtest_config is None:
        shutil.rmtree(temp_folder)
        return

    backtest_name = backtest_config["name"]
    date_start = datetime_normalize(backtest_config["start"])
    date_end = datetime_normalize(backtest_config["end"])

    # Get a list of all the members of the module.py file

    # Portfolio -->

    portfolio = PortfolioT1Backtest()  # TODO Read from database.

    # Selector -->
    # Selector -->
    selector_config = backtest_config["selector"]
    selector_id = selector_config["id"]
    selector_parameters = selector_config["parameters"]
    selector_cls = get_class_from_id(random_id, selector_id)
    # Bind Selector
    if selector_cls is not None:
        selector = selector_cls(*selector_parameters)
        portfolio.bind_selector(selector)
    else:
        console.print(f":sad_but_relieved_face: Cant Locate SELECOTR: {selector_id}")
        shutil.rmtree(temp_folder)
        return
    # <-- Selector
    # <-- Selector

    # Sizer -->
    # Sizer -->
    sizer_config = backtest_config["sizer"]
    sizer_id = sizer_config["id"]
    sizer_parameters = sizer_config["parameters"]
    sizer_cls = get_class_from_id(random_id, sizer_id)
    # Bind Selector
    if sizer_cls is not None:
        sizer = sizer_cls(*sizer_parameters)
        portfolio.bind_sizer(sizer)
    else:
        console.print(f":sad_but_relieved_face:Cant Locate SIZER: {sizer_id}")
        shutil.rmtree(temp_folder)
        return
    # <-- Sizer
    # <-- Sizer

    # Risk -->
    # Risk -->
    risk_config = backtest_config["risk_manager"]
    risk_id = risk_config["id"]
    risk_parameters = risk_config["parameters"]
    risk_cls = get_class_from_id(random_id, risk_id)
    # Bind Selector
    if risk_cls is not None:
        risk = risk_cls(*risk_parameters)
        portfolio.bind_risk(risk)
    else:
        console.print(f":sad_but_relieved_face:Cant Locate RISK: {sizer_id}")
        shutil.rmtree(temp_folder)
        return
    # <-- Risk
    # <-- Risk

    # Srategy -->
    # Srategy -->
    strategies_config = backtest_config["strategies"]
    for strategy_config in strategies_config:
        strategy_id = strategy_config["id"]
        strategy_parameters = strategy_config["parameters"]
        print(strategy_id)
        print(strategy_parameters)
        strategy_cls = get_class_from_id(random_id, strategy_id)
        # Bind Strategy
        if strategy_cls is not None:
            strategy = strategy_cls(*strategy_parameters)
            portfolio.add_strategy(strategy)
        else:
            console.print(
                f":sad_but_relieved_face: Cant Locate Strategy: {strategy_id}"
            )
            shutil.rmtree(temp_folder)
            return

    # <-- Strategy
    # <-- Strategy

    # Analyzer -->
    # Analyzer -->
    analyzer_config = backtest_config["analyzers"]
    for analyze_config in analyzer_config:
        analyzer_id = analyze_config["id"]
        analyzer_parameters = analyze_config["parameters"]
        print(analyzer_id)
        print(analyzer_parameters)
        analyzer_cls = get_class_from_id(random_id, analyzer_id)
        # Bind Analyzer
        if analyzer_cls is not None:
            analyzer = analyzer_cls(*analyzer_parameters)
            analyzer.set_analyzer_id(analyzer_id)
            print(analyzer)
            portfolio.add_analyzer(analyzer)
        else:
            console.print(
                f":sad_but_relieved_face: Cant Locate Analyzer: {analyzer_id}"
            )
            shutil.rmtree(temp_folder)
            return
    # <-- Analyzer
    # <-- Analyzer

    backtest_id = GDATA.add_backtest(random_id, content)
    engine = EventEngine()
    engine.set_backtest_id(backtest_id)
    engine.set_backtest_interval("day")
    engine.set_date_start(date_start)
    engine.set_date_end(date_end)
    engine.bind_portfolio(portfolio)
    matchmaking = MatchMakingSim()
    engine.bind_matchmaking(matchmaking)
    feeder = BacktestFeed()
    feeder.subscribe(portfolio)
    engine.bind_datafeeder(feeder)

    # Event Handler Register
    engine.register(EVENT_TYPES.NEXTPHASE, engine.nextphase)
    engine.register(EVENT_TYPES.NEXTPHASE, feeder.broadcast)
    engine.register(EVENT_TYPES.PRICEUPDATE, portfolio.on_price_update)
    engine.register(EVENT_TYPES.PRICEUPDATE, matchmaking.on_price_update)
    engine.register(EVENT_TYPES.SIGNALGENERATION, portfolio.on_signal)
    engine.register(EVENT_TYPES.ORDERSUBMITTED, matchmaking.on_stock_order)
    engine.register(EVENT_TYPES.ORDERFILLED, portfolio.on_order_filled)
    engine.register(EVENT_TYPES.ORDERCANCELED, portfolio.on_order_canceled)

    t = engine.start()
    # TODO Add Backtest Record
    time_start = datetime.datetime.now()
    GNOTIFIER.echo_to_telegram(f"Backtest {id} start.")
    engine.put(EventNextPhase())

    # Remove the file and directory
    shutil.rmtree(temp_folder)
    t.join()
    GDATA.finish_backtest(random_id)
    worth = 0
    portfolio_node = engine.portfolios.head
    while portfolio_node is not None:
        portfolio = portfolio_node.value
        worth += portfolio.worth
        portfolio_node = portfolio_node.next
    GDATA.update_backtest_worth(random_id, worth)
    time_end = datetime.datetime.now()
    GNOTIFIER.echo_to_telegram(
        f"Backtest {id} finished. From {date_start} to {date_end}. Worth: {worth}  Time: {time_end - time_start}"
    )


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
        if type is FILE_TYPES.BACKTEST:
            file_format = "yml"
        else:
            file_format = "py"
        content = file_in_db.content
        temp_folder = f"{GCONF.WORKING_PATH}/{uuid.uuid4()}"
        os.mkdir(temp_folder)
        with open(f"{temp_folder}/{name}.{file_format}", "wb") as file:
            file.write(content)
        # TODO Support editor set, nvim,vim.vi,nano or vscode?
        edit_name = name.replace(" ", "\ ") if " " in name else name
        os.system(f"nvim {temp_folder}/{edit_name}.{file_format}")
        with open(f"{temp_folder}/{name}.{file_format}", "rb") as file:
            GDATA.update_file(id, type, name, file.read())
            console.print(
                f":bear: [yellow]{type}[/yellow][green bold] {name}[/green bold] Updated."
            )
        # Remove the file and directory
        shutil.rmtree(temp_folder)


@app.command()
def create(
    type: Annotated[
        ResourceType, typer.Argument(case_sensitive=False, help="File Type")
    ],
    name: Annotated[str, typer.Argument(case_sensitive=True, help="File Name")],
    source: Annotated[
        str, typer.Option(case_sensitive=True, help="Copy from Target")
    ] = "",
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
        result = GDATA.remove_file(id)
        if result:
            console.print(f":zany_face: File [yellow]{id}[/yellow] delete.")
            continue
        # Try remove backtest records
        result2 = GDATA.remove_backtest(id)
        if result2:
            console.print(
                f":zany_face: Backtest Record [light_coral]{id}[/light_coral] delete."
            )
            continue
        # Remove order records and analyzers
        result3 = GDATA.remove_orders(id)
        if result3 > 0:
            console.print(
                f":zany_face: Orders about [light_coral]{id}[/light_coral] [yellow]{result3}[/yellow] delete {result3}."
            )
            continue
        result4 = GDATA.remove_analyzers(id)
        if result4 > 0:
            console.print(
                f":zany_face: Analyzers about [light_coral]{id}[/light_coral] [yellow]{result4}[/yellow] delete {result4}."
            )
            continue
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
        file_name = (
            name if name is not "" else f"{yaml.safe_load(content)['name']}_recall"
        )
    except Exception as e:
        print(e)
    file_id = GDATA.add_file(FILE_TYPES.BACKTEST, file_name)
    GDATA.update_file(file_id, FILE_TYPES.BACKTEST, file_name, content)
    console.print(
        f":dove:  Recall the configuration of backtest [light_coral]{id}[/light_coral] as [steel_blue1]{file_name}[/steel_blue1]"
    )


@app.command()
def order(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID")] = "",
    page: Annotated[
        int, typer.Option(case_sensitive=False, help="Limit the number of output.")
    ] = 0,
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
    orders = GDATA.get_order_df_by_backtest(id)
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
        console.print(
            f":sad_but_relieved_face: Record {id} not exist. Please select one of follow."
        )
        print(GDATA.get_backtest_list_df())
        return
    console.print(
        f":sunflower: Backtest [light_coral]{id}[/light_coral]  Worth: {record.profit}"
    )
    console.print(
        f"You could use [green]ginkgo backtest res {id} analyzer_id1 analyzer_id2 ...[/green] to see detail."
    )

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

    from src.ginkgo.backtest.plots.result_plot import ResultPlot

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
