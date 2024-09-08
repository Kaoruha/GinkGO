import typer
import random
import sys
from threading import Thread, Event
from multiprocessing import Process
import multiprocessing
import time
import pandas as pd
import datetime
from enum import Enum
from typing import List as typing_list
from typing_extensions import Annotated
from rich.prompt import Prompt
from rich.console import Console
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.libs.ginkgo_conf import GCONF
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    SpinnerColumn,
    TimeElapsedColumn,
)


class DataType(str, Enum):
    ALL = "all"
    STOCKINFO = "stockinfo"
    CALENDAR = "calendar"
    ADJUST = "adjustfactor"
    DAYBAR = "day"
    TICK = "tick"
    ORDER = "order"
    ANALYZER = "analyzer"


class PLTType(str, Enum):
    DAYBAR = "day"
    TICK = "tick"


class WorkerType(str, Enum):
    ON = "on"
    OFF = "off"


app = typer.Typer(
    help=":jigsaw: Module for DATA. [grey62]CRUD about all kinds of data.[/grey62]"
)
quit_list = ["NO", "N"]
console = Console()


def random_pick_one_code():
    # Random pick one

    code_list = GDATA.get_stock_info_df()
    code = random.choice(code_list.code.to_list())
    console.print(
        f":zap: No Code assigned. Random pick one code: [yellow]{code}[/yellow]"
    )
    return code


def print_df_paganation(df, page: int):
    if page > 0:
        data_length = df.shape[0]
        page_count = int(data_length / page) + 1
        for i in range(page_count):
            print(df[i * page : (i + 1) * page])
            go_next_page = Prompt.ask(
                f"Current: {(i+1)*page}/{data_length}, Conitnue? \[y/N]"
            )
            if go_next_page.upper() in quit_list:
                console.print("See you soon. :sunglasses:")
                raise typer.Abort()
    else:
        df = df.to_string()
        print(df)


def progress_bar(
    title: str,
):
    with Progress(
        SpinnerColumn(),
        # TextColumn(f"[cyan2]{title}"),
        *Progress.get_default_columns(),
        TextColumn(f":beach_with_umbrella: Elapesd: "),
        TimeElapsedColumn(),
        console=console,
        transient=True,
        refresh_per_second=100,
    ) as progress:
        task = progress.add_task(f"{title}", total=None)
        while True:
            progress.advance(task, advance=0.4)
            time.sleep(0.01)


@app.command()
def init():
    """
    Create table.
    """

    GDATA.create_all()


@app.command()
def plot(
    data: Annotated[PLTType, typer.Argument(case_sensitive=False)],
    code: Annotated[str, typer.Option(case_sensitive=False)] = "",
    start: Annotated[
        str,
        typer.Option(
            case_sensitive=False,
            help="Date Start, you could use yyyymmdd or yyyy-mm-dd",
        ),
    ] = "19900101",
    end: Annotated[
        str,
        typer.Option(
            case_sensitive=False,
            help="Date End, you could use yyyymmdd or yyyy-mm-dd",
        ),
    ] = "21200001",
    ma: Annotated[
        int,
        typer.Option(
            case_sensitive=True,
            help="moving Average",
        ),
    ] = None,
    wma: Annotated[
        int, typer.Option(case_sensitive=False, help="Weighted Moving Average")
    ] = None,
    ema: Annotated[
        int, typer.Option(case_sensitive=False, help="Exponential Moving Average")
    ] = None,
    atr: Annotated[
        int, typer.Option(case_sensitive=False, help="Average True Range")
    ] = None,
    pin: Annotated[bool, typer.Option(case_sensitive=False, help="Pin Bar")] = False,
    inf: Annotated[int, typer.Option(case_sensitive=False, help="InflectionPoint")] = 0,
    gap: Annotated[bool, typer.Option(case_sensitive=False, help="Gap")] = False,
):
    """
    Plot for BAR and TICK.
    """
    from ginkgo.backtest.plots import CandlePlot, CandleWithIndexPlot, ResultPlot
    from ginkgo.backtest.indices import (
        SimpleMovingAverage,
        WeightedMovingAverage,
        ExponentialMovingAverage,
        AverageTrueRange,
        PinBar,
        InflectionPoint,
        Gap,
    )

    if code == "":
        code = random_pick_one_code()

    if data == DataType.DAYBAR:
        info = GDATA.get_stock_info(code)
        raw = GDATA.get_daybar_df(code, start, end)
        code_name = info.code_name
        industry = info.industry
        df = GDATA.get_daybar_df(code, start, end)
        plt = CandleWithIndexPlot(f"[{industry}] {code} {code_name}")

        if ma:
            index_ma = SimpleMovingAverage(f"MovingAverage{ma}", int(ma))
            plt.add_index(index_ma, "line")
        if wma:
            index_wma = WeightedMovingAverage(f"WeightedMovingAverage{wma}", wma)
            plt.add_index(index_wma, "line")
        if ema:
            index_ema = ExponentialMovingAverage(f"ExponentialMovingAverage{ema}", ema)
            plt.add_index(index_ema, "line")
        if atr:
            index_atr = AverageTrueRange(f"AverageTrueRange{atr}", atr)
            plt.add_independent_index(index_atr, "line")
        if pin:
            index_pin = PinBar("Pin")
            plt.add_independent_index(index_pin, "scatter")
        if inf != 0:
            index_inf = InflectionPoint("InflectionPoint", inf)
            plt.add_independent_index(index_inf, "scatter")
        if gap:
            index_gap = Gap("Gap")
            plt.add_independent_index(index_gap, "line")

        plt.figure_init()
        plt.update_data(df)
        plt.show()
    elif data == DataType.TICK:
        # TODO How to plot ticks
        pass


