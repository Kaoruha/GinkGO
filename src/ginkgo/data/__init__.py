from typing import List, Dict

import os
import json
import psutil
import inspect
import math
import datetime
import time
import pandas as pd
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn, TextColumn

from ginkgo.enums import SOURCE_TYPES, FREQUENCY_TYPES, FILE_TYPES
from ginkgo.data.sources import GinkgoTushare, GinkgoTDX
from ginkgo.data.operations import get_stockinfo
from ginkgo.data.drivers import create_redis_connection
from ginkgo.libs import (
    GCONF,
    GLOG,
    datetime_normalize,
    to_decimal,
    skip_if_ran,
    cache_with_expiration,
    retry,
    time_logger,
    fix_string_length,
    RichProgress,
    format_time_seconds,
)

console = Console()

# Send Signal to Kafka
main_control_topic = "ginkgo_main_control"
engine_control_topic = "ginkgo_engine_control"
data_handler_topic = "ginkgo_data_handler"


def send_signal_run_engine(engine_id: str, *args, **kwargs):
    from ginkgo.data.drivers import GinkgoProducer

    global main_control_topic

    GinkgoProducer().send(main_control_topic, {"type": "run_engine", "id": str(id)})


def send_signal_stop_engine(*args, **kwargs):
    from ginkgo.data.drivers import GinkgoProducer

    global main_control_topic

    GinkgoProducer().send(main_control_topic, {"type": "kill_engine", "id": str(id)})


def send_signal_to_engine(*args, **kwargs):
    pass


def send_signal_fetch_and_update_stockinfo(*args, **kwargs):
    from ginkgo.data.drivers import GinkgoProducer

    GinkgoProducer().send("ginkgo_data_update", {"type": "stockinfo", "code": "blabla"})


def send_signal_fetch_and_update_adjustfactor(code: str, fast_mode: bool = True, *args, **kwargs):
    from ginkgo.data.drivers import GinkgoProducer

    GinkgoProducer().send("ginkgo_data_update", {"type": "adjust", "code": code, "fast": fast_mode})


def send_signal_fetch_and_update_bar(code: str, fast_mode: bool, *args, **kwargs):
    from ginkgo.data.drivers import GinkgoProducer

    GinkgoProducer().send("ginkgo_data_update", {"type": "bar", "code": code, "fast": fast_mode})


def send_signal_fetch_and_update_tick(code: str, fast_mode: bool = False, max_update: int = 0, *args, **kwargs):
    from ginkgo.data.drivers import GinkgoProducer

    GinkgoProducer().send(
        "ginkgo_data_update", {"type": "tick", "code": code, "fast": fast_mode, "max_update": max_update}
    )


def send_signal_fetch_and_update_tick_summary(*args, **kwargs):
    # TODO
    pass


def send_signal_fetch_and_update_capital_adjustment(*args, **kwargs):
    # TODO
    pass


def send_signal_fetch_and_update_tradeday(*args, **kwargs):
    # TODO
    pass


def send_signal_kill_a_worker(*args, **kwargs):
    from ginkgo.data.drivers import GinkgoProducer

    GinkgoProducer().send("ginkgo_data_update", {"type": "kill", "code": "blabla"})


# Fetch and Update


@time_logger
def fetch_and_update_adjustfactor(*args, **kwargs):
    # TODO
    pass


