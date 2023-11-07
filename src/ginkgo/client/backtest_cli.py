import typer
from enum import Enum
from typing_extensions import Annotated
from rich.prompt import Prompt
from rich.console import Console
from ginkgo.client.unittest_cli import LogLevelType
from ginkgo.libs.ginkgo_logger import GLOG


app = typer.Typer(help="Module for Backtest")
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
    index = "index"


@app.command()
def init():
    """
    Copy files from default.
    """
    from ginkgo.data.ginkgo_data import GDATA

    GDATA.init_file()


@app.command()
def cat(
    id: Annotated[str, typer.Argument(case_sensitive=True)],
):
    """
    Show File content.

    """
    from ginkgo.data.ginkgo_data import GDATA

    file = GDATA.get_file(id)
    content = file.content
    console.print(content.decode("utf-8"))


@app.command()
def ls(
    resource: Annotated[ResourceType, typer.Argument(case_sensitive=False)] = None,
    a: Annotated[
        bool,
        typer.Option(case_sensitive=False, help="Show All Data, include removed file."),
    ] = False,
):
    """
    Show backtest summary.
    """
    # TODO get removed files
    from ginkgo.data.ginkgo_data import GDATA

    if resource is None:
        raw = GDATA.get_file_list_df(resource)
    else:
        from ginkgo.enums import FILE_TYPES

        resource = FILE_TYPES.enum_convert(resource)
        raw = GDATA.get_file_list_df(resource)

    if raw.shape[0] > 0:
        rs = raw[["uuid", "file_name", "type", "update"]]
        msg = ""
        if resource is None:
            msg = f":ramen: There are {raw.shape[0]} files. "
        else:
            msg = f":ramen: There are {raw.shape[0]} files about {resource}. "
        console.print(msg)
        print(rs)
    else:
        console.print(
            f"There is no {resource} in database. You could [green]ginkgo backtest new RESOURCE[/green]"
        )


