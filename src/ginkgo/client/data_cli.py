import typer
from enum import Enum
from typing_extensions import Annotated
from rich.prompt import Prompt


class DataType(str, Enum):
    stockinfo = "stockinfo"
    daybar = "daybar"
    minbar = "minbar"


app = typer.Typer(help="Module for DATA")


@app.command()
def list(
    datatype: Annotated[DataType, typer.Option(case_sensitive=False)],
):
    """
    Show data summary.
    """
    from ginkgo.data.ginkgo_data import GDATA
    import pandas as pd

    pd.set_option("display.unicode.east_asian_width", True)

    if datatype == DataType.stockinfo:
        raw = GDATA.get_stock_info_df()
        raw = raw[
            [
                "code",
                "code_name",
                "industry",
                "currency",
                "update",
            ]
        ]
        print(raw.to_string())
    elif datatype == DataType.daybar:
        code = Prompt.ask("Enter stock code: ")
        pass
    elif datatype == DataType.minbar:
        pass


@app.command()
def show(
    datatype: Annotated[DataType, typer.Option(case_sensitive=False)],
    code: Annotated[str, typer.Option(case_sensitive=False)] = "",
    start: Annotated[str, typer.Option(case_sensitive=False)] = "",
    end: Annotated[str, typer.Option(case_sensitive=False)] = "",
):
    """
    Show data details.
    """
    from ginkgo.data.ginkgo_data import GDATA
    import pandas as pd

    pd.set_option("display.unicode.east_asian_width", True)

    if datatype == DataType.stockinfo:
        raw = GDATA.get_stock_info_df(code=code)
        raw = raw[
            [
                "code",
                "code_name",
                "industry",
                "currency",
                "update",
            ]
        ]
        print(raw.to_string())
    elif datatype == DataType.daybar:
        if start == "" and end == "":
            df = GDATA.get_daybar_df(code)
        else:
            df = GDATA.get_daybar_df(code, start, end)
        print(df.to_string())
    elif datatype == DataType.minbar:
        pass
    pass


@app.command()
def update(
    datatype: Annotated[DataType, typer.Option(case_sensitive=False)],
):
    """
    Update the database.
    """
    pass


@app.command()
def search():
    """
    Try do fuzzy search.
    """
    pass
