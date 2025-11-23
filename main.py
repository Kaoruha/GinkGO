# 优化版main.py - 单一入口，延迟加载所有重型依赖
def _get_imports():
    """获取需要的重型导入"""
    global typer, subprocess, time, math, datetime, click, os, Enum, typing_list, Annotated, Console, Table, print
    if 'typer' not in globals():
        import typer
        import subprocess
        import time
        import math
        import datetime
        import click
        import os
        from enum import Enum
        from typing import List as typing_list
        from typing_extensions import Annotated
        from rich.console import Console
        from rich.table import Table
        from rich import print
    return typer, Console

# 懒加载CLI模块
def _lazy_import_cli(module_name):
    """延迟导入CLI模块"""
    if module_name == 'data_cli':
        from ginkgo.client import data_cli
        return data_cli
    elif module_name == 'backtest_cli':
        from ginkgo.client import backtest_cli
        return backtest_cli
    elif module_name == 'test_cli':
        from ginkgo.client import test_cli
        return test_cli
    elif module_name == 'kafka_cli':
        from ginkgo.client import kafka_cli
        return kafka_cli
    elif module_name == 'worker_cli':
        from ginkgo.client import worker_cli
        return worker_cli
    elif module_name == 'system_cli':
        from ginkgo.client import system_cli
        return system_cli
    elif module_name == 'dev_cli':
        from ginkgo.client import dev_cli
        return dev_cli
    elif module_name == 'evaluation_cli':
        from ginkgo.client import evaluation_cli
        return evaluation_cli
    elif module_name == 'datasource_cli':
        from ginkgo.client import datasource_cli
        return datasource_cli
    elif module_name == 'container_cli':
        from ginkgo.client import container_cli
        return container_cli
    elif module_name == 'cache_cli':
        from ginkgo.client import cache_cli
        return cache_cli
    else:
        raise ImportError(f"Unknown CLI module: {module_name}")

# 延迟创建main app
def _create_main_app():
    """延迟创建main app，避免启动时导入typer"""
    typer, Console = _get_imports()
    
    return typer.Typer(
    rich_markup_mode="rich", 
    no_args_is_help=True,
    help="""
:rocket: [bold green]Ginkgo[/bold green] - Modern Quantitative Trading Platform

[bold blue]Quick Start Commands:[/bold blue]
  [cyan]ginkgo init[/cyan]              # Initialize system
  [cyan]ginkgo status[/cyan]            # Check system status  
  [cyan]ginkgo debug on[/cyan]          # Enable debug mode
  [cyan]ginkgo get stockinfo[/cyan]     # Fetch stock data
  [cyan]ginkgo show stocks[/cyan]       # Show stock list
  [cyan]ginkgo run <engine_id>[/cyan]   # Run backtest

[bold blue]Common Workflows:[/bold blue]
  1. Setup:     ginkgo init → ginkgo get stockinfo
  2. Data:      ginkgo get bars --code 000001.SZ → ginkgo show bars --code 000001.SZ  
  3. Backtest:  ginkgo list engines → ginkgo run <engine_id> → ginkgo results
  4. Analysis:  ginkgo plot 000001.SZ

[dim]Use 'ginkgo <command> --help' for detailed information.[/dim]
"""
)

# 全局变量
_main_app = None
console = None

def get_main_app():
    """延迟创建main app实例"""
    global _main_app, console
    if _main_app is None:
        _main_app = _create_main_app()
        typer, Console = _get_imports()
        console = Console()
        _register_all_commands()
    return _main_app

