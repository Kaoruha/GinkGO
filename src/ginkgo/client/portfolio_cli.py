import typer
from enum import Enum
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console
from rich.prompt import Confirm

# All heavy imports moved to function level for faster CLI startup

app = typer.Typer(
    help=":briefcase: Module for [bold medium_spring_green]PORTFOLIO[/] management. [grey62]Create portfolios and manage component bindings.[/grey62]",
    no_args_is_help=True,
)
console = Console()


@app.command()
def list():
    """
    :open_file_folder: List all portfolios.
    """
    import pandas as pd
    from ginkgo.libs.utils.display import display_dataframe
    from ginkgo.data.containers import container
    
    portfolio_service = container.portfolio_service()
    portfolios_df = portfolio_service.get_portfolios(as_dataframe=True)
    
    if portfolios_df.shape[0] == 0:
        console.print(":exclamation: [yellow]No portfolios found.[/yellow]")
        return
    
    # 配置列显示
    columns_config = {
        "uuid": {"display_name": "Portfolio ID", "style": "dim"},
        "name": {"display_name": "Name", "style": "cyan"},
        "backtest_start_date": {"display_name": "Start Date", "style": "dim"},
        "backtest_end_date": {"display_name": "End Date", "style": "dim"},
        "update_at": {"display_name": "Update At", "style": "dim"}
    }
    
    display_dataframe(
        data=portfolios_df,
        columns_config=columns_config,
        title=":briefcase: [bold]Portfolios:[/bold]",
        console=console
    )


@app.command()
def create(
    name: Annotated[str, typer.Argument(help=":label: Portfolio name")],
    start_date: Annotated[str, typer.Option("--start", "-s", help=":calendar: Backtest start date (YYYYMMDD)")],
    end_date: Annotated[str, typer.Option("--end", "-e", help=":calendar: Backtest end date (YYYYMMDD)")],
    description: Annotated[Optional[str], typer.Option("--desc", help=":memo: Portfolio description")] = None,
):
    """
    :hammer_and_wrench: Create a new portfolio.
    """
    from ginkgo.data.containers import container
    
    portfolio_service = container.portfolio_service()
    result = portfolio_service.create_portfolio(
        name=name,
        backtest_start_date=start_date,
        backtest_end_date=end_date,
        is_live=False,
        description=description or ""
    )
    
    if result.get("success", False):
        console.print(f":white_check_mark: [bold green]Created portfolio[/bold green] [cyan]{name}[/cyan]")
        console.print(f":id: Portfolio ID: [dim]{result.get('portfolio_id', 'N/A')}[/dim]")
        console.print(f":calendar: Period: {start_date} - {end_date}")
    else:
        console.print(f":x: [bold red]Failed to create portfolio:[/bold red] {result.get('error', 'Unknown error')}")


