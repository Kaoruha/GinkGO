import typer
import pandas as pd
import subprocess

from enum import Enum
from typing import List as typing_list, Optional
from typing_extensions import Annotated
from rich.prompt import Prompt
from rich.table import Column, Table
from rich.console import Console
from pathlib import Path

from ginkgo.libs import GLOG
from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
from ginkgo.enums import ORDERSTATUS_TYPES
from ginkgo.client import backtest_update_cli


app = typer.Typer(
    help=":dna: Manage [bold medium_spring_green]COMPONENT[/]. [grey62][/]",
    no_args_is_help=True,
)
app.add_typer(backtest_update_cli.app, name="update")
console = Console()


@app.command(name="create")
def create():
    """
    :ram: Create components.
    """
    print("create component")


@app.command(name="list", no_args_is_help=True)
def ls(
    engine: Annotated[bool, typer.Option(case_sensitive=False, help="List engines.")] = False,
    portfolio: Annotated[bool, typer.Option(case_sensitive=False, help="List portfolios.")] = False,
    file: Annotated[bool, typer.Option(case_sensitive=False, help="List files.")] = False,
    mapping: Annotated[bool, typer.Option(case_sensitive=False, help="List mappings.")] = False,
    param: Annotated[bool, typer.Option(case_sensitive=False, help="List params.")] = False,
    signal: Annotated[bool, typer.Option(case_sensitive=False, help="List signals.")] = False,
    order: Annotated[bool, typer.Option(case_sensitive=False, help="List orders.")] = False,
    position: Annotated[bool, typer.Option(case_sensitive=False, help="List positions.")] = False,
    filter: Annotated[str, typer.Option(case_sensitive=False, help="File filter.")] = None,
    a: Annotated[
        bool,
        typer.Option(case_sensitive=False, help="Show All Data, include removed file."),
    ] = False,
):
    """
    :open_file_folder: Show backtest components list.
    """
    from ginkgo.enums import FILE_TYPES

    def intro_print(data_count: int, data_type: str):
        if filter is None:
            msg = f":ramen: There are {data_count} {data_type}. "
        else:
            msg = f":ramen: There are {data_count} {data_type} about [bold medium_spring_green]{filter}[/]. "
        console.print(msg)

    def print_engine(df):
        intro_print(df.shape[0], "engines")
        if df.shape[0] > 0:
            filtered_columns = ["uuid", "name", "is_live", "update_at"]
            rs = df[filtered_columns]
            table = Table(show_header=True, header_style="bold magenta")

            table.add_column("ID", style="dim")
            table.add_column("Name", style="dim")
            table.add_column("Live", style="dim")
            table.add_column("UpdateAt", style="dim")
            for i, r in rs.iterrows():
                table.add_row(r["uuid"], r["name"], str(r["is_live"]), str(r["update_at"]))
            console.print(table)

    def print_portfolio(df):
        intro_print(df.shape[0], "portfolios")
        if df.shape[0] > 0:
            filtered_columns = ["uuid", "name", "backtest_start_date", "backtest_end_date", "update_at"]
            rs = df[filtered_columns]
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim")
            table.add_column("Name", style="dim")
            table.add_column("Start", style="dim")
            table.add_column("End", style="dim")
            table.add_column("UpdateAt", style="dim")
            for i, r in rs.iterrows():
                table.add_row(
                    r["uuid"],
                    r["name"],
                    str(r["backtest_start_date"]),
                    str(r["backtest_end_date"]),
                    str(r["update_at"]),
                )
            console.print(table)

    def print_file(df):
        intro_print(df.shape[0], "files")
        if df.shape[0] > 0:
            filtered_columns = ["uuid", "name", "type", "update_at"]
            rs = df[filtered_columns]
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim")
            table.add_column("Name", style="dim")
            table.add_column("Type", style="dim")
            table.add_column("UpdateAt", style="dim")
            for i, r in rs.iterrows():
                table.add_row(r["uuid"], r["name"], str(r["type"]), str(r["update_at"]))
            console.print(table)

    def print_mapping(df):
        pass

    res = {}
    from ginkgo.data.operations import (
        get_files_page_filtered,
        get_engines_page_filtered,
        get_orders_page_filtered,
        get_portfolios_page_filtered,
    )

    if engine:
        df = get_engines_page_filtered(name=filter, as_dataframe=True)
        res["engine"] = df
        print_engine(df)

    if portfolio:
        df = get_portfolios_page_filtered(name=filter)
        res["portfolio"] = df
        print_portfolio(df)

    if file:
        if filter is None:
            df = get_files_page_filtered()
        else:
            file_type = FILE_TYPES.enum_convert(filter)
            df1 = pd.DataFrame()
            if file_type:
                df1 = get_files_page_filtered(type=file_type)
            df = get_files_page_filtered(name=filter)
            if df1.shape[0] > 0:
                df = pd.concat([df1, df])
            df = df.drop_duplicates(subset=["uuid"])
        res["file"] = df
        print_file(df)
    if mapping:
        from ginkgo.data.operations import (
            get_engine_handler_mappings_page_filtered,
            get_engine_portfolio_mappings_page_filtered,
            get_portfolio_file_mappings_page_filtered,
        )

        if filter is None:
            df = get_engine_portfolio_mappings_page_filtered()
            intro_print(df.shape[0], "engine portfolio mappings")
            if df.shape[0] > 0:
                filtered_columns = ["uuid", "engine_id", "portfolio_id", "update_at"]
                rs = df[filtered_columns]
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("ID", style="dim")
                table.add_column("Engine", style="dim")
                table.add_column("Portfolio", style="dim")
                table.add_column("UpdateAt", style="dim")
                for i, r in rs.iterrows():
                    table.add_row(r["uuid"], r["engine_id"], r["portfolio_id"], str(r["update_at"]))
                console.print(table)
            df = get_engine_handler_mappings_page_filtered()
            intro_print(df.shape[0], "engine handler mappings")
            # TODO
            df = get_portfolio_file_mappings_page_filtered()
            intro_print(df.shape[0], "portfolio file mappings")
            if df.shape[0] > 0:
                filtered_columns = ["uuid", "portfolio_id", "file_id", "name", "type", "update_at"]
                rs = df[filtered_columns]
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("ID", style="dim")
                table.add_column("Name", style="dim")
                table.add_column("Type", style="dim")
                table.add_column("Portfolio", style="dim")
                table.add_column("File", style="dim")
                table.add_column("UpdateAt", style="dim")
                for i, r in rs.iterrows():
                    table.add_row(
                        r["uuid"], r["name"], str(r["type"]), r["portfolio_id"], r["file_id"], str(r["update_at"])
                    )
                console.print(table)
        else:
            df = get_engine_portfolio_mappings_page_filtered()
            if df.shape[0] > 0:
                df1 = df[df["engine_id"] == filter]
                df2 = df[df["portfolio_id"] == filter]
                df = pd.concat([df1, df2])
            intro_print(df.shape[0], "engine portfolio mappings")
            if df.shape[0] > 0:
                filtered_columns = ["uuid", "engine_id", "portfolio_id", "update_at"]
                rs = df[filtered_columns]
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("ID", style="dim")
                table.add_column("Engine", style="dim")
                table.add_column("Portfolio", style="dim")
                table.add_column("UpdateAt", style="dim")
                for i, r in rs.iterrows():
                    table.add_row(r["uuid"], r["engine_id"], r["portfolio_id"], str(r["update_at"]))
                console.print(table)
            df = get_engine_handler_mappings_page_filtered()
            if df.shape[0] > 0:
                df1 = df[df["engine_id"] == filter]
                df2 = df[df["handler_id"] == filter]
                df = pd.concat([df1, df2])
            intro_print(df.shape[0], "engine handler mappings")
            if df.shape[0] > 0:
                pass
            df = get_portfolio_file_mappings_page_filtered()
            if df.shape[0] > 0:
                df1 = df[df["portfolio_id"] == filter]
                df2 = df[df["file_id"] == filter]
                df = pd.concat([df1, df2])
            intro_print(df.shape[0], "portfolio file mappings")
            if df.shape[0] > 0:
                filtered_columns = ["uuid", "portfolio_id", "file_id", "name", "type", "update_at"]
                rs = df[filtered_columns]
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("ID", style="dim")
                table.add_column("Name", style="dim")
                table.add_column("Type", style="dim")
                table.add_column("Portfolio", style="dim")
                table.add_column("File", style="dim")
                table.add_column("UpdateAt", style="dim")
                for i, r in rs.iterrows():
                    table.add_row(
                        r["uuid"], r["name"], str(r["type"]), r["portfolio_id"], r["file_id"], str(r["update_at"])
                    )
                console.print(table)
    if param:
        from ginkgo.data.operations import get_params_page_filtered

        if filter is not None:
            df = get_params_page_filtered(source_id=filter)
        else:
            df = get_params_page_filtered()
        if df.shape[0] > 0:
            intro_print(df.shape[0], "mapping params")
            filtered_columns = ["uuid", "mapping_id", "index", "value", "update_at"]
            print(df)
            rs = df[filtered_columns]
            rs = rs.sort_values(by=["mapping_id", "index"], ascending=True)
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim")
            table.add_column("Mapping", style="dim")
            table.add_column("Index", style="dim")
            table.add_column("Value", style="dim")
            table.add_column("UpdateAt", style="dim")
            for i, r in rs.iterrows():
                table.add_row(r["uuid"], r["mapping_id"], str(r["index"]), r["value"], str(r["update_at"]))
            console.print(table)

    if signal:
        # Get signal
        # Filter engine
        # Filter portfolio
        # TODO
        pass
    if order:
        # Get Order
        # Filter engine
        # Filter portfolio
        # TODO
        pass
    if position:
        # Get Position
        # Filter engine
        # Filter portfolio
        # TODO
        pass


