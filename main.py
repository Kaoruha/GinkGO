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

# Import existing CLI modules (for backward compatibility)
from ginkgo.client import data_cli
from ginkgo.client import backtest_cli
from ginkgo.client import unittest_cli
from ginkgo.client import kafka_cli
from ginkgo.client import worker_cli
from ginkgo.client import system_cli
from ginkgo.client import dev_cli
from ginkgo.client import evaluation_cli
from ginkgo.client import datasource_cli
from ginkgo.client import container_cli

# Import new core CLI functions
from ginkgo.client import core_cli

# Create main app with improved help
main_app = typer.Typer(
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

# Add new simplified top-level commands
main_app.command(name="status", help=":bar_chart: System status")(core_cli.status)
main_app.command(name="debug", help=":bug: Debug mode toggle")(core_cli.debug)  
main_app.command(name="init", help=":construction: Initialize system")(core_cli.init)
main_app.command(name="get", help=":inbox_tray: Fetch market data")(core_cli.get)
main_app.command(name="show", help=":eyes: Display data")(core_cli.show)
main_app.command(name="plot", help=":chart_with_upwards_trend: Plot charts")(core_cli.plot)
main_app.command(name="run", help=":rocket: Run backtest")(core_cli.run)
main_app.command(name="list", help=":clipboard: List components")(core_cli.list_components)
main_app.command(name="results", help=":bar_chart: Show results")(core_cli.results)
main_app.command(name="config", help=":gear: System config")(core_cli.config)
main_app.command(name="test", help=":test_tube: Run tests")(core_cli.test)

# Add existing CLI modules for backward compatibility
main_app.add_typer(system_cli.app, name="system", help=":bee: [dim]Legacy:[/dim] System management")
main_app.add_typer(data_cli.app, name="data", help=":puzzle_piece: [dim]Legacy:[/dim] Data operations")
main_app.add_typer(backtest_cli.app, name="backtest", help=":shark: [dim]Legacy:[/dim] Backtest operations")
main_app.add_typer(unittest_cli.app, name="unittest", help=":white_check_mark: [dim]Legacy:[/dim] Unit tests")
main_app.add_typer(worker_cli.app, name="worker", help=":construction_worker: [dim]Legacy:[/dim] Worker management")
main_app.add_typer(dev_cli.app, name="dev", help=":beetle: Development tools")
main_app.add_typer(kafka_cli.app, name="kafka", help=":satellite_antenna: Kafka management")
main_app.add_typer(evaluation_cli.app, name="evaluation", help=":chart_with_upwards_trend: Evaluation tools") 
main_app.add_typer(datasource_cli.app, name="datasource", help=":satellite_antenna: Data sources")
main_app.add_typer(container_cli.app, name="container", help=":package: Container management")

console = Console()




@main_app.command()
def version():
    """
    :rabbit: Display Ginkgo version and build information.
    """
    from ginkgo.config.package import PACKAGENAME, VERSION

    print(f":sparkles: [bold medium_spring_green]{PACKAGENAME}[/] [light_goldenrod2]{VERSION}[/light_goldenrod2]")














if __name__ == "__main__":
    main_app()
