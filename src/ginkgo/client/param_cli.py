import typer
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console
from rich.prompt import Prompt, Confirm

# All heavy imports moved to function level for faster CLI startup

app = typer.Typer(
    help=":gear: Module for [bold medium_spring_green]PARAMETER[/] management. [grey62]CRUD operations for component parameters.[/grey62]",
    no_args_is_help=True,
)
console = Console()


@app.command()
def list(
    mapping: Annotated[str, typer.Option("--mapping", "-m", "--m", help=":id: Portfolio-file mapping ID")],
):
    """
    :open_file_folder: List all parameters for a component mapping.
    """
    from ginkgo.data.containers import container
    from ginkgo.libs.utils.display import display_dataframe
    
    param_crud = container.cruds.param()
    params_df = param_crud.get_page_filtered(mapping)
    # 配置列显示
    parameters_columns_config = {
        "uuid": {"display_name": "Parameter ID", "style": "dim"},
        "index": {"display_name": "Index", "style": "green"},
        "value": {"display_name": "Value", "style": "cyan"},
        "update_at": {"display_name": "Update At", "style": "dim"}
    }
    
    display_dataframe(
        data=params_df,
        columns_config=parameters_columns_config,
        title=f":gear: [bold]Parameters for mapping {mapping}:[/bold]",
        console=console
    )


@app.command()
def add(
    mapping: Annotated[str, typer.Option("--mapping", "-m", "--m", help=":id: Portfolio-file mapping ID")],
    value: Annotated[str, typer.Option("--value", "-v", "--v", help=":pencil: Parameter value")],
    index: Annotated[Optional[int], typer.Option("--index", "-i", help=":1234: Specific index (auto-assign if not provided)")] = None,
):
    """
    :heavy_plus_sign: Add a new parameter to a component.
    """
    from ginkgo.data.containers import container
    
    # Determine index if not provided
    if index is None:
        param_crud = container.cruds.param()
        params_df = param_crud.get_page_filtered(mapping)
        index = params_df["index"].max() + 1 if params_df.shape[0] > 0 else 0
    
    try:
        param_crud = container.cruds.param()
        param_data = param_crud.add(mapping_id=mapping, index=index, value=value)
        console.print(f":white_check_mark: [bold green]Added parameter[/bold green] at index {index}: [cyan]{value}[/cyan]")
        console.print(f":id: Param ID: [dim]{param_data['uuid']}[/dim]")
    except Exception as e:
        console.print(f":x: [bold red]Failed to add parameter:[/bold red] {e}")


@app.command()
def update(
    param: Annotated[str, typer.Option("--param", "-p", "--p", help=":id: Parameter ID")],
    value: Annotated[str, typer.Option("--value", "-v", "--v", help=":pencil: New parameter value")],
):
    """
    :memo: Update an existing parameter value.
    """
    from ginkgo.data.containers import container
    
    # Verify parameter exists
    param_crud = container.cruds.param()
    param_df = param_crud.get(param)
    if param_df.shape[0] == 0:
        console.print(f":exclamation: Parameter [light_coral]{param}[/light_coral] not found.")
        return
    
    old_value = param_df.iloc[0]["value"]
    param_index = param_df.iloc[0]["index"]
    
    try:
        param_crud = container.cruds.param()
        param_crud.update(param, value=value)
        console.print(f":white_check_mark: [bold green]Updated parameter[/bold green] at index {param_index}")
        console.print(f"  Old value: [dim]{old_value}[/dim]")
        console.print(f"  New value: [cyan]{value}[/cyan]")
    except Exception as e:
        console.print(f":x: [bold red]Failed to update parameter:[/bold red] {e}")


