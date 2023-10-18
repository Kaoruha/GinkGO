import typer
from enum import Enum
from typing_extensions import Annotated
from rich.prompt import Prompt


app = typer.Typer(help="Module for Backtest")


@app.command()
def list():
    """
    Show strategy summary.
    """
    pass


@app.command()
def run():
    """
    Run Backtest.
    """


@app.command()
def edit():
    """
    Edit Strategy.
    """
    pass
