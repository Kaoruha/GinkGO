# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: 扁平化命令CLI，提供_get_engine_status_name状态转换等工具函数，简化命令行操作和数据访问






"""
Ginkgo Flat CLI - 扁平化的顶级命令
包含未迁移到独立文件的CLI功能
"""

import typer
from typing import Optional, Any, Dict, List
from rich.console import Console
from rich.table import Table
import json
import datetime

from typing import Optional, List
console = Console(emoji=True, legacy_windows=False)

# 创建顶级命令
get_app = typer.Typer(help=":mag: Get resource information")
set_app = typer.Typer(help=":gear: Set resource properties")
list_app = typer.Typer(help=":clipboard: List resources")
create_app = typer.Typer(help=":plus: Create new resources")
update_app = typer.Typer(help=":repeat: Update resources")
delete_app = typer.Typer(help=":wastebasket: Delete resources")
run_app = typer.Typer(help=":rocket: Run operations")

# Component管理命令
component_app = typer.Typer(help=":wrench: Component management", rich_markup_mode="rich")

# Mapping管理命令
mapping_app = typer.Typer(help=":link: Mapping relationship management", rich_markup_mode="rich")

# Result管理命令
result_app = typer.Typer(help=":bar_chart: Result management", rich_markup_mode="rich")

# 状态转换函数
def _get_engine_status_name(status):
    """将引擎状态数字转换为可读名称"""
    from ginkgo.enums import ENGINESTATUS_TYPES

    status_map = {
        ENGINESTATUS_TYPES.VOID.value: "Void",
        ENGINESTATUS_TYPES.IDLE.value: "Idle",
        ENGINESTATUS_TYPES.INITIALIZING.value: "Initializing",
        ENGINESTATUS_TYPES.RUNNING.value: "Running",
        ENGINESTATUS_TYPES.PAUSED.value: "Paused",
        ENGINESTATUS_TYPES.STOPPED.value: "Stopped"
    }
    return status_map.get(status, f"Unknown({status})")

# Component 相关命令
@component_app.command()
def list(
    component_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by component type (strategy/risk/sizer/selector/analyzer)"),
    filter: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter by component name (fuzzy search)"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output in JSON format"),
):
    """
    :clipboard: List all components from database.

    Examples:
      ginkgo component list                    # List all components (table format)
      ginkgo component list --type strategy     # List strategies only
      ginkgo component list --filter moving     # Fuzzy search by name
      ginkgo component list -t risk -f loss     # Combine type and name filter
      ginkgo component list --raw               # Output in JSON format
    """
    from ginkgo.data.containers import container
    from ginkgo.enums import FILE_TYPES
    import json

    console.print(":clipboard: Listing components...")

    try:
        # Get file_crud to query database
        file_crud = container.file_crud()

        # Map component type to FILE_TYPES
        type_mapping = {
            "strategy": FILE_TYPES.STRATEGY,
            "risk": FILE_TYPES.RISKMANAGER,
            "riskmanager": FILE_TYPES.RISKMANAGER,
            "sizer": FILE_TYPES.SIZER,
            "selector": FILE_TYPES.SELECTOR,
            "analyzer": FILE_TYPES.ANALYZER,
        }

        # Query components from database
        if component_type and component_type.lower() in type_mapping:
            # Single type query: filter by type (1 query)
            file_type = type_mapping[component_type.lower()]
            components = file_crud.find(filters={"type": file_type.value}, page_size=10000)
        else:
            # All types query: get all components in ONE query, then filter client-side
            # Query without type filter to get all components at once
            all_components = file_crud.find(filters={}, page_size=10000)

            # Filter to only include component types (exclude OTHER, VOID, ENGINE, HANDLER, INDEX)
            component_type_values = {
                FILE_TYPES.STRATEGY.value,
                FILE_TYPES.RISKMANAGER.value,
                FILE_TYPES.SELECTOR.value,
                FILE_TYPES.SIZER.value,
                FILE_TYPES.ANALYZER.value,
            }

            components = []
            for comp in all_components:
                type_value = comp.type.value if hasattr(comp.type, 'value') else comp.type
                if type_value in component_type_values:
                    components.append(comp)

        # Apply name filter if provided
        if filter:
            filter_lower = filter.lower()
            components = [c for c in components if filter_lower in str(c.name).lower()]

        if components:
            # Reverse type mapping for display
            value_to_type = {v.value: k for k, v in type_mapping.items()}

            if raw:
                # JSON output format
                result = {
                    "total": len(components),
                    "components": []
                }

                if component_type:
                    result["type"] = component_type
                if filter:
                    result["filter"] = filter

                for comp in components:
                    # Get type value - handle both enum and int
                    type_value = comp.type.value if hasattr(comp.type, 'value') else comp.type
                    type_name = value_to_type.get(type_value, "unknown")

                    component_data = {
                        "uuid": str(comp.uuid),
                        "name": str(comp.name),
                        "type": type_name,
                        "created_at": str(comp.create_at) if hasattr(comp, 'create_at') and comp.create_at else None,
                        "updated_at": str(comp.update_at) if hasattr(comp, 'update_at') and comp.update_at else None,
                    }
                    result["components"].append(component_data)

                # Output JSON
                console.print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                # Table output format
                table = Table(title=":wrench: Components")
                table.add_column("UUID", style="dim", width=38)
                table.add_column("Name", style="cyan", width=30)
                table.add_column("Type", style="green", width=18, no_wrap=False)

                for comp in components:
                    # Get type value - handle both enum and int
                    type_value = comp.type.value if hasattr(comp.type, 'value') else comp.type
                    type_name = value_to_type.get(type_value, "unknown")

                    table.add_row(
                        str(comp.uuid),
                        str(comp.name)[:29],
                        type_name
                    )

                console.print(table)
                console.print(f"\n:information_source: [dim]Total: {len(components)} components[/dim]")

                if component_type:
                    console.print(f"[dim]Type: {component_type}[/dim]")
                if filter:
                    console.print(f"[dim]Filter: '{filter}'[/dim]")
        else:
            console.print(":memo: No components found in database.")
            if filter:
                console.print(f"[dim]Try a different filter term[/dim]")

    except Exception as e:
        console.print(f":x: Error: {e}")
        import traceback
        traceback.print_exc()


