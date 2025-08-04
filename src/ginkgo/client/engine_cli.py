import typer
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console
from rich.prompt import Confirm

# All heavy imports moved to function level for faster CLI startup

app = typer.Typer(
    help=":wrench: Module for [bold medium_spring_green]ENGINE[/] management. [grey62]Create, bind portfolios, and manage engine lifecycle.[/grey62]",
    no_args_is_help=True,
)
console = Console()


@app.command()
def list(
    active: Annotated[bool, typer.Option("--active", "-a", help=":green_circle: Show only active engines")] = False,
):
    """
    :open_file_folder: List all backtest engines.
    """
    from ginkgo.data.containers import container
    from ginkgo.libs.utils.display import display_dataframe
    
    engine_service = container.engine_service()
    engines_df = engine_service.get_engines(as_dataframe=True)
    
    if active and engines_df.shape[0] > 0:
        # Filter for active engines if the field exists
        if "is_active" in engines_df.columns:
            engines_df = engines_df[engines_df["is_active"] == True]
    
    # 配置列显示
    engines_columns_config = {
        "uuid": {"display_name": "Engine ID", "style": "dim"},
        "name": {"display_name": "Name", "style": "cyan"},
        "desc": {"display_name": "Description", "style": "dim"},
        "update_at": {"display_name": "Update At", "style": "dim"}
    }
    
    title = ":wrench: [bold]Active Engines:[/bold]" if active else ":wrench: [bold]Engines:[/bold]"
    display_dataframe(
        data=engines_df,
        columns_config=engines_columns_config,
        title=title,
        console=console
    )


@app.command()
def create(
    name: Annotated[str, typer.Argument(help=":label: Engine name")],
    description: Annotated[Optional[str], typer.Option("--desc", "-d", help=":memo: Engine description")] = None,
):
    """
    :hammer_and_wrench: Create a new backtest engine.
    """
    from ginkgo.data.containers import container
    
    engine_service = container.engine_service()
    result = engine_service.create_engine(name=name, is_live=False, description=description or "")
    
    if result.get("success", False):
        console.print(f":white_check_mark: [bold green]Created engine[/bold green] [cyan]{name}[/cyan]")
        console.print(f":id: Engine ID: [dim]{result.get('engine_id', 'N/A')}[/dim]")
    else:
        console.print(f":x: [bold red]Failed to create engine:[/bold red] {result.get('error', 'Unknown error')}")


@app.command()
def bind(
    engine_id: Annotated[str, typer.Argument(help=":id: Engine ID")],
    portfolio_id: Annotated[str, typer.Argument(help=":id: Portfolio ID")],
):
    """
    :link: Bind a portfolio to an engine.
    """
    from ginkgo.data.containers import container
    
    engine_service = container.engine_service()
    portfolio_service = container.portfolio_service()
    
    # Verify engine exists
    engine_data = engine_service.get_engine(engine_id, as_dataframe=True)
    if engine_data.shape[0] == 0:
        console.print(f":exclamation: Engine [light_coral]{engine_id}[/light_coral] not found.")
        return
    
    # Verify portfolio exists
    portfolio_data = portfolio_service.get_portfolio(portfolio_id, as_dataframe=True)
    if portfolio_data.shape[0] == 0:
        console.print(f":exclamation: Portfolio [light_coral]{portfolio_id}[/light_coral] not found.")
        return
    
    # Use engine service to add portfolio mapping
    result = engine_service.add_portfolio_to_engine(
        engine_id=engine_id, 
        portfolio_id=portfolio_id,
        engine_name=engine_data.iloc[0]["name"],
        portfolio_name=portfolio_data.iloc[0]["name"]
    )
    
    if result.get("success", False):
        engine_name = engine_data.iloc[0]["name"]
        portfolio_name = portfolio_data.iloc[0]["name"]
        
        console.print(f":white_check_mark: [bold green]Successfully bound[/bold green] portfolio [cyan]{portfolio_name}[/cyan] to engine [cyan]{engine_name}[/cyan]")
        console.print(f":id: Mapping ID: [dim]{result.get('mapping_id', 'N/A')}[/dim]")
    else:
        console.print(f":x: [bold red]Failed to bind portfolio to engine:[/bold red] {result.get('error', 'Unknown error')}")