@retry
@skip_if_ran
@time_logger
def fetch_and_update_cn_daybar(code: str, fast_mode: bool = True, console: bool = False, *args, **kwargs):
    from ginkgo.data.models import MBar
    from ginkgo.data.operations import add_bars
    from ginkgo.data.operations.bar_crud import delete_bars_by_code_and_dates

    def split_data_into_update_and_insert(raw_data, update_list, insert_list, progress, task):
        for i, r in raw_data.iterrows():
            item = MBar(
                code=r["ts_code"],
                open=to_decimal(r["open"]),
                high=to_decimal(r["high"]),
                low=to_decimal(r["low"]),
                close=to_decimal(r["close"]),
                volume=int(r["vol"]),
                amount=to_decimal(r["amount"]),
                frequency=FREQUENCY_TYPES.DAY,
                timestamp=datetime_normalize(r["trade_date"]),
                source=SOURCE_TYPES.TUSHARE,
            )
            try:
                if pd.Timestamp(item.timestamp) in data_in_db["timestamp"].values:
                    update_list.append(item)
                else:
                    insert_list.append(item)
            except Exception as e:
                print(e)
            finally:
                pass
            progress.update(task, advance=1, description=fix_string_length(f"{code} {item.timestamp}", 30))

    def do_update(update_list, update_dates, progress, task):
        for i in update_list:
            update_dates.append(i.timestamp)
            progress.update(task, advance=1, description=fix_string_length(f"{code} {i.timestamp}", 30))
        delete_bars_by_code_and_dates(code=code, dates=update_dates)
        time.sleep(0.2)
        progress.update(task2, advance=1, description="Del Data")
        for i in range(0, len(update_list), batch_size):
            add_bars(update_list[i : i + batch_size], progress=progress)
            progress.update(task, advance=len(update_list[i : i + batch_size]), description=f"Update {code}")

    def do_insert(insert_list, progress, task):
        for i in range(0, len(insert_list), batch_size):
            add_bars(insert_list[i : i + batch_size], progress=progress)
            progress.update(task, advance=batch_size, description=f"Insert {len(insert_list[i:i+batch_size])}")

    # Check code
    if not is_code_in_stocklist(code):
        GLOG.DEBUG(f"Exit fetch and update daybar {code}.")
        return

    # Get Data from database
    if not console:
        data_in_db = get_bars(code=code, as_dataframe=True)
    else:
        with console.status(f"[bold green]Get Daybar about {code} from Clickhouse..[/]") as status:
            data_in_db = get_bars(code=code, as_dataframe=True)
            status.stop()

    start_date = GCONF.DEFAULTSTART
    end_date = datetime.datetime.now()
    if data_in_db.shape[0] == 0:
        GLOG.DEBUG(f"Code {code} has no data not db, do update.")
    elif fast_mode:
        GLOG.DEBUG(f"Update {code} in fast_mode, just fetch data from lastest timestamp.")
        start_date = data_in_db.iloc[-1]["timestamp"]

    # Fetch from tushare
    data_from_tushare = GinkgoTushare().fetch_cn_stock_daybar(code=code, start_date=start_date, end_date=end_date)

    update_list = []
    insert_list = []
    with RichProgress() as progress:
        # Split data into update and insert
        task1 = progress.add_task("[cyan]Split Date", total=data_from_tushare.shape[0])
        split_data_into_update_and_insert(data_from_tushare, update_list, insert_list, progress, task1)
        progress.update(
            task1, completed=data_from_tushare.shape[0], description=f":white_check_mark: Split {code} data Done."
        )

        # Do Update
        batch_size = 1000
        if len(update_list) > 0:
            task_count = len(update_list) * 2 + 1
            task2 = progress.add_task("[cyan]Convert Time", total=task_count)
            update_dates = []
            do_update(update_list, update_dates, progress, task2)
            progress.update(task2, completed=task_count, description=f":white_check_mark: Update {code} Daybar Done.")
        else:
            GLOG.DEBUG(f":hear-no-evil_monkey: {code} Daybar has no data to update.")

        # Do Insert
        if len(insert_list) > 0:
            task_count = len(insert_list)
            task3 = progress.add_task(f"[cyan]Insert {code}", total=task_count)
            do_insert(insert_list, progress, task3)
            progress.update(task3, completed=task_count, description=f":white_check_mark: Insert {code} Daybar Done.")
        else:
            GLOG.DEBUG(f":hear-no-evil_monkey: {code} Daybar has no data to insert.")


@time_logger
def fetch_and_update_capital_adjustment(*args, **kwargs):
    # TODO
    pass


