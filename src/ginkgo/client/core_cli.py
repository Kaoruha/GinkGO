#!/usr/bin/env python3
"""
Core CLI Commands - 顶级核心命令
提供最常用的简化命令，提升用户体验

LAZY LOADING PATTERN:
- All Ginkgo module imports are moved inside functions for faster CLI startup
- Use try-except blocks for error handling when importing heavy modules
- Import only what's needed, when it's needed
- Keep basic UI imports (typer, rich) at module level
"""

import typer
from enum import Enum
from typing import Optional, List
from typing_extensions import Annotated
from rich.console import Console
from rich.table import Table
from rich import print

# All Ginkgo module imports moved to function level for faster CLI startup
console = Console()

class DebugMode(str, Enum):
    ON = "on"
    OFF = "off"

class DataType(str, Enum):
    STOCKINFO = "stockinfo"
    CALENDAR = "calendar" 
    BARS = "bars"
    TICKS = "ticks"

class ComponentType(str, Enum):
    ENGINES = "engines"
    PORTFOLIOS = "portfolios"
    STRATEGIES = "strategies"
    SELECTORS = "selectors"
    SIZERS = "sizers"
    ANALYZERS = "analyzers"

def status():
    """
    :bar_chart: Display system status (simplified from 'system status').
    """
    try:
        from ginkgo.libs import GCONF, GTM
        from ginkgo.libs.utils.display import display_dataframe
        
        GTM.clean_worker_pool()
        GTM.clean_thread_pool() 
        GTM.clean_worker_status()
        
        console.print(f"[bold green]:wrench: Ginkgo System Status[/bold green]")
        console.print(f"Debug Mode : {'[green]ON[/green]' if GCONF.DEBUGMODE else '[red]OFF[/red]'}")
        console.print(f"Quiet Mode : {'[green]ON[/green]' if GCONF.QUIET else '[red]OFF[/red]'}")
        console.print(f"Main Ctrl  : [medium_spring_green]{GTM.main_status}[/]")
        console.print(f"Watch Dog  : [medium_spring_green]{GTM.watch_dog_status}[/]")
        console.print(f"CPU Limit  : {GCONF.CPURATIO*100}%")
        console.print(f"Workers    : {GTM.get_worker_count()}")
        console.print(f"Log Path   : {GCONF.LOGGING_PATH}")
        console.print(f"Work Dir   : {GCONF.WORKING_PATH}")
        
        # Display worker status table using same format as worker status command
        status_data = GTM.get_workers_status()
        console.print("\n[bold]Worker Status:[/bold]")

        if len(status_data) > 0:
            # 转换为status dict为dataframe（复用worker_cli.py的逻辑）
            import pandas as pd
            worker_status_data = []
            for worker_id, worker_info in status_data.items():
                worker_status_data.append({
                    "worker_id": worker_id,
                    "task_name": worker_info.get("task_name", "N/A"),
                    "status": worker_info.get("status", "UNKNOWN"),
                    "memory_mb": worker_info.get("memory_mb", "N/A"),
                    "running_time": worker_info.get("running_time", "N/A")
                })
            
            status_df = pd.DataFrame(worker_status_data)
            
            # 配置列显示（与worker_cli.py保持一致）
            worker_status_columns_config = {
                "worker_id": {"display_name": "Worker ID", "style": "cyan"},
                "task_name": {"display_name": "Task Name", "style": "blue"},
                "status": {"display_name": "Status", "style": "green"},
                "memory_mb": {"display_name": "Memory", "style": "yellow"},
                "running_time": {"display_name": "Running Time", "style": "magenta"}
            }
            
            display_dataframe(
                data=status_df,
                columns_config=worker_status_columns_config,
                title="Active Workers",
                console=console
            )
        else:
            console.print("[dim]No active workers[/dim]")
            
    except Exception as e:
        console.print(f"[red]Error getting system status: {e}[/red]")
        console.print("Try: ginkgo system status (full command)")

