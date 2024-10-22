import pandas as pd
import os
import inspect
import math
import datetime
import time
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn, TextColumn

from ginkgo.enums import SOURCE_TYPES, FREQUENCY_TYPES, FILE_TYPES
from ginkgo.data.sources import GinkgoTushare, GinkgoTDX
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


def send_signal_test_dataworker(*args, **kwargs):
    # TODO
    pass


def send_signal_fetch_and_update_adjustfactor(*args, **kwargs):
    # TODO
    pass


def send_signal_fetch_and_update_bar(*args, **kwargs):
    # TODO
    pass


def send_signal_fetch_and_update_all_bar(*args, **kwargs):
    # TODO
    pass


def send_signal_fetch_and_update_tick(code: str, date: any, fast_mode: bool = False, *args, **kwargs):
    # Get stock list
    # Check code exist
    # Check Table exist
    # Check Data exist
    # Do fetch and update
    # TODO
    pass


def send_signal_fetch_and_update_all_tick(*args, **kwargs):
    # TODO
    pass


def send_signal_fetch_and_update_tick_summary(*args, **kwargs):
    # TODO
    pass


def send_signal_fetch_and_update_capital_adjustment(*args, **kwargs):
    # TODO
    pass


def send_signal_fetch_and_update_stockinfo(*args, **kwargs):
    # TODO
    pass


def send_signal_fetch_and_update_tradeday(*args, **kwargs):
    # TODO
    pass


# Fetch and Update


@time_logger
def fetch_and_update_adjustfactor(*args, **kwargs):
    # TODO
    pass


@skip_if_ran
@time_logger
def fetch_and_update_cn_daybar(code: str, fast_mode: bool = True, *args, **kwargs):
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
            if pd.Timestamp(item.timestamp) in data_in_db["timestamp"].values:
                update_list.append(item)
            else:
                insert_list.append(item)
            progress.update(task, advance=1, description=fix_string_length(f"{code} {item.timestamp}", 30))

    def do_update(update_list, update_dates, progress, task):
        for i in update_list:
            update_dates.append(i.timestamp)
            progress.update(task, advance=1, description=fix_string_length(f"{code} {i.timestamp}", 30))
        delete_bars_by_code_and_dates(code=code, dates=update_dates)
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
        batch_size = 200
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


