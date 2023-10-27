import typer
from enum import Enum
from typing_extensions import Annotated
from rich.prompt import Prompt


app = typer.Typer(help="Module for Unittest")


@app.command()
def list():
    """
    Show unittest summary.
    """
    pass


@app.command()
def run():
    """
    Run Unittest.
    """
    pass
