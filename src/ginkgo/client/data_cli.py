import typer
import sys
from threading import Thread, Event
from multiprocessing import Process
import time
import datetime
from enum import Enum
from typing_extensions import Annotated
from rich.prompt import Prompt
from rich.console import Console
from ginkgo.libs.ginkgo_normalize import datetime_normalize
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


app = typer.Typer(help=":jigsaw: Module for DATA. CRUD about all kinds of data.")
quit_list = ["NO", "N"]
console = Console()


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
    from ginkgo.data.ginkgo_data import GDATA

    GDATA.create_all()


@app.command()
def plot(
    data: Annotated[PLTType, typer.Argument(case_sensitive=False)],
    code: Annotated[str, typer.Option(case_sensitive=False)] = "600000.SH",
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
):
    """
    Plot for BAR and TICK.
    """
    from ginkgo.data.ginkgo_data import GDATA
    from ginkgo.backtest.plots import CandlePlot

    if data == DataType.DAYBAR:
        info = GDATA.get_stock_info(code)
        raw = GDATA.get_daybar_df(code, start, end)
        code_name = info.code_name
        industry = info.industry
        df = GDATA.get_daybar_df(code, start, end)
        plt = CandlePlot(f"[{industry}] {code} {code_name}")
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
    from ginkgo.data.ginkgo_data import GDATA
    import pandas as pd

    pd.set_option("display.unicode.east_asian_width", True)
    rs = pd.DataFrame()

    if data == DataType.STOCKINFO:
        raw = GDATA.get_stock_info_df_cached(filter)
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
        raw = GDATA.get_trade_calendar_df_cached()
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
            raw = GDATA.get_order_df_by_backtest(filter)
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
    code: Annotated[str, typer.Option(case_sensitive=False)] = "600000.SH",
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
):
    """
    Show data details.
    """
    from ginkgo.data.ginkgo_data import GDATA
    import pandas as pd

    # TODO Reset the log level

    pd.set_option("display.unicode.east_asian_width", True)
    t0 = datetime.datetime.now()

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
        raw = GDATA.get_adjustfactor_df_cached(code)
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
        raw = GDATA.get_daybar_df_cached(code, start, end)
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
    data: Annotated[DataType, typer.Argument(case_sensitive=False)],
    fast: Annotated[
        bool,
        typer.Option(
            case_sensitive=False, help="If set, ginkgo will try update in fast mode."
        ),
    ] = False,
    code: Annotated[
        str,
        typer.Option(
            case_sensitive=False,
            help="If set,ginkgo will try to update the data of specific code.",
        ),
    ] = "",
    debug: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    Update the database.
    """
    from ginkgo.data.ginkgo_data import GDATA
    from ginkgo.libs.ginkgo_logger import GLOG

    if debug:
        GLOG.set_level("DEBUG")
    else:
        GLOG.set_level("INFO")
    GDATA.create_all()
    if data == DataType.ALL:
        # TODO Update all
        pass
    elif data == DataType.STOCKINFO:
        GDATA.update_stock_info()
    elif data == DataType.CALENDAR:
        GDATA.update_cn_trade_calendar()
    elif data == DataType.ADJUST:
        if code == "":
            GDATA.update_all_cn_adjustfactor_aysnc()
        else:
            GDATA.update_cn_adjustfactor(code)
    elif data == DataType.DAYBAR:
        if code == "":
            GDATA.update_all_cn_daybar_aysnc()
        else:
            GDATA.update_cn_daybar(code)
    elif data == DataType.TICK:
        if code == "":
            GDATA.update_all_cn_tick_aysnc(fast_mode=fast)
        else:
            GDATA.update_tick(code, fast_mode=fast)


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
):
    from ginkgo.data.ginkgo_data import GDATA
    from ginkgo.data.models import MOrder, MBacktest, MFile, MBacktest, MAnalyzer
    from ginkgo.libs.ginkgo_logger import GLOG

    if order:
        GDATA.drop_table(MOrder)

    if record:
        GDATA.drop_table(MBacktest)

    if file:
        GDATA.drop_table(MFile)

    if backtest:
        GDATA.drop_table(MBacktest)

    if analyzer:
        GDATA.drop_table(MAnalyzer)

    GDATA.create_all()