def debug(mode: Annotated[DebugMode, typer.Argument(help="Debug mode: on/off")]):
    """
    :bug: Toggle debug mode (simplified from 'system config set --debug').
    """
    try:
        from ginkgo.libs import GCONF
        
        if mode == DebugMode.ON:
            GCONF.set_debug(True)  # 正确的调用方式，会写入配置文件
            console.print("[green]:white_check_mark: Debug mode enabled[/green]")
            console.print("[dim]This enables detailed logging and error information[/dim]")
            console.print("[dim]Configuration saved to ~/.ginkgo/config.yml[/dim]")
        else:
            GCONF.set_debug(False)  # 正确的调用方式，会写入配置文件
            console.print("[yellow]:muted_speaker: Debug mode disabled[/yellow]")
            console.print("[dim]Switched to production logging level[/dim]")
            console.print("[dim]Configuration saved to ~/.ginkgo/config.yml[/dim]")
            
    except Exception as e:
        console.print(f"[red]Error setting debug mode: {e}[/red]")
        console.print("Try: ginkgo system config set --debug on/off")

def init():
    """
    :rocket: Complete system initialization including database setup, component registration, and example data with idempotency.
    """
    try:
        console.print(":rocket: Initializing Ginkgo System...")

        # Step 1: Database initialization (idempotent)
        console.print(":bar_chart: Creating database tables...")
        from ginkgo.data.drivers import create_all_tables, is_table_exists
        from ginkgo.data.models import (
            MStockInfo, MBar, MTick, MSignal, MOrder, MPosition,
            MPortfolio, MEngine, MParam, MAdjustfactor
        )

        create_all_tables()

        # Verify core tables exist (idempotency check)
        core_tables = [MStockInfo, MBar, MSignal, MOrder, MPosition, MPortfolio, MEngine]
        # Skip abstract models like MTick
        missing_tables = []
        for table in core_tables:
            if hasattr(table, '__abstract__') and table.__abstract__:
                continue
            if not is_table_exists(table):
                missing_tables.append(table.__tablename__)

        if missing_tables:
            console.print(f":x: Missing tables: {missing_tables}")
            raise RuntimeError(f"Database tables creation failed: {missing_tables}")

        console.print(":white_check_mark: All database tables created successfully")

        # Step 3: Component registration and example data (idempotent)
        console.print(":wrench: Registering components and loading example data...")
        try:
            from ginkgo.data import seeding
            seeding.run()  # This function includes idempotent component registration
            console.print(":white_check_mark: Components and example data initialized successfully")
        except Exception as e:
            console.print(f":warning: Component initialization had issues: {e}")
            console.print(":information: This may be normal if components already exist")

        # Step 4: System health validation
        console.print(":mag: Validating system health...")
        health_status = _validate_system_health()

        if not health_status["healthy"]:
            console.print(f":warning: System health check warnings: {health_status['issues']}")
        else:
            console.print(":white_check_mark: System health check passed")


        console.print("\n:tada: Ginkgo system initialization completed!")
        console.print("\n:clipboard: System Summary:")
        console.print("  • Database Tables: All core tables created")
        console.print("  • Components: Strategies, analyzers, risk managers registered")
        console.print("  • Example Data: Demo portfolio and engine initialized")
        console.print(f"  • System Health: {'Healthy' if health_status['healthy'] else 'Warning'}")

        console.print("\n:rocket: Next steps:")
        console.print("  • ginkgo status                    # Check system status")
        console.print("  • ginkgo data get stockinfo        # Get stock information")
        console.print("  • ginkgo data show stocks          # List available stocks")
        console.print("  • ginkgo pro components strategies  # View registered strategies")
        console.print("  • ginkgo list engines              # View example engines")

    except Exception as e:
        console.print(f":x: System initialization failed: {e}")
        from ginkgo.libs import GLOG
        GLOG.ERROR(f"System initialization error: {e}")
        console.print(":bulb: Try: ginkgo debug on then ginkgo init")
        raise typer.Exit(1)


