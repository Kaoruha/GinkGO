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

from ginkgo.client.unittest_cli import LogLevelType
from ginkgo.libs import GLOG
from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
from ginkgo.enums import ORDERSTATUS_TYPES


app = typer.Typer(
    help=":hammer_and_wrench:  Manage [bold medium_spring_green]Strategy/Components[/]. [grey62][/]",
    no_args_is_help=True,
)
console = Console()


@app.command(name="init")
def init():
    """
    :ram: Init the basic file to database. Copy files from source.
    """
    from ginkgo.data import init_example_data as func

    func()


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


@app.command()
def recall(
    id: Annotated[str, typer.Option(..., "--id", "-id", case_sensitive=True, help="Backtest ID")],
    name: Annotated[str, typer.Option(case_sensitive=True, help="File Name")] = "",
):
    """
    :open_file_folder: Recall the backtest configuration from a completed backtest. # TODO
    """
    # TODO
    from ginkgo.data.operations import add_file, update_file, get_backtest_record
    from ginkgo.enums import FILE_TYPES
    import yaml
    import datetime

    backtest = get_backtest_record(id)
    if backtest is None:
        return
    content = backtest.content
    file_name = "Edo Tensei"
    try:
        file_name = name if name != "" else f"{yaml.safe_load(content)['name']}_recall"
    except Exception as e:
        print(e)
    file_id = add_file(FILE_TYPES.ENGINE, file_name)
    update_file(file_id, FILE_TYPES.ENGINE, file_name, content)
    console.print(
        f":dove:  Recall the configuration of backtest [light_coral]{id}[/light_coral] as [medium_spring_green]{file_name}[/medium_spring_green]"
    )