@app.command()
def update(
    engine_id: Annotated[str, typer.Argument(help=":id: Engine ID")],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help=":label: New engine name")] = None,
    description: Annotated[Optional[str], typer.Option("--desc", "-d", help=":memo: New engine description")] = None,
):
    """
    :memo: Update engine metadata.
    """
    from ginkgo.data.containers import container
    
    engine_service = container.engine_service()
    
    # Verify engine exists
    engine_data = engine_service.get_engine(engine_id, as_dataframe=True)
    if engine_data.shape[0] == 0:
        console.print(f":exclamation: Engine [light_coral]{engine_id}[/light_coral] not found.")
        return
    
    # Update fields
    updates = {}
    if name:
        updates['name'] = name
    if description:
        updates['desc'] = description
    
    if not updates:
        console.print(":information: No updates specified.")
        return
    
    # Use engine service update method
    result = engine_service.update_engine(engine_id, **updates)
    
    if result.get("success", False):
        console.print(f":white_check_mark: [bold green]Updated engine[/bold green] [cyan]{engine_data.iloc[0]['name']}[/cyan]")
        
        for field, value in updates.items():
            console.print(f"  {field}: [cyan]{value}[/cyan]")
    else:
        console.print(f":x: [bold red]Failed to update engine:[/bold red] {result.get('error', 'Unknown error')}")


@app.command()
def unbind(
    engine: Annotated[str, typer.Option("--engine", "-e", "--e", help=":id: Engine ID")],
    portfolio: Annotated[str, typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help=":exclamation: Skip confirmation")] = False,
):
    """
    :unlink: Unbind a portfolio from an engine.
    """
    from ginkgo.data.operations import (
        get_engine_portfolio_mappings_page_filtered,
        get_engine, get_portfolio
    )
    from ginkgo.data.operations.engine_portfolio_mapping_crud import delete_engine_portfolio_mapping
    
    # Find the mapping
    mappings_df = get_engine_portfolio_mappings_page_filtered()
    target_mapping = mappings_df[
        (mappings_df["engine_id"] == engine) & 
        (mappings_df["portfolio_id"] == portfolio)
    ]
    
    if target_mapping.shape[0] == 0:
        console.print(f":exclamation: Portfolio [light_coral]{portfolio}[/light_coral] is not bound to engine [light_coral]{engine}[/light_coral].")
        return
    
    # Get names for display
    engine_df = get_engine(engine)
    portfolio_df = get_portfolio(portfolio)
    engine_name = engine_df.iloc[0]["name"] if engine_df.shape[0] > 0 else engine
    portfolio_name = portfolio_df.iloc[0]["name"] if portfolio_df.shape[0] > 0 else portfolio
    
    if not force:
        if not Confirm.ask(f":question: Unbind portfolio [cyan]{portfolio_name}[/cyan] from engine [cyan]{engine_name}[/cyan]?", default=True):
            console.print(":relieved_face: Operation cancelled.")
            return
    
    try:
        for _, mapping in target_mapping.iterrows():
            delete_engine_portfolio_mapping(mapping["uuid"])
        
        console.print(f":white_check_mark: [bold green]Successfully unbound[/bold green] portfolio [cyan]{portfolio_name}[/cyan] from engine [cyan]{engine_name}[/cyan]")
    except Exception as e:
        console.print(f":x: [bold red]Failed to unbind portfolio from engine:[/bold red] {e}")


@app.command()
def remove(
    engine: Annotated[str, typer.Option("--engine", "-e", "--e", help=":id: Engine ID to delete")],
    force: Annotated[bool, typer.Option("--force", "-f", help=":exclamation: Skip confirmation")] = False,
):
    """
    :wastebasket: Delete an engine and all its related data (signals, mappings, etc.).
    """
    from ginkgo.data.containers import container
    
    engine_service = container.engine_service()
    
    # Verify engine exists
    engine_data = engine_service.get_engine(engine, as_dataframe=True)
    if engine_data.shape[0] == 0:
        console.print(f":exclamation: Engine [light_coral]{engine}[/light_coral] not found.")
        return
    
    engine_name = engine_data.iloc[0]["name"]
    
    if not force:
        console.print(f":warning: [bold yellow]This will permanently delete engine [cyan]{engine_name}[/cyan] and ALL related data including:[/bold yellow]")
        console.print("  • All signals generated by this engine")
        console.print("  • All portfolio mappings")
        console.print("  • All analyzer records")
        console.print("  • All other related records")
        console.print("")
        
        if not Confirm.ask(f":question: Are you sure you want to delete engine [cyan]{engine_name}[/cyan]?", default=False):
            console.print(":relieved_face: Operation cancelled.")
            return
    
    # Use engine service delete method
    result = engine_service.delete_engine(engine)
    
    if result.get("success", False):
        console.print(f":white_check_mark: [bold green]Successfully deleted engine[/bold green] [cyan]{engine_name}[/cyan] and all related data")
    else:
        console.print(f":x: [bold red]Failed to delete engine:[/bold red] {result.get('error', 'Unknown error')}")