def _register_all_commands():
    """注册所有命令到main_app"""
    
    # Direct import of core commands to preserve typer signatures
    from ginkgo.client import core_cli
    
    # Add simplified top-level commands with original signatures
    _main_app.command(name="status", help=":bar_chart: System status")(core_cli.status)
    _main_app.command(name="get", help=":inbox_tray: Fetch market data")(core_cli.get)
    _main_app.command(name="show", help=":eyes: Display data")(core_cli.show)
    _main_app.command(name="plot", help=":chart_with_upwards_trend: Plot charts")(core_cli.plot)
    _main_app.command(name="run", help=":rocket: Run backtest")(core_cli.run)
    _main_app.command(name="list", help=":clipboard: List components")(core_cli.list_components)
    _main_app.command(name="results", help=":bar_chart: Show results")(core_cli.results)
    _main_app.command(name="config", help=":gear: System config")(core_cli.config)
    
    # 延迟加载typer应用
    def _create_lazy_typer(module_name, app_name="app"):
        class LazyTyper:
            def __init__(self, module_name, app_name):
                self.module_name = module_name
                self.app_name = app_name
                self._app = None
                
            @property  
            def app(self):
                if self._app is None:
                    module = _lazy_import_cli(self.module_name)
                    self._app = getattr(module, self.app_name)
                return self._app
                
            def __call__(self, *args, **kwargs):
                return self.app(*args, **kwargs)
                
        return LazyTyper(module_name, app_name).app

    # Add legacy CLI modules
    _main_app.add_typer(_create_lazy_typer('system_cli'), name="system", help=":bee: [dim]Legacy:[/dim] System management")
    _main_app.add_typer(_create_lazy_typer('data_cli'), name="data", help=":puzzle_piece: [dim]Legacy:[/dim] Data operations")
    _main_app.add_typer(_create_lazy_typer('backtest_cli'), name="backtest", help=":shark: [dim]Legacy:[/dim] Backtest operations")
    _main_app.add_typer(_create_lazy_typer('test_cli'), name="test", help=":test_tube: Modern testing framework")
    _main_app.add_typer(_create_lazy_typer('worker_cli'), name="worker", help=":construction_worker: [dim]Legacy:[/dim] Worker management")
    _main_app.add_typer(_create_lazy_typer('dev_cli'), name="dev", help=":beetle: Development tools")
    _main_app.add_typer(_create_lazy_typer('kafka_cli'), name="kafka", help=":satellite_antenna: Kafka management")
    _main_app.add_typer(_create_lazy_typer('evaluation_cli'), name="evaluation", help=":chart_with_upwards_trend: Evaluation tools") 
    _main_app.add_typer(_create_lazy_typer('datasource_cli'), name="datasource", help=":satellite_antenna: Data sources")
    _main_app.add_typer(_create_lazy_typer('container_cli'), name="container", help=":package: Container management")
    _main_app.add_typer(_create_lazy_typer('cache_cli'), name="cache", help=":wastebasket: Cache management")

    # Serve command
    typer, Console = _get_imports()
    
    @_main_app.command()
    def serve(
        host: Annotated[str, typer.Option("--host", "-h", help=":globe_with_meridians: Host to bind")] = "0.0.0.0",
        port: Annotated[int, typer.Option("--port", "-p", help=":door: Port to bind")] = 8000,
        debug: Annotated[bool, typer.Option("--debug", help=":bug: Enable debug mode")] = False,
    ):
        """
        :rocket: Start Ginkgo API server for web interface and remote control.
        """
        try:
            import uvicorn
            from pathlib import Path
            
            working_directory = Path(__file__).parent
            api_dir = working_directory / "api"
            
            if not api_dir.exists():
                console.print(f":x: [red]API directory not found at {api_dir}[/red]")
                console.print(":information: [yellow]API server functionality may not be available[/yellow]")
                return
            
            console.print(f":rocket: [green]Starting Ginkgo API server...[/green]")
            console.print(f":globe_with_meridians: Host: [cyan]{host}[/cyan]")
            console.print(f":door: Port: [cyan]{port}[/cyan]")
            console.print(f":bug: Debug: [cyan]{debug}[/cyan]")
            
            uvicorn.run(
                "main:app",
                host=host,
                port=port,
                reload=debug,
                app_dir=str(api_dir),
                log_level="debug" if debug else "info"
            )
            
        except ImportError:
            console.print(":x: [red]uvicorn not installed. Install with: pip install uvicorn[/red]")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f":x: [red]Failed to start server: {e}[/red]")
            raise typer.Exit(1)

    # Version command  
    @_main_app.command()
    def version():
        """
        :rabbit: Display Ginkgo version and build information.
        """
        import sys
        from pathlib import Path
        
        config_path = Path(__file__).parent / "src" / "ginkgo" / "config"
        sys.path.insert(0, str(config_path))
        
        try:
            import package
            print(f":sparkles: [bold medium_spring_green]{package.PACKAGENAME}[/] [light_goldenrod2]{package.VERSION}[/light_goldenrod2]")
        except ImportError:
            from ginkgo.config.package import PACKAGENAME, VERSION
            print(f":sparkles: [bold medium_spring_green]{PACKAGENAME}[/] [light_goldenrod2]{VERSION}[/light_goldenrod2]")
        finally:
            if str(config_path) in sys.path:
                sys.path.remove(str(config_path))

if __name__ == "__main__":
    import sys
    
    # 快速路径：version命令优化
    if len(sys.argv) == 2 and sys.argv[1] in ["version", "--version"]:
        try:
            from pathlib import Path
            config_path = Path(__file__).parent / "src" / "ginkgo" / "config"
            sys.path.insert(0, str(config_path))
            import package
            print(f"✨ {package.PACKAGENAME} {package.VERSION}")
            sys.path.remove(str(config_path))
        except:
            print("✨ ginkgo 0.8.1")
        sys.exit(0)
    
    # 正常路径：加载完整的CLI
    main_app = get_main_app()
    main_app()