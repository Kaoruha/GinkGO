import typer
from rich.console import Console
from enum import Enum
from typing_extensions import Annotated
from typing import List as typing_list
from ginkgo.client import mapping_create_cli
from ginkgo.enums import FILE_TYPES

app = typer.Typer(help=":shark: Create [bold medium_spring_green]BACKTEST[/] componnets.", no_args_is_help=True)
app.add_typer(mapping_create_cli.app, name="mapping", help=":shark: Create [bold medium_spring_green]MAPPING[/].")


console = Console()


@app.command(name="engine")
def create_engine(
    name: Annotated[
        str, typer.Option(..., "--name", "-n", case_sensitive=True, help="Engine Name", show_default=False)
    ],
    live: Annotated[bool, typer.Option("--live", "-l", case_sensitive=False)] = False,
):
    """
    :ramen: Create [bold medium_spring_green]ENGINE[/]. [gray62]For backtest[/].
    """
    from ginkgo.data.operations import add_engine

    try:
        res = None
        res = add_engine(name=name, is_live=live)
    except Exception as e:
        print(e)
    finally:
        pass
    if res is not None:
        console.print(f"{'Live' if live else 'Backtest'} Engine created")
        console.print(res.uuid)
    else:
        console.print("Create Engine Failed.")


@app.command(name="portfolio")
def create_portfolio(
    name: Annotated[str, typer.Option(..., "--name", "-n", case_sensitive=True, help="Portfolio Name")],
    start_date: Annotated[
        str, typer.Option("--start", "-s", case_sensitive=True, help="Backtest Start Date")
    ] = "2000-01-01",
    end_date: Annotated[str, typer.Option("--end", "-e", case_sensitive=True, help="Backtest End Date")] = "2020-01-01",
    live: Annotated[bool, typer.Option("--live", "-l", case_sensitive=False, help="Live Mode Switch.")] = False,
):
    """
    :ramen: Create [bold medium_spring_green]PORTFOLIO[/]. [gray62]For managing assets and allocations[/]
    """
    from ginkgo.data.operations import add_portfolio

    try:
        res = None
        res = add_portfolio(name=name, backtest_start_date=start_date, backtest_end_date=end_date, is_live=live)
    except Exception as e:
        print(e)
    finally:
        pass
    if res:
        console.print(f"{'Live' if live else 'Backtest'} Portfolio Created")
        console.print(res.uuid)
    else:
        console.print("Create Portfolio Failed.")


class ResourceType(str, Enum):
    backtest = "backtest"
    strategy = "strategy"
    selector = "selector"
    sizer = "sizer"
    risk_manager = "riskmanager"
    portfolio = "portfolio"
    analyzer = "analyzer"
    plot = "plot"


@app.command(name="file")
def create_file(
    type: Annotated[ResourceType, typer.Option(..., "--type", "-t", case_sensitive=False, help="File Type")],
    name: Annotated[str, typer.Option(..., "--name", "-n", case_sensitive=True, help="File Name")] = "",
    live: Annotated[bool, typer.Option("--live", "-l", case_sensitive=True, help="Set for engine")] = False,
    clone: Annotated[str, typer.Option("--clone", "-c", case_sensitive=True, help="Clone from Target")] = None,
):
    """
    :ramen: Create [bold medium_spring_green]FILE[/].[gray62] strategy, analyzer, selector, sizer, risk_manager[/]
    """
    from ginkgo.data import add_file, copy_file, get_file
    import uuid

    if name == "":
        name = uuid.uuid4().hex
        console.print("File name is None, use a random uuid as name.")
        print(name)

    resource = FILE_TYPES.enum_convert(type)
    if resource in FILE_TYPES:
        if clone == "":
            r = add_file(type=resource, name=name, data=b"")
            console.print(f"Create file [yellow]{name}[/yellow].")
            console.print(r.uuid)
        else:
            raw = get_file(id=clone)
            r = copy_file(type=resource, name=name, clone=clone)
            if r is None:
                console.print(f"Copy file [yellow]{name}[/yellow] Failed.")
            else:
                pass
                console.print(f"Copy file [yellow]{name}[/yellow] Done.")
                print(r.uuid)
                return r.uuid
    else:
        print(f"File type not support.")


@app.command(name="param")
def create_param(
    mapping_id: Annotated[str, typer.Option(..., "--file", "-f", case_sensitive=True, help="File ID")],
    index: Annotated[int, typer.Option(..., "--index", "-i", case_sensitive=True, help="Param Index")],
    value: Annotated[str, typer.Option(..., "--value", "-v", case_sensitive=True, help="Param Value")],
):
    # def add_param(source_id: str, index: int, value: str, *args, **kwargs) -> pd.Series:
    """
    :ramen: Create [bold medium_spring_green]PARAM[/]. [gray62]For strategy, analyzer...[/]
    """
    from ginkgo.data.operations import get_params, add_param, get_portfolio_file_mapping

    # Check id exist.
    mapping_df = get_portfolio_file_mapping(id=mapping_id)
    print(mapping_df)
    if mapping_df.shape[0] ==0:
        console.print("Mapping not exist. Check the id first.")
        return
    params_df = get_params()
    # Check index ok.
    # Store param in db.
    console.print("Backtest Update Param")
