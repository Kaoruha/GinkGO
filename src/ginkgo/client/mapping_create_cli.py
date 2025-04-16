import typer
from rich.console import Console
from enum import Enum
from typing_extensions import Annotated
from typing import List as typing_list

app = typer.Typer(help=":shark: Create [bold medium_spring_green]MAPPING[/].", no_args_is_help=True)
console = Console()


@app.command(name="engine_portfolio", no_args_is_help=True)
def create_mapping_engine_portfolio(
    engine: Annotated[str, typer.Option(..., "--engine", case_sensitive=True, help="Engine ID")],
    portfolio: Annotated[str, typer.Option(..., "--portfolio", case_sensitive=True, help="Portfolio ID")],
):
    """
    Create [bold medium_spring_green]MAPPING[/] [gray62]PORTFOLIO >> ENGINE.[/]
    """
    # Check engine exsist
    from ginkgo.data.operations import get_engine, get_portfolio, get_engine_portfolio_mappings, add_engine_portfolio_mapping
    engine_df = get_engine(engine)
    if engine_df.shape[0] == 0:
        console.print(f"Engine {engine} not exist. Please check the id again.")
        return
    # Check portfolio exsist
    portfolio_df = get_portfolio(portfolio)
    if portfolio_df.shape[0] == 0:
        console.print(f"Portfolio {portfolio} not exist. Please check the id again.")
        return
    # Try get mapping by engine
    mapping_df = get_engine_portfolio_mappings(engine)
    if (mapping_df['portfolio_id']==portfolio).any():
        console.print(f"Mapping Portfolio_[bold medium_spring_green]{portfolio}[/] >> Engine_[bold medium_spring_green]{engine}[/] already exists.")
        return
    # Check if mapping about engine and portfolio exists

    # create new mapping
    res = add_engine_portfolio_mapping(engine_id=engine, portfolio_id=portfolio)
    if res is not None:
        print(res.uuid)
    else:
        console.print(f"Something wrong when creating mapping. Please check.")


@app.command(name="engine_handler")
def create_mapping_engine_handler(
    mapping: Annotated[
        typing_list[str],
        typer.Argument(
            case_sensitive=True,
            help="List of IDs to construct a mapping between Engine and Portfolio,Engine and Handler or Portfolio and File.",
        ),
    ] = None,
):
    """
    Create [bold medium_spring_green]MAPPING[/] [gray62]HANDLER >> ENGINE.[/]
    """
    if len(mapping) != 2:
        console.print("Please input 2 IDs to construct the mapping.")
        return
    # File mapping
    # Portfolio mapping
    console.print("Create Backtest Mapping.")


@app.command(name="portfolio_file")
def create_mapping_portfolio_file(
    mapping: Annotated[
        typing_list[str],
        typer.Argument(
            case_sensitive=True,
            help="List of IDs to construct a mapping between Engine and Portfolio,Engine and Handler or Portfolio and File.",
        ),
    ] = None,
):
    """
    Create [bold medium_spring_green]MAPPING[/] [gray62]FILE >> PORTFOLIO.[/]
    """
    if len(mapping) != 2:
        console.print("Please input 2 IDs to construct the mapping.")
        return
    # File mapping
    # Portfolio mapping
    console.print("Create Backtest Mapping.")
