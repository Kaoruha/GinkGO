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
    page: Annotated[
        int, typer.Option("--page", help=":1234: 页码（0-based，旧版 --page 语义为每页条数，已迁移至 --page-size）")
    ] = 0,
    page_size: Annotated[int, typer.Option("--page-size", help=":page_facing_up: 每页条数（0=全部）")] = 50,
    format: Annotated[str, typer.Option("--format", "-F", help="输出格式: text/json")] = "text",
):
    """
    :satellite_antenna: List trading signals.

    All filters (-p/-e/-t) optional. Symmetric with ``record order/position``.
    """
    from ginkgo.data.containers import container
    from ginkgo.libs.utils.display import display_dataframe
    from ginkgo.client.cli_utils import build_list_result, format_result
    from ginkgo.data.services.base_service import ServiceResult

    # #5009 契约：--page（0-based）+ --page-size（0=全量）
    # ADR-021：参数校验失败 exit 2（BAD_PARAMS）；JSON 模式发错误 envelope（#6652 review E2）。
    if page < 0:
        if format == "json":
            format_result(
                ServiceResult.failure(message="--page 必须 >= 0", code="BAD_PARAMS"), format="json", command="list"
            )
            raise typer.Exit(2)
        console.print("[red]:x: --page 必须 >= 0[/red]")
        raise typer.Exit(2)
    if page_size < 0:
        if format == "json":
            format_result(
                ServiceResult.failure(message="--page-size 必须 >= 0（0=全部）", code="BAD_PARAMS"),
                format="json",
                command="list",
            )
            raise typer.Exit(2)
        console.print("[red]:x: --page-size 必须 >= 0（0=全部）[/red]")
        raise typer.Exit(2)
    unlimited = page_size == 0
    q_page = None if unlimited else page
    q_page_size = None if unlimited else page_size

    try:
        signal_svc = container.signal_service()
        result = signal_svc.get_signals_df(
            portfolio_id=portfolio,
            engine_id=engine,
            task_id=task,
            page=q_page,
            page_size=q_page_size,
        )
        if not result.success:
            if format == "json":
                format_result(result, format="json", command="signal")
            else:
                console.print(f":x: [red]{result.error}[/red]")
                raise typer.Exit(1)

        # ADR-010 R2b: get_signals_df 出口已保证 data 为 DataFrame（类型即契约）
        signals_df = result.data if isinstance(result.data, pd.DataFrame) else pd.DataFrame()

        # #5009：metadata.total = count_signals 真实总数（signals_df 已被 page_size 截断）
        count_res = signal_svc.count_signals(portfolio_id=portfolio, engine_id=engine, task_id=task)
        total = (
            count_res.data.get("count", 0)
            if count_res.success and isinstance(count_res.data, dict)
            else len(signals_df)
        )

        if format == "json":
            records = signals_df.to_dict("records") if not signals_df.empty else []
            json_result = build_list_result(
                records, total=total, limit=q_page_size, offset=0 if unlimited else page * page_size
            )
            format_result(json_result, format="json", command="signal")
            return

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

        if unlimited is False and total > signals_df.shape[0]:
            console.print(
                f"[dim]共 {total} 条，当前第 {page + 1} 页（每页 {page_size} 条）。使用 --page 翻页，--page-size 0 看全部。[/dim]"
            )

    except typer.Exit:
        raise
    except Exception as e:
        if format == "json":
            from ginkgo.data.services.base_service import ServiceResult

            format_result(
                ServiceResult.failure(message=f"Error: {e}", code="INTERNAL"),
                format="json",
                command="signal",
            )
        else:
            console.print(f":x: [bold red]Failed to fetch signals:[/bold red] {e}")
            raise typer.Exit(1)


