# Upstream: CLI主入口(ginkgo logging命令调用)
# Downstream: LevelService(动态日志级别管理)、LogService(日志查询)、Rich库(表格显示)
# Role: 日志管理CLI，提供日志查看、级别设置等功能

"""
Ginkgo Logging CLI - 日志管理命令
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(help=":memo: Logging management", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)

LEVEL_STYLES = {"ERROR": "red", "WARNING": "yellow", "DEBUG": "dim", "CRITICAL": "bold red"}


def _parse_time(s: str):
    from datetime import datetime
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid time format: '{s}'. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS")


@app.command()
def set_level(
    module: str = typer.Argument(..., help="Module name (e.g., backtest, trading, data, analysis)"),
    level: str = typer.Argument(..., help="Log level (DEBUG/INFO/WARNING/ERROR/CRITICAL)"),
):
    """
    :wrench: Set log level for a specific module.

    Sets the log level for the specified module. Only modules in the whitelist
    (backtest, trading, data, analysis) can be modified.

    Example:
        ginkgo logging set-level backtest DEBUG
    """
    from ginkgo.services.logging.containers import container

    level_service = container.level_service()

    # 检查模块是否在白名单
    if not level_service.is_module_allowed(module):
        console.print(f"[red]✗[/red] 模块 '{module}' 不在白名单中")
        console.print(f"允许的模块: {', '.join(level_service.get_whitelist())}")
        raise typer.Exit(1)

    # 设置级别
    result = level_service.set_level(module, level)

    if result.success:
        console.print(f"[green]✓[/green] {result.message}")
    else:
        console.print(f"[red]✗[/red] {result.error}")
        raise typer.Exit(1)


@app.command()
def get_level(
    module: Optional[str] = typer.Option(None, "--module", "-m", help="Module name (shows all if not specified)"),
):
    """
    :mag: Get current log level(s).

    Shows the current log level for a specific module or all modules.

    Example:
        ginkgo logging get-level
        ginkgo logging get-level --module backtest
    """
    from ginkgo.services.logging.containers import container

    level_service = container.level_service()

    if module:
        # 显示单个模块的级别
        if not level_service.is_module_allowed(module):
            console.print(f"[red]✗[/red] 模块 '{module}' 不在白名单中")
            raise typer.Exit(1)

        level = level_service.get_level(module)
        console.print(Panel(f"[bold]{module}[/bold]: {level}", title="Current Log Level"))
    else:
        # 显示所有模块的级别
        levels = level_service.get_all_levels()

        table = Table(title="Log Levels", show_header=True, header_style="bold magenta")
        table.add_column("Module", style="cyan", width=20)
        table.add_column("Level", style="green", width=10)

        for mod, lvl in levels.items():
            table.add_row(mod, lvl)

        console.print(table)


@app.command()
def reset_level():
    """
    :arrows_counterclockwise: Reset all log levels to default.

    Resets all custom log level settings back to their default values (INFO).

    Example:
        ginkgo logging reset-level
    """
    from ginkgo.services.logging.containers import container

    level_service = container.level_service()

    result = level_service.reset_levels()

    if result.success:
        console.print(f"[green]✓[/green] {result.message}")
    else:
        console.print(f"[red]✗[/red] {result.error}")
        raise typer.Exit(1)


@app.command()
def whitelist():
    """
    :list: Show module whitelist.

    Displays the list of modules that are allowed to have their
    log levels dynamically adjusted.

    Example:
        ginkgo logging whitelist
    """
    from ginkgo.services.logging.containers import container

    level_service = container.level_service()
    whitelist = level_service.get_whitelist()

    console.print(Panel(
        "\n".join(f"  [cyan]•[/cyan] {module}" for module in whitelist),
        title=f"[bold]Level Whitelist ({len(whitelist)} modules)",
        border_style="blue"
    ))


# 添加级别验证
def validate_level(value: str) -> str:
    """验证日志级别"""
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if value.upper() not in valid_levels:
        raise typer.BadParameter(f"Invalid level. Valid levels: {', '.join(valid_levels)}")
    return value.upper()


@app.command("logs")
def view_logs(
    task_id: Optional[str] = typer.Option(None, "--task", "-t", help="Backtest task ID"),
    portfolio_id: Optional[str] = typer.Option(None, "--portfolio", "-p", help="Portfolio ID"),
    level: Optional[str] = typer.Option(None, "--level", "-l", help="Log level filter (ERROR/WARNING/INFO/DEBUG)"),
    event_type: Optional[str] = typer.Option(None, "--event", "-e", help="Event type filter (e.g. SIGNALGENERATION, ORDERSEND)"),
    symbol: Optional[str] = typer.Option(None, "--symbol", "-s", help="Symbol filter (e.g. 000001.SZ)"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="Search keyword in message"),
    start: Optional[str] = typer.Option(None, "--start", help="Start time (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"),
    end: Optional[str] = typer.Option(None, "--end", help="End time (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)"),
    page: int = typer.Option(0, "--page", help="Page number (0-based)"),
    page_size: int = typer.Option(50, "--page-size", help="Results per page"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw JSON"),
):
    """
    :mag: View backtest logs.

    Examples:
        ginkgo logging logs --task <task_id>
        ginkgo logging logs --task <task_id> --level ERROR
        ginkgo logging logs --portfolio <id> --event SIGNALGENERATION
        ginkgo logging logs --task <task_id> --start 2024-01-01 --end 2024-06-30
        ginkgo logging logs --task <task_id> --keyword "signal" --page 2
    """
    from ginkgo.services.logging.containers import container
    from datetime import datetime as dt
    import json

    log_service = container.log_service()

    # 解析时间
    start_time = _parse_time(start) if start else None
    end_time = _parse_time(end) if end else None

    offset = page * page_size
    limit = page_size

    if keyword:
        logs = log_service.search_logs(keyword, log_type="backtest", limit=limit, offset=offset)
    else:
        logs = log_service.query_backtest_logs(
            portfolio_id=portfolio_id,
            task_id=task_id,
            level=level.upper() if level else None,
            event_type=event_type,
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

    if not logs:
        console.print(f":information: No logs found (page {page}).")
        return

    if raw:
        console.print(json.dumps(logs, indent=2, ensure_ascii=False, default=str))
        return

    # 获取总数用于分页提示
    total = log_service.get_log_count(log_type="backtest", task_id=task_id, portfolio_id=portfolio_id, level=level) if not keyword else None
    page_info = f"page {page}" + (f", total {total}" if total else "")

    table = Table(title=f"Backtest Logs ({len(logs)} entries, {page_info})")
    table.add_column("Time", style="dim", width=19)
    table.add_column("Level", width=8)
    table.add_column("Event", width=18)
    table.add_column("Symbol", width=12)
    table.add_column("Message", width=60)

    for entry in logs:
        ts = str(entry.get("timestamp", ""))[:19]
        lvl = entry.get("level", "")
        evt = str(entry.get("event_type", ""))[:18]
        sym = entry.get("symbol", "") or entry.get("portfolio_id", "")[:8]
        msg = str(entry.get("message", ""))[:60]
        style = LEVEL_STYLES.get(lvl, "")
        table.add_row(ts, f"[{style}]{lvl}[/{style}]" if style else lvl, evt, sym, msg)

    console.print(table)


@app.command("errors")
def view_errors(
    task_id: Optional[str] = typer.Option(None, "--task", "-t", help="Backtest task ID"),
    portfolio_id: Optional[str] = typer.Option(None, "--portfolio", "-p", help="Portfolio ID"),
    limit: int = typer.Option(30, "--limit", "-n", help="Max results"),
    hours: Optional[int] = typer.Option(None, "--hours", help="Lookback hours (default: all history)"),
):
    """
    :exclamation: View backtest error logs.

    Examples:
        ginkgo logging errors --task <task_id>
        ginkgo logging errors --portfolio <id>
    """
    from ginkgo.services.logging.containers import container
    from datetime import datetime, timedelta

    log_service = container.log_service()
    end_time = datetime.utcnow() if hours is not None else None
    start_time = end_time - timedelta(hours=hours) if end_time is not None else None
    range_label = f"last {hours}h" if hours is not None else "all history"

    query_kwargs = {
        "portfolio_id": portfolio_id,
        "task_id": task_id,
        "level": "ERROR",
        "limit": limit,
    }
    if start_time is not None:
        query_kwargs["start_time"] = start_time
        query_kwargs["end_time"] = end_time

    logs = log_service.query_backtest_logs(**query_kwargs)

    if not logs:
        console.print(f":white_check_mark: No errors found ({range_label}).")
        return

    console.print(f":exclamation: [red]{len(logs)} error(s) found[/red] ({range_label})")

    for entry in logs[-10:]:
        ts = str(entry.get("timestamp", ""))[:19]
        msg = entry.get("message", "")
        evt = entry.get("event_type", "")
        console.print(f"  [dim]{ts}[/dim] [{evt}] {msg}")


@app.command("stats")
def log_stats(
    portfolio_id: Optional[str] = typer.Option(None, "--portfolio", "-p", help="Portfolio ID"),
    hours: int = typer.Option(24, "--hours", "-h", help="Lookback hours"),
):
    """
    :bar_chart: Show error statistics.

    Examples:
        ginkgo logging stats
        ginkgo logging stats --portfolio <id> --hours 48
    """
    from ginkgo.services.logging.containers import container

    log_service = container.log_service()

    stats = log_service.get_error_stats(portfolio_id=portfolio_id, hours=hours)

    console.print(Panel(
        f"[bold]Error Stats (last {hours}h)[/bold]\n"
        f"Total errors: [red]{stats.get('total_errors', 0)}[/red]",
        title="Error Statistics"
    ))

    patterns = stats.get("top_error_patterns", [])
    if patterns:
        table = Table(title="Top Error Patterns")
        table.add_column("Pattern", style="red", width=60)
        table.add_column("Count", style="bold", width=8)
        for pattern, count in patterns:
            table.add_row(str(pattern), str(count))
        console.print(table)