@skip_if_ran
@time_logger
def fetch_and_update_tick_on_date(code: str, date: any, fast_mode: bool = False, *args, **kwargs) -> int:
    """

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
    from ginkgo.data.operations import get_ticks, delete_ticks, add_ticks
    from ginkgo.enums import TICKDIRECTION_TYPES
    from ginkgo.backtest import Tick

    # Check code
    if not is_code_in_stocklist(code):
        GLOG.DEBUG(f"Exit fetch and update tick {code} on {date}.")
        return -1
    # Get data from database
    date = datetime_normalize(date).strftime("%Y-%m-%d")
    date = datetime_normalize(date)
    start_date = date + datetime.timedelta(minutes=1)
    end_date = date + datetime.timedelta(days=1) + datetime.timedelta(minutes=-1)
    if fast_mode:
        data_in_db = get_ticks(code=code, start_date=start_date, end_date=end_date, as_dataframe=True)
        if data_in_db.shape[0] > 0:
            GLOG.DEBUG(f"{code} on {date} has {data_in_db.shape[0]} ticks in db, skip.")
            return 0
    # Fetch data
    data_from_tdx = GinkgoTDX().fetch_history_transaction_detail(code, date)
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
    batch_size = 200
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


@skip_if_ran
@time_logger
def fetch_and_update_tick(code: str, fast_mode: bool = False, *args, **kwargs):
    # Check code
    if not is_code_in_stocklist(code):
        GLOG.DEBUG(f"Exit fetch and update tick {code} on {date}.")
        return
    now = datetime.datetime.now().date()
    exit_count = 0
    should_stop = False
    # If click force_rebuild, do entire fetch and update
    while not should_stop:
        res = fetch_and_update_tick_on_date(code, now, fast_mode=fast_mode)
        if res == 2:
            exit_count = 0
        elif res == 1:
            exit_count += 1
        elif res == 0:
            exit_count = 0
        now = now + datetime.timedelta(days=-1)
        if exit_count >= 60:
            should_stop = True
        print(f"current count: {exit_count}")


@time_logger
def fetch_and_update_tick_summary(*args, **kwargs):
    # TODO
    pass


@time_logger
def fetch_and_update_tradeday(*args, **kwargs):
    # TODO
    pass


# Get


@time_logger
@cache_with_expiration
def get_stockinfos(*args, **kwargs):
    from ginkgo.data.operations import get_stockinfos

    df = get_stockinfos()
    return df


def get_adjustfactors(*args, **kwargs):
    # TODO
    pass


def get_bars(*args, **kwargs):
    from ginkgo.data.operations import get_bars as func

    return func(*args, **kwargs)


def get_ticks(*args, **kwargs):
    # TODO
    pass


def get_tick_summarys(*args, **kwargs):
    # TODO
    pass


def get_transfers(*args, **kwargs):
    # TODO
    pass


def get_signals(*args, **kwargs):
    # TODO
    pass


def get_orders(*args, **kwargs):
    # TODO
    pass


def get_order_records(*args, **kwargs):
    # TODO
    pass


def get_handlers(*args, **kwargs):
    # TODO
    pass


def add_file(*args, **kwargs):
    # TODO
    pass


def copy_file(*args, **kwargs):
    # TODO
    pass


def remove_file(*args, **kwargs):
    # TODO
    pass


def update_file(*args, **kwargs):
    # TODO
    pass


def get_file(*args, **kwargs):
    # TODO
    pass


def init_example_data(*args, **kwargs):
    # TODO Progress
    from ginkgo.data.operations import (
        get_files,
        add_file,
        delete_file,
        delete_files,
        delete_engine,
        delete_engines,
        add_engine,
        get_portfolios,
        add_portfolio,
        delete_portfolios,
    )

    # Engine
    example_engine_name = "backtest_example"
    df = get_engines(name=example_engine_name)
    if df.shape[0] > 1:
        delete_engines(ids=df["uuid"].values)
        console.print(f":sun:  [light_coral]DELETE[/] Example engines.")
        time.sleep(0.1)
    add_engine(name=example_engine_name, is_live=False)

    # File

    working_dir = GCONF.WORKING_PATH
    file_root = f"{working_dir}/src/ginkgo/backtest"

    def walk_through(folder: str, status):
        path = f"{file_root}/{folder}"
        files = os.listdir(path)
        black_list = ["__", "base"]
        for file_name in files:
            if any(substring in file_name for substring in black_list):
                continue
            file_path = f"{path}/{file_name}"
            file_name = file_name.split(".")[0]
            df = get_files(name=file_name)
            if df.shape[0] > 0:
                delete_files(ids=df["uuid"].values)
                status.update(f":sun:  [light_coral]DELETE[/] {file_type_map[folder]} {file_name}.")
                time.sleep(0.2)
            with open(file_path, "rb") as file:
                content = file.read()
                df = add_file(name=file_name, type=file_type_map[folder], data=content)
                status.update(f":sunglasses: [medium_spring_green]CREATE[/] {file_type_map[folder]} {file_name}.")
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

    # Portfolio
    example_portfolio_name = "portfolio_example"
    df = get_portfolios(example_portfolio_name)
    print(df)
    if df.shape[0] > 1:
        delete_portfolios(ids=df["uuid"].values)
        console.print(f":sun:  [light_coral]DELETE[/] Example portfolios.")
        time.sleep(0.2)
    add_portfolio(
        name=example_portfolio_name, backtest_start_date="2020-01-01", backtest_end_date="2021-01-01", is_live=False
    )
    # Handler
    # TODO
    # Engine_Portfolio_Mapping
    # TODO
    # Engine_Handler_Mapping
    # TODO


def get_files(*args, **kwargs):
    from ginkgo.data.operations import get_files as func

    return func(*args, **kwargs)


def add_engine(*args, **kwargs):
    from ginkgo.data.operations import add_engine as func

    return func(*args, **kwargs)


def get_engines(*args, **kwargs):
    from ginkgo.data.operations import get_engines as func

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
    # TODO
    pass


def compute_adjusted_prices(*args, **kwargs):
    # TODO
    pass


__all__ = [name for name, obj in inspect.getmembers(inspect.getmodule(inspect.currentframe()), inspect.isfunction)]