@app.command()
def order(
    portfolio: Annotated[
        Optional[str], typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID filter")
    ] = None,
    engine: Annotated[Optional[str], typer.Option("--engine", "-e", "--e", help=":id: Engine ID filter")] = None,
    task: Annotated[Optional[str], typer.Option("--task", "-t", "--t", help=":id: Task ID filter")] = None,
    page: Annotated[
        int, typer.Option("--page", help=":1234: 页码（0-based，旧版 --page 语义为每页条数，已迁移至 --page-size）")
    ] = 0,
    page_size: Annotated[int, typer.Option("--page-size", help=":page_facing_up: 每页条数（0=全部）")] = 50,
    format: Annotated[str, typer.Option("--format", "-F", help="输出格式: text/json")] = "text",
):
    """
    :clipboard: List order records.
    """
    from ginkgo.data.containers import container
    from ginkgo.libs.utils.display import display_dataframe
    from ginkgo.client.cli_utils import build_list_result, format_result
    from ginkgo.data.services.base_service import ServiceResult

    # #5009 契约：--page（0-based）+ --page-size（0=全量）
    # ADR-021：参数校验失败 exit 2（BAD_PARAMS）；JSON 模式发错误 envelope（#6652 review E2）。
    if page < 0:
        if format == "json":
            format_result(
                ServiceResult.failure(message="--page 必须 >= 0", code="BAD_PARAMS"), format="json", command="list"
            )
            raise typer.Exit(2)
        console.print("[red]:x: --page 必须 >= 0[/red]")
        raise typer.Exit(2)
    if page_size < 0:
        if format == "json":
            format_result(
                ServiceResult.failure(message="--page-size 必须 >= 0（0=全部）", code="BAD_PARAMS"),
                format="json",
                command="list",
            )
            raise typer.Exit(2)
        console.print("[red]:x: --page-size 必须 >= 0（0=全部）[/red]")
        raise typer.Exit(2)
    unlimited = page_size == 0
    q_page = None if unlimited else page
    q_page_size = None if unlimited else page_size

    try:
        order_svc = container.order_service()
        result = order_svc.get_orders_df(
            portfolio_id=portfolio,
            engine_id=engine,
            task_id=task,
            page=q_page,
            page_size=q_page_size,
        )
        if not result.success:
            if format == "json":
                format_result(result, format="json", command="order")
            else:
                console.print(f":x: [red]{result.error}[/red]")
                raise typer.Exit(1)

        # ADR-010 R2b: get_orders_df 出口已保证 data 为 DataFrame（类型即契约）
        orders_df = result.data if isinstance(result.data, pd.DataFrame) else pd.DataFrame()

        # #5009：metadata.total = count_orders 真实总数
        count_res = order_svc.count_orders(portfolio_id=portfolio, engine_id=engine, task_id=task)
        total = (
            count_res.data.get("count", 0) if count_res.success and isinstance(count_res.data, dict) else len(orders_df)
        )

        if format == "json":
            records = orders_df.to_dict("records") if not orders_df.empty else []
            json_result = build_list_result(
                records, total=total, limit=q_page_size, offset=0 if unlimited else page * page_size
            )
            format_result(json_result, format="json", command="order")
            return

        if orders_df.shape[0] == 0:
            console.print(":exclamation: [yellow]No orders found.[/yellow]")
            return

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

        if unlimited is False and total > orders_df.shape[0]:
            console.print(
                f"[dim]共 {total} 条，当前第 {page + 1} 页（每页 {page_size} 条）。使用 --page 翻页，--page-size 0 看全部。[/dim]"
            )

    except typer.Exit:
        raise
    except Exception as e:
        if format == "json":
            from ginkgo.data.services.base_service import ServiceResult

            format_result(
                ServiceResult.failure(message=f"Error: {e}", code="INTERNAL"),
                format="json",
                command="order",
            )
        else:
            console.print(f":x: [bold red]Failed to fetch orders:[/bold red] {e}")
            raise typer.Exit(1)


