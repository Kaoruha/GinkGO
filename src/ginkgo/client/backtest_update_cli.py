import typer
from typing_extensions import Annotated
from rich.table import Column, Table
from rich.console import Console

app = typer.Typer(help=":shark: Update [bold medium_spring_green]BACKTEST[/] components.", no_args_is_help=True)
console = Console()


# @app.command(name="engine")
# def update_engine(
#     id: Annotated[str, typer.Option(..., "--id", "-id", case_sensitive=True, help="Engine ID")] = None,
# ):
#     """
#     Update Engine.
#     """
#     from ginkgo.data.operations import get_engine

#     engine = get_engine(id=id, as_dataframe=True)
#     print(engine.iloc[0])
#     console.print("Backtest Update Engine")


@app.command(name="portfolio")
def update_portfolio(
    id: Annotated[str, typer.Option(..., "--id", "-id", case_sensitive=True, help="Portfolio ID")] = None,
    name: Annotated[str, typer.Option(..., "--name", "-name", case_sensitive=True, help="New Name")] = None,
    description: Annotated[
        str, typer.Option(..., "--desc", "-desc", case_sensitive=True, help="New Description")
    ] = None,
    start: Annotated[
        str, typer.Option(..., "--start", "-start", case_sensitive=True, help="Backtest Start Time")
    ] = None,
    end: Annotated[str, typer.Option(..., "--end", "-end", case_sensitive=True, help="Backtest End Time")] = None,
    live: Annotated[str, typer.Option(..., "--live", "-live", case_sensitive=True, help="Live Mode")] = None,
):
    """
    Update Portfolio.
    """
    from ginkgo.data.operations import get_portfolio, get_portfolios_page_filtered, update_portfolio

    if id is None:
        df = get_portfolios_page_filtered()
        if df.shape[0] == 0:
            console.print("No portfolio found. Please create one first.")
            return
        msg = "You could choose portfolio below with --id."
        console.print(msg)
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="dim")
        table.add_column("Description", style="dim")
        table.add_column("Update At", style="dim")
        for i, r in df.iterrows():
            table.add_row(
                r["uuid"],
                r["name"],
                r["desc"],
                str(r["update_at"]),
            )
        console.print(table)
        return
    console.print("Backtest Update Portfolio")

    p = get_portfolio(id=id, as_dataframe=True)
    if p.shape[0] == 0:
        console.print(f"Portfolio {id} not exist in database. Please confirm id again.")
        return
    print(p.iloc[0])
    if all(x is None for x in [name, description, start, end, live]):
        console.print("No update fields provided. You could update by --name, --desc, --start, --end, --live.")
        return
    try:
        from ginkgo.enums import LIVE_MODE

        if live is not None:
            if live == LIVE_MODE.ON:
                live = True
            elif live == LIVE_MODE.OFF:
                live = False

        update_portfolio(
            id=id,
            name=name,
            backtest_start_date=start,
            backtest_end_date=end,
            description=description,
            is_live=live,
        )
    except Exception as e:
        print(e)
    finally:
        pass


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