@app.command()
def delete(
    param: Annotated[str, typer.Option("--param", "-p", "--p", help=":id: Parameter ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help=":exclamation: Skip confirmation")] = False,
):
    """
    :wastebasket: Delete a parameter.
    """
    from ginkgo.data.containers import container
    
    # Verify parameter exists
    param_crud = container.cruds.param()
    param_df = param_crud.get(param)
    if param_df.shape[0] == 0:
        console.print(f":exclamation: Parameter [light_coral]{param}[/light_coral] not found.")
        return
    
    param_value = param_df.iloc[0]["value"]
    param_index = param_df.iloc[0]["index"]
    
    if not force:
        if not Confirm.ask(f":question: Delete parameter at index {param_index} ([cyan]{param_value}[/cyan])?", default=False):
            console.print(":relieved_face: Operation cancelled.")
            return
    
    try:
        param_crud = container.cruds.param()
        param_crud.delete(param)
        console.print(f":white_check_mark: [bold green]Deleted parameter[/bold green] at index {param_index}: [dim]{param_value}[/dim]")
    except Exception as e:
        console.print(f":x: [bold red]Failed to delete parameter:[/bold red] {e}")


@app.command()
def reorder(
    mapping: Annotated[str, typer.Option("--mapping", "-m", "--m", help=":id: Portfolio-file mapping ID")],
    from_index: Annotated[int, typer.Option("--from", "-f", "--f", help=":arrow_right: Source index")],
    to_index: Annotated[int, typer.Option("--to", "-t", "--t", help=":arrow_left: Target index")],
):
    """
    :arrow_up_down: Reorder parameters by swapping indices.
    """
    from ginkgo.data.containers import container
    
    param_crud = container.cruds.param()
    params_df = param_crud.get_page_filtered(mapping)
    
    if params_df.shape[0] == 0:
        console.print(f":exclamation: No parameters found for mapping [light_coral]{mapping}[/light_coral].")
        return
    
    # Find source parameter
    source_params = params_df[params_df["index"] == from_index]
    if source_params.shape[0] == 0:
        console.print(f":exclamation: No parameter found at index [light_coral]{from_index}[/light_coral].")
        return
    
    source_param = source_params.iloc[0]
    
    if from_index == to_index:
        console.print(":information: Source and target indices are the same. No changes made.")
        return
    
    try:
        # Check if target index exists
        target_params = params_df[params_df["index"] == to_index]
        
        if target_params.shape[0] > 0:
            # Swap with existing parameter
            target_param = target_params.iloc[0]
            
            # Perform swap
            param_crud = container.cruds.param()
            param_crud.update(source_param["uuid"], index=to_index)
            param_crud.update(target_param["uuid"], index=from_index)
            
            console.print(f":white_check_mark: [bold green]Swapped parameters[/bold green] at indices {from_index} ↔ {to_index}")
        else:
            # Just move to new index
            param_crud = container.cruds.param()
            param_crud.update(source_param["uuid"], index=to_index)
            console.print(f":white_check_mark: [bold green]Moved parameter[/bold green] from index {from_index} → {to_index}")
            
    except Exception as e:
        console.print(f":x: [bold red]Failed to reorder parameters:[/bold red] {e}")


@app.command()
def interactive(
    mapping: Annotated[str, typer.Option("--mapping", "-m", "--m", help=":id: Portfolio-file mapping ID")],
):
    """
    :computer: Interactive parameter management session.
    """
    from ginkgo.data.containers import container
    
    # Verify mapping exists and get component info
    param_crud = container.cruds.param()
    params_df = param_crud.get_page_filtered(mapping)
    
    console.print(f":gear: [bold]Interactive parameter management for mapping {mapping}[/bold]")
    
    if params_df.shape[0] == 0:
        console.print("[dim]No parameters found for this mapping[/dim]")
    
    while True:
        # Show current parameters
        param_crud = container.cruds.param()
        current_params = param_crud.get_page_filtered(mapping_id)
        if current_params.shape[0] > 0:
            console.print(f"\n:gear: [bold]Current parameters:[/bold]")
            # 配置列显示
            parameters_columns_config = {
                "uuid": {"display_name": "Parameter ID", "style": "dim"},
                "index": {"display_name": "Index", "style": "green"},
                "value": {"display_name": "Value", "style": "cyan"},
                "update_at": {"display_name": "Update At", "style": "dim"}
            }
            
            display_dataframe(
                data=current_params,
                columns_config=parameters_columns_config,
                title=None,
                console=console
            )
        else:
            console.print("\n:gear: [bold]No parameters found[/bold]")
        
        console.print(f"\n[bold]Parameter management options:[/bold]")
        console.print("[1] Add parameter")
        console.print("[2] Update parameter") 
        console.print("[3] Delete parameter")
        console.print("[4] Reorder parameters")
        console.print("[5] Exit")
        
        choice = Prompt.ask("Select action", choices=["1", "2", "3", "4", "5"], default="5")
        
        if choice == "1":
            _interactive_add(mapping)
        elif choice == "2":
            _interactive_update(mapping)
        elif choice == "3":
            _interactive_delete(mapping)
        elif choice == "4":
            _interactive_reorder(mapping)
        elif choice == "5":
            console.print(":wave: Exiting interactive mode.")
            break


def _interactive_add(mapping: str):
    """Interactive add parameter"""
    from ginkgo.data.containers import container
    
    # Get next available index
    param_crud = container.cruds.param()
    params_df = param_crud.get_page_filtered(mapping)
    next_index = params_df["index"].max() + 1 if params_df.shape[0] > 0 else 0
    
    value = Prompt.ask(f":pencil: Enter parameter value (will be at index {next_index})")
    
    try:
        param_crud = container.cruds.param()
        param_crud.add(mapping_id=mapping, index=next_index, value=value)
        console.print(f":white_check_mark: [bold green]Added parameter[/bold green] at index {next_index}: [cyan]{value}[/cyan]")
    except Exception as e:
        console.print(f":x: [bold red]Failed to add parameter:[/bold red] {e}")


def _interactive_update(mapping: str):
    """Interactive update parameter"""
    from ginkgo.data.containers import container
    
    param_crud = container.cruds.param()
    params_df = param_crud.get_page_filtered(mapping)
    if params_df.shape[0] == 0:
        console.print(":exclamation: No parameters to update.")
        return
    
    indices = [str(idx) for idx in params_df["index"].tolist()]
    index = int(Prompt.ask(f":arrow_right: Select parameter index to update", choices=indices))
    
    param_row = params_df[params_df["index"] == index].iloc[0]
    current_value = param_row["value"]
    param_id = param_row["uuid"]
    
    console.print(f"Current value: [cyan]{current_value}[/cyan]")
    new_value = Prompt.ask(f":pencil: Enter new value", default=current_value)
    
    if new_value == current_value:
        console.print(":information: No changes made.")
        return
    
    try:
        param_crud = container.cruds.param()
        param_crud.update(param_id, value=new_value)
        console.print(f":white_check_mark: [bold green]Updated parameter[/bold green] at index {index}: [cyan]{new_value}[/cyan]")
    except Exception as e:
        console.print(f":x: [bold red]Failed to update parameter:[/bold red] {e}")


def _interactive_delete(mapping: str):
    """Interactive delete parameter"""
    from ginkgo.data.containers import container, delete_param
    
    param_crud = container.cruds.param()
    params_df = param_crud.get_page_filtered(mapping)
    if params_df.shape[0] == 0:
        console.print(":exclamation: No parameters to delete.")
        return
    
    indices = [str(idx) for idx in params_df["index"].tolist()]
    index = int(Prompt.ask(f":arrow_right: Select parameter index to delete", choices=indices))
    
    param_row = params_df[params_df["index"] == index].iloc[0]
    value = param_row["value"]
    param_id = param_row["uuid"]
    
    if not Confirm.ask(f":question: Delete parameter at index {index} ([cyan]{value}[/cyan])?", default=False):
        console.print(":relieved_face: Operation cancelled.")
        return
    
    try:
        param_crud = container.cruds.param()
        param_crud.delete(param_id)
        console.print(f":white_check_mark: [bold green]Deleted parameter[/bold green] at index {index}")
    except Exception as e:
        console.print(f":x: [bold red]Failed to delete parameter:[/bold red] {e}")


def _interactive_reorder(mapping: str):
    """Interactive reorder parameters"""
    from ginkgo.data.containers import container
    
    param_crud = container.cruds.param()
    params_df = param_crud.get_page_filtered(mapping)
    if params_df.shape[0] <= 1:
        console.print(":exclamation: Need at least 2 parameters to reorder.")
        return
    
    indices = [str(idx) for idx in params_df["index"].tolist()]
    from_index = int(Prompt.ask(f":arrow_right: Select parameter index to move", choices=indices))
    to_index = int(Prompt.ask(f":arrow_right: Move to index position"))
    
    if from_index == to_index:
        console.print(":information: No changes made.")
        return
    
    try:
        source_param = params_df[params_df["index"] == from_index].iloc[0]
        target_params = params_df[params_df["index"] == to_index]
        
        if target_params.shape[0] > 0:
            target_param = target_params.iloc[0]
            param_crud = container.cruds.param()
            param_crud.update(source_param["uuid"], index=to_index)
            param_crud.update(target_param["uuid"], index=from_index)
            console.print(f":white_check_mark: [bold green]Swapped parameters[/bold green] at indices {from_index} ↔ {to_index}")
        else:
            param_crud = container.cruds.param()
            param_crud.update(source_param["uuid"], index=to_index)
            console.print(f":white_check_mark: [bold green]Moved parameter[/bold green] from index {from_index} → {to_index}")
            
    except Exception as e:
        console.print(f":x: [bold red]Failed to reorder parameters:[/bold red] {e}")