@app.command()
def position(
    portfolio: Annotated[
        Optional[str], typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID filter")
    ] = None,
    engine: Annotated[Optional[str], typer.Option("--engine", "-e", "--e", help=":id: Engine ID filter")] = None,
    task: Annotated[Optional[str], typer.Option("--task", "-t", "--t", help=":id: Task ID filter")] = None,
    page: Annotated[
        int, typer.Option("--page", help=":1234: 页码（0-based，旧版 --page 语义为每页条数，已迁移至 --page-size）")
    ] = 0,
    page_size: Annotated[int, typer.Option("--page-size", help=":page_facing_up: 每页条数（0=全部）")] = 50,
    format: Annotated[str, typer.Option("--format", "-F", help="输出格式: text/json")] = "text",
):
    """
    :bar_chart: List position records.
    """
    from ginkgo.data.containers import container
    from ginkgo.libs.utils.display import display_dataframe
    from ginkgo.client.cli_utils import build_list_result, format_result
    from ginkgo.data.services.base_service import ServiceResult

    # #5009 契约：--page（0-based）+ --page-size（0=全量）
    # ADR-021：参数校验失败 exit 2（BAD_PARAMS）；JSON 模式发错误 envelope（#6652 review E2）。
    if page < 0:
        if format == "json":
            format_result(
                ServiceResult.failure(message="--page 必须 >= 0", code="BAD_PARAMS"), format="json", command="list"
            )
            raise typer.Exit(2)
        console.print("[red]:x: --page 必须 >= 0[/red]")
        raise typer.Exit(2)
    if page_size < 0:
        if format == "json":
            format_result(
                ServiceResult.failure(message="--page-size 必须 >= 0（0=全部）", code="BAD_PARAMS"),
                format="json",
                command="list",
            )
            raise typer.Exit(2)
        console.print("[red]:x: --page-size 必须 >= 0（0=全部）[/red]")
        raise typer.Exit(2)
    unlimited = page_size == 0
    q_page = None if unlimited else page
    q_page_size = None if unlimited else page_size

    try:
        # #5341: 回测持仓经 create_position_record 写 MPositionRecord（流水表），
        # PositionService 查 MPosition（当前态表）永远空。改读 ResultService
        # （get_positions_df 查 PositionRecordCRUD，与写路径同表）。
        result_svc = container.result_service()
        result = result_svc.get_positions_df(
            portfolio_id=portfolio,
            engine_id=engine,
            task_id=task,
            page=q_page,
            page_size=q_page_size,
        )
        if not result.success:
            if format == "json":
                format_result(result, format="json", command="position")
            else:
                console.print(f":x: [red]{result.error}[/red]")
                raise typer.Exit(1)

        # ADR-010 R2b: get_positions_df 出口已保证 data 为 DataFrame（类型即契约）
        positions_df = result.data if isinstance(result.data, pd.DataFrame) else pd.DataFrame()

        # #5009：metadata.total = count_positions 真实总数（MPositionRecord ClickHouse 流水）
        count_res = result_svc.count_positions(portfolio_id=portfolio, engine_id=engine, task_id=task)
        total = (
            count_res.data.get("count", 0)
            if count_res.success and isinstance(count_res.data, dict)
            else len(positions_df)
        )

        if format == "json":
            records = positions_df.to_dict("records") if not positions_df.empty else []
            json_result = build_list_result(
                records, total=total, limit=q_page_size, offset=0 if unlimited else page * page_size
            )
            format_result(json_result, format="json", command="position")
            return

        if positions_df.shape[0] == 0:
            console.print(":exclamation: [yellow]No positions found.[/yellow]")
            return

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

        if unlimited is False and total > positions_df.shape[0]:
            console.print(
                f"[dim]共 {total} 条，当前第 {page + 1} 页（每页 {page_size} 条）。使用 --page 翻页，--page-size 0 看全部。[/dim]"
            )

    except typer.Exit:
        raise
    except Exception as e:
        if format == "json":
            from ginkgo.data.services.base_service import ServiceResult

            format_result(
                ServiceResult.failure(message=f"Error: {e}", code="INTERNAL"),
                format="json",
                command="position",
            )
        else:
            console.print(f":x: [bold red]Failed to fetch positions:[/bold red] {e}")
            raise typer.Exit(1)


