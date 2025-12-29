# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: 统一CLI接口，提供get获取、set设置、list列表、create创建、delete删除、run运行等统一命令模式，简化CLI操作和学习曲线






"""
Ginkgo Unified CLI - 统一的命令行接口
使用 get/set/list/create/delete/run 统一命令模式
"""

import typer
from typing import Optional, Any, Dict, List
from rich.console import Console
from rich.table import Table
from rich import print
import json

app = typer.Typer(help="[yellow]:zap:[/yellow] Ginkgo Unified Commands", rich_markup_mode="rich")
console = Console()

# 资源类型定义
RESOURCE_TYPES = {
    'engines': {
        'service': 'engine_service',
        'commands': ['get', 'list', 'create', 'delete', 'set', 'run'],
        'description': 'Backtesting engines'
    },
    'portfolios': {
        'service': 'portfolio_service',
        'commands': ['get', 'list', 'create', 'delete', 'set'],
        'description': 'Trading portfolios'
    },
    'data': {
        'service': 'data_service',
        'subtypes': ['stockinfo', 'bars', 'ticks', 'sources'],
        'commands': ['get', 'list', 'set'],
        'description': 'Market data'
    },
    'config': {
        'service': 'config_service',
        'commands': ['get', 'set', 'list'],
        'description': 'System configuration'
    },
    'strategies': {
        'service': 'strategy_service',
        'commands': ['get', 'list', 'create', 'delete'],
        'description': 'Trading strategies'
    }
}