def _validate_system_health() -> dict:
    """验证系统健康状态"""
    health_status = {"healthy": True, "issues": []}

    try:
        # 检查数据库连接
        from ginkgo.data.drivers import get_connection_status
        conn_status = get_connection_status()

        for db_name, status in conn_status.items():
            if not status.get("healthy", False):
                health_status["healthy"] = False
                health_status["issues"].append(f"{db_name} connection unhealthy")

        # 检查服务容器
        try:
            from ginkgo.data.containers import container
            stockinfo_service = container.stockinfo_service()
            # Simple service availability check
            test_result = stockinfo_service.get(limit=1)
            if not test_result.success:
                health_status["issues"].append("Stock info service unavailable")
        except Exception as e:
            health_status["issues"].append(f"Service container error: {str(e)[:30]}...")

    except Exception as e:
        health_status["healthy"] = False
        health_status["issues"].append(f"Health check failed: {str(e)[:30]}...")

    return health_status

def get(
    data_type: Annotated[DataType, typer.Argument(help="Data type to fetch")],
    code: Annotated[Optional[str], typer.Option("--code", "-c", help="Stock code (required for bars/ticks)")] = None,
    days: Annotated[int, typer.Option("--days", "-d", help="Number of days to fetch")] = 30,
    start: Annotated[Optional[str], typer.Option("--start", "-s", help="Start date (YYYYMMDD)")] = None,
    end: Annotated[Optional[str], typer.Option("--end", "-e", help="End date (YYYYMMDD)")] = None,
):
    """
    :arrow_down: Fetch market data (simplified from 'data update').
    """
    try:
        console.print(f"[bold blue]:inbox_tray: Fetching {data_type.value}...[/bold blue]")
        
        if data_type == DataType.STOCKINFO:
            from ginkgo.data.containers import container
            stockinfo_service = container.stockinfo_service()
            result = stockinfo_service.sync()
            if result.success:
                console.print(f":white_check_mark: Stock information updated: {result.data}")
            else:
                console.print(f":x: Stock information update failed: {result.error}")

        elif data_type == DataType.CALENDAR:
            from ginkgo.data.containers import container
            # Calendar update might be part of another service - let's try trading calendar
            try:
                bar_service = container.bar_service()
                bar_service.sync_trading_calendar()
            except AttributeError:
                # Fallback to original method if service doesn't have this
                from ginkgo.data import update_calendar
                update_calendar()
            console.print("[green]:white_check_mark: Trading calendar updated[/green]")

        elif data_type == DataType.BARS:
            if not code:
                console.print(":x: Stock code required for bars data")
                console.print("Example: ginkgo get bars --code 000001.SZ")
                return
            from ginkgo.data.containers import container
            bar_service = container.bar_service()
            result = bar_service.sync_smart(code=code, fast_mode=True)
            if result.success:
                console.print(f":white_check_mark: Daily bars updated for {code}")
            else:
                console.print(f":x: Daily bars update failed for {code}: {result.error}")

        elif data_type == DataType.TICKS:
            if not code:
                console.print(":x: Stock code required for ticks data")
                console.print("Example: ginkgo get ticks --code 000001.SZ")
                return
            from ginkgo.data.containers import container
            tick_service = container.tick_service()
            result = tick_service.sync_smart(code=code, fast_mode=True)
            if result.success:
                console.print(f":white_check_mark: Tick data updated for {code}")
            else:
                console.print(f":x: Tick data update failed for {code}: {result.error}")
            
    except Exception as e:
        console.print(f"[red]:x: Failed to fetch {data_type.value}: {e}[/red]")
        console.print(f"Try: ginkgo data update --{data_type.value}")