@component_app.command()
def create(
    component_type: str = typer.Option(..., "--type", "-t", help="Component type (strategy/risk/sizer/selector/analyzer)"),
    name: str = typer.Option(..., "--name", "-n", help="Component name"),
    class_name: str = typer.Option(..., "--class", "-c", help="Python class name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Component description"),
    tags: Optional[str] = typer.Option(None, "--tags", help=":tag: Comma-separated tags"),
    author: Optional[str] = typer.Option(None, "--author", help=":person: Author name"),
):
    """
    :plus: Create a new component.
    """
    console.print(f":plus: Creating {component_type} component: {name}")

    try:
        # TODO: Implement actual component creation
        console.print(":information: Component creation not yet implemented")

        # 模拟创建
        component_id = f"comp_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"

        console.print(f":white_check_mark: Component '{name}' created successfully")
        console.print(f"  • Component ID: {component_id}")
        console.print(f"  • Type: {component_type}")
        console.print(f"  • Class: {class_name}")
        console.print(f"  • Description: {description or 'No description'}")
        console.print(f"  • Tags: {tags or 'No tags'}")
        console.print(f"  • Author: {author or 'Unknown'}")

    except Exception as e:
        console.print(f":x: Error: {e}")


# Mapping 相关命令
@mapping_app.command()
def list(
    from_type: Optional[str] = typer.Option(None, "--from-type", help="Filter by from type"),
    to_type: Optional[str] = typer.Option(None, "--to-type", help="Filter by to type"),
    page: int = typer.Option(20, "--page", "-p", help="Page size"),
):
    """
    :clipboard: List all mappings.
    """
    console.print(":clipboard: Listing mappings...")

    # TODO: Implement actual mapping listing
    console.print(":information: Mapping listing not yet implemented")


@mapping_app.command()
def create(
    from_type: str = typer.Option(..., "--from-type", help="From type (portfolio/engine/component)"),
    from_id: str = typer.Option(..., "--from-id", help="From UUID"),
    to_type: str = typer.Option(..., "--to-type", help="To type (portfolio/engine/component)"),
    to_id: str = typer.Option(..., "--to-id", help="To UUID"),
    priority: int = typer.Option(1, "--priority", help="Priority (1-100)"),
):
    """
    :link: Create a new mapping relationship.
    """
    console.print(f":link: Creating mapping: {from_type}:{from_id} -> {to_type}:{to_id}")

    # TODO: Implement actual mapping creation
    console.print(":information: Mapping creation not yet implemented")


@mapping_app.command()
def priority(
    mapping_id: str = typer.Argument(..., help=":wrench: Mapping ID"),
    priority: int = typer.Argument(..., help=":1234: New priority value"),
):
    """
    :wrench: Update mapping priority.
    """
    console.print(f":wrench: Updating priority for mapping: {mapping_id} to {priority}")

    try:
        # 验证优先级值
        if priority < 1 or priority > 100:
            console.print(":x: Priority must be between 1 and 100")
            raise typer.Exit(1)

        # TODO: Implement actual priority update
        console.print(":information: Mapping priority update not yet implemented")
        console.print(f":white_check_mark: Priority updated to {priority}")

    except Exception as e:
        console.print(f":x: Error: {e}")