@retry
@skip_if_ran
@time_logger
def fetch_and_update_stockinfo(*args, **kwargs):
    from ginkgo.data.models import MStockInfo
    from ginkgo.data.operations import upsert_stockinfo
    from ginkgo.enums import MARKET_TYPES, SOURCE_TYPES, CURRENCY_TYPES

    base_log = "[bold green]Fetch and update StockInfo..[/]"
    res = pd.DataFrame()

    with console.status(base_log) as status:
        status.update(base_log + "[bold green]Connecting Tushare..[/]")
        res = GinkgoTushare().fetch_cn_stockinfo()
        status.stop()
        console.print()
    l = []

    with RichProgress() as progress:
        task = progress.add_task("[cyan]Dealing", total=res.shape[0])

        for i, r in res.iterrows():
            code = r["ts_code"]
            name = r["name"]
            industry = r["industry"]
            currency = CURRENCY_TYPES.CNY
            market = MARKET_TYPES.CHINA
            list_date = r["list_date"]
            delist_date = r["delist_date"]
            upsert_stockinfo(
                code=code,
                code_name=name,
                industry=industry,
                currency=currency,
                market=market,
                list_date=list_date,
                delist_date=delist_date,
                source=SOURCE_TYPES.TUSHARE,
            )
            progress.update(task, advance=1, description=fix_string_length(f"{code} {name}", 30))
        progress.update(task, completed=True)


@time_logger
def is_tick_in_db(*args, **kwargs) -> bool:
    pass


def is_code_in_stocklist(code: str, *args, **kwargs) -> None:
    # Verify the code's validity.
    stock_list = get_stockinfos()
    if code not in stock_list["code"].values:
        GLOG.ERROR(f"Code {code} not in StockList")
        return False
    else:
        return True


@retry
@skip_if_ran
@time_logger
def fetch_and_update_tick_on_date(code: str, date: any, fast_mode: bool = False, *args, **kwargs) -> int:
    """
    Update tick on a specific date.
    :param code:
    :param date:
    :param fast_mode:
    :param args:
    :param kwargs:
    :return:
        -1 if code not in stocklist
         0 data in db, but run fast_mode
         1 no data from remote
         2 do fetch and update
    """
    from ginkgo.data.operations import delete_ticks, add_ticks
    from ginkgo.enums import TICKDIRECTION_TYPES
    from ginkgo.backtest import Tick

    # Check code
    if not is_code_in_stocklist(code):
        GLOG.DEBUG(f"Exit fetch and update tick {code} on {date}.")
        return -1
    # Get data from database
    date = datetime_normalize(date).strftime("%Y-%m-%d")
    date = datetime_normalize(date)  # TODO Have no idea why i need this.
    start_date = date + datetime.timedelta(minutes=1)
    end_date = date + datetime.timedelta(days=1) - datetime.timedelta(minutes=1)
    if fast_mode:
        data_in_db = get_ticks(code=code, start_date=start_date, end_date=end_date, as_dataframe=True)
        if data_in_db.shape[0] > 0:
            GLOG.DEBUG(f"{code} on {date} has {data_in_db.shape[0]} ticks in db, skip.")
            return 0
    # Fetch data
    data_from_tdx = GinkgoTDX().fetch_history_transaction_detail(code, date)
    if data_from_tdx is None:
        return 1
    if data_from_tdx.shape[0] == 0:
        return 1
    # Del data in db
    delete_ticks(code=code, start_date=start_date, end_date=end_date)
    # Insert
    l = []
    with RichProgress() as progress:
        task1 = progress.add_task("[cyan]Prepare Tick", total=data_from_tdx.shape[0])
        for i, r in data_from_tdx.iterrows():
            direction = TICKDIRECTION_TYPES(r["buyorsell"])
            item = Tick(
                code=code,
                price=r["price"],
                volume=r["volume"],
                direction=direction,
                timestamp=r["timestamp"],
                source=SOURCE_TYPES.TDX,
            )
            l.append(item)
            progress.update(task1, advance=1, description=f"{code} {r['timestamp']}")
        progress.update(task1, completed=data_from_tdx.shape[0], description=":white_check_mark: Prepare Tick Done.")
    batch_size = 1000
    with RichProgress() as progress:
        task2 = progress.add_task("[cyan]Insert Tick", total=data_from_tdx.shape[0])
        for i in range(0, len(l), batch_size):
            add_ticks(l[i : i + batch_size], progress=progress)
            progress.update(
                task2,
                advance=len(l[i : i + batch_size]),
                description=f"Insert Tick {code} on {date.date()}",
            )
        progress.update(
            task2, completed=len(l), description=f":white_check_mark: Insert Tick {code} on {date.date()} Done."
        )
    return 2


