# Upstream: Data Layer (Service)
# Downstream: CLI 用户交互
# Role: 记录管理CLI，提供signal信号、order委托、position持仓、analyzer分析等命令，支持交易记录的查询与管理


import typer
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console
import pandas as pd

app = typer.Typer(
    help=":clipboard: Module for [bold medium_spring_green]RECORD[/] management. [grey62]View trading signals, orders, and positions.[/grey62]",
    no_args_is_help=True,
)
console = Console()


def _print_page_hint(row_count: int, page: int, page_size: int) -> None:
    if page_size > 0 and row_count == page_size:
        console.print(
            f"[dim]Showing page {page} ({page_size} records per page). Use --page-size 0 to see all records.[/dim]"
        )


@app.command()
def signal(
    portfolio: Annotated[
        Optional[str], typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID filter")
    ] = None,
    engine: Annotated[Optional[str], typer.Option("--engine", "-e", "--e", help=":id: Engine ID filter")] = None,
    task: Annotated[Optional[str], typer.Option("--task", "-t", "--t", help=":id: Task ID filter")] = None,
    page: Annotated[int, typer.Option("--page", help=":page_facing_up: Page number (0-based)")] = 0,
    page_size: Annotated[int, typer.Option("--page-size", help=":1234: Items per page (0=no pagination)")] = 50,
):
    """
    :satellite_antenna: List trading signals.

    All filters (-p/-e/-t) optional. Symmetric with ``record order/position``.
    """
    from ginkgo.data.containers import Container
    from ginkgo.libs.utils.display import display_dataframe

    try:
        signal_svc = Container.signal_service()
        result = signal_svc.get_signals_df(
            portfolio_id=portfolio,
            engine_id=engine,
            task_id=task,
            page=page,
            page_size=page_size,
        )
        if not result.success:
            console.print(f":x: [red]{result.error}[/red]")
            return

        # ADR-010 R2b: get_signals_df 出口已保证 data 为 DataFrame（类型即契约）
        signals_df = result.data if isinstance(result.data, pd.DataFrame) else pd.DataFrame()

        if signals_df.shape[0] == 0:
            console.print(":exclamation: [yellow]No signals found.[/yellow]")
            return

        signal_columns_config = {
            "uuid": {"display_name": "Signal ID", "style": "dim"},
            "engine_id": {"display_name": "Engine ID", "style": "dim"},
            "portfolio_id": {"display_name": "Portfolio ID", "style": "dim"},
            "task_id": {"display_name": "Task ID", "style": "dim"},
            "direction": {"display_name": "Direction", "style": "green"},
            "code": {"display_name": "Code", "style": "cyan"},
            "timestamp": {"display_name": "Timestamp", "style": "dim"},
            "reason": {"display_name": "Reason", "style": "yellow"},
        }

        title = ":satellite_antenna: [bold]Signals:[/bold]"
        display_dataframe(data=signals_df, columns_config=signal_columns_config, title=title, console=console)

        _print_page_hint(signals_df.shape[0], page, page_size)

    except Exception as e:
        console.print(f":x: [bold red]Failed to fetch signals:[/bold red] {e}")


@app.command()
def order(
    portfolio: Annotated[
        Optional[str], typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID filter")
    ] = None,
    engine: Annotated[Optional[str], typer.Option("--engine", "-e", "--e", help=":id: Engine ID filter")] = None,
    task: Annotated[Optional[str], typer.Option("--task", "-t", "--t", help=":id: Task ID filter")] = None,
    page: Annotated[int, typer.Option("--page", help=":page_facing_up: Page number (0-based)")] = 0,
    page_size: Annotated[int, typer.Option("--page-size", help=":1234: Items per page (0=no pagination)")] = 50,
):
    """
    :clipboard: List order records.
    """
    from ginkgo.data.containers import Container
    from ginkgo.libs.utils.display import display_dataframe

    try:
        order_svc = Container.order_service()
        result = order_svc.get_orders_df(
            portfolio_id=portfolio,
            engine_id=engine,
            task_id=task,
            page=page,
            page_size=page_size,
        )
        if not result.success:
            console.print(f":x: [red]{result.error}[/red]")
            return

        # ADR-010 R2b: get_orders_df 出口已保证 data 为 DataFrame（类型即契约）
        orders_df = result.data if isinstance(result.data, pd.DataFrame) else pd.DataFrame()

        order_columns_config = {
            "uuid": {"display_name": "Order ID", "style": "dim"},
            "portfolio_id": {"display_name": "Portfolio ID", "style": "dim"},
            "code": {"display_name": "Code", "style": "cyan"},
            "direction": {"display_name": "Direction", "style": "green"},
            "order_type": {"display_name": "Order Type", "style": "blue"},
            "quantity": {"display_name": "Quantity", "style": "yellow"},
            "limit_price": {"display_name": "Limit Price", "style": "yellow"},
            "timestamp": {"display_name": "Timestamp", "style": "dim"},
            "status": {"display_name": "Status", "style": "green"},
        }

        title = (
            f":clipboard: [bold]Orders for portfolio {portfolio}:[/bold]"
            if portfolio
            else ":clipboard: [bold]Orders:[/bold]"
        )
        display_dataframe(data=orders_df, columns_config=order_columns_config, title=title, console=console)

        _print_page_hint(orders_df.shape[0], page, page_size)

    except Exception as e:
        console.print(f":x: [bold red]Failed to fetch orders:[/bold red] {e}")