@app.command(name="bind")
def bind():
    print("bind components")


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
                # 尝试运行编辑器，如果成功则说明可用
                result = subprocess.run([editor, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if result.returncode == 0:
                    return True, editor
            except FileNotFoundError:
                # 编辑器未安装或不在 PATH 中
                continue
        return False, None

    editor_res = check_editor()
    if not editor_res[0]:
        print("There is no editor in Systemt PATH.")
        return

    editor = editor_res[1]

    from ginkgo.libs.core.config import GCONF
    from ginkgo.data.operations import get_file, update_file
    from ginkgo.enums import FILE_TYPES

    file_in_db = get_file(id=id, as_dataframe=True)

    if file_in_db.shape[0] == 0:
        console.print(
            f":sad_but_relieved_face: File [yellow]{id}[/yellow] not exists. Try [green]ginkgo backtest list[/green] first."
        )
    else:
        import uuid
        import shutil
        import os

        id = file_in_db.uuid
        name = file_in_db["name"]
        type = file_in_db.type
        if type is FILE_TYPES.ENGINE:
            file_format = "yml"
        else:
            file_format = "py"
        content = file_in_db.data
        temp_folder = f"{GCONF.WORKING_PATH}/{uuid.uuid4()}"
        Path(temp_folder).mkdir(parents=True, exist_ok=True)
        with open(f"{temp_folder}/{name}.{file_format}", "wb") as file:
            file.write(content)
        # TODO Support editor set, nvim,vim.vi,nano or vscode?
        edit_name = name.replace(" ", r"\ ") if " " in name else name
        os.system(f"{editor} {temp_folder}/{edit_name}.{file_format}")
        with open(f"{temp_folder}/{name}.{file_format}", "rb") as file:
            update_file(id, type, name, file.read())
            console.print(f":bear: [yellow]{type}[/yellow][green bold] {name}[/green bold] Updated.")
        # Remove the file and directory
        shutil.rmtree(temp_folder)


@app.command(name="cat")
def cat(
    id: Annotated[str, typer.Option(..., "--id", "-id", case_sensitive=True, help="File id.")],
):
    """
    :see_no_evil: Show [bold medium_spring_green]FILE[/] content.
    """
    from ginkgo.data.operations import get_file

    file = get_file(id)
    content = file.content
    console.print(content.decode("utf-8"))


@app.command(name="remove")
def remove(
    ids: Annotated[
        typing_list[str],
        typer.Argument(case_sensitive=True, help="File IDs"),
    ],
):
    """
    :boom: Delete [bold light_coral]FILE[/] or [bold light_coral]BACKTEST RECORD[/].
    """
    from ginkgo.data.operations import delete_file, delete_engine, delete_portfolio

    for i in ids:
        id = i
        # Try remove file
        result_file = delete_file(id)
        if result_file > 0:
            msg = f":zany_face: File [yellow]{id}[/yellow] delete."
            console.print(msg)
        # Try remove backtest engine
        result_back = delete_engine(id)
        if result_back > 0:
            msg = f":zany_face: Backtest Engine [light_coral]{id}[/light_coral] deleted."
            console.print(msg)
        # remove portfolios
        result_portfolio = delete_portfolio(id)
        if result_portfolio > 0:
            msg = f":zany_face: Portfolio [light_coral]{id}[/light_coral] deleted."
            console.print(msg)
        # remove backtest signals
        # remove backtest orders
        # remove backtest orders records
        # remove backtest analyzers
        # remove backtest positions
        # TODO Update delete functions
        continue
        # Remove order records and analyzers
        result_order = remove_orders(id)
        if result_order > 0:
            msg = f":zany_face: Orders about [light_coral]{id}[/light_coral] [yellow]{result_order}[/yellow] delete."
            console.print(msg)
        result_ana = remove_analyzers(id)
        if result_ana > 0:
            msg = f":zany_face: Analyzers about [light_coral]{id}[/light_coral] [yellow]{result_ana}[/yellow] delete."
            console.print(msg)

        result_pos = remove_positions(id)
        if result_pos > 0:
            msg = f":zany_face: Positions in backtest [light_coral]{id}[/light_coral] [yellow]{result_pos}[/yellow] delete."
            console.print(msg)

        if result_file == 0 and result_back == 0 and result_order == 0 and result_ana == 0 and result_pos == 0:
            console.print(
                f"There is no file or backtest record about [light_coral]{id}[/light_coral]. Please check id again."
            )
