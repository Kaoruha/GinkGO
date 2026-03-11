# Upstream: CLI主入口(ginkgo logging命令调用)
# Downstream: LevelService(动态日志级别管理)、GLOG(日志记录器)、Rich库(表格显示)
# Role: 日志管理CLI，提供set-level设置级别、get-level获取级别、reset-level重置级别等命令

"""
Ginkgo Logging CLI - 日志级别管理命令
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(help=":memo: Logging management", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


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