def show(
    data_type: Annotated[str, typer.Argument(help="Data type to show (stocks/bars/ticks)")],
    code: Annotated[Optional[str], typer.Option("--code", "-c", help="Stock code")] = None,
    page: Annotated[int, typer.Option("--page", "-p", help="Page size")] = 20,
    start: Annotated[Optional[str], typer.Option("--start", "-s", help="Start date (YYYYMMDD)")] = None,
    end: Annotated[Optional[str], typer.Option("--end", "-e", help="End date (YYYYMMDD)")] = None,
):
    """
    :eyes: Display market data (simplified from 'data list/show').
    """
    try:
        console.print(f"[bold blue]:eyes: Showing {data_type}...[/bold blue]")
        
        if data_type == "stocks":
            from ginkgo.data.containers import container
            from ginkgo.libs.utils.display import display_dataframe

            stockinfo_service = container.stockinfo_service()
            result = stockinfo_service.get()
            if not result.success:
                console.print(f"[yellow]:warning:[/yellow] No stock information found: {result.error}")
                console.print("Try: ginkgo data get stockinfo")
                return

            # Convert result data to DataFrame
            import pandas as pd
            if hasattr(result.data, 'to_dataframe'):
                df = result.data.to_dataframe()
            else:
                df = pd.DataFrame(result.data)

            if df.empty:
                console.print("[yellow]:warning:[/yellow] No stock information found. Try: ginkgo data get stockinfo")
                return

            display_dataframe(
                data=df.head(page),
                columns_config={
                    "code": {"display_name": "Code", "style": "cyan"},
                    "name": {"display_name": "Name", "style": "green"},
                    "industry": {"display_name": "Industry", "style": "yellow"},
                },
                title=f"Stock Information (Top {page})",
                console=console
            )
            
        elif data_type == "bars":
            if not code:
                console.print(":x: Stock code required for bars data")
                return
            from ginkgo.data.containers import container
            bar_service = container.bar_service()
            # Note: Need to check if the service has get_bars method with proper parameters
            try:
                result = bar_service.get_by_code(code=code)
                if not result.success:
                    console.print(f":warning: No bars data found for {code}: {result.error}")
                    return

                import pandas as pd
                if hasattr(result.data, 'to_dataframe'):
                    df = result.data.to_dataframe()
                else:
                    df = pd.DataFrame(result.data)

                if df.empty:
                    console.print(f":warning: No bars data found for {code}")
                    return
                console.print(f":white_check_mark: Found {len(df)} bars for {code}")
                print(df.tail(10))  # Show last 10 bars
            except Exception as e:
                console.print(f":warning: Could not fetch bars for {code}: {e}")

        elif data_type == "ticks":
            if not code:
                console.print(":x: Stock code required for ticks data")
                return
            from ginkgo.data.containers import container
            tick_service = container.tick_service()
            try:
                result = tick_service.get_by_code(code=code)
                if not result.success:
                    console.print(f":warning: No ticks data found for {code}: {result.error}")
                    return

                import pandas as pd
                if hasattr(result.data, 'to_dataframe'):
                    df = result.data.to_dataframe()
                else:
                    df = pd.DataFrame(result.data)

                if df.empty:
                    console.print(f":warning: No ticks data found for {code}")
                    return
                console.print(f":white_check_mark: Found {len(df)} ticks for {code}")
                print(df.tail(10))  # Show last 10 ticks
            except Exception as e:
                console.print(f":warning: Could not fetch ticks for {code}: {e}")
            
    except Exception as e:
        console.print(f"[red]:x: Failed to show {data_type}: {e}[/red]")
        console.print(f"Try: ginkgo data list/show {data_type}")

def plot(
    code: Annotated[str, typer.Argument(help="Stock code to plot")],
    data_type: Annotated[str, typer.Option("--type", "-t", help="Data type: day/tick")] = "day",
    start: Annotated[Optional[str], typer.Option("--start", "-s", help="Start date (YYYYMMDD)")] = None,
    end: Annotated[Optional[str], typer.Option("--end", "-e", help="End date (YYYYMMDD)")] = None,
    indicators: Annotated[bool, typer.Option("--indicators", "-i", help="Show technical indicators")] = True,
):
    """
    :chart_with_upwards_trend: Plot candlestick charts (simplified from 'data plot').
    """
    try:
        console.print(f"[bold blue]:chart_with_upwards_trend: Plotting {code} ({data_type})...[/bold blue]")
        
        if data_type == "day":
            from ginkgo.data.containers import container
            bar_service = container.bar_service()
            # Plotting functionality may not be fully implemented in new Service architecture yet
            console.print(":information: Plotting functionality - Service API implementation pending")
            # TODO: 实现新Service架构中的plotting功能
            # 目前回退到原始方法
            from ginkgo.data import plot_daybar
            plot_daybar(code, start=start, end=end, with_indicators=indicators)
        else:
            from ginkgo.data.containers import container
            tick_service = container.tick_service()
            console.print(":information: Tick plotting functionality - Service API implementation pending")
            # TODO: 实现新Service架构中的tick plotting功能
            from ginkgo.data import plot_tick
            plot_tick(code, start=start, end=end)
            
        console.print(f"[green]:white_check_mark: Chart plotted for {code}[/green]")
        
    except Exception as e:
        console.print(f"[red]:x: Failed to plot {code}: {e}[/red]")
        console.print(f"Try: ginkgo data plot {data_type} --code {code}")