@app.command()
def bind(
    portfolio: Annotated[Optional[str], typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID")] = None,
    component: Annotated[Optional[str], typer.Option("--component", "-c", "--c", help=":id: Component (file) ID")] = None,
    type: Annotated[Optional[str], typer.Option("--type", "-t", help=":gear: Component type (analyzer, index, riskmanager, selector, sizer, strategy, engine, handler)")] = None,
    name: Annotated[Optional[str], typer.Option("--name", "-n", help=":label: Custom component name")] = None,
):
    """
    :link: Bind a component to a portfolio.
    """
    from ginkgo.data.containers import container
    
    from ginkgo.enums import FILE_TYPES
    from ginkgo.libs.utils.display import display_dataframe
    
    # 获取服务
    portfolio_service = container.portfolio_service()
    file_service = container.file_service()
    
    # Convert string type to FILE_TYPES enum if provided
    if type is not None:
        try:
            type = FILE_TYPES.enum_convert(type)
            if type is None:
                valid_types = [item.name.lower() for item in FILE_TYPES if item.name != 'OTHER']
                console.print(f":x: [bold red]Invalid component type.[/bold red] Valid types: {', '.join(valid_types)}")
                return
        except Exception as e:
            valid_types = [item.name.lower() for item in FILE_TYPES if item.name != 'OTHER']
            console.print(f":x: [bold red]Invalid component type.[/bold red] Valid types: {', '.join(valid_types)}")
            return
    
    # Check portfolio
    if portfolio is None:
        portfolios_df = get_portfolios_page_filtered()
        # 配置列显示
        columns_config = {
            "uuid": {"display_name": "Portfolio ID", "style": "dim"},
            "name": {"display_name": "Name", "style": "cyan"},
            "backtest_start_date": {"display_name": "Start Date", "style": "dim"},
            "backtest_end_date": {"display_name": "End Date", "style": "dim"},
            "update_at": {"display_name": "Update At", "style": "dim"}
        }
        
        display_dataframe(
            data=portfolios_df,
            columns_config=columns_config,
            title=":briefcase: [bold]Available Portfolios:[/bold]",
            console=console
        )
        return
    
    portfolio_df = get_portfolio(portfolio)
    if portfolio_df.shape[0] == 0:
        console.print(f":exclamation: Portfolio [light_coral]{portfolio}[/light_coral] not found.")
        portfolios_df = get_portfolios_page_filtered()
        # 配置列显示
        columns_config = {
            "uuid": {"display_name": "Portfolio ID", "style": "dim"},
            "name": {"display_name": "Name", "style": "cyan"},
            "backtest_start_date": {"display_name": "Start Date", "style": "dim"},
            "backtest_end_date": {"display_name": "End Date", "style": "dim"},
            "update_at": {"display_name": "Update At", "style": "dim"}
        }
        
        display_dataframe(
            data=portfolios_df,
            columns_config=columns_config,
            title=":briefcase: [bold]Available Portfolios:[/bold]",
            console=console
        )
        return
    
    # Check component
    if component is None:
        # Filter by type if provided
        if type is not None:
            files_df = get_files_page_filtered(as_dataframe=True, type=type)
        else:
            files_df = get_files_page_filtered(as_dataframe=True)
        # Filter out removed files
        if files_df.shape[0] > 0 and 'is_del' in files_df.columns:
            files_df = files_df[files_df['is_del'] == False]
        # 配置列显示
        components_columns_config = {
            "uuid": {"display_name": "Component ID", "style": "dim"},
            "name": {"display_name": "Name", "style": "cyan"},
            "type": {"display_name": "Type", "style": "green"},
            "path": {"display_name": "Path", "style": "dim"},
            "update_at": {"display_name": "Update At", "style": "dim"}
        }
        
        display_dataframe(
            data=files_df,
            columns_config=components_columns_config,
            title=":dna: [bold]Available Components:[/bold]",
            console=console
        )
        return
    
    file_df = get_file(component)
    if file_df.shape[0] == 0:
        console.print(f":exclamation: Component [light_coral]{component}[/light_coral] not found.")
        # Filter by type if provided
        if type is not None:
            files_df = get_files_page_filtered(as_dataframe=True, type=type)
        else:
            files_df = get_files_page_filtered(as_dataframe=True)
        # Filter out removed files
        if files_df.shape[0] > 0 and 'is_del' in files_df.columns:
            files_df = files_df[files_df['is_del'] == False]
        # 配置列显示
        components_columns_config = {
            "uuid": {"display_name": "Component ID", "style": "dim"},
            "name": {"display_name": "Name", "style": "cyan"},
            "type": {"display_name": "Type", "style": "green"},
            "path": {"display_name": "Path", "style": "dim"},
            "update_at": {"display_name": "Update At", "style": "dim"}
        }
        
        display_dataframe(
            data=files_df,
            columns_config=components_columns_config,
            title=":dna: [bold]Available Components:[/bold]",
            console=console
        )
        return
    
    # Get type from component file if not provided
    if type is None:
        file_type = file_df.iloc[0]["type"]
        console.print(f":gear: Using component type: [cyan]{file_type}[/cyan]")
    else:
        # 直接使用FILE_TYPES，不需要映射
        file_type = type
    
    # Get name from component file if not provided
    component_name = name if name else file_df.iloc[0]["name"]
    if name is None:
        console.print(f":label: Using component name: [cyan]{component_name}[/cyan]")
    
    # Check if mapping already exists
    from ginkgo.data.operations import get_portfolio_file_mappings_page_filtered
    existing_mappings = get_portfolio_file_mappings_page_filtered(portfolio=portfolio)
    if existing_mappings.shape[0] > 0:
        # Check if this file_id is already bound to this portfolio
        duplicate_mapping = existing_mappings[existing_mappings['file_id'] == component]
        if duplicate_mapping.shape[0] > 0:
            existing_info = duplicate_mapping.iloc[0]
            console.print(f":exclamation: [bold red]Mapping already exists![/bold red]")
            console.print(f"Portfolio [yellow]{portfolio}[/yellow] is already bound to file [cyan]{component}[/cyan]")
            console.print(f"Existing mapping details:")
            console.print(f"  - Mapping ID: [dim]{existing_info['uuid']}[/dim]")
            console.print(f"  - Name: [cyan]{existing_info['name']}[/cyan]")
            console.print(f"  - Type: [green]{existing_info['type']}[/green]")
            console.print(f"  - Created: [dim]{existing_info['create_at']}[/dim]")
            return
    
    try:
        mapping = add_portfolio_file_mapping(
            portfolio=portfolio,
            file_id=component,
            name=component_name,
            type=file_type
        )
        console.print(f":white_check_mark: [bold green]Successfully bound {file_type}[/bold green] [cyan]{component_name}[/cyan] to portfolio [yellow]{portfolio}[/yellow]")
        console.print(f":id: Mapping ID: [dim]{mapping['uuid']}[/dim]")
    except Exception as e:
        console.print(f":x: [bold red]Failed to bind component:[/bold red] {e}")


@app.command()
def update(
    portfolio: Annotated[str, typer.Argument(help=":id: Portfolio ID")],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help=":label: New portfolio name")] = None,
    description: Annotated[Optional[str], typer.Option("--desc", "-d", help=":memo: New portfolio description")] = None,
    start_date: Annotated[Optional[str], typer.Option("--start", "-s", help=":calendar: New start date (YYYYMMDD)")] = None,
    end_date: Annotated[Optional[str], typer.Option("--end", "-e", help=":calendar: New end date (YYYYMMDD)")] = None,
):
    """
    :memo: Update portfolio metadata.
    """
    from ginkgo.data.operations import get_portfolio, update_portfolio
    
    # Verify portfolio exists
    portfolio_df = get_portfolio(portfolio)
    if portfolio_df.shape[0] == 0:
        console.print(f":exclamation: Portfolio [light_coral]{portfolio}[/light_coral] not found.")
        return
    
    # Update fields
    updates = {}
    if name:
        updates['name'] = name
    if description:
        updates['desc'] = description
    if start_date:
        updates['backtest_start_date'] = start_date
    if end_date:
        updates['backtest_end_date'] = end_date
    
    if not updates:
        console.print(":information: No updates specified.")
        return
    
    try:
        update_portfolio(portfolio, **updates)
        console.print(f":white_check_mark: [bold green]Updated portfolio[/bold green] [cyan]{portfolio_df.iloc[0]['name']}[/cyan]")
        
        for field, value in updates.items():
            console.print(f"  {field}: [cyan]{value}[/cyan]")
            
    except Exception as e:
        console.print(f":x: [bold red]Failed to update portfolio:[/bold red] {e}")


