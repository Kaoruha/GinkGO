import typer
import subprocess
from pathlib import Path
from enum import Enum
from typing import List as typing_list, Optional
from typing_extensions import Annotated
from rich.prompt import Prompt
from rich.table import Column, Table
from rich.console import Console
import pandas as pd

# All heavy imports moved to function level for faster CLI startup

app = typer.Typer(
    help=":dna: Manage [bold medium_spring_green]COMPONENT[/] files. [grey62]Create, edit, and manage component files.[/grey62]",
    no_args_is_help=True,
)
console = Console()


@app.command(name="create")
def create():
    """
    :ram: Create components.
    """
    print("create component")


@app.command(name="list")
def list(
    type: Annotated[Optional[str], typer.Option("--type", "-t", help="Filter by component type (strategy, analyzer, selector, sizer, risk)")] = None,
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="Filter by component name")] = None,
    include_removed: Annotated[bool, typer.Option("--all", "-a", help="Include removed components")] = False,
):
    """
    :open_file_folder: List component files.
    """
    from ginkgo.enums import FILE_TYPES
    from ginkgo.data.containers import Container
    from ginkgo.libs.utils.display import display_dataframe
    
    # Build filters
    filters = {}
    if name:
        filters['name'] = name
    if type:
        # Map string type to FILE_TYPES
        type_mapping = {
            'strategy': FILE_TYPES.STRATEGY,
            'analyzer': FILE_TYPES.ANALYZER,
            'selector': FILE_TYPES.SELECTOR,
            'sizer': FILE_TYPES.SIZER,
            'risk': FILE_TYPES.RISKMANAGER,
        }
        if type.lower() in type_mapping:
            filters['type'] = type_mapping[type.lower()]
        else:
            console.print(f":exclamation: Invalid component type: [light_coral]{type}[/light_coral]")
            console.print("Valid types: strategy, analyzer, selector, sizer, risk")
            return
    
    # Get component files
    try:
        file_crud = Container.file_crud()
        files = file_crud.find(filters=filters)
        
        # Convert objects to dataframe
        if files:
            data_rows = []
            for file_obj in files:
                data_rows.append({
                    'uuid': file_obj.uuid,
                    'name': file_obj.name,
                    'type': file_obj.type.name if hasattr(file_obj.type, 'name') else str(file_obj.type),
                    'path': getattr(file_obj, 'path', ''),
                    'update_at': getattr(file_obj, 'update_at', ''),
                    'is_del': getattr(file_obj, 'is_del', False)
                })
            files_df = pd.DataFrame(data_rows)
        else:
            files_df = pd.DataFrame()
        
        # Filter out removed files unless requested
        if files_df.shape[0] > 0 and not include_removed and 'is_del' in files_df.columns:
            files_df = files_df[files_df['is_del'] == False]
        
        # Display results
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
            title=":dna: [bold]Components:[/bold]",
            console=console
        )
        
    except Exception as e:
        console.print(f":x: [bold red]Failed to list components:[/bold red] {e}")


@app.command()
def update(
    component: Annotated[str, typer.Option("--component", "-c", "--c", help=":id: Component file ID")],
    name: Annotated[Optional[str], typer.Option("--name", "-n", help=":label: New component name")] = None,
    description: Annotated[Optional[str], typer.Option("--desc", help=":memo: New component description")] = None,
):
    """
    :memo: Update component file metadata.
    """
    from ginkgo.data.containers import Container
    
    # Verify file exists
    file_crud = Container.file_crud()
    file_obj = file_crud.get(id)
    if not file_obj:
        console.print(f":exclamation: Component file [light_coral]{id}[/light_coral] not found.")
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
    
    try:
        file_crud.update(id, **updates)
        console.print(f":white_check_mark: [bold green]Updated component file[/bold green] [cyan]{file_obj.name}[/cyan]")
        
        for field, value in updates.items():
            console.print(f"  {field}: [cyan]{value}[/cyan]")
            
    except Exception as e:
        console.print(f":x: [bold red]Failed to update component:[/bold red] {e}")


@app.command()
def edit(
    id: Annotated[str, typer.Option(..., "--id", "-id", case_sensitive=True, help="File ID")],
):
    """
    :orange_book: Edit [bold yellow]FILE[/].
    """

    def check_editor():
        editors = ["nvim", "vim"]
        for editor in editors:
            try:
                result = subprocess.run(
                    ["which", editor], capture_output=True, text=True
                )
                if result.returncode == 0:
                    return editor
            except FileNotFoundError:
                continue
        return None

    from ginkgo.data.containers import Container

    file_crud = Container.file_crud()
    file_obj = file_crud.get(id)
    if not file_obj:
        console.print(f"The file {id} not exist.")
        return

    file_path = getattr(file_obj, 'path', '')
    file_name = file_obj.name
    console.print(f"EDIT file: {file_name}")
    console.print(f"PATH: {file_path}")

    if not Path(file_path).exists():
        console.print(f"PATH [bold red]{file_path}[/] not exist.")
        return

    editor = check_editor()
    if editor:
        subprocess.run([editor, file_path])
    else:
        console.print("No suitable editor found (nvim or vim).")


