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
        
        # Display worker status table
        status_data = GTM.get_workers_status()
        if isinstance(status_data, dict) and status_data:
            console.print("\n[bold]Worker Status:[/bold]")
            # Convert dict to simple display
            for worker_id, status in status_data.items():
                console.print(f"  Worker {worker_id}: {status}")
        elif hasattr(status_data, 'shape') and status_data.shape[0] > 0:
            console.print("\n[bold]Worker Status:[/bold]")
            display_dataframe(
                data=status_data,
                columns_config={
                    "worker_id": {"display_name": "Worker ID", "style": "cyan"},
                    "status": {"display_name": "Status", "style": "green"},
                    "task": {"display_name": "Current Task", "style": "yellow"},
                },
                title="Active Workers",
                console=console
            )
        else:
            console.print("\n[dim]No active workers[/dim]")
            
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
    :construction: Initialize database and example data (simplified from 'data init').
    """
    try:
        console.print("[bold blue]:rocket: Initializing Ginkgo...[/bold blue]")
        
        # Initialize database tables
        console.print(":bar_chart: Creating database tables...")
        from ginkgo.data.drivers import create_all_tables
        create_all_tables()
        console.print("[green]:white_check_mark: Database tables created[/green]")
        
        # Initialize example data
        console.print(":memo: Loading example data...")
        from ginkgo.data import seeding
        seeding.run()
        console.print("[green]:white_check_mark: Example data loaded[/green]")
        
        console.print("\n[bold green]:party_popper: Initialization complete![/bold green]")
        console.print("Next steps:")
        console.print("  • ginkgo get stockinfo     # Get stock information")
        console.print("  • ginkgo show stocks       # List available stocks")
        console.print("  • ginkgo status            # Check system status")
        
    except Exception as e:
        console.print(f"[red]:x: Initialization failed: {e}[/red]")
        console.print("Try: ginkgo data init (full command)")

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
            stockinfo_service.sync_all()
            console.print("[green]:white_check_mark: Stock information updated[/green]")
            
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
                console.print("[red]:x: Stock code required for bars data[/red]")
                console.print("Example: ginkgo get bars --code 000001.SZ")
                return
            from ginkgo.data.containers import container
            bar_service = container.bar_service()
            bar_service.sync_bars_for_code(code, start_date=start, end_date=end)
            console.print(f"[green]:white_check_mark: Daily bars updated for {code}[/green]")
            
        elif data_type == DataType.TICKS:
            if not code:
                console.print("[red]:x: Stock code required for ticks data[/red]")
                console.print("Example: ginkgo get ticks --code 000001.SZ")
                return
            from ginkgo.data.containers import container
            tick_service = container.tick_service()
            tick_service.sync_ticks_for_code(code, start_date=start, end_date=end)
            console.print(f"[green]:white_check_mark: Tick data updated for {code}[/green]")
            
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
            df = stockinfo_service.get_stockinfos()
            if df.shape[0] == 0:
                console.print("[yellow]No stock information found. Try: ginkgo get stockinfo[/yellow]")
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
                console.print("[red]:x: Stock code required for bars data[/red]")
                return
            from ginkgo.data.containers import container
            bar_service = container.bar_service()
            df = bar_service.get_bars(code, start=start, end=end, as_dataframe=True)
            if df.shape[0] == 0:
                console.print(f"[yellow]No bars data found for {code}[/yellow]")
                return
            console.print(f"[green]Found {df.shape[0]} bars for {code}[/green]")
            print(df.tail(10))  # Show last 10 bars
            
        elif data_type == "ticks":
            if not code:
                console.print("[red]:x: Stock code required for ticks data[/red]")
                return
            from ginkgo.data.containers import container
            tick_service = container.tick_service()
            df = tick_service.get_ticks(code, start=start, end=end, as_dataframe=True)
            if df.shape[0] == 0:
                console.print(f"[yellow]No ticks data found for {code}[/yellow]")
                return
            console.print(f"[green]Found {df.shape[0]} ticks for {code}[/green]")
            print(df.tail(10))  # Show last 10 ticks
            
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
            # Try service method first, fallback to original if needed
            try:
                bar_service.plot_bars(code, start_date=start, end_date=end, with_indicators=indicators)
            except AttributeError:
                from ginkgo.data import plot_daybar
                plot_daybar(code, start=start, end=end, with_indicators=indicators)
        else:
            from ginkgo.data.containers import container
            tick_service = container.tick_service()
            try:
                tick_service.plot_ticks(code, start_date=start, end_date=end)
            except AttributeError:
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
        
        from ginkgo.backtest.execution.engines.engine_assembler_factory import assembler_backtest_engine
        
        if debug_mode:
            from ginkgo.libs import GCONF
            GCONF.set_debug(True)
            console.print("[dim]Debug mode enabled for this run[/dim]")
        
        engine = assembler_backtest_engine(engine_id)
        if engine:
            console.print(f"[green]:white_check_mark: Backtest {engine_id} completed successfully[/green]")
            console.print("View results with: ginkgo results")
        else:
            console.print(f"[red]:x: Failed to run backtest {engine_id}[/red]")
            
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
    :test_tube: Run tests (simplified from 'unittest run').
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
        console.print("Try: ginkgo unittest run --a")