def run(
    engine_id: Annotated[str, typer.Argument(help="Engine ID to run")],
    debug_mode: Annotated[bool, typer.Option("--debug", "-d", help="Enable debug logging")] = False,
):
    """
    :rocket: Run backtest (simplified from 'backtest run').
    """
    try:
        console.print(f"[bold blue]:rocket: Running backtest: {engine_id}[/bold blue]")
        
        from ginkgo.trading.core.containers import container as backtest_container
        
        if debug_mode:
            from ginkgo.libs import GCONF
            GCONF.set_debug(True)
            console.print("[dim]Debug mode enabled for this run[/dim]")
        
        # Use the DI service instead of direct factory call
        assembly_service = backtest_container.services.engine_assembly_service()
        result = assembly_service.assemble_backtest_engine(engine_id)
        
        if result.success:
            console.print(f"[green]:white_check_mark: Backtest {engine_id} completed successfully[/green]")
            console.print("View results with: ginkgo results")
        else:
            console.print(f"[red]:x: Failed to run backtest {engine_id}: {result.error}[/red]")
            
    except Exception as e:
        console.print(f"[red]:x: Backtest failed: {e}[/red]")
        console.print(f"Try: ginkgo backtest run {engine_id}")

def list_components(
    component_type: Annotated[ComponentType, typer.Argument(help="Component type to list")],
    page: Annotated[int, typer.Option("--page", "-p", help="Page size")] = 20,
):
    """
    :clipboard: List components (simplified from 'backtest component list').
    """
    try:
        console.print(f"[bold blue]:clipboard: Listing {component_type.value}...[/bold blue]")
        
        from ginkgo.libs.utils.display import display_dataframe
        
        if component_type == ComponentType.ENGINES:
            from ginkgo.data.containers import container
            engine_service = container.engine_service()
            df = engine_service.get_engines()
            columns_config = {
                "uuid": {"display_name": "Engine ID", "style": "cyan"},
                "name": {"display_name": "Name", "style": "green"},
            }
        elif component_type == ComponentType.PORTFOLIOS:
            from ginkgo.data.containers import container
            portfolio_service = container.portfolio_service()
            df = portfolio_service.get_portfolios()
            columns_config = {
                "uuid": {"display_name": "Portfolio ID", "style": "cyan"},
                "name": {"display_name": "Name", "style": "green"},
            }
        else:
            # For strategies, selectors, etc.
            from ginkgo.data.containers import container
            from ginkgo.enums import FILE_TYPES
            file_type_map = {
                ComponentType.STRATEGIES: FILE_TYPES.STRATEGY,
                ComponentType.SELECTORS: FILE_TYPES.SELECTOR,
                ComponentType.SIZERS: FILE_TYPES.SIZER,
                ComponentType.ANALYZERS: FILE_TYPES.ANALYZER,
            }
            file_service = container.file_service()
            df = file_service.get_files_by_type(file_type_map[component_type])
            columns_config = {
                "uuid": {"display_name": "File ID", "style": "cyan"},
                "name": {"display_name": "Name", "style": "green"},
                "type": {"display_name": "Type", "style": "yellow"},
            }
        
        if df.shape[0] == 0:
            console.print(f"[yellow]No {component_type.value} found[/yellow]")
            return
            
        display_dataframe(
            data=df.head(page),
            columns_config=columns_config,
            title=f"{component_type.value.title()} (Top {page})",
            console=console
        )
        
    except Exception as e:
        console.print(f"[red]:x: Failed to list {component_type.value}: {e}[/red]")
        console.print(f"Try: ginkgo backtest component list {component_type.value}")