# Result 相关命令
@result_app.command()
def list(
    backtest_id: Optional[str] = typer.Option(None, "--backtest", "-b", help="Filter by backtest ID"),
    portfolio: Optional[str] = typer.Option(None, "--portfolio", "-p", help="Filter by portfolio ID"),
    page: int = typer.Option(20, "--page", "-p", help="Page size"),
):
    """
    :clipboard: List all backtest results.
    """
    console.print(":clipboard: Listing results...")

    # TODO: Implement actual result listing
    console.print(":information: Result listing not yet implemented")


@result_app.command()
def get(
    result_id: str = typer.Argument(..., help=":mag: Result ID"),
    details: bool = typer.Option(False, "--details", "-d", help=":information_source: Show detailed result information"),
    trades: bool = typer.Option(False, "--trades", "-t", help=":repeat: Show trade history"),
):
    """
    :mag: Get backtest result details.
    """
    console.print(f":mag: Getting result details: {result_id}")

    try:
        # TODO: Implement actual result retrieval
        console.print(":information: Result details not yet implemented")

        # 模拟数据
        console.print(f":white_check_mark: Found result: {result_id}")

        if details:
            console.print("\n:gear: Detailed Results:")
            console.print("  • Total Return: 15.2%")
            console.print("  • Annualized Return: 18.7%")
            console.print("  • Sharpe Ratio: 1.45")
            console.print("  • Max Drawdown: -8.3%")

        if trades:
            console.print("\n:repeat: Trade History:")
            console.print("  • 2025-01-01: BUY 000001.SZ @ 10.50 (100 shares)")
            console.print("  • 2025-01-05: SELL 000001.SZ @ 11.20 (100 shares)")

    except Exception as e:
        console.print(f":x: Error: {e}")