@time_logger
def fetch_and_update_tick(code: str, fast_mode: bool = False, max_backtrack_day: int = 0, *args, **kwargs):
    GLOG.INFO(f"Fetch and update tick {code}")
    # Check code
    if not is_code_in_stocklist(code):
        GLOG.DEBUG(f"Exit fetch and update tick {code} on {date}.")
        return
    info = get_stockinfo(code)
    if info is None:
        return
    now = datetime.datetime.now()
    list_date = info["list_date"].values[0]
    list_date = datetime_normalize(list_date)
    # If click force_rebuild, do entire fetch and update
    try:
        redis = create_redis_connection()
        redis_key = f"tick_update_{code}"
        cache_ = redis.smembers(redis_key)
        ttl = 60 * 60 * 24 * 14  # 14 Days Cache
    except Exception as e:
        cache_ = None
    if cache_:
        cache = {item.decode("utf-8") for item in cache_}
    else:
        cache = None

    update_count = 0

    while True:
        update_count += 1
        print(update_count)
        if cache is not None:
            exists = now.strftime("%Y-%m-%d") in cache
            if exists:
                now = now - datetime.timedelta(days=1)
                time_to_live = redis.ttl(redis_key)
                print(f"Updating ticks about {code} on {now} is processed, ttl: {format_time_seconds(time_to_live)}")
                if max_backtrack_day > 0 and update_count > max_backtrack_day:
                    break
                continue
        res = fetch_and_update_tick_on_date(code, now, fast_mode=fast_mode)
        should_cache = False
        if res == 2:
            console.print("do update")
            should_cache = True
        elif res == 1:
            console.print("no data from remote")
            if (datetime.datetime.now() - now).days > 2:
                should_cache = True
        elif res == 0:
            console.print("data in db")
            should_cache = True
        if redis and should_cache:
            redis.sadd(redis_key, now.strftime("%Y-%m-%d"))
            redis.expire(redis_key, ttl)
            cache_ = redis.smembers(redis_key)
            cache = {item.decode("utf-8") for item in cache_}
        now = now - datetime.timedelta(days=1)
        if now < list_date:
            break
        if max_backtrack_day > 0 and update_count > max_backtrack_day:
            break


@time_logger
def fetch_and_update_tick_summary(*args, **kwargs):
    # TODO
    pass


@time_logger
def fetch_and_update_tradeday(*args, **kwargs):
    # TODO
    print("TODO fetch_and_update_tradeday")
    pass


# Get
@cache_with_expiration
def get_stockinfos(*args, **kwargs):
    from ginkgo.data.operations import get_stockinfos_filtered as func

    return func(*args, **kwargs)


def get_adjustfactors(*args, **kwargs):
    from ginkgo.data.operations import get_adjustfactors_page_filtered as func

    return func(*args, **kwargs)


def get_bars(*args, **kwargs):
    from ginkgo.data.operations import get_bars_page_filtered as func

    return func(*args, **kwargs)


def get_ticks(*args, **kwargs):
    from ginkgo.data.operations import get_ticks_page_filtered as func

    return func(*args, **kwargs)


def get_transfers(*args, **kwargs):
    # TODO
    pass


def get_signals(*args, **kwargs):
    from ginkgo.data.operations import get_signals_page_filtered as func

    return func(*args, **kwargs)


def get_orders(*args, **kwargs):
    from ginkgo.data.operations import get_orders_page_filtered as func

    return func(*args, **kwargs)


def get_order_records(*args, **kwargs):
    from ginkgo.data.operations import get_order_records_page_filtered as func

    return func(*args, **kwargs)


def get_handlers(*args, **kwargs):
    from ginkgo.data.operations import get_handlers_page_filtered as func

    return func(*args, **kwargs)


def add_file(*args, **kwargs):
    from ginkgo.data.operations import add_file as func

    return func(*args, **kwargs)


def copy_file(*args, **kwargs):
    # got data from source
    file_type = kwargs.get("type")
    if file_type is None:
        return
    name = kwargs.get("name")
    if name is None:
        return
    clone_id = kwargs.get("clone")
    if clone_id is None:
        return

    from ginkgo.data.operations import get_file_content

    raw_content = get_file_content(id=clone_id)
    # add new file
    from ginkgo.data.operations import add_file as func

    return func(type=file_type, name=name, data=raw_content)