@app.command()
def ls(
    data: Annotated[DataType, typer.Argument(case_sensitive=False)],
    page: Annotated[
        int, typer.Option(case_sensitive=False, help="Limit the number of output.")
    ] = 0,
    filter: Annotated[
        str, typer.Option(case_sensitive=True, help="Filter the output.")
    ] = "",
):
    """
    Show data summary.
    """
    # TODO limit and filter

    pd.set_option("display.unicode.east_asian_width", True)
    rs = pd.DataFrame()

    if data == DataType.STOCKINFO:
        raw = GDATA.get_stock_info_df(filter)
        if raw.shape[0] == 0:
            rs = raw
        else:
            rs = raw[
                [
                    "code",
                    "code_name",
                    "industry",
                    "currency",
                    "update",
                ]
            ]
    elif data == DataType.CALENDAR:
        raw = GDATA.get_trade_calendar_df()
        rs = raw[["timestamp", "market", "is_open"]]
    elif data == DataType.ADJUST:
        pass
    elif data == DataType.DAYBAR:
        pass
    elif data == DataType.TICK:
        pass
    elif data == DataType.ORDER:
        if filter == "":
            GLOG.WARN("Please input backtest_id to filter the order.")
            return
        else:
            raw = GDATA.get_order_df_by_portfolioid(filter)
            print(raw)
            rs = raw
        pass
    elif data == DataType.ANALYZER:
        pass

    if rs.shape[0] < page:
        print(rs.to_string())
    else:
        print_df_paganation(rs, page)


@app.command()
def show(
    data: Annotated[DataType, typer.Argument(case_sensitive=False)] = "stockinfo",
    code: Annotated[str, typer.Option(case_sensitive=False)] = "",
    start: Annotated[
        str,
        typer.Option(
            case_sensitive=False,
            help="Date Start, you could use yyyymmdd or yyyy-mm-dd",
        ),
    ] = "19900101",
    end: Annotated[
        str,
        typer.Option(
            case_sensitive=False,
            help="Date End, you could use yyyymmdd or yyyy-mm-dd",
        ),
    ] = "21200001",
    page: Annotated[
        int, typer.Option(case_sensitive=False, help="Limit the number of output.")
    ] = 0,
    filter: Annotated[
        str, typer.Option(case_sensitive=False, help="Fuzzy Search KeyWords.")
    ] = None,
):
    """
    Show data details.
    """

    # TODO Reset the log level

    pd.set_option("display.unicode.east_asian_width", True)
    t0 = datetime.datetime.now()
    if code == "":
        code = random_pick_one_code()

    if data == DataType.STOCKINFO:
        raw = GDATA.get_stock_info_df(code=code)
        if raw.shape[0] == 0:
            rs = raw
        else:
            rs = raw[
                [
                    "code",
                    "code_name",
                    "industry",
                    "currency",
                    "update",
                ]
            ]
    elif data == DataType.ADJUST:
        raw = GDATA.get_adjustfactor_df(code)
        if raw.shape[0] == 0:
            rs = raw
        else:
            rs = raw[
                [
                    "code",
                    "timestamp",
                    "foreadjustfactor",
                    "backadjustfactor",
                    "adjustfactor",
                ]
            ]
    elif data == DataType.DAYBAR:
        p = Process(
            target=progress_bar,
            args=(f"Get Daybar {code}",),
        )
        p.start()
        raw = GDATA.get_daybar_df(code, start, end)
        if raw.shape[0] == 0:
            rs = raw
        else:
            rs = raw[
                [
                    "code",
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ]
            ]
        p.kill()
        p.join()
        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.flush()
        t1 = datetime.datetime.now()
        if t1 - t0 < datetime.timedelta(seconds=1):
            console.print(
                f":zap: Daybar [yellow]{code}[/yellow] Cost: [yellow]{t1-t0}[/yellow]. Seems REDIS works."
            )
        else:
            console.print(
                f":hugging_face: Daybar [yellow]{code}[/yellow] Cost: [yellow]{t1-t0}[/yellow]"
            )

    elif data == DataType.TICK:
        if datetime_normalize(end) - datetime_normalize(start) > datetime.timedelta(
            days=10
        ):
            console.print(
                f":banana: Tick Data just support querying less than 10 days."
            )
            console.print(
                f":peach: Please optimize the [yellow]start[/yellow] or [yellow]end[/yellow] to do the query."
            )
            return
        p = Process(
            target=progress_bar,
            args=(f"Get Tick {code}",),
        )
        p.start()
        t0 = datetime.datetime.now()
        raw = GDATA.get_tick_df(code, start, end)
        if raw.shape[0] == 0:
            rs = raw
        else:
            rs = raw[["timestamp", "code", "price", "volume", "direction"]]
        p.kill()
        p.join()
        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.flush()
        t1 = datetime.datetime.now()
        if t1 - t0 < datetime.timedelta(seconds=1):
            console.print(
                f":zap: Tick [yellow]{code}[/yellow] Cost: [yellow]{t1-t0}[/yellow]."
            )
        else:
            console.print(
                f":hugging_face: Tick [yellow]{code}[/yellow] Cost: [yellow]{t1-t0}[/yellow]"
            )

    if rs.shape[0] < page:
        print(rs.to_string())
    else:
        print_df_paganation(rs, page)