@app.command()
def position(
    portfolio: Annotated[
        Optional[str], typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID filter")
    ] = None,
    engine: Annotated[Optional[str], typer.Option("--engine", "-e", "--e", help=":id: Engine ID filter")] = None,
    task: Annotated[Optional[str], typer.Option("--task", "-t", "--t", help=":id: Task ID filter")] = None,
    page: Annotated[int, typer.Option("--page", help=":page_facing_up: Page number (0-based)")] = 0,
    page_size: Annotated[int, typer.Option("--page-size", help=":1234: Items per page (0=no pagination)")] = 50,
):
    """
    :bar_chart: List position records.
    """
    from ginkgo.data.containers import Container
    from ginkgo.libs.utils.display import display_dataframe

    try:
        # #5341: 回测持仓经 create_position_record 写 MPositionRecord（流水表），
        # PositionService 查 MPosition（当前态表）永远空。改读 ResultService
        # （get_positions_df 查 PositionRecordCRUD，与写路径同表）。
        result_svc = Container.result_service()
        result = result_svc.get_positions_df(
            portfolio_id=portfolio,
            engine_id=engine,
            task_id=task,
            page=page,
            page_size=page_size,
        )
        if not result.success:
            console.print(f":x: [red]{result.error}[/red]")
            return

        # ADR-010 R2b: get_positions_df 出口已保证 data 为 DataFrame（类型即契约）
        positions_df = result.data if isinstance(result.data, pd.DataFrame) else pd.DataFrame()

        # MPositionRecord 流水字段（volume/cost/price/fee），非 MPosition 当前态字段
        position_columns_config = {
            "uuid": {"display_name": "Position ID", "style": "dim"},
            "portfolio_id": {"display_name": "Portfolio ID", "style": "dim"},
            "code": {"display_name": "Code", "style": "cyan"},
            "volume": {"display_name": "Volume", "style": "yellow"},
            "cost": {"display_name": "Cost", "style": "yellow"},
            "price": {"display_name": "Price", "style": "yellow"},
            "fee": {"display_name": "Fee", "style": "green"},
            "timestamp": {"display_name": "Timestamp", "style": "dim"},
        }

        title = (
            f":bar_chart: [bold]Positions for portfolio {portfolio}:[/bold]"
            if portfolio
            else ":bar_chart: [bold]Positions:[/bold]"
        )
        display_dataframe(data=positions_df, columns_config=position_columns_config, title=title, console=console)

        _print_page_hint(positions_df.shape[0], page, page_size)

    except Exception as e:
        console.print(f":x: [bold red]Failed to fetch positions:[/bold red] {e}")


@app.command()
def analyzer(
    portfolio: Annotated[
        Optional[str], typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID filter")
    ] = None,
    engine: Annotated[Optional[str], typer.Option("--engine", "-e", "--e", help=":id: Engine ID filter")] = None,
    page: Annotated[int, typer.Option("--page", help=":page_facing_up: Page number (0-based)")] = 0,
    page_size: Annotated[int, typer.Option("--page-size", help=":1234: Items per page (0=no pagination)")] = 50,
):
    """
    :bar_chart: List analyzer records.
    """
    from ginkgo.data.containers import Container
    from ginkgo.libs.utils.display import display_dataframe

    try:
        analyzer_svc = Container.analyzer_service()
        result = analyzer_svc.get_records_df(
            portfolio_id=portfolio,
            engine_id=engine,
            page=page,
            page_size=page_size,
        )
        if not result.success:
            console.print(f":x: [red]{result.error}[/red]")
            return

        analyzer_df = result.data if isinstance(result.data, pd.DataFrame) else pd.DataFrame()

        title_parts = []
        if portfolio:
            title_parts.append(f"portfolio {portfolio}")
        if engine:
            title_parts.append(f"engine {engine}")

        analyzer_columns_config = {
            "uuid": {"display_name": "Record ID", "style": "dim"},
            "portfolio_id": {"display_name": "Portfolio ID", "style": "dim"},
            "engine_id": {"display_name": "Engine ID", "style": "dim"},
            "analyzer_id": {"display_name": "Analyzer ID", "style": "cyan"},
            "name": {"display_name": "Name", "style": "cyan"},
            "value": {"display_name": "Value", "style": "yellow"},
            "timestamp": {"display_name": "Timestamp", "style": "dim"},
        }

        title = (
            f":bar_chart: [bold]Analyzer records for {' and '.join(title_parts)}:[/bold]"
            if title_parts
            else ":bar_chart: [bold]Analyzer records:[/bold]"
        )
        display_dataframe(data=analyzer_df, columns_config=analyzer_columns_config, title=title, console=console)

        _print_page_hint(analyzer_df.shape[0], page, page_size)

    except Exception as e:
        console.print(f":x: [bold red]Failed to fetch analyzer records:[/bold red] {e}")
