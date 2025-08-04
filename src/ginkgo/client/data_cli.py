import typer
from enum import Enum
from typing import List as typing_list
from typing_extensions import Annotated
from rich.prompt import Prompt, Confirm
from rich.console import Console
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    SpinnerColumn,
    TimeElapsedColumn,
)

# All heavy imports moved to function level for faster CLI startup

console = Console()


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
    help=":jigsaw: Module for [bold medium_spring_green]DATA[/]. [grey62]CRUD about all kinds of data.[/grey62]",
    no_args_is_help=True,
)
quit_list = ["NO", "N"]


def random_pick_one_code():
    # Random pick one
    import random
    from ginkgo.data import get_stockinfos

    code_list = get_stockinfos()
    code = random.choice(code_list.code.to_list())
    console.print(f":zap: No Code assigned. Random pick one code: [yellow]{code}[/yellow]")
    return code




def progress_bar(title: str):
    import time
    
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
    :construction: Initialize database tables and example data.
    """
    from ginkgo.data.drivers import create_all_tables as func

    func()

    from ginkgo.data import init_example_data as func

    func()


@app.command()
def plot(
    data: Annotated[PLTType, typer.Argument(case_sensitive=False, help=":bar_chart: Data type to plot (day/tick)")],
    code: Annotated[str, typer.Option("--code", "-c", case_sensitive=False, help=":chart_with_upwards_trend: Stock code (e.g., 000001.SZ)")] = "",
    start: Annotated[
        str,
        typer.Option(
            "--start", "-s",
            case_sensitive=False,
            help=":calendar: Start date (yyyymmdd or yyyy-mm-dd)",
        ),
    ] = "19900101",
    end: Annotated[
        str,
        typer.Option(
            "--end", "-e",
            case_sensitive=False,
            help=":calendar: End date (yyyymmdd or yyyy-mm-dd)",
        ),
    ] = "21200001",
    ma: Annotated[
        int,
        typer.Option(
            case_sensitive=True,
            help=":chart_with_upwards_trend: Simple Moving Average period",
        ),
    ] = None,
    wma: Annotated[int, typer.Option(case_sensitive=False, help=":bar_chart: Weighted Moving Average period")] = None,
    ema: Annotated[int, typer.Option(case_sensitive=False, help=":chart_with_downwards_trend: Exponential Moving Average period")] = None,
    atr: Annotated[int, typer.Option(case_sensitive=False, help=":bar_chart: Average True Range period")] = None,
    pin: Annotated[bool, typer.Option(case_sensitive=False, help=":round_pushpin: Show Pin Bar patterns")] = False,
    inf: Annotated[int, typer.Option(case_sensitive=False, help=":arrows_counterclockwise: Inflection Point detection period")] = 0,
    gap: Annotated[bool, typer.Option(case_sensitive=False, help=":bar_chart: Show Gap patterns")] = False,
    adjusted: Annotated[bool, typer.Option("--adjusted", "-adj", help=":arrows_counterclockwise: Show price-adjusted data")] = False,
    adj_type: Annotated[str, typer.Option("--adj-type", help=":arrows_counterclockwise: Adjustment type (fore/back)")] = "fore",
):
    """
    :chart_with_upwards_trend: Plot candlestick charts with technical indicators.
    """
    from ginkgo.backtest.analysis.plots import CandlePlot, CandleWithIndexPlot, ResultPlot
    from ginkgo.backtest.computation import (
        SimpleMovingAverage,
        WeightedMovingAverage,
        ExponentialMovingAverage,
        AverageTrueRange,
        PinBar,
        InflectionPoint,
        Gap,
    )
    from ginkgo.data import get_stockinfos, get_bars, get_bars_adjusted
    from ginkgo.enums import ADJUSTMENT_TYPES

    if code == "":
        code = random_pick_one_code()

    if data == DataType.DAYBAR:
        info_df = get_stockinfos()
        info = info_df[info_df['code'] == code].iloc[0] if len(info_df[info_df['code'] == code]) > 0 else None
        if info is None:
            console.print(f"Stock {code} not found")
            return
        
        # 根据adjusted参数选择获取原始数据还是复权数据
        if adjusted:
            # 验证adj_type参数
            if adj_type.lower() not in ['fore', 'back']:
                console.print(f":x: Invalid adjustment type: {adj_type}. Must be 'fore' or 'back'.")
                return
            adjustment_type = ADJUSTMENT_TYPES.FORE if adj_type.lower() == 'fore' else ADJUSTMENT_TYPES.BACK
            raw = get_bars_adjusted(code=code, adjustment_type=adjustment_type, start_date=start, end_date=end, as_dataframe=True)
            console.print(f":arrows_counterclockwise: Using {adj_type} adjustment for price data")
        else:
            raw = get_bars(code=code, start_date=start, end_date=end, as_dataframe=True)
        
        code_name = info.code_name
        industry = info.industry
        df = raw
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


@app.command(name="list")
def list(
    data: Annotated[DataType, typer.Argument(case_sensitive=False, help=":bar_chart: Data type to list")],
    page: Annotated[int, typer.Option("--page", "-p", case_sensitive=False, help=":page_facing_up: Items per page (0=no pagination)")] = 0,
    filter: Annotated[str, typer.Option("--filter", case_sensitive=True, help=":mag: Filter keyword")] = "",
):
    """
    :page_facing_up: Display data summary in paginated format.
    """
    # Import ginkgo modules at function level for faster CLI startup
    import pandas as pd
    from ginkgo.libs import GLOG
    from ginkgo.libs.utils.display import display_dataframe_interactive
    from ginkgo.data import get_orders
    
    # TODO limit and filter

    pd.set_option("display.unicode.east_asian_width", True)
    rs = pd.DataFrame()
    from ginkgo.data import get_stockinfos

    if data == DataType.STOCKINFO:
        raw = get_stockinfos()
        if raw.shape[0] == 0:
            rs = raw
        else:
            rs = raw[
                [
                    "code",
                    "code_name",
                    "industry",
                    "currency",
                    "update_at",
                ]
            ]
    elif data == DataType.CALENDAR:
        # TODO: implement calendar data retrieval
        rs = pd.DataFrame(columns=["timestamp", "market", "is_open"])
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
            raw = get_orders(portfolio_id=filter, as_dataframe=True)
            print(raw)
            rs = raw
        pass
    elif data == DataType.ANALYZER:
        pass

    display_dataframe_interactive(
        data=rs,
        columns_config=None,  # Use default column configuration
        title=None,
        page_size=page if page > 0 else 20,
        enable_interactive=(page > 0 and rs.shape[0] > page),
        console=console
    )


@app.command()
def show(
    data: Annotated[DataType, typer.Argument(case_sensitive=False, help=":bar_chart: Data type to show")] = "stockinfo",
    code: Annotated[str, typer.Option("--code", "-c", case_sensitive=False, help=":chart_with_upwards_trend: Stock code filter")] = "",
    start: Annotated[
        str,
        typer.Option(
            "--start", "-s",
            case_sensitive=False,
            help=":calendar: Start date (yyyymmdd or yyyy-mm-dd)",
        ),
    ] = "19900101",
    end: Annotated[
        str,
        typer.Option(
            "--end", "-e",
            case_sensitive=False,
            help=":calendar: End date (yyyymmdd or yyyy-mm-dd)",
        ),
    ] = "21200001",
    page: Annotated[int, typer.Option("--page", "-p", case_sensitive=False, help=":page_facing_up: Items per page (0=no pagination)")] = 0,
    filter: Annotated[str, typer.Option("--filter", case_sensitive=False, help=":mag: Fuzzy search keywords")] = None,
    debug: Annotated[bool, typer.Option("--debug", "-d", case_sensitive=False, help=":bug: Enable debug logging")] = False,
    adjusted: Annotated[bool, typer.Option("--adjusted", "-adj", help=":arrows_counterclockwise: Show price-adjusted data")] = False,
    adj_type: Annotated[str, typer.Option("--adj-type", help=":arrows_counterclockwise: Adjustment type (fore/back)")] = "fore",
):
    """
    :mag: Show detailed data with filters and date range.
    """
    # Import ginkgo modules at function level for faster CLI startup
    import pandas as pd
    import datetime
    import sys
    from multiprocessing import Process
    from ginkgo.libs import GLOG, datetime_normalize
    from ginkgo.data import get_stockinfos, get_adjustfactors, get_ticks, get_bars_adjusted, get_ticks_adjusted
    from ginkgo.libs.utils.display import display_dataframe_interactive
    from ginkgo.enums import ADJUSTMENT_TYPES

    if debug:
        GLOG.set_level("DEBUG")
    else:
        GLOG.set_level("INFO")

    # if code == "":
    #     code = random_pick_one_code()
    pd.set_option("display.unicode.east_asian_width", True)

    if data == DataType.STOCKINFO:
        raw = get_stockinfos()
        if code != "":
            raw = raw[raw["code"] == code]
        if raw.shape[0] == 0:
            rs = raw
        else:
            rs = raw[
                [
                    "code",
                    "code_name",
                    "industry",
                    "currency",
                    "update_at",
                ]
            ]
    elif data == DataType.ADJUST:
        raw = get_adjustfactors(code=code, as_dataframe=True)
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
        from ginkgo.data import get_bars

        # 根据adjusted参数选择获取原始数据还是复权数据
        if adjusted:
            # 验证adj_type参数
            if adj_type.lower() not in ['fore', 'back']:
                console.print(f":x: Invalid adjustment type: {adj_type}. Must be 'fore' or 'back'.")
                return
            adjustment_type = ADJUSTMENT_TYPES.FORE if adj_type.lower() == 'fore' else ADJUSTMENT_TYPES.BACK
            raw = get_bars_adjusted(code=code, adjustment_type=adjustment_type, start_date=start, end_date=end, as_dataframe=True)
            console.print(f":arrows_counterclockwise: Using {adj_type} adjustment for price data")
        else:
            raw = get_bars(code=code, start_date=start, end_date=end, as_dataframe=True)
        
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

    elif data == DataType.TICK:
        if datetime_normalize(end) - datetime_normalize(start) > datetime.timedelta(days=10):
            console.print(f":banana: Tick Data just support querying less than 10 days.")
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
        
        # 根据adjusted参数选择获取原始数据还是复权数据
        if adjusted:
            # 验证adj_type参数
            if adj_type.lower() not in ['fore', 'back']:
                console.print(f":x: Invalid adjustment type: {adj_type}. Must be 'fore' or 'back'.")
                return
            adjustment_type = ADJUSTMENT_TYPES.FORE if adj_type.lower() == 'fore' else ADJUSTMENT_TYPES.BACK
            raw = get_ticks_adjusted(code=code, adjustment_type=adjustment_type, start_date=start, end_date=end, as_dataframe=True)
            console.print(f":arrows_counterclockwise: Using {adj_type} adjustment for tick data")
        else:
            raw = get_ticks(code=code, start_date=start, end_date=end, as_dataframe=True)
        
        t1 = datetime.datetime.now()
        if raw.shape[0] == 0:
            rs = raw
        else:
            rs = raw[["timestamp", "code", "price", "volume", "direction"]]
        p.kill()
        p.join()
        sys.stdout.write("\r" + " " * 100 + "\r")
        sys.stdout.flush()
        if t1 - t0 < datetime.timedelta(seconds=1):
            console.print(f":zap: Tick [yellow]{code}[/yellow] Cost: [yellow]{t1-t0}[/yellow].")
        else:
            console.print(f":hugging_face: Tick [yellow]{code}[/yellow] Cost: [yellow]{t1-t0}[/yellow]")

    display_dataframe_interactive(
        data=rs,
        columns_config=None,  # Use default column configuration
        title=None,
        page_size=page if page > 0 else 20,
        enable_interactive=(page > 0 and rs.shape[0] > page),
        console=console
    )


@app.command()
def update(
    a: Annotated[bool, typer.Option("--all", "-a", case_sensitive=False, help=":arrows_counterclockwise: Update everything")] = False,
    # data: Annotated[DataType, typer.Argument(case_sensitive=False)],
    stockinfo: Annotated[bool, typer.Option("--stockinfo", case_sensitive=False, help=":chart_with_upwards_trend: Update stock info")] = False,
    calendar: Annotated[bool, typer.Option("--calendar", case_sensitive=False, help=":calendar: Update trading calendar")] = False,
    adjust: Annotated[bool, typer.Option("--adjust", case_sensitive=False, help=":arrows_counterclockwise: Update adjustment factors")] = False,
    day: Annotated[bool, typer.Option("--day", case_sensitive=False, help=":bar_chart: Update daily bar data")] = False,
    tick: Annotated[bool, typer.Option("--tick", case_sensitive=False, help=":zap: Update tick data")] = False,
    daemon: Annotated[bool, typer.Option("--daemon", "-D", case_sensitive=False, help=":wrench: Run in background worker mode")] = False,
    fast: Annotated[
        bool,
        typer.Option("--fast", "-F", case_sensitive=False, help=":zap: Fast mode (incremental update)"),
    ] = False,
    code: Annotated[
        typing_list[str],
        typer.Argument(
            case_sensitive=True,
            help=":chart_with_upwards_trend: Specific stock codes to update (e.g., 000001.SZ 000002.SZ)",
        ),
    ] = None,
    max_update: Annotated[int, typer.Option("--max-update", case_sensitive=False, help=":bar_chart: Max days to backtrack for tick data")] = 0,
    debug: Annotated[bool, typer.Option("--debug", "-d", case_sensitive=False, help=":bug: Enable debug logging")] = False,
):
    """
    :arrows_counterclockwise: Update database with latest market data.
    """
    from ginkgo.libs import GTM, GLOG
    from ginkgo.data import (
        get_stockinfos,
        fetch_and_update_stockinfo,
        fetch_and_update_adjustfactor,
        fetch_and_update_tradeday,
        fetch_and_update_cn_daybar,
        fetch_and_update_tick,
    )
    from ginkgo.data.containers import container

    # Set debug level
    if debug:
        GLOG.set_level("DEBUG")
    else:
        GLOG.set_level("INFO")

    l = []
    if code == None:
        info = get_stockinfos()
        for i, r in info.iterrows():
            c = r["code"]
            l.append(c)
    else:
        for item in code:
            l.append(item)

    if daemon:
        worker_count = GTM.get_worker_count()
        console.print(f"Current worker: {worker_count}")
        if worker_count == 0:
            console.print(":sad_but_relieved_face: There is no worker running. Can not handle the update request.")
            return
        
        kafka_service = container.kafka_service()
        
        if a:
            kafka_service.send_stockinfo_update_signal()
            # GDATA.send_signal_update_calender() # TODO
            for i in l:
                kafka_service.send_adjustfactor_update_signal(i, fast)
            for i in l:
                kafka_service.send_daybar_update_signal(i, fast)
            for i in l:
                kafka_service.send_tick_update_signal(i, fast, max_update)
            return

        if stockinfo:
            kafka_service.send_stockinfo_update_signal()

        if calendar:
            # TODO
            print("update canlerdar in future.")
            # GDATA.send_signal_update_calender()

        if adjust:
            if code == None:
                stockinfos = get_stockinfos()
                for i, r in stockinfos.iterrows():
                    stock_code = r["code"]
                    kafka_service.send_adjustfactor_update_signal(stock_code, fast)
            else:
                for i in l:
                    kafka_service.send_adjustfactor_update_signal(i, fast)

        if day:
            if code == None:
                stockinfos = get_stockinfos()
                for i, r in stockinfos.iterrows():
                    stock_code = r["code"]
                    kafka_service.send_daybar_update_signal(stock_code, fast)
            else:
                for i in l:
                    kafka_service.send_daybar_update_signal(i, fast)

        if tick:
            if code == None:
                stockinfos = get_stockinfos()
                for i, r in stockinfos.iterrows():
                    stock_code = r["code"]
                    kafka_service.send_tick_update_signal(stock_code, fast, max_update)
            else:
                for i in l:
                    kafka_service.send_tick_update_signal(i, fast, max_update)

    else:
        if a:
            fetch_and_update_stockinfo()
            fetch_and_update_tradeday()
            stockinfos = get_stockinfos()
            for i, r in stockinfos.iterrows():
                stock_code = r["code"]
                fetch_and_update_cn_daybar(stock_code, fast)
                fetch_and_update_adjustfactor(stock_code, fast)
                fetch_and_update_tick(stock_code, fast, max_update)
            return

        if stockinfo:
            fetch_and_update_stockinfo()

        if calendar:
            fetch_and_update_tradeday()

        if adjust:
            if code == None:
                stockinfos = get_stockinfos()
                for i, r in stockinfos.iterrows():
                    stock_code = r["code"]
                    fetch_and_update_adjustfactor(stock_code, fast)
            else:
                for i in l:
                    fetch_and_update_adjustfactor(i, fast)

        if day:
            if code == None:
                stockinfos = get_stockinfos()
                for i, r in stockinfos.iterrows():
                    stock_code = r["code"]
                    fetch_and_update_cn_daybar(stock_code, fast)
            else:
                for i in l:
                    fetch_and_update_cn_daybar(i, fast)

        if tick:
            if code == None:
                stockinfos = get_stockinfos()
                for i, r in stockinfos.iterrows():
                    stock_code = r["code"]
                    fetch_and_update_tick(stock_code, fast, max_update)
            else:
                for i in l:
                    fetch_and_update_tick(i, fast, max_update)


@app.command()
def search(
    filter: Annotated[str, typer.Option(case_sensitive=True, help=":mag: Keywords to search in data")] = "",
):
    """
    :mag_right: Search data using fuzzy matching keywords.
    """
    pass


@app.command()
def rebuild(
    engine: Annotated[bool, typer.Option(case_sensitive=False, help=":wrench: Rebuild Engine Table")] = False,
    portfolio: Annotated[bool, typer.Option(case_sensitive=False, help=":briefcase: Rebuild Portfolio Table")] = False,
    order: Annotated[bool, typer.Option(case_sensitive=False, help=":clipboard: Rebuild Order Table")] = False,
    orderrecord: Annotated[bool, typer.Option(case_sensitive=False, help=":memo: Rebuild OrderRecord Table")] = False,
    file: Annotated[bool, typer.Option(case_sensitive=False, help=":file_folder: Rebuild File Table")] = False,
    param: Annotated[bool, typer.Option(case_sensitive=False, help=":gear: Rebuild Param Table")] = False,
    analyzerrecord: Annotated[bool, typer.Option(case_sensitive=False, help=":bar_chart: Rebuild Analyzer Table")] = False,
    stockinfo: Annotated[bool, typer.Option(case_sensitive=False, help=":chart_with_upwards_trend: Rebuild StockInfo Table")] = False,
    signal: Annotated[bool, typer.Option(case_sensitive=False, help=":satellite_antenna: Rebuild Signal Table")] = False,
    calendar: Annotated[bool, typer.Option(case_sensitive=False, help=":calendar: Rebuild Calendar Table")] = False,
    adjust: Annotated[bool, typer.Option(case_sensitive=False, help=":arrows_counterclockwise: Rebuild Adjustment Table")] = False,
):
    """
    :building_construction: Rebuild database tables (DANGEROUS: Will delete existing data).
    """
    from ginkgo.enums import MARKET_TYPES
    from ginkgo.data.drivers import drop_table, create_all_tables
    from ginkgo.data.models import (
        MOrder,
        MPortfolio,
        MOrderRecord,
        MAdjustfactor,
        MFile,
        MSignal,
        MAnalyzerRecord,
        MStockInfo,
        MTradeDay,
        MEngine,
        MParam,
    )

    if engine:
        drop_table(MEngine)

    if portfolio:
        drop_table(MPortfolio)

    if order:
        drop_table(MOrder)

    if orderrecord:
        drop_table(MOrderRecord)

    if file:
        drop_table(MFile)

    if param:
        drop_table(MParam)

    if analyzerrecord:
        drop_table(MAnalyzerRecord)

    if signal:
        drop_table(MSignal)

    if stockinfo:
        drop_table(MStockInfo)

    if calendar:
        drop_table(MTradeDay)

    if adjust:
        drop_table(MAdjustfactor)

    # TODO Mapping

    create_all_tables()


@app.command()
def calc(
    code: Annotated[
        typing_list[str],
        typer.Argument(
            case_sensitive=True,
            help=":chart_with_upwards_trend: Specific stock codes to calculate adjust factors (e.g., 000001.SZ 000002.SZ). Leave empty to process all stocks.",
        ),
    ] = None,
    all: Annotated[bool, typer.Option("--all", "-a", case_sensitive=False, help=":arrows_counterclockwise: Calculate adjust factors for all stocks")] = False,
    debug: Annotated[bool, typer.Option("--debug", "-d", case_sensitive=False, help=":bug: Enable debug logging")] = False,
):
    """
    :bar_chart: Calculate fore/back adjust factors based on existing adj_factor data.
    
    This command recalculates the fore/back adjust factors from the original 
    adj_factor data already stored in the database. Use this after updating 
    adjust factor data with 'ginkgo data update --adjust'.
    
    Examples:
        ginkgo data calc 000001.SZ           # Calculate for single stock
        ginkgo data calc 000001.SZ 000002.SZ # Calculate for specific stocks  
        ginkgo data calc --all               # Calculate for all stocks
        ginkgo data calc                     # Calculate for all stocks (default)
    """
    from ginkgo.libs import GLOG
    from ginkgo.data.containers import container
    
    # Set debug level
    if debug:
        GLOG.set_level("DEBUG")
    else:
        GLOG.set_level("INFO")
    
    adjustfactor_service = container.adjustfactor_service()
    
    # Determine codes to process
    if all or code is None:
        # Process all available codes
        console.print(":arrows_counterclockwise: Calculating adjust factors for [yellow]all stocks[/yellow]...")
        result = adjustfactor_service.recalculate_adjust_factors_batch()
    else:
        # Process specific codes
        codes_list = list(code)  # Convert from tuple to list
        console.print(f":chart_with_upwards_trend: Calculating adjust factors for [yellow]{len(codes_list)}[/yellow] stocks: {', '.join(codes_list)}")
        result = adjustfactor_service.recalculate_adjust_factors_batch(codes_list)
    
    # Display results summary
    total_codes = result["total_codes"]
    successful_codes = result["successful_codes"]
    failed_codes = result["failed_codes"]
    total_records_updated = result["total_records_updated"]
    
    if successful_codes > 0:
        console.print(f":white_check_mark: Successfully processed [green]{successful_codes}[/green] stocks")
        console.print(f":bar_chart: Updated [green]{total_records_updated}[/green] adjust factor records")
    
    if failed_codes > 0:
        console.print(f":x: Failed to process [red]{failed_codes}[/red] stocks")
        
        # Show failure details
        failures = result.get("failures", [])
        if failures:
            console.print(":warning: [yellow]Failure Details:[/yellow]")
            for failure in failures[:10]:  # Show first 10 failures
                code_str = failure.get("code", "Unknown")
                error_str = failure.get("error", "Unknown error")
                console.print(f"  - [red]{code_str}[/red]: {error_str}")
            
            if len(failures) > 10:
                console.print(f"  ... and {len(failures) - 10} more failures")
    
    # Final summary
    if total_codes == 0:
        console.print(":warning: [yellow]No stocks to process[/yellow]")
    elif successful_codes == total_codes:
        console.print(f":tada: [green]All {total_codes} stocks processed successfully![/green]")
    else:
        console.print(f":information: Processed {successful_codes}/{total_codes} stocks successfully")


@app.command()
def clean():
    """
    :broom: Clean database by removing dirty data and invalid mappings.
    """
    from ginkgo.data import clean_portfolio_file_mapping as func

    func()
    from ginkgo.data import clean_engine_portfolio_mapping as func

    func()


@app.command()
def stats():
    """
    :bar_chart: Display comprehensive database statistics.
    
    Shows counts, data ranges, and availability statistics for all data types
    including stock info, bars, ticks, adjustment factors, and trading data.
    """
    from ginkgo.data.containers import container
    from rich.table import Table
    from rich.panel import Panel
    from rich.columns import Columns
    import datetime
    
    console.print(":bar_chart: [bold blue]Ginkgo Database Statistics[/bold blue]")
    console.print()
    
    # 获取各种服务
    stockinfo_service = container.stockinfo_service()
    bar_service = container.bar_service()
    tick_service = container.tick_service()
    adjustfactor_service = container.adjustfactor_service()
    
    # 创建统计表格
    stats_table = Table(title=":bar_chart: Data Statistics", show_header=True, header_style="bold magenta")
    stats_table.add_column("Data Type", style="cyan", width=20)
    stats_table.add_column("Total Records", justify="right", style="green", width=15)
    stats_table.add_column("Available Codes", justify="right", style="yellow", width=15)
    stats_table.add_column("Date Range", style="dim", width=25)
    
    # 获取股票信息统计
    try:
        stockinfos = stockinfo_service.get_stockinfos(as_dataframe=True)
        stock_count = len(stockinfos) if stockinfos is not None and len(stockinfos) > 0 else 0
        stats_table.add_row(
            ":chart_with_upwards_trend: Stock Info", 
            str(stock_count), 
            str(stock_count),
            "N/A"
        )
    except Exception as e:
        stats_table.add_row(":chart_with_upwards_trend: Stock Info", "Error", "Error", str(e)[:20])
    
    # 获取日线数据统计
    try:
        bar_codes = bar_service.get_available_codes()
        bar_count = bar_service.count_bars()
        stats_table.add_row(
            ":bar_chart: Daily Bars", 
            f"{bar_count:,}" if bar_count else "0", 
            str(len(bar_codes)) if bar_codes else "0",
            "Various ranges"
        )
    except Exception as e:
        stats_table.add_row(":bar_chart: Daily Bars", "Error", "Error", str(e)[:20])
    
    # 获取逐笔数据统计
    try:
        tick_codes = tick_service.get_available_codes()
        tick_count = tick_service.count_ticks()
        stats_table.add_row(
            ":zap: Tick Data", 
            f"{tick_count:,}" if tick_count else "0", 
            str(len(tick_codes)) if tick_codes else "0",
            "Recent days"
        )
    except Exception as e:
        stats_table.add_row(":zap: Tick Data", "Error", "Error", str(e)[:20])
    
    # 获取复权因子统计
    try:
        adj_codes = adjustfactor_service.get_available_codes()
        adj_count = adjustfactor_service.count_adjustfactors()
        stats_table.add_row(
            ":arrows_counterclockwise: Adjust Factors", 
            f"{adj_count:,}" if adj_count else "0", 
            str(len(adj_codes)) if adj_codes else "0",
            "Historical data"
        )
    except Exception as e:
        stats_table.add_row(":arrows_counterclockwise: Adjust Factors", "Error", "Error", str(e)[:20])
    
    console.print(stats_table)
    console.print()
    
    # 显示数据完整性信息
    completeness_info = []
    
    try:
        # 检查数据完整性
        total_stocks = stock_count
        bar_coverage = len(bar_codes) / total_stocks * 100 if total_stocks > 0 else 0
        tick_coverage = len(tick_codes) / total_stocks * 100 if total_stocks > 0 else 0  
        adj_coverage = len(adj_codes) / total_stocks * 100 if total_stocks > 0 else 0
        
        completeness_info.append(Panel(
            f":bar_chart: Bar Data: [green]{bar_coverage:.1f}%[/green] coverage\n"
            f":zap: Tick Data: [yellow]{tick_coverage:.1f}%[/yellow] coverage\n" 
            f":arrows_counterclockwise: Adjust Factors: [blue]{adj_coverage:.1f}%[/blue] coverage",
            title=":chart_with_upwards_trend: Data Coverage",
            border_style="green"
        ))
        
        completeness_info.append(Panel(
            f":one_oclock: Last Updated: [cyan]{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/cyan]\n"
            f":calendar: Data Status: [green]Active[/green]\n"
            f":wrench: Services: [blue]Running[/blue]",
            title=":zap: System Status", 
            border_style="blue"
        ))
        
    except Exception as e:
        completeness_info.append(Panel(
            f":x: Error calculating statistics: {e}",
            title=":warning: Warning",
            border_style="red"
        ))
    
    if completeness_info:
        console.print(Columns(completeness_info))


@app.command() 
def health():
    """
    🏥 Perform comprehensive health check on data integrity.
    
    Checks for missing data, inconsistencies, and potential issues
    across all data types including orphaned records and data gaps.
    """
    from ginkgo.data.containers import container
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.panel import Panel
    import datetime
    
    console.print(":hospital: [bold green]Ginkgo Database Health Check[/bold green]")
    console.print()
    
    health_issues = []
    health_warnings = []
    health_info = []
    
    # 获取服务
    stockinfo_service = container.stockinfo_service()
    bar_service = container.bar_service()
    tick_service = container.tick_service() 
    adjustfactor_service = container.adjustfactor_service()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        
        # 检查股票信息完整性
        task1 = progress.add_task("Checking stock info integrity...", total=None)
        try:
            stockinfos = stockinfo_service.get_stockinfos(as_dataframe=True)
            if stockinfos is None or len(stockinfos) == 0:
                health_issues.append(":x: No stock information found in database")
            else:
                stock_codes = set(stockinfos['code'].tolist())
                health_info.append(f":white_check_mark: Found {len(stock_codes)} stocks in database")
                
                # 检查必要字段
                required_fields = ['code', 'code_name', 'industry']
                missing_fields = [field for field in required_fields if field not in stockinfos.columns]
                if missing_fields:
                    health_warnings.append(f":warning: Missing stock info fields: {', '.join(missing_fields)}")
                
        except Exception as e:
            health_issues.append(f":x: Stock info check failed: {e}")
        
        progress.update(task1, completed=True)
        
        # 检查日线数据一致性
        task2 = progress.add_task("Checking bar data consistency...", total=None)
        try:
            bar_codes = set(bar_service.get_available_codes())
            if len(bar_codes) == 0:
                health_warnings.append(":warning: No bar data found")
            else:
                health_info.append(f":white_check_mark: Bar data available for {len(bar_codes)} stocks")
                
                # 检查孤立的bar数据（股票信息中不存在的代码）
                if 'stock_codes' in locals():
                    orphaned_bars = bar_codes - stock_codes
                    if orphaned_bars:
                        health_warnings.append(f":warning: Found {len(orphaned_bars)} orphaned bar records")
                
        except Exception as e:
            health_issues.append(f":x: Bar data check failed: {e}")
        
        progress.update(task2, completed=True)
        
        # 检查逐笔数据
        task3 = progress.add_task("Checking tick data...", total=None)
        try:
            tick_codes = set(tick_service.get_available_codes())
            if len(tick_codes) > 0:
                health_info.append(f":white_check_mark: Tick data available for {len(tick_codes)} stocks")
                
                # 检查孤立的tick数据
                if 'stock_codes' in locals():
                    orphaned_ticks = tick_codes - stock_codes
                    if orphaned_ticks:
                        health_warnings.append(f":warning: Found {len(orphaned_ticks)} orphaned tick records")
            else:
                health_info.append("ℹ️ No tick data found (this may be normal)")
                
        except Exception as e:
            health_issues.append(f":x: Tick data check failed: {e}")
        
        progress.update(task3, completed=True)
        
        # 检查复权因子数据
        task4 = progress.add_task("Checking adjustment factors...", total=None)
        try:
            adj_codes = set(adjustfactor_service.get_available_codes())
            if len(adj_codes) > 0:
                health_info.append(f":white_check_mark: Adjustment factors available for {len(adj_codes)} stocks")
                
                # 检查孤立的复权数据
                if 'stock_codes' in locals():
                    orphaned_adj = adj_codes - stock_codes
                    if orphaned_adj:
                        health_warnings.append(f":warning: Found {len(orphaned_adj)} orphaned adjustment records")
            else:
                health_warnings.append(":warning: No adjustment factors found")
                
        except Exception as e:
            health_issues.append(f":x: Adjustment factor check failed: {e}")
        
        progress.update(task4, completed=True)
    
    # 显示健康检查结果
    console.print()
    
    if health_issues:
        issues_panel = Panel(
            "\n".join(health_issues),
            title="🚨 Critical Issues",
            border_style="red"
        )
        console.print(issues_panel)
        console.print()
    
    if health_warnings:
        warnings_panel = Panel(
            "\n".join(health_warnings),
            title=":warning: Warnings",
            border_style="yellow"
        )
        console.print(warnings_panel)
        console.print()
    
    if health_info:
        info_panel = Panel(
            "\n".join(health_info),
            title="ℹ️ Health Information",
            border_style="green"
        )
        console.print(info_panel)
        console.print()
    
    # 总结
    if not health_issues and not health_warnings:
        console.print(":white_check_mark: [bold green]Database health check passed! All systems are healthy.[/bold green]")
    elif health_issues:
        console.print(f":x: [bold red]Found {len(health_issues)} critical issues that need attention.[/bold red]")
    else:
        console.print(f":warning: [bold yellow]Found {len(health_warnings)} warnings but no critical issues.[/bold yellow]")
    
    console.print(f"\n:clock: Health check completed at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


@app.command()
def test(
    unit: Annotated[bool, typer.Option(help=":test_tube: Run unit tests for data module")] = False,
    integration: Annotated[bool, typer.Option(help=":link: Run integration tests for data module")] = False,
    database: Annotated[bool, typer.Option(help="🗄️ Run database tests (REQUIRES CONFIRMATION)")] = False,
    containers: Annotated[bool, typer.Option(help=":package: Run container tests for data module")] = False,
    all: Annotated[bool, typer.Option(help=":arrows_counterclockwise: Run all data module tests (except database)")] = False,
    verbose: Annotated[bool, typer.Option("-v", help=":memo: Verbose output")] = False,
    coverage: Annotated[bool, typer.Option(help=":bar_chart: Generate coverage report")] = False,
):
    """
    :test_tube: Run tests specifically for the data module.
    
    This command runs data module tests in the layered test architecture:
    • Unit tests: Pure logic tests (fast, safe)
    • Integration tests: Service interaction tests with mocks
    • Database tests: Real database operations (requires confirmation)
    • Container tests: DI container functionality
    
    EXAMPLES:
    ginkgo data test --unit              # Fast unit tests only
    ginkgo data test --integration       # Integration tests with mocks
    ginkgo data test --database          # Database tests (with confirmation)
    ginkgo data test --all               # All tests except database
    """
    import subprocess
    import sys
    from pathlib import Path
    
    # Default to unit tests if nothing specified
    if not any([unit, integration, database, containers, all]):
        unit = True
        console.print("ℹ️ [cyan]No test type specified. Running unit tests by default.[/cyan]")
    
    if all:
        unit = True
        integration = True
        containers = True
        # Database tests are NOT included in --all for safety
    
    # Build the command to delegate to unittest CLI
    cmd = [sys.executable, "-m", "ginkgo.client.unittest_cli", "run", "--module", "data"]
    
    if unit:
        cmd.append("--unit")
    if integration:
        cmd.append("--integration")
    if database:
        cmd.append("--database")
    if containers:
        cmd.append("--containers")
    if verbose:
        cmd.append("--verbose")
    if coverage:
        cmd.append("--coverage")
    
    console.print(f":rocket: [cyan]Running data module tests...[/cyan]")
    
    try:
        # Use subprocess to call the unittest CLI
        result = subprocess.run(cmd, check=False)
        
        if result.returncode == 0:
            console.print(":white_check_mark: [bold green]Data module tests completed successfully![/bold green]")
        else:
            console.print(":x: [bold red]Some data module tests failed. Check output above for details.[/bold red]")
            sys.exit(result.returncode)
            
    except FileNotFoundError:
        console.print(":x: [red]Could not find unittest CLI. Make sure Ginkgo is properly installed.[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f":x: [red]Error running tests: {e}[/red]")
        sys.exit(1)