@app.command(name="cat")
def cat(
    id: Annotated[str, typer.Option(..., "--id", "-id", case_sensitive=True, help="File ID")],
):
    """
    :information_source: Display file content.
    """
    from ginkgo.data.containers import Container

    file_crud = Container.file_crud()
    file_obj = file_crud.get(id)
    if not file_obj:
        console.print(f"The file {id} not exist.")
        return

    file_path = getattr(file_obj, 'path', '')
    file_name = file_obj.name

    if not Path(file_path).exists():
        console.print(f"PATH [bold red]{file_path}[/] not exist.")
        return

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        console.print(f"[bold cyan]File: {file_name}[/bold cyan]")
        console.print(f"[dim]Path: {file_path}[/dim]")
        console.print("─" * 60)
        console.print(content)
    except Exception as e:
        console.print(f":x: [bold red]Failed to read file:[/bold red] {e}")


@app.command(name="remove")
def remove(
    id: Annotated[str, typer.Option(..., "--id", "-id", case_sensitive=True, help="File ID")],
):
    """
    :wastebasket: Remove component file.
    """
    from ginkgo.data.containers import Container
    from rich.prompt import Confirm

    file_res = get_file(id)
    if file_res.shape[0] == 0:
        console.print(f"The file {id} not exist.")
        return

    file_name = file_res.iloc[0]["name"]
    
    if not Confirm.ask(f":question: Remove component file [cyan]{file_name}[/cyan]?", default=False):
        console.print(":relieved_face: Operation cancelled.")
        return

    try:
        file_crud.remove(id)
        console.print(f":white_check_mark: [bold green]Removed component file[/bold green] [cyan]{file_name}[/cyan]")
    except Exception as e:
        console.print(f":x: [bold red]Failed to remove file:[/bold red] {e}")


@app.command()
def validate(
    component: Annotated[Optional[str], typer.Option("--component", "-c", "--c", help=":id: Component ID to validate")] = None,
    file_path: Annotated[Optional[str], typer.Option("--file", "-f", "--f", help=":page_facing_up: File path to validate")] = None,
    type: Annotated[Optional[str], typer.Option("--type", "-t", help=":gear: Component type (strategy, analyzer, risk, sizer)")] = None,
):
    """
    :white_check_mark: Validate component compliance with framework standards.
    """
    try:
        from ginkgo.libs import validate_component
        
        if validate_component is None:
            console.print(":x: [bold red]Validation module not available.[/bold red]")
            console.print("Please ensure the validators module is properly installed.")
            return
        
        # 参数验证
        if not component and not file_path:
            console.print(":exclamation: [bold red]Must specify either --component or --file[/bold red]")
            console.print("Examples:")
            console.print("  ginkgo backtest component validate --component abc123 --type strategy")
            console.print("  ginkgo backtest component validate --file ./my_strategy.py --type strategy")
            return
        
        if not type:
            console.print(":exclamation: [bold red]Component type is required[/bold red]")
            console.print("Valid types: strategy, analyzer, risk, sizer")
            return
        
        # 执行校验
        if component:
            console.print(f":mag: [bold blue]Validating component[/bold blue] [cyan]{component}[/cyan] as [green]{type}[/green]...")
            result = validate_component(type, component_id=component)
        else:
            console.print(f":mag: [bold blue]Validating file[/bold blue] [cyan]{file_path}[/cyan] as [green]{type}[/green]...")
            result = validate_component(type, file_path=file_path)
        
        # 显示结果
        _display_validation_result(result)
        
    except Exception as e:
        console.print(f":x: [bold red]Validation failed:[/bold red] {e}")


@app.command()
def test(
    component: Annotated[str, typer.Option("--component", "-c", "--c", help=":id: Component ID to test")],
    test_type: Annotated[str, typer.Option("--type", "-t", help=":test_tube: Test type (unit, integration, performance)")] = "integration",
):
    """
    :test_tube: Run component tests in a safe sandbox environment.
    """
    try:
        from ginkgo.libs import test_component
        
        if test_component is None:
            console.print(":x: [bold red]Testing module not available.[/bold red]")
            console.print("Please ensure the validators module is properly installed.")
            return
        
        console.print(f":test_tube: [bold blue]Running {test_type} tests[/bold blue] for component [cyan]{component}[/cyan]...")
        
        # 执行测试
        result = test_component(component, test_type)
        
        # 显示结果
        _display_validation_result(result)
        
    except Exception as e:
        console.print(f":x: [bold red]Testing failed:[/bold red] {e}")


def _display_validation_result(result):
    """
    显示校验结果
    
    Args:
        result: ValidationResult对象
    """
    # 状态图标和颜色
    if result.is_valid:
        if result.level.value == "warning":
            status_icon = ":warning:"
            status_color = "yellow"
            status_text = "PASSED WITH WARNINGS"
        else:
            status_icon = ":white_check_mark:"
            status_color = "green" 
            status_text = "PASSED"
    else:
        status_icon = ":x:"
        status_color = "red"
        status_text = "FAILED"
    
    # 显示主要结果
    console.print(f"\n{status_icon} [bold {status_color}]{status_text}[/bold {status_color}]")
    console.print(f"[bold]Message:[/bold] {result.message}")
    
    # 显示详细信息
    if result.details:
        console.print(f"[bold]Details:[/bold] {result.details}")
    
    # 显示建议
    if result.suggestions:
        console.print(f"\n[bold yellow]Suggestions:[/bold yellow]")
        for i, suggestion in enumerate(result.suggestions, 1):
            console.print(f"  {i}. {suggestion}")
    
    console.print("")  # 空行