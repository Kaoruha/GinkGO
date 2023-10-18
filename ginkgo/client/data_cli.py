import typer
from enum import Enum


class DataType(str, Enum):
    stockinfo = "stockinfo"
    daybar = "daybar"
    minbar = "minbar"


app = typer.Typer(help="Module for DATA")


@app.command()
def list():
    pass


@app.command()
def show():
    pass


@app.command()
def update():
    pass
