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
    help=":shark: Manage [bold medium_spring_green]MAPPING[/]. [grey62][/]",
    no_args_is_help=True,
)
console = Console()


@app.command(name="e_p_bind")
def e_p_bind():
    """
    :ram: Bind Engine and Portfolio.
    """
    print("bind engine and portfolio")