@app.command()
def analyzer(
    portfolio: Annotated[
        Optional[str], typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID filter")
    ] = None,
    engine: Annotated[Optional[str], typer.Option("--engine", "-e", "--e", help=":id: Engine ID filter")] = None,
    page: Annotated[
        int, typer.Option("--page", help=":1234: 页码（0-based，旧版 --page 语义为每页条数，已迁移至 --page-size）")
    ] = 0,
    page_size: Annotated[int, typer.Option("--page-size", help=":page_facing_up: 每页条数（0=全部）")] = 50,
    format: Annotated[str, typer.Option("--format", "-F", help="输出格式: text/json")] = "text",
):
    """
    :bar_chart: List analyzer records.
    """
    from ginkgo.data.containers import container
    from ginkgo.libs.utils.display import display_dataframe
    from ginkgo.client.cli_utils import build_list_result, format_result
    from ginkgo.data.services.base_service import ServiceResult

    # #5009 契约：--page（0-based）+ --page-size（0=全量）
    # ADR-021：参数校验失败 exit 2（BAD_PARAMS）；JSON 模式发错误 envelope（#6652 review E2）。
    if page < 0:
        if format == "json":
            format_result(
                ServiceResult.failure(message="--page 必须 >= 0", code="BAD_PARAMS"), format="json", command="list"
            )
            raise typer.Exit(2)
        console.print("[red]:x: --page 必须 >= 0[/red]")
        raise typer.Exit(2)
    if page_size < 0:
        if format == "json":
            format_result(
                ServiceResult.failure(message="--page-size 必须 >= 0（0=全部）", code="BAD_PARAMS"),
                format="json",
                command="list",
            )
            raise typer.Exit(2)
        console.print("[red]:x: --page-size 必须 >= 0（0=全部）[/red]")
        raise typer.Exit(2)
    unlimited = page_size == 0
    q_page = None if unlimited else page
    q_page_size = None if unlimited else page_size

    try:
        analyzer_svc = container.analyzer_service()
        result = analyzer_svc.get_records_df(
            portfolio_id=portfolio,
            engine_id=engine,
            page=q_page,
            page_size=q_page_size,
        )
        if not result.success:
            if format == "json":
                format_result(result, format="json", command="analyzer")
            else:
                console.print(f":x: [red]{result.error}[/red]")
                raise typer.Exit(1)

        analyzer_df = result.data if isinstance(result.data, pd.DataFrame) else pd.DataFrame()

        # #5009：metadata.total = count_records 真实总数
        count_res = analyzer_svc.count_records(portfolio_id=portfolio, engine_id=engine)
        total = (
            count_res.data.get("count", 0)
            if count_res.success and isinstance(count_res.data, dict)
            else len(analyzer_df)
        )

        if format == "json":
            records = analyzer_df.to_dict("records") if not analyzer_df.empty else []
            json_result = build_list_result(
                records, total=total, limit=q_page_size, offset=0 if unlimited else page * page_size
            )
            format_result(json_result, format="json", command="analyzer")
            return

        if analyzer_df.shape[0] == 0:
            console.print(":exclamation: [yellow]No analyzer records found.[/yellow]")
            return

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

        if unlimited is False and total > analyzer_df.shape[0]:
            console.print(
                f"[dim]共 {total} 条，当前第 {page + 1} 页（每页 {page_size} 条）。使用 --page 翻页，--page-size 0 看全部。[/dim]"
            )

    except typer.Exit:
        raise
    except Exception as e:
        if format == "json":
            from ginkgo.data.services.base_service import ServiceResult

            format_result(
                ServiceResult.failure(message=f"Error: {e}", code="INTERNAL"),
                format="json",
                command="analyzer",
            )
        else:
            console.print(f":x: [bold red]Failed to fetch analyzer records:[/bold red] {e}")
            raise typer.Exit(1)
