import typer
from tabulate import tabulate
from enum import Enum
from typing import List as typing_list, Optional
from typing_extensions import Annotated
from rich.prompt import Prompt
from rich.console import Console
from ginkgo.client.unittest_cli import LogLevelType
from ginkgo.libs.ginkgo_logger import GLOG


app = typer.Typer(
    help=":shark: Module for BACKTEST. Build your own strategy and do backtest."
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
        print(rs)
    else:
        # If there is no file in database.
        console.print(
            f"There is no [light_coral]{filter}[/light_coral] in database. You could run [steel_blue1]ginkgo backtest init[/steel_blue1] or [steel_blue1]ginkgo backtest new [FileType][/steel_blue1]"
        )


@app.command()
def run(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID.")],
    level: Annotated[
        LogLevelType, typer.Option(case_sensitive=False, help="DEBUG Level")
    ] = "INFO",
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

    GLOG.set_level(level)

    def get_class_from_id(father_directory: str, file_id: str):
        model = GDATA.get_file(file_id)
        path = f"{father_directory}/{file_id}.py"
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
            portfolio.add_analyzer(analyzer)
        else:
            console.print(
                f":sad_but_relieved_face: Cant Locate Analyzer: {analyzer_id}"
            )
            shutil.rmtree(temp_folder)
            return
    # <-- Analyzer
    # <-- Analyzer

    engine = EventEngine()
    engine.set_backtest_id(random_id)
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

    with open(f"{temp_folder}/{id}.yml", "rb") as file:
        GDATA.add_backtest(str(random_id), file.read())
    t = engine.start()
    # TODO Add Backtest Record
    engine.put(EventNextPhase())

    # Remove the file and directory
    shutil.rmtree(temp_folder)
    t.join()
    GDATA.finish_backtest(random_id)
    profit = 0
    portfolio_node = engine.portfolios.head
    while portfolio_node is not None:
        portfolio = portfolio_node.value
        profit += portfolio.worth
        portfolio_node = portfolio_node.next
    GDATA.update_backtest_profit(random_id, profit)


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
            return
        else:
            console.print(
                f":face_with_raised_eyebrow: File [light_coral]{id}[/light_coral] not exist."
            )
        # Try remove backtest records
        result2 = GDATA.remove_backtest(id)
        if result2:
            console.print(
                f":zany_face: Backtest Record [light_coral]{id}[/light_coral] delete."
            )
        else:
            console.print(
                f":face_with_raised_eyebrow: Record [light_coral]{id}[/light_coral] not exist."
            )
            # Remove order records and analyzers
        result3 = GDATA.remove_orders(id)
        console.print(
            f":zany_face: Orders about [light_coral]{id}[/light_coral] [yellow]{result3}[/yellow] delete."
        )
        result4 = GDATA.remove_analyzers(id)
        console.print(
            f":zany_face: Analyzers about [light_coral]{id}[/light_coral] [yellow]{result4}[/yellow] delete."
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
def res(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID")] = "",
    plt: Annotated[
        bool,
        typer.Option(case_sensitive=False, help="Plot."),
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
    :one-piece_swimsuit: Show the backtest result.
    """
    from ginkgo.data.ginkgo_data import GDATA

    if id == "":
        raw = GDATA.get_backtest_list_df()
        if raw.shape[0] == 0:
            console.print(
                f":sad_but_relieved_face: There is no [light_coral]backtest record[/light_coral] in database."
            )
            return
        rs = raw[["uuid", "profit", "start_at", "finish_at"]]
        print(rs)
    else:
        if order:
            raw = GDATA.get_order_df_by_backtest(id)
            if raw.shape[0] == 0:
                console.print(
                    f":sad_but_relieved_face: There is no [light_coral]order[/light_coral] about [light_coral]{id}[/light_coral] in database."
                )
                return
            print(raw)

        raw = GDATA.get_analyzer_df_by_backtest(id)
        if raw.shape[0] == 0:
            console.print(
                f":sad_but_relieved_face: There is no [light_coral]backtest analyzer[/light_coral] about [light_coral]{id}[/light_coral] in database."
            )
            return
        if analyzer:
            # TODO Split different analyzer
            import pdb

            pdb.set_trace()
            analyzers = raw["name"].unique()
            for analyzer_name in analyzers:
                df = raw[raw["name"] == analyzer_name]
                rs = df[["timestamp", "name", "value"]]
                print(tabulate(rs, headers="keys", tablefmt="psql"))

        if plt:
            from ginkgo.backtest.plots import ResultPlot

            analyzers = raw["name"].unique()
            data = {}
            for analyzer_name in analyzers:
                df = raw[raw["name"] == analyzer_name]
                data[analyzer_name] = df

            plt = ResultPlot()
            plt.update_data(id, data)