def delete_file(*args, **kwargs):
    from ginkgo.data.operations import delete_file as func

    return func(*args, **kwargs)


def update_file(*args, **kwargs):
    from ginkgo.data.operations import update_file as func

    return update_file(*args, **kwargs)


def get_file(*args, **kwargs):
    from ginkgo.data.operations import get_file as func

    return func(*args, **kwargs)


def init_example_data(*args, **kwargs):
    from ginkgo.data.operations.portfolio_file_mapping_crud import (
        delete_portfolio_file_mappings_filtered,
        get_portfolio_file_mappings_page_filtered,
        fget_portfolio_file_mappings_page_filtered,
    )
    from ginkgo.data.operations.file_crud import get_files_page_filtered, add_file, delete_file, delete_files
    from ginkgo.data.operations.engine_crud import delete_engine, delete_engines, add_engine
    from ginkgo.data.operations.portfolio_crud import delete_portfolios, add_portfolio, get_portfolios_page_filtered
    from ginkgo.data.operations.portfolio_file_mapping_crud import (
        add_portfolio_file_mapping,
        delete_portfolio_file_mapping,
    )

    from ginkgo.data.operations.param_crud import add_param, delete_params_filtered

    # Engine
    example_engine_name = "backtest_example"
    df = get_engines(name=example_engine_name)
    if df.shape[0] > 0:
        delete_engines(ids=df["uuid"].values.tolist())
        time.sleep(1)
        console.print(f":sun:  [light_coral]DELETE[/] Example engines.")
    engine_data = add_engine(name=example_engine_name, is_live=False)

    # File
    working_dir = GCONF.WORKING_PATH
    file_root = f"{working_dir}/src/ginkgo/backtest"

    def walk_through(folder: str, status):
        path = f"{file_root}/{folder}"
        files = os.listdir(path)
        black_list = ["__", "base"]
        count = 0
        for file_name in files:
            GLOG.DEBUG(f"Check {file_name}.")
            if any(substring in file_name for substring in black_list):
                continue
            count += 1
            file_path = f"{path}/{file_name}"
            file_name = file_name.split(".")[0]
            df = get_files_page_filtered(name=file_name)
            if df.shape[0] > 0:
                delete_files(ids=df["uuid"].values.tolist())
                status.update(f":sun:  [light_coral]DELETE[/] {file_type_map[folder]} {file_name}.")
            with open(file_path, "rb") as file:
                content = file.read()
                df = add_file(name=file_name, type=file_type_map[folder], data=content)
                status.update(f":sunglasses: [medium_spring_green]CREATE[/] {file_type_map[folder]} {file_name}.")
        console.print(f":page_facing_up: [blue]DONE[/] {count} files about {folder}.")
        status.stop()

    file_type_map = {
        "analyzers": FILE_TYPES.ANALYZER,
        "risk_managements": FILE_TYPES.RISKMANAGER,
        "selectors": FILE_TYPES.SELECTOR,
        "sizers": FILE_TYPES.SIZER,
        "strategies": FILE_TYPES.STRATEGY,
    }

    for i in file_type_map:
        with console.status(f"[bold green]Init File from source..[/]") as status:
            walk_through(i, status)
    time.sleep(0.2)

    # Portfolio
    example_portfolio_name = "portfolio_example"
    df = get_portfolios_page_filtered(example_portfolio_name)
    if df.shape[0] > 1:
        ids = df["uuid"].values.tolist()
        delete_portfolios(ids=ids)
        console.print(f":sun:  [light_coral]DELETE[/] Example portfolios.")
        with console.status(f"[bold green]Waiting for DELETING ...[/]") as status:
            while True:
                time.sleep(1)
                df = get_portfolios_page_filtered(example_portfolio_name)
                if df.shape[0] > 0:
                    time.sleep(0.2)
                else:
                    break
            status.stop()
    portfolio = add_portfolio(
        name=example_portfolio_name, backtest_start_date="2020-01-01", backtest_end_date="2021-01-01", is_live=False
    )
    console.print(f":sun:  [medium_spring_green]CREATE[/] Example portfolio.")
    # TODO Multi portfolios
    # Engine_Portfolio_Mapping
    engine_portfolio_mapping = add_engine_portfolio_mapping(engine_id=engine_data.uuid, portfolio_id=portfolio.uuid)
    console.print(f":sun:  [medium_spring_green]CREATE[/] Example engine portfolio mapping.")
    # Portfolio File Mapping
    strategy_names = ["random_choice", "loss_limit"]
    for i in strategy_names:
        raw_files = get_files_page_filtered(name=i)
        file_id = raw_files.iloc[0]["uuid"]
        name = f"example_strategy_{raw_files.iloc[0]['name']}"
        # Clean old data
        mapping_old = fget_portfolio_file_mappings_page_filtered(name=name)
        for i2, r2 in mapping_old.iterrows():
            delete_portfolio_file_mapping(r2["uuid"])
        time.sleep(1)
        new_portfolio_file_mapping = add_portfolio_file_mapping(
            portfolio_id=portfolio.uuid, file_id=file_id, name=name, type=FILE_TYPES.STRATEGY
        )
        GLOG.DEBUG(f"add new_portfolio_file_mapping: {new_portfolio_file_mapping}")
        if i == "random_choice":
            add_param(new_portfolio_file_mapping["uuid"], 0, "ExampleRandomChoice")
        if i == "loss_limit":
            add_param(new_portfolio_file_mapping["uuid"], 0, "ExampleLossLimit")
            add_param(new_portfolio_file_mapping["uuid"], 1, "13.5")
    time.sleep(1)
    df = get_files_page_filtered()

    # Portfolio Selector Mapping
    raw_selectors = get_files_page_filtered(type=FILE_TYPES.SELECTOR, name="fixed_selector")
    selector_mapping = add_portfolio_file_mapping(
        portfolio_id=portfolio.uuid,
        file_id=raw_selectors.iloc[0]["uuid"],
        name="example_fixed_selector",
        type=FILE_TYPES.SELECTOR,
    )

    code_list = ["600594.SH", "600000.SH"]
    # selector params
    add_param(selector_mapping["uuid"], 0, "example_fixed_selector")
    add_param(selector_mapping["uuid"], 1, json.dumps(code_list))
    # Portfolio Sizer Mapping
    raw_sizers = get_files_page_filtered(type=FILE_TYPES.SIZER, name="fixed_sizer")
    sizer_mapping = add_portfolio_file_mapping(
        portfolio_id=portfolio.uuid,
        file_id=raw_sizers.iloc[0]["uuid"],
        name="example_fixed_sizer",
        type=FILE_TYPES.SIZER,
    )
    # sizer param
    add_param(sizer_mapping["uuid"], 0, "example_fixed_sizer")
    add_param(sizer_mapping["uuid"], 1, "500")
    # Portfolio Analyzer Mapping
    # analyzer param
    raw_analyzers = get_files_page_filtered(type=FILE_TYPES.ANALYZER, name="profit")
    analyzer_mapping = add_portfolio_file_mapping(
        portfolio_id=portfolio.uuid,
        file_id=raw_analyzers.iloc[0]["uuid"],
        name="example_profit",
        type=FILE_TYPES.ANALYZER,
    )
    add_param(analyzer_mapping["uuid"], 0, "example_profit")

    # Handler
    # TODO
    # Engine_Handler_Mapping
    # TODO


