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
from rich.prompt import Confirm

app = typer.Typer(
    help=":wrench: Module for [bold medium_spring_green]PARAMETER[/] management. [grey62]CRUD operations for component parameters.[/grey62]",
    no_args_is_help=True,
)
console = Console(emoji=True, legacy_windows=False)


@app.command()
def list(
    mapping: Annotated[str, typer.Option("--mapping", "-m", "--m", help=":id: Portfolio-file mapping ID")],
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw data as JSON"),
):
    """
    :open_file_folder: List all parameters for a component mapping.
    """
    from ginkgo.data.containers import container
    from ginkgo.libs.utils.display import display_dataframe

    param_crud = container.cruds.param()
    params_df = param_crud.get_page_filtered(mapping)

    # Raw output mode
    if raw:
        import json
        raw_data = params_df.to_dict('records')
        console.print(json.dumps(raw_data, indent=2, ensure_ascii=False, default=str))
        return

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
        title=f":wrench: [bold]Parameters for mapping {mapping}:[/bold]",
        console=console
    )


@app.command()
def add(
    mapping: Annotated[str, typer.Option("--mapping", "-m", "--m", help=":id: Portfolio-file mapping ID")],
    value: Annotated[str, typer.Option("--value", "-v", "--v", help=":pencil: Parameter value")],
    index: Annotated[Optional[int], typer.Option("--index", "-i", help=":1234: Specific index (auto-assign if not provided)")] = None,
):
    """
    :plus: Add a new parameter to a component.
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