@app.command()
def unbind(
    portfolio: Annotated[Optional[str], typer.Option("--portfolio", "-p", "--p", help=":id: Portfolio ID")] = None,
    component: Annotated[Optional[str], typer.Option("--component", "-c", "--c", help=":id: Component (file) ID")] = None,
    force: Annotated[bool, typer.Option("--force", "-f", help=":exclamation: Skip confirmation")] = False,
):
    """
    :unlink: Unbind a component from a portfolio.
    """
    from ginkgo.data.operations import (
        get_portfolio, get_portfolio_file_mappings_page_filtered, delete_portfolio_file_mapping, get_portfolios_page_filtered
    )
    
    # Check portfolio
    if portfolio is None:
        portfolios_df = get_portfolios_page_filtered()
        # 配置列显示
        columns_config = {
            "uuid": {"display_name": "Portfolio ID", "style": "dim"},
            "name": {"display_name": "Name", "style": "cyan"},
            "backtest_start_date": {"display_name": "Start Date", "style": "dim"},
            "backtest_end_date": {"display_name": "End Date", "style": "dim"},
            "update_at": {"display_name": "Update At", "style": "dim"}
        }
        
        display_dataframe(
            data=portfolios_df,
            columns_config=columns_config,
            title=":briefcase: [bold]Available Portfolios:[/bold]",
            console=console
        )
        return
    
    portfolio_df = get_portfolio(portfolio)
    if portfolio_df.shape[0] == 0:
        console.print(f":exclamation: Portfolio [light_coral]{portfolio}[/light_coral] not found.")
        portfolios_df = get_portfolios_page_filtered()
        # 配置列显示
        columns_config = {
            "uuid": {"display_name": "Portfolio ID", "style": "dim"},
            "name": {"display_name": "Name", "style": "cyan"},
            "backtest_start_date": {"display_name": "Start Date", "style": "dim"},
            "backtest_end_date": {"display_name": "End Date", "style": "dim"},
            "update_at": {"display_name": "Update At", "style": "dim"}
        }
        
        display_dataframe(
            data=portfolios_df,
            columns_config=columns_config,
            title=":briefcase: [bold]Available Portfolios:[/bold]",
            console=console
        )
        return
    
    # Check component
    if component is None:
        mappings_df = get_portfolio_file_mappings_page_filtered(portfolio=portfolio)
        # 配置列显示
        bound_components_columns_config = {
            "uuid": {"display_name": "Mapping ID", "style": "dim"},
            "name": {"display_name": "Component Name", "style": "cyan"},
            "type": {"display_name": "Type", "style": "green"},
            "file_id": {"display_name": "File ID", "style": "dim"},
            "update_at": {"display_name": "Update At", "style": "dim"}
        }
        
        display_dataframe(
            data=mappings_df,
            columns_config=bound_components_columns_config,
            title=f":link: [bold]Bound Components for Portfolio {portfolio}:[/bold]",
            console=console
        )
        return
    
    # Find the mapping
    mappings_df = get_portfolio_file_mappings_page_filtered(portfolio=portfolio)
    target_mapping = mappings_df[mappings_df["file_id"] == component]
    
    if target_mapping.shape[0] == 0:
        console.print(f":exclamation: Component [light_coral]{component}[/light_coral] is not bound to portfolio [light_coral]{portfolio}[/light_coral].")
        mappings_df = get_portfolio_file_mappings_page_filtered(portfolio=portfolio)
        # 配置列显示
        bound_components_columns_config = {
            "uuid": {"display_name": "Mapping ID", "style": "dim"},
            "name": {"display_name": "Component Name", "style": "cyan"},
            "type": {"display_name": "Type", "style": "green"},
            "file_id": {"display_name": "File ID", "style": "dim"},
            "update_at": {"display_name": "Update At", "style": "dim"}
        }
        
        display_dataframe(
            data=mappings_df,
            columns_config=bound_components_columns_config,
            title=f":link: [bold]Bound Components for Portfolio {portfolio}:[/bold]",
            console=console
        )
        return
    
    if target_mapping.shape[0] > 1:
        console.print(f":warning: [yellow]Multiple bindings found for component[/yellow] [light_coral]{component}[/light_coral]. Auto-removing all {target_mapping.shape[0]} bindings.")
        
        # Display all mappings to be removed
        for idx, mapping in target_mapping.iterrows():
            console.print(f"  - Mapping ID: [dim]{mapping['uuid']}[/dim] | Name: [cyan]{mapping['name']}[/cyan] | Type: [green]{mapping['type']}[/green]")
        
        # Delete all mappings
        deleted_count = 0
        for idx, mapping in target_mapping.iterrows():
            try:
                delete_portfolio_file_mapping(mapping["uuid"])
                deleted_count += 1
            except Exception as e:
                console.print(f":x: [red]Failed to delete mapping {mapping['uuid']}:[/red] {e}")
        
        console.print(f":white_check_mark: [bold green]Successfully removed {deleted_count} duplicate bindings[/bold green] for component [cyan]{component}[/cyan]")
        return
    
    mapping_row = target_mapping.iloc[0]
    component_name = mapping_row["name"]
    component_type = mapping_row["type"]
    
    if not force:
        if not Confirm.ask(f":question: Unbind {component_type.value} [cyan]{component_name}[/cyan] from portfolio?", default=True):
            console.print(":relieved_face: Operation cancelled.")
            return
    
    try:
        delete_portfolio_file_mapping(mapping_row["uuid"])
        console.print(f":white_check_mark: [bold green]Successfully unbound[/bold green] [cyan]{component_name}[/cyan] from portfolio [yellow]{portfolio}[/yellow]")
    except Exception as e:
        console.print(f":x: [bold red]Failed to unbind component:[/bold red] {e}")