@app.command()
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
        typing_list[str],
        typer.Argument(
            case_sensitive=True,
            help="If set,ginkgo will try to update the data of specific code.",
        ),
    ] = None,
    debug: Annotated[bool, typer.Option(case_sensitive=False)] = False,
    d: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    Update the database.
    """
    from ginkgo.libs.ginkgo_thread import GTM

    if debug:
        GLOG.set_level("DEBUG")
    else:
        GLOG.set_level("INFO")
    GDATA.create_all()

    l = []
    if code == []:
        info = GDATA.get_stock_info_df()
        for i, r in info.iterrows():
            c = r["code"]
            l.append(c)
    else:
        for item in code:
            l.append(item)

    if d:
        console.print(f"Current worker: {GTM.dataworker_count}")
        if GTM.dataworker_count == 0:
            console.print(
                ":sad_but_relieved_face: There is no worker running. Can not handle the update request."
            )
            return
        if a:
            GDATA.send_signal_update_stockinfo()
            GDATA.send_signal_update_calender()
            for i in l:
                GDATA.send_signal_update_adjust(i, fast)
            for i in l:
                GDATA.send_signal_update_bar(i, fast)
            for i in l:
                GDATA.send_signal_update_tick(i, fast)
            return

        if stockinfo:
            GDATA.send_signal_update_stockinfo()

        if calendar:
            GDATA.send_signal_update_calender()

        if adjust:
            for i in l:
                GDATA.send_signal_update_adjust(i, fast)

        if day:
            for i in l:
                GDATA.send_signal_update_bar(i, fast)

        if tick:
            for i in l:
                GDATA.send_signal_update_tick(i, fast)
    else:
        if a:
            GDATA.update_stock_info()
            GDATA.update_cn_trade_calendar()
            GDATA.update_all_cn_adjustfactor_aysnc(fast)
            GDATA.update_all_cn_daybar_aysnc(fast)
            GDATA.update_all_cn_tick_aysnc(fast)
            return

        if stockinfo:
            GDATA.update_stock_info()

        if calendar:
            GDATA.update_cn_trade_calendar()

        if adjust:
            if code == []:
                GDATA.update_all_cn_adjustfactor_aysnc()
            else:
                for i in l:
                    GDATA.update_cn_adjustfactor(i, fast)

        if day:
            if code == []:
                GDATA.update_all_cn_daybar_aysnc()
            else:
                for i in l:
                    GDATA.update_cn_daybar(i, fast)

        if tick:
            if code == []:
                GDATA.update_all_cn_tick_aysnc()
            else:
                for i in l:
                    GDATA.update_tick(i, fast)


@app.command()
def search(
    filter: Annotated[
        str, typer.Option(case_sensitive=True, help="Key words to search")
    ] = "",
):
    """
    Try do fuzzy search.
    """
    pass


@app.command()
def rebuild(
    order: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Order Table")
    ] = False,
    orderrecord: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild OrderRecord Table")
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
    signal: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Signal Table")
    ] = False,
    calendar: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Calendar Table")
    ] = False,
    adjust: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Adjust Table")
    ] = False,
):
    """
    :fox_face: Rebuild [light_coral]TABLE[/light_coral] in database. Attention.
    """
    from ginkgo.enums import MARKET_TYPES
    from ginkgo.data.models import (
        MOrder,
        MOrderRecord,
        MAdjustfactor,
        MBacktest,
        MFile,
        MSignal,
        MBacktest,
        MAnalyzer,
        MStockInfo,
        MTradeDay,
    )

    if order:
        GDATA.drop_table(MOrder)

    if orderrecord:
        GDATA.drop_table(MOrderRecord)
    if record:
        GDATA.drop_table(MBacktest)

    if file:
        GDATA.drop_table(MFile)

    if backtest:
        GDATA.drop_table(MBacktest)

    if analyzer:
        GDATA.drop_table(MAnalyzer)
    if signal:
        GDATA.drop_table(MSignal)

    if stockinfo:
        GDATA.drop_table(MStockInfo)

    if calendar:
        GDATA.drop_table(MTradeDay)

    if adjust:
        GDATA.drop_table(MAdjustfactor)

    GDATA.create_all()
