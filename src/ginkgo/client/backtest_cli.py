import typer
from enum import Enum
from typing_extensions import Annotated
from rich.prompt import Prompt


app = typer.Typer(help="Module for Backtest")


class ResourceType(str, Enum):
    backtest = "backtest"
    strategy = "strategy"
    selector = "selector"
    sizer = "sizer"
    risk_manager = "risk"
    portfolio = "portfolio"
    analyzer = "analyzer"
    plot = "plot"


@app.command()
def list(
    resource: Annotated[ResourceType, typer.Argument(case_sensitive=False)],
):
    """
    Show backtest summary.
    """
    pass


@app.command()
def run(
    id: Annotated[str, typer.Argument(case_sensitive=True)],
):
    """
    Run Backtest.
    """


@app.command()
def edit(
    resource: Annotated[ResourceType, typer.Argument(case_sensitive=False)],
    id: Annotated[str, typer.Option(case_sensitive=True)],
):
    """
    Edit Resources.
    """
    pass