def get_files(*args, **kwargs):
    from ginkgo.data.operations import get_files_page_filtered as func

    return func(*args, **kwargs)


def get_instance_by_file(file_id: str, mapping_id: str, file_type: FILE_TYPES):
    from ginkgo.data.operations import get_file_content
    from ginkgo.backtest.strategies import StrategyBase
    from ginkgo.backtest.analyzers import BaseAnalyzer
    from ginkgo.backtest.selectors import BaseSelector
    from ginkgo.backtest.sizers import BaseSizer
    from ginkgo.backtest.risk_managements import BaseRiskManagement

    cls_base_mapping = {
        FILE_TYPES.ANALYZER: BaseAnalyzer,
        FILE_TYPES.RISKMANAGER: BaseRiskManagement,
        FILE_TYPES.SELECTOR: BaseSelector,
        FILE_TYPES.SIZER: BaseSizer,
        FILE_TYPES.STRATEGY: StrategyBase,
    }

    content = get_file_content(file_id)
    if len(content) == 0:
        return
    # 直接在全局作用域中执行 exec
    namespace = {}
    exec(content.decode("utf-8"), namespace)
    # exec(content.decode("utf-8"), globals())

    classes = [
        cls for cls in namespace.values() if isinstance(cls, type) and cls_base_mapping[file_type] in cls.__bases__
    ]
    if len(classes) == 0:
        raise ValueError(f"未找到任何 {cls_base_mapping[file_type]} 的子类")
    cls = classes[0]
    from ginkgo.data.operations import get_params_page_filtered

    params = get_params_page_filtered(mapping_id)
    if params.shape[0] > 0:
        params = params["value"].values
    else:
        params = []
    try:
        ins = cls(*params)  # 实例化类
        if file_type == FILE_TYPES.ANALYZER:
            ins.set_analyzer_id(file_id)
        return ins
    except Exception as e:
        # DEBUG
        print(1)
        return None
    finally:
        pass


