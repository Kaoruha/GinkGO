import typer
from rich.console import Console

app = typer.Typer(help=":shark: Update [bold medium_spring_green]BACKTEST[/] components.", no_args_is_help=True)
console = Console()


@app.command(name="engine")
def update_engine():
    """
    Update Engine.
    """
    console.print("Backtest Update Engine")


@app.command(name="portfolio")
def update_portfolio():
    """
    Update Portfolio.
    """
    console.print("Backtest Update Portfolio")


@app.command(name="mapping")
def update_mapping():
    """
    Update Mapping.
    """
    console.print("Backtest Update Mapping")


@app.command(name="file")
def update_file():
    """
    Update File.
    """
    console.print("Backtest Update File")


@app.command(name="param")
def update_param():
    """
    Update Param.
    """
    console.print("Backtest Update Param")
