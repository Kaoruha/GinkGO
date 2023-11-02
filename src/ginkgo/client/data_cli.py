import typer
from enum import Enum
from typing_extensions import Annotated
from rich.prompt import Prompt
from rich.console import Console


class DataType(str, Enum):
    STOCKINFO = "stockinfo"
    CALENDAR = "calendar"
    ADJUST = "adjustfactor"
    DAYBAR = "day"
    TICK = "tick"


class PLTType(str, Enum):
    DAYBAR = "day"
    TICK = "tick"


app = typer.Typer(help="Module for DATA")
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
def list(
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

    if data == DataType.STOCKINFO:
        raw = GDATA.get_stock_info_df(code=code)
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
        raw = GDATA.get_daybar_df_cached(code, start, end)
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
    elif data == DataType.TICK:
        raw = GDATA.get_tick_df(code, start, end)
        rs = raw[["timestamp", "code", "price", "volume", "update", "direction"]]
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
):
    """
    Update the database.
    """
    from ginkgo.data.ginkgo_data import GDATA

    # from ginkgo.libs.ginkgo_logger import GLOG

    GLOG.set_level("critical")
    GDATA.create_all()

    if data == DataType.STOCKINFO:
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
