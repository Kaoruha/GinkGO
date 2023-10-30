import typer
from enum import Enum
from typing_extensions import Annotated
from rich.prompt import Prompt


class DataType(str, Enum):
    STOCKINFO = "stockinfo"
    ADJUST = "adjust"
    DAYBAR = "day"
    MINBAR = "min"


app = typer.Typer(help="Module for DATA")


@app.command()
def list(
    data: Annotated[DataType, typer.Argument(case_sensitive=False)],
    limit: Annotated[
        int, typer.Option(case_sensitive=False, help="Limit the number of output.")
    ] = 0,
    filter: Annotated[
        str, typer.Option(case_sensitive=True, help="Filter the output.")
    ] = "",
):
    """
    Show data summary.
    """
    # TODO limit and filter
    from ginkgo.data.ginkgo_data import GDATA
    import pandas as pd

    pd.set_option("display.unicode.east_asian_width", True)

    if datatype == DataType.CODE:
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
    elif datatype == DataType.DAYBAR:
        pass
    elif datatype == DataType.MINBAR:
        pass


@app.command()
def show(
    data: Annotated[DataType, typer.Argument(case_sensitive=False)] = "stockinfo",
    code: Annotated[str, typer.Argument(case_sensitive=False)] = "600000.SH",
    start: Annotated[
        str,
        typer.Option(
            case_sensitive=False,
            help="Date start, you could use yyyymmdd or yyyy-mm-dd",
        ),
    ] = "20200101",
    end: Annotated[
        str,
        typer.Option(
            case_sensitive=False,
            help="Date start, you could use yyyymmdd or yyyy-mm-dd",
        ),
    ] = "20200201",
):
    """
    Show data details.
    """
    from ginkgo.data.ginkgo_data import GDATA
    import pandas as pd

    # TODO Reset the log level

    pd.set_option("display.unicode.east_asian_width", True)

    if data == DataType.STOCKINFO:
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
    elif data == DataType.DAYBAR:
        df = GDATA.get_daybar_df(code, start, end)
        print(df.to_string())
    elif data == DataType.MINBAR:
        pass
    pass


@app.command()
def update(
    data: Annotated[DataType, typer.Argument(case_sensitive=False)],
    fast: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    Update the database.
    """
    from ginkgo.data.ginkgo_data import GDATA
    from ginkgo.libs.ginkgo_logger import GLOG
    import logging

    GLOG.set_level("CRITICAL")

    if data == DataType.STOCKINFO:
        GDATA.update_stock_info()
    elif data == DataType.ADJUST:
        pass
    elif data == DataType.DAYBAR:
        pass
    elif data == DataType.MINBAR:
        pass


@app.command()
def search(
    filter: Annotated[
        str, typer.Option(case_sensitive=True, help="Key words to search")
    ] = "",
):
    """
    Try do fuzzy search.
    """
    pass
