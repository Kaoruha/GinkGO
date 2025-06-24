# coding:utf-8
import typer
from enum import Enum
from typing_extensions import Annotated
from rich.prompt import Prompt
from rich import print
import sys
import datetime
import os
import unittest


from ginkgo.libs.core.config import GCONF
from ginkgo.libs import GLOG


app = typer.Typer(
    help=":dove_of_peace:  Module for [bold medium_spring_green]UNITTEST[/]. [grey62]Confirm functional integrity.[/grey62]",
    no_args_is_help=True,
)


class LogLevelType(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@app.command()
def list():
    """
    Show unittest summary.
    """
    pass


@app.command()
def run(
    a: Annotated[bool, typer.Option(case_sensitive=False, help="Run All Modules of Unittest.")] = False,
    base: Annotated[bool, typer.Option(case_sensitive=False)] = False,
    db: Annotated[bool, typer.Option(case_sensitive=False)] = False,
    libs: Annotated[bool, typer.Option(case_sensitive=False)] = False,
    datasource: Annotated[bool, typer.Option(case_sensitive=False)] = False,
    backtest: Annotated[bool, typer.Option(case_sensitive=False)] = False,
    lab: Annotated[bool, typer.Option(case_sensitive=False)] = False,
    y: Annotated[bool, typer.Option(case_sensitive=False)] = False,
    debug: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    Run Unittest.
    """
    if debug:
        GLOG.set_level("debug")
    LOGGING_FILE_ON = GCONF.LOGGING_FILE_ON
    LOGGING_PATH = GCONF.LOGGING_PATH
    suite = unittest.TestSuite()
    origin_path = f"{GCONF.WORKING_PATH}/test"
    path = []

    if a:
        base = True
        db = True
        libs = True
        datasource = True
        backtest = True

    if base:
        path.append(origin_path)

    if db:
        if GCONF.DEBUGMODE == False:
            print("[red]DB MODE Only work on DEBUGMODE[/red]")
        else:
            if not y:
                port = GCONF.CLICKPORT
                if port == "18123":
                    msg = "[medium_spring_green]DEV DATABASE[/medium_spring_green]:monkey_face:"
                else:
                    msg = "You might have connected to a [bold red]PRODUCTION DATABASE[/bold red]:boom: or you have changed the default port of dev clickhouse."
                print(f"Current PORT is {GCONF.CLICKPORT}")
                print(msg)
                result = typer.confirm(f"DB Moduel may erase the database, Conitnue? ")
                if result:
                    t = origin_path + "/db"
                    path.append(t)
            else:
                t = origin_path + "/db"
                path.append(t)

    if libs:
        t = origin_path + "/libs"
        path.append(t)

    if datasource:
        t = origin_path + "/data"
        path.append(t)

    if backtest:
        t = origin_path + "/backtest"
        path.append(t)

    if lab:
        t = origin_path + "/lab"
        path.append(t)

    for i in path:
        tests = unittest.TestLoader().discover(i, pattern="test_*.py")
        suite.addTest(tests)

    log_path = LOGGING_PATH + "unittest.log"
    if LOGGING_FILE_ON:
        GLOG.reset_logfile("unittest.log")
        try:
            f = open(log_path, "w")
            f.truncate()
        except Exception as e:
            print(e)

    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
