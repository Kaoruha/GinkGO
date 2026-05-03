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
    portfolio_result = portfolio_service.get_by_id(portfolio)
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