@app.command()
def get(
    resource: str = typer.Argument(..., help="Resource type (engines/portfolios/data/config/strategies)"),
    resource_id: Optional[str] = typer.Argument(None, help="Resource ID (for specific resource)"),
    subtype: Optional[str] = typer.Option(None, "--type", "-t", help="Resource subtype (for data: stockinfo/bars/ticks/sources)"),
    filters: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter criteria (key=value format)"),
    format: Optional[str] = typer.Option("table", "--format", help="Output format (table/json)"),
    page: int = typer.Option(20, "--page", "-p", help="Page size for list results"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit results"),
):
    """
    [blue]:mag:[/blue] Get resource information.

    Examples:
      ginkgo get engines                           # List all engines
      ginkgo get engines <engine-id>               # Get specific engine
      ginkgo get data stockinfo                   # Get stock information
      ginkgo get config debug                     # Get debug setting
      ginkgo get strategies --filter name=ma*     # Filter strategies
    """
    try:
        if resource not in RESOURCE_TYPES:
            console.print(f"[red]:x:[/red] Unknown resource type: {resource}")
            console.print(f"Available resources: {', '.join(RESOURCE_TYPES.keys())}")
            raise typer.Exit(1)

        if 'get' not in RESOURCE_TYPES[resource]['commands']:
            console.print(f"[red]:x:[/red] 'get' command not supported for {resource}")
            raise typer.Exit(1)

        # 解析过滤器
        filter_dict = {}
        if filters:
            try:
                for item in filters.split(','):
                    if '=' in item:
                        key, value = item.split('=', 1)
                        filter_dict[key.strip()] = value.strip()
            except Exception as e:
                console.print(f"[red]:x:[/red] Invalid filter format: {e}")
                raise typer.Exit(1)

        # 路由到具体的处理函数
        if resource == 'engines':
            _handle_get_engines(resource_id, filter_dict, format, page, limit)
        elif resource == 'portfolios':
            _handle_get_portfolios(resource_id, filter_dict, format, page, limit)
        elif resource == 'data':
            if not subtype:
                console.print("[red]:x:[/red] Data subtype required (stockinfo/bars/ticks/sources)")
                raise typer.Exit(1)
            _handle_get_data(subtype, resource_id, filter_dict, format, page, limit)
        elif resource == 'config':
            _handle_get_config(resource_id, format)
        elif resource == 'strategies':
            _handle_get_strategies(resource_id, filter_dict, format, page, limit)

    except Exception as e:
        console.print(f"[red]:x:[/red] Error: {e}")
        raise typer.Exit(1)

@app.command()
def set(
    resource: str = typer.Argument(..., help="Resource type (engines/portfolios/data/config)"),
    key: str = typer.Argument(..., help="Setting key or resource ID"),
    value: Optional[str] = typer.Argument(None, help="Setting value"),
    subtype: Optional[str] = typer.Option(None, "--type", "-t", help="Resource subtype (for data)"),
    filters: Optional[str] = typer.Option(None, "--filter", "-f", help="Additional filters"),
):
    """
    [blue]:gear:[/blue] Set resource properties or configuration.

    Examples:
      ginkgo set config debug on                    # Set debug mode
      ginkgo set config cpu_ratio 80                # Set CPU usage limit
      ginkgo set data stockinfo sync                # Sync stock data
      ginkgo set engine <engine-id> status active   # Set engine status
    """
    try:
        if resource not in RESOURCE_TYPES:
            console.print(f"[red]:x:[/red] Unknown resource type: {resource}")
            raise typer.Exit(1)

        if 'set' not in RESOURCE_TYPES[resource]['commands']:
            console.print(f"[red]:x:[/red] 'set' command not supported for {resource}")
            raise typer.Exit(1)

        # 路由到具体的处理函数
        if resource == 'config':
            _handle_set_config(key, value)
        elif resource == 'data':
            if not subtype:
                console.print("[red]:x:[/red] Data subtype required")
                raise typer.Exit(1)
            _handle_set_data(subtype, key, value)
        elif resource == 'engines':
            _handle_set_engine(key, value, filters)
        elif resource == 'portfolios':
            _handle_set_portfolio(key, value, filters)

    except Exception as e:
        console.print(f"[red]:x:[/red] Error: {e}")
        raise typer.Exit(1)

@app.command()
def list(
    resource: str = typer.Argument(..., help="Resource type (engines/portfolios/data/config/strategies)"),
    subtype: Optional[str] = typer.Option(None, "--type", "-t", help="Resource subtype (for data)"),
    filters: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter criteria"),
    format: Optional[str] = typer.Option("table", "--format", help="Output format (table/json)"),
    page: int = typer.Option(20, "--page", "-p", help="Page size"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="Limit results"),
):
    """
    [blue]:clipboard:[/blue] List resources.

    Examples:
      ginkgo list engines                           # List all engines
      ginkgo list portfolios                        # List all portfolios
      ginkgo list data sources                      # List data sources
      ginkgo list strategies --filter name=ma*     # Filter strategies
      ginkgo list config --format json             # Export as JSON
    """
    try:
        if resource not in RESOURCE_TYPES:
            console.print(f"[red]:x:[/red] Unknown resource type: {resource}")
            raise typer.Exit(1)

        if 'list' not in RESOURCE_TYPES[resource]['commands']:
            console.print(f"[red]:x:[/red] 'list' command not supported for {resource}")
            raise typer.Exit(1)

        # 解析过滤器
        filter_dict = {}
        if filters:
            try:
                for item in filters.split(','):
                    if '=' in item:
                        key, value = item.split('=', 1)
                        filter_dict[key.strip()] = value.strip()
            except Exception as e:
                console.print(f"[red]:x:[/red] Invalid filter format: {e}")
                raise typer.Exit(1)

        # 路由到具体的处理函数
        if resource == 'engines':
            _handle_get_engines(None, filter_dict, format, page, limit)
        elif resource == 'portfolios':
            _handle_get_portfolios(None, filter_dict, format, page, limit)
        elif resource == 'data':
            if not subtype:
                console.print("[red]:x:[/red] Data subtype required")
                raise typer.Exit(1)
            _handle_get_data(subtype, None, filter_dict, format, page, limit)
        elif resource == 'config':
            _handle_get_config(None, format)
        elif resource == 'strategies':
            _handle_get_strategies(None, filter_dict, format, page, limit)

    except Exception as e:
        console.print(f"[red]:x:[/red] Error: {e}")
        raise typer.Exit(1)

@app.command()
def create(
    resource: str = typer.Argument(..., help="Resource type (engines/portfolios/strategies)"),
    name: str = typer.Option(..., "--name", "-n", help="Resource name"),
    resource_type: Optional[str] = typer.Option(None, "--type", "-t", help="Resource type (for engines)"),
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Configuration JSON or file"),
):
    """
    [green]➕[/green] Create new resources.

    Examples:
      ginkgo create engine "My Backtest Engine" --type historic
      ginkgo create portfolio "Test Portfolio"
      ginkgo create strategy "My Strategy" --file /path/to/strategy.py
    """
    try:
        if resource not in RESOURCE_TYPES:
            console.print(f"[red]:x:[/red] Unknown resource type: {resource}")
            raise typer.Exit(1)

        if 'create' not in RESOURCE_TYPES[resource]['commands']:
            console.print(f"[red]:x:[/red] 'create' command not supported for {resource}")
            raise typer.Exit(1)

        # 路由到具体的处理函数
        if resource == 'engines':
            _handle_create_engine(name, resource_type, config)
        elif resource == 'portfolios':
            _handle_create_portfolio(name, config)
        elif resource == 'strategies':
            _handle_create_strategy(name, config)

    except Exception as e:
        console.print(f"[red]:x:[/red] Error: {e}")
        raise typer.Exit(1)

@app.command()
def delete(
    resource: str = typer.Argument(..., help="Resource type (engines/portfolios/strategies)"),
    resource_id: str = typer.Argument(..., help="Resource ID to delete"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
):
    """
    [red]:wastebasket:[/red] Delete resources.

    Examples:
      ginkgo delete engine <engine-id>
      ginkgo delete portfolio <portfolio-id> --confirm
      ginkgo delete strategy <strategy-id>
    """
    try:
        if resource not in RESOURCE_TYPES:
            console.print(f"[red]:x:[/red] Unknown resource type: {resource}")
            raise typer.Exit(1)

        if 'delete' not in RESOURCE_TYPES[resource]['commands']:
            console.print(f"[red]:x:[/red] 'delete' command not supported for {resource}")
            raise typer.Exit(1)

        # 确认删除
        if not confirm:
            if not typer.confirm(f"Are you sure you want to delete {resource} {resource_id}?"):
                console.print("[red]:x:[/red] Deletion cancelled")
                raise typer.Exit(0)

        # 路由到具体的处理函数
        if resource == 'engines':
            _handle_delete_engine(resource_id)
        elif resource == 'portfolios':
            _handle_delete_portfolio(resource_id)
        elif resource == 'strategies':
            _handle_delete_strategy(resource_id)

    except Exception as e:
        console.print(f"[red]:x:[/red] Error: {e}")
        raise typer.Exit(1)

# 处理函数 - 这些将调用具体的服务
def _handle_get_engines(engine_id=None, filters=None, format="table", page=20, limit=None):
    """处理引擎获取"""
    from ginkgo.data.containers import container

    engine_service = container.engine_service()

    if engine_id:
        # 获取特定引擎
        result = engine_service.get(engine_id=engine_id)
        if result.success and result.data:
            engine = result.data
            console.print(f"[blue]:wrench:[/blue] Engine: {engine.name}")
            console.print(f"[blue]:clipboard:[/blue] UUID: {engine.uuid}")
            console.print(f"[blue]:bar_chart:[/blue] Status: {engine.status}")
            console.print(f"[blue]🔄[/blue] Is Live: {engine.is_live}")
        else:
            console.print(f"[red]:x:[/red] Engine not found: {engine_id}")
    else:
        # 列出引擎
        result = engine_service.get(limit=limit or page)
        if result.success and result.data:
            engines = result.data
            if format == "json":
                engine_list = [{"uuid": e.uuid, "name": e.name, "status": e.status, "is_live": e.is_live} for e in engines]
                print(json.dumps(engine_list, indent=2))
            else:
                table = Table(title="[blue]:wrench:[/blue] Engines")
                table.add_column("UUID", style="cyan", width=36)
                table.add_column("Name", style="green", width=20)
                table.add_column("Status", style="yellow", width=15)
                table.add_column("Live", style="red", width=8)

                for engine in engines:
                    table.add_row(engine.uuid[:36], engine.name[:18], str(engine.status)[:13], str(engine.is_live)[:6])

                console.print(table)
        else:
            console.print("[blue]📭[/blue] No engines found")

def _handle_get_portfolios(portfolio_id=None, filters=None, format="table", page=20, limit=None):
    """处理投资组合获取"""
    from ginkgo.data.containers import container

    portfolio_service = container.portfolio_service()

    if portfolio_id:
        # 获取特定投资组合
        result = portfolio_service.get(portfolio_id=portfolio_id)
        if result.success and result.data:
            portfolio = result.data
            console.print(f"[blue]🏦[/blue] Portfolio: {portfolio.name}")
            console.print(f"[blue]:clipboard:[/blue] UUID: {portfolio.uuid}")
            console.print(f"[blue]:bar_chart:[/blue] Status: {portfolio.status}")
            console.print(f"[blue]🔄[/blue] Is Live: {portfolio.is_live}")
        else:
            console.print(f"[red]:x:[/red] Portfolio not found: {portfolio_id}")
    else:
        # 列出投资组合
        result = portfolio_service.get(limit=limit or page)
        if result.success and result.data:
            portfolios = result.data
            if format == "json":
                portfolio_list = [{"uuid": p.uuid, "name": p.name, "status": p.status, "is_live": p.is_live} for p in portfolios]
                print(json.dumps(portfolio_list, indent=2))
            else:
                table = Table(title="[blue]🏦[/blue] Portfolios")
                table.add_column("UUID", style="cyan", width=36)
                table.add_column("Name", style="green", width=25)
                table.add_column("Status", style="yellow", width=15)
                table.add_column("Live", style="red", width=8)

                for portfolio in portfolios:
                    table.add_row(portfolio.uuid[:36], portfolio.name[:23], str(portfolio.status)[:13], str(portfolio.is_live)[:6])

                console.print(table)
        else:
            console.print("[blue]📭[/blue] No portfolios found")

def _handle_get_data(subtype, resource_id=None, filters=None, format="table", page=20, limit=None):
    """处理数据获取"""
    from ginkgo.data.containers import container

    if subtype == "stockinfo":
        stockinfo_service = container.stockinfo_service()
        result = stockinfo_service.get(limit=limit or page)
        if result.success and result.data:
            if format == "json":
                print(result.data.to_json() if hasattr(result.data, 'to_json') else str(result.data))
            else:
                table = Table(title="[blue]:bar_chart:[/blue] Stock Information")
                table.add_column("Code", style="cyan", width=12)
                table.add_column("Name", style="green", width=25)
                table.add_column("Market", style="yellow", width=10)
                table.add_column("Industry", style="magenta", width=20)

                # 显示前几条记录
                df = result.data if hasattr(result.data, 'head') else result.data
                for _, row in df.head(limit or 10).iterrows() if hasattr(df, 'iterrows') else []:
                    table.add_row(str(row.get('code', ''))[:10], str(row.get('name', ''))[:23],
                                str(row.get('market', ''))[:8], str(row.get('industry', ''))[:18])

                console.print(table)
    elif subtype == "sources":
        console.print("[blue]📡[/blue] Available Data Sources:")
        table = Table()
        table.add_column("Source", style="cyan", width=15)
        table.add_column("Type", style="green", width=15)
        table.add_column("Status", style="yellow", width=10)
        table.add_column("Description", style="white", width=30)

        table.add_row("tushare", "Premium", "Active", "Chinese stock market data")
        table.add_row("akshare", "Free", "Active", "Free Chinese financial data")
        table.add_row("yfinance", "Free", "Active", "Yahoo Finance data")

        console.print(table)
    else:
        console.print(f"[red]:x:[/red] Data subtype '{subtype}' not yet implemented")

def _handle_get_config(key=None, format="table"):
    """处理配置获取"""
    from ginkgo.libs import GCONF

    if key:
        if key.lower() == 'debug':
            console.print(f"[green]:white_check_mark:[/green] debug: {GCONF.DEBUGMODE}")
        elif key.lower() == 'quiet':
            console.print(f"[green]:white_check_mark:[/green] quiet: {GCONF.QUIET}")
        elif key.lower() == 'cpu_ratio':
            console.print(f"[green]:white_check_mark:[/green] cpu_ratio: {GCONF.CPURATIO*100:.1f}%")
        else:
            console.print(f"[red]:x:[/red] Configuration key '{key}' not found")
    else:
        # 显示所有配置
        console.print("[blue]:gear:[/blue] System Configuration:")

        if format == "json":
            config_data = {
                "debug": GCONF.DEBUGMODE,
                "quiet": GCONF.QUIET,
                "cpu_ratio": GCONF.CPURATIO * 100,
                "log_path": str(GCONF.LOGGING_PATH),
                "working_path": str(GCONF.WORKING_PATH)
            }
            print(json.dumps(config_data, indent=2))
        else:
            table = Table()
            table.add_column("Key", style="cyan", width=15)
            table.add_column("Value", style="green", width=25)
            table.add_column("Description", style="dim", width=30)

            table.add_row("debug", str(GCONF.DEBUGMODE), "Enable detailed logging")
            table.add_row("quiet", str(GCONF.QUIET), "Suppress verbose output")
            table.add_row("cpu_ratio", f"{GCONF.CPURATIO*100:.1f}%", "CPU usage limit")
            table.add_row("log_path", str(GCONF.LOGGING_PATH), "Log files location")
            table.add_row("working_path", str(GCONF.WORKING_PATH), "Working directory")

            console.print(table)

def _handle_get_strategies(strategy_id=None, filters=None, format="table", page=20, limit=None):
    """处理策略获取"""
    from ginkgo.data.containers import container

    console.print("[blue]:clipboard:[/blue] Available Strategies:")
    table = Table()
    table.add_column("Strategy", style="cyan", width=20)
    table.add_column("Type", style="green", width=15)
    table.add_column("Description", style="white", width=35)

    # 示例策略列表
    strategies = [
        ("random_signal", "Strategy", "Random signal strategy for testing"),
        ("preset_trend_follow", "Strategy", "Trend following strategy"),
        ("preset_mean_reversion", "Strategy", "Mean reversion strategy"),
        ("preset_loss_limit", "RiskManager", "Loss limit risk management"),
        ("preset_fixed_selector", "Selector", "Fixed stock selector"),
        ("preset_fixed_sizer", "Sizer", "Fixed position sizer"),
    ]

    for strategy in strategies:
        table.add_row(*strategy)

    console.print(table)

def _handle_set_config(key, value):
    """处理配置设置"""
    from ginkgo.libs import GCONF

    if key.lower() == 'debug':
        debug_value = value.lower() in ['on', 'true', '1', 'yes']
        GCONF.set_debug(debug_value)
        console.print(f"[green]:white_check_mark:[/green] Set debug = {debug_value}")
    elif key.lower() == 'quiet':
        quiet_value = value.lower() in ['on', 'true', '1', 'yes']
        GCONF.set_quiet(quiet_value)
        console.print(f"[green]:white_check_mark:[/green] Set quiet = {quiet_value}")
    elif key.lower() == 'cpu_ratio':
        cpu_value = float(value) / 100.0
        GCONF.set_cpu_ratio(cpu_value)
        console.print(f"[green]:white_check_mark:[/green] Set cpu_ratio = {value}%")
    else:
        console.print(f"[red]:x:[/red] Configuration key '{key}' not found")

def _handle_set_data(subtype, action, value):
    """处理数据设置"""
    if subtype == "stockinfo" and action == "sync":
        from ginkgo.data.containers import container
        stockinfo_service = container.stockinfo_service()
        result = stockinfo_service.sync()
        if result.success:
            console.print(f"[green]:white_check_mark:[/green] Stock info sync completed: {result.data}")
        else:
            console.print(f"[red]:x:[/red] Stock info sync failed: {result.error}")
    else:
        console.print(f"[red]:x:[/red] Data action '{action}' for '{subtype}' not yet implemented")

def _handle_set_engine(engine_id, key, value, filters):
    """处理引擎设置"""
    console.print(f"[red]:x:[/red] Engine setting not yet implemented: {key} = {value}")

def _handle_set_portfolio(portfolio_id, key, value, filters):
    """处理投资组合设置"""
    console.print(f"[red]:x:[/red] Portfolio setting not yet implemented: {key} = {value}")

def _handle_create_engine(name, engine_type, config):
    """处理引擎创建"""
    from ginkgo.data.containers import container

    engine_service = container.engine_service()
    is_live = engine_type == "live" if engine_type else False

    result = engine_service.add(name=name, is_live=is_live)
    if result.success:
        engine_uuid = result.data.uuid if result.data else None
        console.print(f"[green]:white_check_mark:[/green] Engine created successfully")
        console.print(f"[blue]:wrench:[/blue] Name: {name}")
        console.print(f"[blue]:clipboard:[/blue] UUID: {engine_uuid}")
        console.print(f"[blue]🔄[/blue] Type: {'Live' if is_live else 'Backtest'}")
    else:
        console.print(f"[red]:x:[/red] Engine creation failed: {result.error}")

def _handle_create_portfolio(name, config):
    """处理投资组合创建"""
    from ginkgo.data.containers import container

    portfolio_service = container.portfolio_service()

    result = portfolio_service.add(name=name, backtest_start_date="2020-01-01",
                                 backtest_end_date="2021-01-01", is_live=False)
    if result.success:
        portfolio_uuid = result.data.uuid if result.data else None
        console.print(f"[green]:white_check_mark:[/green] Portfolio created successfully")
        console.print(f"[blue]🏦[/blue] Name: {name}")
        console.print(f"[blue]:clipboard:[/blue] UUID: {portfolio_uuid}")
        console.print(f"[blue]:bar_chart:[/blue] Period: 2020-01-01 to 2021-01-01")
    else:
        console.print(f"[red]:x:[/red] Portfolio creation failed: {result.error}")

def _handle_create_strategy(name, config):
    """处理策略创建"""
    console.print(f"[red]:x:[/red] Strategy creation not yet implemented: {name}")

def _handle_delete_engine(engine_id):
    """处理引擎删除"""
    from ginkgo.data.containers import container

    engine_service = container.engine_service()
    result = engine_service.delete(engine_id)
    if result.success:
        console.print(f"[green]:white_check_mark:[/green] Engine {engine_id} deleted successfully")
    else:
        console.print(f"[red]:x:[/red] Engine deletion failed: {result.error}")

def _handle_delete_portfolio(portfolio_id):
    """处理投资组合删除"""
    from ginkgo.data.containers import container

    portfolio_service = container.portfolio_service()
    result = portfolio_service.delete(portfolio_id)
    if result.success:
        console.print(f"[green]:white_check_mark:[/green] Portfolio {portfolio_id} deleted successfully")
    else:
        console.print(f"[red]:x:[/red] Portfolio deletion failed: {result.error}")

def _handle_delete_strategy(strategy_id):
    """处理策略删除"""
    console.print(f"[red]:x:[/red] Strategy deletion not yet implemented: {strategy_id}")

if __name__ == "__main__":
    app()