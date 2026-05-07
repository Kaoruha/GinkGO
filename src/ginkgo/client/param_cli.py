# Upstream: CLI主入口(ginkgo param命令调用)
# Downstream: DataContainer(通过container访问ParamCRUD)、Rich库(表格/确认框显示)
# Role: 参数管理CLI，提供list列表、add添加、delete删除、update更新等命令，支持组件参数的动态配置和管理




"""
Ginkgo Parameter CLI - 参数管理命令
"""

import typer
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm

app = typer.Typer(
    help=":wrench: Module for [bold medium_spring_green]PARAMETER[/] management. [grey62]CRUD operations for component parameters.[/grey62]",
    no_args_is_help=True,
)
console = Console(emoji=True, legacy_windows=False)


@app.command()
def list(
    mapping: Annotated[str, typer.Option("--mapping", "-m", help="Portfolio-file mapping ID")],
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw data as JSON"),
):
    """
    :open_file_folder: List all parameters for a component mapping.
    """
    from ginkgo.data.containers import container

    param_crud = container.cruds.param()
    params = param_crud.find_by_mapping_id(mapping)

    if raw:
        import json
        raw_data = []
        for p in params:
            raw_data.append({"uuid": p.uuid, "index": p.index, "value": p.value})
        console.print(json.dumps(raw_data, indent=2, ensure_ascii=False, default=str))
        return

    if not params:
        console.print(f":information: No parameters found for mapping {mapping[:8]}...")
        return

    table = Table(title=f":wrench: Parameters for mapping {mapping[:8]}...")
    table.add_column("UUID", style="dim", width=32)
    table.add_column("Index", style="green", width=6)
    table.add_column("Value", style="cyan", width=30)
    table.add_column("Updated", style="dim", width=20)

    for p in sorted(params, key=lambda x: x.index):
        updated = str(p.update_at)[:19] if hasattr(p, 'update_at') and p.update_at else "N/A"
        table.add_row(p.uuid, str(p.index), str(p.value), updated)

    console.print(table)


@app.command()
def add(
    mapping: Annotated[str, typer.Option("--mapping", "-m", help="Portfolio-file mapping ID")],
    value: Annotated[str, typer.Option("--value", "-v", help="Parameter value")],
    index: Annotated[Optional[int], typer.Option("--index", "-i", help="Specific index (auto-assign if not provided)")] = None,
):
    """
    :plus: Add a new parameter to a component.
    """
    from ginkgo.data.containers import container

    param_crud = container.cruds.param()

    if index is None:
        existing = param_crud.find_by_mapping_id(mapping)
        if existing:
            index = max(p.index for p in existing) + 1
        else:
            index = 0

    try:
        param_crud.set_param_value(mapping, index, value)
        console.print(f":white_check_mark: Added parameter at index {index}: [cyan]{value}[/cyan]")
    except Exception as e:
        console.print(f":x: Failed to add parameter: {e}")
        raise typer.Exit(1)


@app.command()
def update(
    param_id: Annotated[str, typer.Option("--param", "-p", help="Parameter UUID")],
    value: Annotated[str, typer.Option("--value", "-v", help="New parameter value")],
):
    """
    :memo: Update an existing parameter value.
    """
    from ginkgo.data.containers import container

    try:
        param_crud = container.cruds.param()
        param_crud.update_value(param_id, value)
        console.print(f":white_check_mark: Updated parameter {param_id[:8]}... to [cyan]{value}[/cyan]")
    except Exception as e:
        console.print(f":x: Failed to update parameter: {e}")
        raise typer.Exit(1)


@app.command()
def delete(
    param_id: Annotated[str, typer.Option("--param", "-p", help="Parameter UUID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
):
    """
    :wastebasket: Delete a parameter.
    """
    from ginkgo.data.containers import container

    if not force:
        if not Confirm.ask(f":question: Delete parameter {param_id[:8]}...?", default=False):
            console.print("Cancelled.")
            return

    try:
        param_crud = container.cruds.param()
        param_crud.delete_by_uuid(param_id)
        console.print(f":white_check_mark: Deleted parameter {param_id[:8]}...")
    except Exception as e:
        console.print(f":x: Failed to delete parameter: {e}")
        raise typer.Exit(1)