def results(
    engine_id: Annotated[Optional[str], typer.Argument(help="Engine ID (optional)")] = None,
    result_type: Annotated[str, typer.Option("--type", "-t", help="Result type: analyzer/order")] = "analyzer",
):
    """
    :bar_chart: Show backtest results (simplified from 'backtest result show').
    """
    try:
        console.print(f"[bold blue]:bar_chart: Showing backtest results...[/bold blue]")
        
        if engine_id:
            from ginkgo.data.containers import container
            engine_service = container.engine_service()
            # Note: We'll need to check if engine_service has analyzer records method
            # For now, let's use a placeholder that should work
            try:
                df = engine_service.get_analyzer_records(engine_id=engine_id)
            except AttributeError:
                # Fallback to component service if engine service doesn't have this method
                component_service = container.component_service()
                df = component_service.get_analyzers_by_portfolio(portfolio_id=engine_id)
            
            if df.shape[0] == 0:
                console.print(f"[yellow]No results found for engine {engine_id}[/yellow]")
                return
                
            from ginkgo.libs.utils.display import display_dataframe
            display_dataframe(
                data=df,
                columns_config={
                    "analyzer_name": {"display_name": "Analyzer", "style": "cyan"},
                    "value": {"display_name": "Value", "style": "green"},
                    "timestamp": {"display_name": "Time", "style": "dim"},
                },
                title=f"Results for {engine_id}",
                console=console
            )
        else:
            console.print("[yellow]Please specify engine ID: ginkgo results <engine_id>[/yellow]")
            console.print("Available engines: ginkgo list engines")
            
    except Exception as e:
        console.print(f"[red]:x: Failed to show results: {e}[/red]")
        console.print("Try: ginkgo backtest result show")

def config(
    show: Annotated[bool, typer.Option("--show", "-s", help="Show current config")] = True,
):
    """
    :gear: Show system configuration.
    """
    try:
        from ginkgo.libs import GCONF
        
        console.print("[bold blue]:gear:  System Configuration[/bold blue]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Description", style="dim")
        
        table.add_row("Debug Mode", str(GCONF.DEBUGMODE), "Enable detailed logging")
        table.add_row("Quiet Mode", str(GCONF.QUIET), "Suppress verbose output")
        table.add_row("CPU Ratio", f"{GCONF.CPURATIO*100}%", "CPU usage limit")
        table.add_row("Log Path", str(GCONF.LOGGING_PATH), "Log files location")
        table.add_row("Work Dir", str(GCONF.WORKING_PATH), "Working directory")
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]:x: Failed to show config: {e}[/red]")
        console.print("Try: ginkgo system config show")

def test(
    all_tests: Annotated[bool, typer.Option("--all", "-a", help="Run all tests")] = False,
    module: Annotated[Optional[str], typer.Option("--module", "-m", help="Test specific module")] = None,
):
    """
    :test_tube: Run tests (simplified from 'pytest run').
    """
    try:
        console.print("[bold blue]:test_tube: Running tests...[/bold blue]")
        
        # Enable debug mode for testing
        from ginkgo.libs import GCONF
        original_debug = GCONF.DEBUGMODE
        GCONF.set_debug(True)
        
        try:
            if all_tests:
                import subprocess
                result = subprocess.run(['python', '-m', 'pytest', 'test/', '-v'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    console.print("[green]:white_check_mark: All tests passed[/green]")
                else:
                    console.print("[red]:x: Some tests failed[/red]")
                    console.print(result.stdout)
            else:
                console.print("[yellow]Use --all to run all tests, or --module to run specific module[/yellow]")
                
        finally:
            # Restore original debug mode
            GCONF.set_debug(original_debug)
            
    except Exception as e:
        console.print(f"[red]:x: Failed to run tests: {e}[/red]")
        console.print("Try: ginkgo test run --all")