def get_trading_system_components_by_portfolio(portfolio_id: str, file_type: FILE_TYPES = None, *args, **kwargs):
    if not isinstance(file_type, FILE_TYPES):
        GLOG.WARN(f"Invalid type: {type}.")
        return []
    from ginkgo.data.operations import get_portfolio_file_mappings_page_filtered

    mappings = get_portfolio_file_mappings_page_filtered(portfolio_id=portfolio_id, type=file_type)
    l = []
    for i, r in mappings.iterrows():
        file_id = r["file_id"]
        mapping_id = r["uuid"]
        ins = get_instance_by_file(file_id, mapping_id, file_type)
        if ins is not None:
            l.append(ins)
    return l


def get_analyzers_by_portfolio(portfolio_id: str, *args, **kwargs):
    # TODO
    pass


def add_engine(*args, **kwargs):
    from ginkgo.data.operations import add_engine as func

    return func(*args, **kwargs)


def get_engine(*args, **kwargs):
    from ginkgo.data.operations import get_engine as func

    return func(*args, **kwargs)


def get_engines(*args, **kwargs):
    from ginkgo.data.operations import get_engines_page_filtered as func

    return func(*args, **kwargs)


def add_portfolio(*args, **kwargs):
    # TODO
    pass


def remove_portfolio(*args, **kwargs):
    # TODO
    pass


def update_portfolio(*args, **kwargs):
    # TODO
    pass


def get_portfolio(*args, **kwargs):
    from ginkgo.data.operations import get_portfolio as func

    return func(*args, **kwargs)


def get_portfolios(*args, **kwargs):
    from ginkgo.data.operations import get_portfolios_page_filtered as func

    return func(*args, **kwargs)


def delete_portfolio(*args, **kwargs):
    from ginkgo.data.operations import delete_portfolio as func

    return func(*args, **kwargs)


def delete_portfolios(*args, **kwargs):
    from ginkgo.data.operations import delete_portfolios_filtered as func

    return func(*args, **kwargs)


def compute_adjusted_prices(*args, **kwargs):
    # TODO
    pass


def add_engine_portfolio_mapping(*args, **kwargs):
    from ginkgo.data.operations import add_engine_portfolio_mapping as func

    return func(*args, **kwargs)


def get_engine_portfolio_mappings(*args, **kwargs):
    from ginkgo.data.operations import get_engine_portfolio_mappings_page_filtered as func

    return func(*args, **kwargs)


def add_engine_handler_mapping(*args, **kwargs):
    from ginkgo.data.operations import add_engine_handler_mapping as func

    return func(*args, **kwargs)


def get_engine_handler_mappings(*args, **kwargs):
    from ginkgo.data.operations import get_engine_handler_mappings_page_filtered as func

    return func(*args, **kwargs)


def remove_from_redis(key: str, *args, **kwargs):
    from ginkgo.libs import create_redis_connection

    conn = create_redis_connection()
    conn.delete(key)


__all__ = [name for name, obj in inspect.getmembers(inspect.getmodule(inspect.currentframe()), inspect.isfunction)]