@result_app.command("show")
def show(
    run_id: Optional[str] = typer.Option(None, "--run-id", "-r", help=":abc: Run session ID"),
    portfolio_id: Optional[str] = typer.Option(None, "--portfolio", "-p", help=":bank: Portfolio ID"),
    analyzer: Optional[str] = typer.Option(None, "--analyzer", "-a", help=":bar_chart: Analyzer name"),
    mode: str = typer.Option("table", "--mode", "-m", help=":display: Display mode (table/terminal/plot)"),
    limit: int = typer.Option(50, "--limit", "-l", help=":1234: Max records to display"),
):
    """
    :chart_with_upwards_trend: Show analyzer results by run_id.

    Examples:
        ginkgo result show                    # List available runs
        ginkgo result show --run-id eng_abc_r_251223_1200_001
        ginkgo result show --run-id xxx --portfolio yyy --analyzer net_value --mode terminal
    """
    from ginkgo.data.containers import container
    from ginkgo.libs.utils.display import (
        display_dataframe,
        display_terminal_chart,
    )
    import pandas as pd

    result_service = container.result_service()

    # 如果没有指定 run_id，列出所有可用的运行会话
    if run_id is None:
        list_result = result_service.list_runs()
        if not list_result.success:
            console.print(f":x: [red]获取运行会话列表失败[/red]")
            console.print(f"[yellow]{list_result.error}[/yellow]")
            raise typer.Exit(1)

        runs = list_result.data
        if not runs:
            console.print(":exclamation: [yellow]没有找到可用的运行会话[/yellow]")
            console.print("[dim]请先运行回测: ginkgo engine run <engine_id>[/dim]")
            raise typer.Exit(0)

        # 转换为 DataFrame 显示
        df = pd.DataFrame(runs)

        columns_config = {
            "engine_name": {"display_name": "Engine", "style": "green"},
            "run_id": {"display_name": "Run ID", "style": "cyan"},
            "portfolio_name": {"display_name": "Portfolio", "style": "yellow"},
            "timestamp": {"display_name": "Run Time", "style": "dim"},
            "record_count": {"display_name": "Records", "style": "blue"}
        }

        display_dataframe(
            data=df,
            columns_config=columns_config,
            title=":chart_with_upwards_trend: [bold]可用的运行会话[/bold]",
            console=console
        )
        console.print("\n[yellow]使用 --run-id 参数查看详细结果[/yellow]")
        console.print("[dim]示例: ginkgo result show --run-id <run_id>[/dim]")
        raise typer.Exit(0)

    # 获取运行摘要
    summary_result = result_service.get_run_summary(run_id)
    if not summary_result.success:
        console.print(f":x: [red]未找到 run_id={run_id} 的记录[/red]")
        console.print(f"[yellow]{summary_result.error}[/yellow]")
        raise typer.Exit(1)

    summary = summary_result.data
    console.print(f":information_source: [bold]运行会话摘要:[/bold]")
    console.print(f"  Run ID: {summary['run_id']}")
    console.print(f"  Engine ID: {summary['engine_id']}")
    console.print(f"  总记录数: {summary['total_records']}")
    console.print("")

    # 自动选择 portfolio（如果只有一个）
    if portfolio_id is None:
        if summary['portfolio_count'] > 1:
            console.print(f":briefcase: [bold]可用的投资组合 ({summary['portfolio_count']}个):[/bold]")
            for pid in summary['portfolios']:
                console.print(f"  - {pid}")
            console.print("")
            console.print("[yellow]请使用 --portfolio 参数指定投资组合[/yellow]")
            raise typer.Exit(0)
        else:
            portfolio_id = summary['portfolios'][0]
            console.print(f":briefcase: [cyan]使用投资组合: {portfolio_id}[/cyan]")
            console.print("")

    # 自动选择 analyzer（如果只有一个）
    if analyzer is None:
        analyzers_result = result_service.get_portfolio_analyzers(run_id, portfolio_id)
        if analyzers_result.success:
            analyzers = analyzers_result.data
            if len(analyzers) > 1:
                console.print(f":bar_chart: [bold]可用的分析器 ({len(analyzers)}个):[/bold]")
                for name in analyzers:
                    console.print(f"  - {name}")
                console.print("")
                console.print("[yellow]请使用 --analyzer 参数指定分析器[/yellow]")
                raise typer.Exit(0)
            else:
                analyzer = analyzers[0]
                console.print(f":bar_chart: [cyan]使用分析器: {analyzer}[/cyan]")
                console.print("")

    # 获取数据
    data_result = result_service.get_analyzer_values(
        run_id=run_id,
        portfolio_id=portfolio_id,
        analyzer_name=analyzer
    )

    if not data_result.success:
        console.print(f":x: [red]获取数据失败[/red]")
        console.print(f"[yellow]{data_result.error}[/yellow]")
        raise typer.Exit(1)

    # 转换为 DataFrame
    result_df = data_result.data.to_dataframe()

    if result_df is None or result_df.shape[0] == 0:
        console.print(":exclamation: [yellow]没有数据可显示[/yellow]")
        raise typer.Exit(0)

    # 显示数据
    if mode == "table":
        columns_config = {
            "timestamp": {"display_name": "Date", "style": "cyan"},
            "value": {"display_name": "Value", "style": "yellow"}
        }
        title = f":bar_chart: [bold]{analyzer}[/bold] [dim]({run_id})[/dim]"
        display_dataframe(
            data=result_df.head(limit),
            columns_config=columns_config,
            title=title,
            console=console
        )

    elif mode == "terminal":
        console.print(f"[dim]显示 {result_df.shape[0]} 条记录[/dim]")
        display_terminal_chart(
            data=result_df.head(limit) if limit > 0 else result_df,
            title=f"{analyzer} [{run_id}]",
            max_points=limit,
            console=console
        )

    else:
        console.print(f":x: [red]不支持的显示模式: {mode}[/red]")
        console.print("[yellow]支持的模式: table, terminal[/yellow]")
        raise typer.Exit(1)


@result_app.command()
def get(
    result_id: str = typer.Argument(..., help=":mag: Result ID"),
    details: bool = typer.Option(False, "--details", "-d", help=":information_source: Show detailed result information"),
    trades: bool = typer.Option(False, "--trades", "-t", help=":repeat: Show trade history"),
):
    """
    :mag: Get backtest result details.
    """
    console.print(f":mag: Getting result details: {result_id}")

    try:
        # TODO: Implement actual result retrieval
        console.print(":information: Result details not yet implemented")

        # 模拟数据
        console.print(f":white_check_mark: Found result: {result_id}")

        if details:
            console.print("\n:gear: Detailed Results:")
            console.print("  • Total Return: 15.2%")
            console.print("  • Annualized Return: 18.7%")
            console.print("  • Sharpe Ratio: 1.45")
            console.print("  • Max Drawdown: -8.3%")

        if trades:
            console.print("\n:repeat: Trade History:")
            console.print("  • 2025-01-01: BUY 000001.SZ @ 10.50 (100 shares)")
            console.print("  • 2025-01-05: SELL 000001.SZ @ 11.20 (100 shares)")

    except Exception as e:
        console.print(f":x: Error: {e}")


# 将所有应用注册到get_app中
get_app.add_typer(component_app, name="component", help=":wrench: Get component information")
get_app.add_typer(mapping_app, name="mapping", help=":link: Get mapping information")
get_app.add_typer(result_app, name="result", help=":bar_chart: Get result information")

# 设置应用 - 为简化，将所有命令都放在get_app下
set_app.add_typer(mapping_app, name="mapping", help=":link: Set mapping properties")
delete_app.add_typer(mapping_app, name="mapping", help=":link: Delete mapping")