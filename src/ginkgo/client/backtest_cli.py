# Upstream: CLI入口 (ginkgo backtest命令)
# Downstream: BacktestTaskService, container.backtest_task_service()
# Role: 回测任务CLI命令 — list/cat

"""
Backtest CLI Commands - 统一回测命令入口
"""

import json
import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ginkgo.data.services.base_service import ServiceResult

console = Console(emoji=True, legacy_windows=False)
app = typer.Typer(
    help=":chart_with_upwards_trend: Backtest task management",
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.command("create")
def create_task(
    portfolio: str = typer.Option(..., "--portfolio", "-p", help="Portfolio UUID (required)"),
    start: str = typer.Option(..., "--start", help="Backtest start date (YYYY-MM-DD)"),
    end: str = typer.Option(..., "--end", help="Backtest end date (YYYY-MM-DD)"),
    cash: float = typer.Option(100000, "--cash", help="Initial capital (default: 100000)"),
    commission: float = typer.Option(0.0003, "--commission", help="Commission rate"),
    slippage: float = typer.Option(0.0001, "--slippage", help="Slippage rate"),
    frequency: str = typer.Option("DAY", "--frequency", help="Frequency (DAY/HOUR/MINUTE)"),
    name: Optional[str] = typer.Option(None, "--name", help="Task name"),
):
    """:plus: Create a backtest task."""
    from ginkgo.data.containers import container
    from ginkgo.workers.backtest_worker.task_helpers import load_portfolio_components

    # 校验 portfolio 存在
    portfolio_service = container.portfolio_service()
    portfolio_result = portfolio_service.get(portfolio_id=portfolio)
    if not portfolio_result.is_success():
        console.print(f":x: Portfolio not found: {portfolio}")
        raise typer.Exit(1)

    # 校验 portfolio 有组件绑定
    try:
        load_portfolio_components(portfolio, "cli-create")
    except ValueError as e:
        console.print(f":x: {e}")
        raise typer.Exit(1)

    # 构建 config_snapshot（与 WebUI 一致）
    config_snapshot = {
        "start_date": start,
        "end_date": end,
        "initial_cash": cash,
        "commission_rate": commission,
        "slippage_rate": slippage,
        "frequency": frequency,
        "portfolio_uuids": [portfolio],
        "analyzers": [],
        "broker_type": "backtest",
    }

    task_name = name or f"Backtest {start}~{end}"

    service = container.backtest_task_service()
    result = service.create(
        name=task_name,
        portfolio_id=portfolio,
        config_snapshot=config_snapshot,
    )

    if not result.is_success():
        console.print(f":x: {result.error}")
        raise typer.Exit(1)

    task = result.data
    task_uuid = task.uuid if hasattr(task, "uuid") else str(task)
    console.print(f":white_check_mark: Backtest task created: [bold green]{task_uuid}[/bold green]")
    console.print(f"   Run with: [cyan]ginkgo backtest run {task_uuid}[/cyan]")


@app.command("run")
def run_task(
    task_id: str = typer.Argument(help="Task UUID to run"),
    bg: bool = typer.Option(False, "--bg", help="Run in background thread"),
):
    """:rocket: Run a backtest task locally."""
    import json as _json
    import threading
    from ginkgo import services
    from ginkgo.data.containers import container
    from ginkgo.workers.backtest_worker.models import BacktestConfig
    from ginkgo.workers.backtest_worker.task_helpers import (
        build_engine_data,
        load_portfolio_components,
        build_portfolio_config,
    )
    from ginkgo.libs import GinkgoLogger
    from ginkgo.trading.time.clock import now as clock_now

    service = container.backtest_task_service()
    result = service.get_by_id(task_id)

    if not result.is_success():
        # 精确匹配失败，尝试模糊匹配
        fuzzy_result = service.fuzzy_search(task_id)
        if fuzzy_result.is_success() and fuzzy_result.data and len(fuzzy_result.data) == 1:
            result = ServiceResult.success(fuzzy_result.data[0])
        elif fuzzy_result.is_success() and fuzzy_result.data and len(fuzzy_result.data) > 1:
            console.print(f"[yellow]Found {len(fuzzy_result.data)} matching tasks:[/yellow]\n")
            table = Table(show_header=True, header_style="bold")
            table.add_column("UUID", style="cyan")
            table.add_column("Name")
            table.add_column("Status")
            for t in fuzzy_result.data:
                table.add_row(
                    t.uuid[:12] + "...",
                    t.name or "-",
                    t.status or "-",
                )
            console.print(table)
            console.print(f"\n[yellow]Please use a more specific UUID.[/yellow]")
            raise typer.Exit(1)

    if not result.is_success():
        console.print(f":x: {result.error}")
        raise typer.Exit(1)

    task = result.data

    # 解析 config_snapshot → BacktestConfig
    config_snapshot = _json.loads(task.config_snapshot) if isinstance(task.config_snapshot, str) else task.config_snapshot
    config = BacktestConfig(
        start_date=config_snapshot.get("start_date", "2024-01-01"),
        end_date=config_snapshot.get("end_date", "2024-12-31"),
        initial_cash=config_snapshot.get("initial_cash", 100000),
        commission_rate=config_snapshot.get("commission_rate", 0.0003),
        slippage_rate=config_snapshot.get("slippage_rate", 0.0001),
        frequency=config_snapshot.get("frequency", "DAY"),
    )

    portfolio_uuid = task.portfolio_id

    # 更新状态为 running
    service.update_status(task.uuid, "running")

    console.print(f":rocket: Starting backtest: [bold]{task.name}[/bold]")
    console.print(f"   Period: {config.start_date} ~ {config.end_date}")
    console.print(f"   Capital: {config.initial_cash}")
    console.print(f"   Portfolio: {portfolio_uuid[:12]}")
    console.print()

    try:
        from ginkgo.trading.services.backtest_orchestrator import BacktestOrchestrator
        from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator

        orchestrator = BacktestOrchestrator(
            assembly_service=container.engine_assembly_service()
                if hasattr(container, 'engine_assembly_service')
                else services.trading.services.engine_assembly_service(),
            portfolio_service=container.portfolio_service(),
            task_service=service,
            result_aggregator=BacktestResultAggregator(
                analyzer_service=container.analyzer_service(),
                backtest_task_service=service,
            ),
        )

        if bg:
            def _run_in_thread():
                result = orchestrator.run(
                    task_id=task.uuid, config=config, portfolio_id=portfolio_uuid,
                )
                if result.is_success():
                    console.print(f":white_check_mark: Backtest completed: {task.uuid[:12]}")
                else:
                    console.print(f":x: Backtest failed: {result.error}")

            thread = threading.Thread(target=_run_in_thread, daemon=True)
            thread.start()
            console.print(f":hourglass: Backtest running in background (thread)")
        else:
            result = orchestrator.run(
                task_id=task.uuid, config=config, portfolio_id=portfolio_uuid,
            )

            if not result.is_success():
                console.print(f":x: Backtest failed: {result.error}")
                raise typer.Exit(1)

            # 灌入日志到 ClickHouse（静默降级）
            try:
                from ginkgo.services.logging.log_ingester import LogIngester
                ingester = LogIngester()
                ingest_result = ingester.ingest_task_logs(task.uuid)
                if ingest_result.inserted > 0:
                    console.print(f"   Logs ingested: {ingest_result.inserted} records")
            except Exception:
                pass

            console.print(f":white_check_mark: Backtest completed: [bold green]{task.uuid[:12]}[/bold green]")

    except Exception as e:
        service.update_status(task.uuid, "failed", error_message=str(e))
        console.print(f":x: Backtest failed: {e}")
        raise typer.Exit(1)


@app.command("edit")
def edit_task(
    task_id: str = typer.Argument(help="Task UUID to edit"),
    start: Optional[str] = typer.Option(None, "--start", help="New start date (YYYY-MM-DD)"),
    end: Optional[str] = typer.Option(None, "--end", help="New end date (YYYY-MM-DD)"),
    cash: Optional[float] = typer.Option(None, "--cash", help="New initial capital"),
    commission: Optional[float] = typer.Option(None, "--commission", help="New commission rate"),
    slippage: Optional[float] = typer.Option(None, "--slippage", help="New slippage rate"),
    name: Optional[str] = typer.Option(None, "--name", help="New task name"),
):
    """:pencil2: Edit an uncompleted backtest task."""
    from ginkgo.data.containers import container

    service = container.backtest_task_service()
    result = service.get_by_id(task_id)

    if not result.is_success():
        console.print(f":x: {result.error}")
        raise typer.Exit(1)

    task = result.data
    status_val = task.status if hasattr(task, "status") else ""
    if status_val == "completed":
        console.print(":x: Cannot edit a completed task.")
        raise typer.Exit(1)

    config_snapshot = json.loads(task.config_snapshot) if isinstance(task.config_snapshot, str) else task.config_snapshot

    if start:
        config_snapshot["start_date"] = start
    if end:
        config_snapshot["end_date"] = end
    if cash is not None:
        config_snapshot["initial_cash"] = cash
    if commission is not None:
        config_snapshot["commission_rate"] = commission
    if slippage is not None:
        config_snapshot["slippage_rate"] = slippage

    updates = {"config_snapshot": json.dumps(config_snapshot)}
    if name:
        updates["name"] = name

    update_result = service.update(task.uuid, **updates)

    if not update_result.is_success():
        console.print(f":x: {update_result.error}")
        raise typer.Exit(1)

    console.print(f":white_check_mark: Task [bold]{task.uuid[:12]}[/bold] updated.")


@app.command("delete")
def delete_task(
    task_id: str = typer.Argument(help="Task UUID to delete"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """:wastebasket: Delete a backtest task (soft delete)."""
    from ginkgo.data.containers import container

    service = container.backtest_task_service()
    result = service.get_by_id(task_id)

    if not result.is_success():
        console.print(f":x: {result.error}")
        raise typer.Exit(1)

    task = result.data
    task_name = task.name if hasattr(task, "name") else task_id
    task_uuid = task.uuid if hasattr(task, "uuid") else task_id

    if not confirm:
        confirmed = typer.confirm(f"Delete task '{task_name}' ({task_uuid[:12]})?")
        if not confirmed:
            console.print("Cancelled.")
            return

    delete_result = service.update(task_uuid, is_del=True)

    if not delete_result.is_success():
        console.print(f":x: {delete_result.error}")
        raise typer.Exit(1)

    console.print(f":white_check_mark: Task [bold]{task_uuid[:12]}[/bold] deleted.")


@app.command("list")
def list_tasks(
    portfolio: Optional[str] = typer.Option(None, "--portfolio", "-p", help="Filter by portfolio UUID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (pending/running/completed/failed)"),
    page_size: int = typer.Option(20, "--page-size", help="Items per page"),
    page: int = typer.Option(0, "--page", help="Page number"),
):
    """:clipboard: List backtest tasks."""
    from ginkgo.data.containers import container

    service = container.backtest_task_service()
    result = service.list(page=page, page_size=page_size, portfolio_id=portfolio, status=status)

    if not result.is_success():
        console.print(f":x: {result.error}")
        raise typer.Exit(1)

    data = result.data
    tasks = data.get("data", [])
    total = data.get("total", 0)

    if not tasks:
        console.print(":memo: No backtest tasks found.")
        return

    table = Table(title=":chart_with_upwards_trend: Backtest Tasks")
    table.add_column("UUID", style="dim", width=12)
    table.add_column("Name", style="bold", width=20)
    table.add_column("Portfolio", width=12)
    table.add_column("Status", width=12)
    table.add_column("Progress", width=8)
    table.add_column("Created", width=19)

    for task in tasks:
        uuid_str = task.uuid[:12] if hasattr(task, "uuid") else str(task.get("uuid", ""))[:12]
        name = task.name if hasattr(task, "name") else task.get("name", "")
        portfolio_id = (
            task.portfolio_id[:12] if hasattr(task, "portfolio_id")
            else str(task.get("portfolio_id", ""))[:12]
        )
        status_val = task.status if hasattr(task, "status") else task.get("status", "")
        progress = task.progress if hasattr(task, "progress") else task.get("progress", 0)
        created = str(task.create_at)[:19] if hasattr(task, "create_at") else ""

        status_style = {"completed": "green", "running": "yellow", "failed": "red"}.get(
            status_val, "white"
        )

        table.add_row(
            uuid_str,
            name[:20],
            portfolio_id,
            f"[{status_style}]{status_val}[/{status_style}]",
            f"{progress:.0%}" if isinstance(progress, (int, float)) else str(progress),
            created,
        )

    console.print(table)
    console.print(f"\n  Total: {total} tasks (Page {page}, size {page_size})")


@app.command("cat")
def cat_task(
    task_id: str = typer.Argument(help="Task UUID or task_id"),
):
    """:mag: Show backtest task details."""
    from ginkgo.data.containers import container

    service = container.backtest_task_service()
    result = service.get_by_id(task_id)

    if not result.is_success():
        # 精确匹配失败，尝试模糊匹配
        fuzzy_result = service.fuzzy_search(task_id)
        if fuzzy_result.is_success() and fuzzy_result.data and len(fuzzy_result.data) == 1:
            result = ServiceResult.success(fuzzy_result.data[0])
        elif fuzzy_result.is_success() and fuzzy_result.data and len(fuzzy_result.data) > 1:
            console.print(f"[yellow]Fuzzy match found {len(fuzzy_result.data)} tasks:[/yellow]\n")
            table = Table(show_header=True, header_style="bold")
            table.add_column("UUID", style="cyan")
            table.add_column("Name")
            table.add_column("Status")
            table.add_column("Created")
            for t in fuzzy_result.data:
                table.add_row(
                    t.uuid[:12] + "...",
                    t.name or "-",
                    t.status or "-",
                    str(t.create_at)[:-7] if t.create_at else "-",
                )
            console.print(table)
            console.print(f"\n[yellow]Please use a more specific identifier.[/yellow]")
            raise typer.Exit(1)

    if not result.is_success():
        console.print(f":x: {result.error}")
        raise typer.Exit(1)

    task = result.data

    # -- Basic info --
    info_lines = []
    info_lines.append(f"[bold]UUID:[/bold]         {task.uuid}")
    info_lines.append(f"[bold]Task ID:[/bold]      {task.task_id}")
    info_lines.append(f"[bold]Name:[/bold]         {task.name}")
    info_lines.append(f"[bold]Portfolio:[/bold]    {task.portfolio_id}")
    info_lines.append(f"[bold]Engine:[/bold]       {task.engine_id}")
    status_val = task.status
    status_style = {"completed": "green", "running": "yellow", "failed": "red"}.get(
        status_val, "white"
    )
    info_lines.append(f"[bold]Status:[/bold]       [{status_style}]{status_val}[/{status_style}]")
    info_lines.append(f"[bold]Progress:[/bold]     {task.progress}%")
    info_lines.append(f"[bold]Created:[/bold]      {task.create_at}")

    if task.start_time:
        info_lines.append(f"[bold]Started:[/bold]      {task.start_time}")
    if task.end_time:
        info_lines.append(f"[bold]Completed:[/bold]    {task.end_time}")
    if task.duration_seconds:
        info_lines.append(f"[bold]Duration:[/bold]     {task.duration_seconds}s")

    if task.error_message:
        info_lines.append(f"[bold red]Error:[/bold red]        {task.error_message[:200]}")

    console.print(Panel("\n".join(info_lines), title=f":mag: Task {task.uuid[:12]}"))

    # -- Configuration --
    if task.config_snapshot:
        try:
            config = (
                json.loads(task.config_snapshot)
                if isinstance(task.config_snapshot, str)
                else task.config_snapshot
            )
            config_lines = []
            config_lines.append(f"[bold]Start Date:[/bold]     {config.get('start_date', 'N/A')}")
            config_lines.append(f"[bold]End Date:[/bold]       {config.get('end_date', 'N/A')}")
            config_lines.append(f"[bold]Initial Cash:[/bold]   {config.get('initial_cash', 'N/A')}")
            config_lines.append(f"[bold]Commission:[/bold]     {config.get('commission_rate', 'N/A')}")
            config_lines.append(f"[bold]Slippage:[/bold]       {config.get('slippage_rate', 'N/A')}")
            config_lines.append(f"[bold]Frequency:[/bold]      {config.get('frequency', 'N/A')}")
            console.print(Panel("\n".join(config_lines), title=":gear: Configuration"))
        except (json.JSONDecodeError, TypeError):
            console.print(f"[dim]Config snapshot: {task.config_snapshot[:200]}")

    # -- Results (direct columns, not a JSON blob) --
    result_lines = []
    metrics = [
        ("Final Value", task.final_portfolio_value),
        ("Total PnL", task.total_pnl),
        ("Max Drawdown", task.max_drawdown),
        ("Sharpe Ratio", task.sharpe_ratio),
        ("Annual Return", task.annual_return),
        ("Win Rate", task.win_rate),
    ]
    has_metrics = any(v and v != 0.0 for _, v in metrics)
    if has_metrics:
        for label, value in metrics:
            if value and value != 0.0:
                result_lines.append(f"[bold]{label}:[/bold] {value:.4f}")
        console.print(Panel("\n".join(result_lines), title=":bar_chart: Results"))

    # -- Statistics --
    stats_lines = []
    stats = [
        ("Signals", task.total_signals),
        ("Orders", task.total_orders),
        ("Positions", task.total_positions),
        ("Events", task.total_events),
    ]
    has_stats = any(v and v != 0 for _, v in stats)
    if has_stats:
        for label, value in stats:
            if value and value != 0:
                stats_lines.append(f"[bold]{label}:[/bold] {value}")
        console.print(Panel("\n".join(stats_lines), title=":1234: Statistics"))


def _save_results(service, task_uuid: str, engine, portfolio_id: str):
    """保存回测结果到 backtest_task 表（复用 BacktestResultAggregator）。"""
    try:
        from ginkgo.data.containers import container as data_container
        from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator

        analyzer_service = data_container.analyzer_service()
        aggregator = BacktestResultAggregator(
            analyzer_service=analyzer_service,
            backtest_task_service=service,
        )
        result = aggregator.aggregate_and_save(
            task_id=task_uuid,
            portfolio_id=portfolio_id,
            engine_id=task_uuid,
            status="completed",
        )
        if not result.is_success():
            from ginkgo.libs import GLOG
            GLOG.ERROR(f"Failed to aggregate results for {task_uuid[:8]}: {result.error}")

    except Exception as e:
        from ginkgo.libs import GLOG
        GLOG.ERROR(f"Failed to save results for {task_uuid[:8]}: {e}")