@app.command()
def run_dev(
    id: Annotated[str, typer.Argument(case_sensitive=True)],
    level: Annotated[LogLevelType, typer.Option(case_sensitive=False)] = "INFO",
):
    """
    Run Backtest.
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

    def get_class_from_id(father_directory, file_id):
        model = GDATA.get_file(file_id)
        path = f"{father_directory}/{file_id}.py"
        with open(path, "wb") as file:
            file.write(model.content)
            file.flush()  # Flush the data to the disk
            os.fsync(file.fileno())  # ensure the changes are permanent
        # print(path)  # print the path variable
        # print(os.path.exists(path))  # print True if the file exists, False otherwise
        # print(os.path.isfile(path))  # )
        # print(sys.path)
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
                    import pdb

                    pdb.set_trace()
                    break
                time.sleep(2)
        if module is None:
            return None
        classes = inspect.getmembers(module, inspect.isclass)
        filtered_classes = []
        for name, cls in classes:
            if hasattr(cls, "__abstract__"):
                filtered_classes.append(cls)
        # TODO Check the length
        if len(filtered_classes) == 1:
            return filtered_classes[0]
        else:
            # TODO Raise Exception
            return None

    # 1. Create a temp folder.

    random_id = uuid.uuid4()
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
        console.print(f":sad_but_relieved_face:Cant Locate SELECOTR: {selector_id}")
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
        console.print(f":sad_but_relieved_face:Cant Locate SIZER: {sizer_id}")
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
            console.print(f":sad_but_relieved_face:Cant Locate Strategy: {strategy_id}")

    # <-- Strategy
    # <-- Strategy

    engine = EventEngine()
    engine.set_backtest_interval("day")
    engine.set_date_start(date_start)
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

    engine.start()
    engine.put(EventNextPhase())

    # Remove the file and directory
    shutil.rmtree(temp_folder)


@app.command()
def run(
    id: Annotated[str, typer.Argument(case_sensitive=True)],
):
    """
    Run Backtest.
    """
    # TODO The DEMO param should be replaced with dynamic backtest id.
    # TODO backtest id -->> backtest file -->> backtest setting.
    # TODO setting could be a yaml, include sizer_id, selector_id, start and end, strategy_ids with setting(read strategy, and export dynamic parameters to set).
    # TODO Create a temp folder, copy sizer.py selector.py and so on.
    # TODO Dynamic create a .py file with dynamic import.
    # TODO Run backtest, and do index monitor, put back to the model of backtest(strategy).
    # TODO Remove the temp folder.
    import uuid
    import os
    from ginkgo.libs.ginkgo_conf import GCONF
    from ginkgo.data.ginkgo_data import GDATA
    import shutil
    import yaml
    from ginkgo.backtest.engines import EventEngine
    from ginkgo.backtest.portfolios import PortfolioT1Backtest
    from ginkgo.libs import datetime_normalize

    # 1. Create a temp folder.

    temp_folder = f"{GCONF.WORKING_PATH}/{uuid.uuid4()}"
    os.mkdir(temp_folder)  # TODO Activa after dev

    # 2 Read config from database.
    backtest_config_model = GDATA.get_file(id)
    if backtest_config_model is None:
        print(f"Backtest {id} not exsit.")
        return

    # 2. Read the id, Get backtest config from database. Write to local temp
    content = backtest_config_model.content
    with open(f"{temp_folder}/{id}.yml", "wb") as file:
        file.write(content)

    # Read local file --> config yaml
    try:
        with open(f"{temp_folder}/{id}.yml", "r") as file:
            backtest_config = yaml.safe_load(file)
    except Exception as e:
        print(e)
        return
    if backtest_config is None:
        return

    print(backtest_config)
    backtest_name = backtest_config["name"]

    date_start = datetime_normalize(backtest_config["start"])
    date_end = datetime_normalize(backtest_config["end"])
    print(backtest_name)
    print(date_start)
    print(date_end)

    import inspect
    import importlib
    import ast

    # Get a list of all the members of the module.py file

    # Portfolio -->
    # Portfolio -->
    # TODO

    portfolio = PortfolioT1Backtest()  # TODO Read from database.

    # Selector -->
    # Selector -->

    selectors = backtest_config["selectors"]
    for selector in selectors:
        select_id = selector["id"]
        params = selector["params"]
        print("Trying add selector::")
        print(select_id)
        file_path = f"{temp_folder}/{select_id}.py"
        selector_model = GDATA.get_file(select_id)
        selector_content = selector_model.content
        with open(file_path, "wb") as file:
            file.write(selector_content)

        with open(file_path) as file:
            source = file.read()
            tree = ast.parse(source, mode="exec")
            code = compile(tree, filename=file_path, mode="exec")
            namespace = {}
            exec(code, namespace)
            node = ast.parse(source)
            classes = [n for n in node.body if isinstance(n, ast.ClassDef)]
        # TODO if there are more than 1 class in py file.
        class_obj = namespace.get(classes[0].name)
        instance = class_obj(params)
        print(instance)

    # 3. Read backtest config, Get Sizer, Selector... from database.
    # 4. Gen *.py, record the map of py file name and module.
    # 5. Gen run.py.
    # 6. Run Backtest.
    # 7. Do Records.
    # 8. Clean the temp folder.
    # shutil.rmtree(temp_folder)

    # datestart = 20000101

    # portfolio = PortfolioT1Backtest()
    # codes = GDATA.get_stock_info_df()
    # codes = codes.code.to_list()

    # codes = random.sample(codes, 200)
    # selector = FixedSelector(codes)
    # portfolio.bind_selector(selector)

    # risk = BaseRiskManagement()
    # portfolio.bind_risk(risk)

    # sizer = FixedSizer(name="500Sizer", volume=500)
    # portfolio.bind_sizer(sizer)
    # strategy = StrategyVolumeActivate()
    # win_stop = StrategyProfitLimit(5)
    # lose_stop = StrategyLossLimit(5)
    # portfolio.add_strategy(strategy)
    # portfolio.add_strategy(win_stop)
    # portfolio.add_strategy(lose_stop)

    # engine = EventEngine()
    # engine.set_backtest_interval("day")
    # engine.set_date_start(datestart)
    # engine.bind_portfolio(portfolio)
    # matchmaking = MatchMakingSim()
    # engine.bind_matchmaking(matchmaking)
    # feeder = BacktestFeed()
    # feeder.subscribe(portfolio)
    # engine.bind_datafeeder(feeder)

    # # Event Handler Register
    # engine.register(EVENT_TYPES.NEXTPHASE, engine.nextphase)
    # engine.register(EVENT_TYPES.NEXTPHASE, feeder.broadcast)
    # engine.register(EVENT_TYPES.PRICEUPDATE, portfolio.on_price_update)
    # engine.register(EVENT_TYPES.PRICEUPDATE, matchmaking.on_price_update)
    # engine.register(EVENT_TYPES.SIGNALGENERATION, portfolio.on_signal)
    # engine.register(EVENT_TYPES.ORDERSUBMITTED, matchmaking.on_stock_order)
    # engine.register(EVENT_TYPES.ORDERFILLED, portfolio.on_order_filled)
    # engine.register(EVENT_TYPES.ORDERCANCELED, portfolio.on_order_canceled)

    # engine.put(EventNextPhase())
    # engine.start()

    # # Remove the file and directory
    # shutil.rmtree(temp_folder)


@app.command()
def edit(
    id: Annotated[str, typer.Argument(case_sensitive=True)],
):
    """
    Edit Resources.
    """
    from ginkgo.data.ginkgo_data import GDATA
    from ginkgo.libs.ginkgo_conf import GCONF
    from ginkgo.enums import FILE_TYPES

    file_in_db = GDATA.get_file(id)
    if file_in_db is None:
        console.print(
            f":sad_but_relieved_face:File [yellow]{id}[/yellow] not exists. Try [green]ginkgo backtest list[/green] first."
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
    resource: Annotated[ResourceType, typer.Argument(case_sensitive=False)],
    name: Annotated[str, typer.Argument(case_sensitive=True)],
):
    """
    Create file in database.
    """
    from ginkgo.data.ginkgo_data import GDATA
    from ginkgo.enums import FILE_TYPES

    resource = FILE_TYPES.enum_convert(resource)
    if resource in FILE_TYPES:
        GDATA.add_file(resource, name)
        console.print(f"Create file [yellow]{name}[/yellow].")
    else:
        print(f"File type not support.")


@app.command()
def rm(
    id: Annotated[str, typer.Argument(case_sensitive=True)],
):
    """
    Delete file in database.
    """
    from ginkgo.data.ginkgo_data import GDATA

    result = GDATA.remove_file(id)
    if result:
        console.print(f"File [yellow]{id}[/yellow] delete.")
    else:
        console.print(f"File [red]{id}[/red] not exist.")
