import typer
import time
from typing import List as typing_list
import click
import os
from cmd import Cmd
from typing_extensions import Annotated
from rich.console import Console
from rich.live import Live
from rich import print

from enum import Enum
from ginkgo.backtest.plots import CandlePlot
from ginkgo.client import data_cli
from ginkgo.client import backtest_cli
from ginkgo.client import unittest_cli
from ginkgo.client.interactive_cli import MyPrompt
from ginkgo.client.backtest_cli import LogLevelType
from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
from ginkgo.libs.ginkgo_conf import GCONF


main_app = typer.Typer(
    help="Usage: ginkgo [OPTIONS] COMMAND [ARGS]...", rich_markup_mode="rich"
)
main_app.add_typer(data_cli.app, name="data")
main_app.add_typer(backtest_cli.app, name="backtest")
main_app.add_typer(unittest_cli.app, name="unittest")

console = Console()


class DEBUG_TYPE(str, Enum):
    ON = "on"
    OFF = "off"


@main_app.command()
def status(
    stream: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    :bullet_train: Check the module status.
    """
    from ginkgo.data.ginkgo_data import GDATA
    from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
    from ginkgo.libs.ginkgo_thread import GTM

    console.print(f"DEBUGMODE : {GCONF.DEBUGMODE}")
    console.print(f"QUIETMODE : {GCONF.QUIET}")
    console.print(f"CPU LIMIT : {GCONF.CPURATIO*100}%")
    console.print(f"LOG  PATH : {GCONF.LOGGING_PATH}")
    console.print(f"WORK  DIR : {GCONF.WORKING_PATH}")
    console.print(f"WORKER    : {GTM.dataworker_count}")
    console.print(f"TELE BOT  : [steel_blue1]{GNOTIFIER.telebot_status}[/steel_blue1]")
    if stream:
        os.system(
            "docker stats redis_master clickhouse_master mysql_master clickhouse_test mysql_test kafka1 kafka2 kafka3"
        )
    else:
        os.system(
            "docker stats redis_master clickhouse_master mysql_master clickhouse_test mysql_test kafka1 kafka2 kafka3 --no-stream"
        )
    console.print(f"RECENT LOG:")
    log()


@main_app.command()
def version():
    """
    :sheep: Show the version of Client.
    """
    from ginkgo.config.package import PACKAGENAME, VERSION

    print(
        f":sparkles: [bold medium_spring_green]{PACKAGENAME}[/bold medium_spring_green] [light_goldenrod2]{VERSION}[/light_goldenrod2]"
    )


@main_app.command()
def interactive():
    """
    :robot: Active interactive mode.
    """
    os.system("clear")
    p = MyPrompt()
    p.cmdloop()


@main_app.command()
def configure(
    cpu: Annotated[float, typer.Option(case_sensitive=False)] = None,
    debug: Annotated[DEBUG_TYPE, typer.Option(case_sensitive=False)] = None,
    worker: Annotated[DEBUG_TYPE, typer.Option(case_sensitive=False)] = None,
    telebot: Annotated[DEBUG_TYPE, typer.Option(case_sensitive=False)] = None,
    logpath: Annotated[str, typer.Option(case_sensitive=True)] = None,
    workpath: Annotated[str, typer.Option(case_sensitive=True)] = None,
):
    """
    :wrench: Configure Ginkgo.
    """
    if (
        cpu is None
        and debug is None
        and logpath is None
        and worker is None
        and telebot is None
        and workpath is None
    ):
        console.print(
            "You could set cpu usage by --cpu, switch the debug mode by --debug."
        )

    from ginkgo.libs.ginkgo_conf import GCONF
    from ginkgo.data.ginkgo_data import GDATA
    import datetime

    if cpu is not None:
        if isinstance(cpu, float):
            GCONF.set_cpu_ratio(cpu)
        console.print(f"CPU RATIO: {GCONF.CPURATIO*100}%")

    if debug is not None:
        if debug == DEBUG_TYPE.ON:
            GCONF.set_debug(True)
        elif debug == DEBUG_TYPE.OFF:
            GCONF.set_debug(False)
        console.print(f"DEBUE: {GCONF.DEBUGMODE}")

    if worker is not None:
        from ginkgo.libs.ginkgo_thread import GTM

        if worker == DEBUG_TYPE.ON:
            """
            $SHELL_FOLDER/venv/bin/python $SHELL_FOLDER/main.py
            """
            current_count = GTM.dataworker_count
            target_count = GCONF.CPURATIO * 12
            target_count = int(target_count)
            console.print(
                f":penguin: Target Worker: {target_count}, Current Worker: {current_count}"
            )

            count = target_count - current_count
            if count > 0:
                GTM.start_multi_worker(count)
            else:
                for i in range(count):
                    GDATA.send_signal_stop_dataworker()
        elif worker == DEBUG_TYPE.OFF:
            GTM.reset_worker_pool()
        console.print(f"WORKER    : {GTM.dataworker_count}")
    if telebot is not None:
        time_out = 8
        if telebot == DEBUG_TYPE.ON:
            """
            $SHELL_FOLDER/venv/bin/python $SHELL_FOLDER/main.py
            """
            if GNOTIFIER.telebot_status == "RUNNING":
                console.print(
                    f":sun_with_face: TeleBot is [steel_blue1]RUNNING[/steel_blue1].",
                    end="\r",
                )
                return

            import os
            from ginkgo.libs import GCONF

            file_name = "telebot_run.py"
            content = """ 
from ginkgo.notifier.ginkgo_notifier import GNOTIFIER

if __name__ == "__main__": 
    GNOTIFIER.run_telebot() 
"""

            # 打开文件进行写入
            work_dir = GCONF.WORKING_PATH
            with open(file_name, "w") as file:
                file.write(content)
            cmd = f"nohup {work_dir}/venv/bin/python -u {work_dir}/{file_name} >>{GCONF.LOGGING_PATH}/telegram_bot.log 2>&1 &"
            os.system(cmd)

            count = datetime.timedelta(seconds=0)
            t0 = datetime.datetime.now()
            with Live(console=console, refresh_per_second=50) as live:
                while count < datetime.timedelta(seconds=time_out):
                    t1 = datetime.datetime.now()
                    count = t1 - t0
                    status = GNOTIFIER.telebot_status
                    if status == "RUNNING":
                        break
                    else:
                        live.update(
                            f":sun_with_face: TeleBot is [steel_blue1]STARTING[/steel_blue1] now. {count}",
                            refresh=True,
                        )
                        time.sleep(0.02)

                live.update(
                    f":sun_with_face: TeleBot is [steel_blue1]{GNOTIFIER.telebot_status}[/steel_blue1] now."
                )
            os.remove(f"{work_dir}/{file_name}")

        elif telebot == DEBUG_TYPE.OFF:
            GNOTIFIER.kill_telebot()
            count = datetime.timedelta(seconds=0)
            t0 = datetime.datetime.now()

            with Live(console=console, refresh_per_second=50) as live:
                while count < datetime.timedelta(seconds=time_out):
                    t1 = datetime.datetime.now()
                    count = t1 - t0
                    status = GNOTIFIER.telebot_status
                    if status == "DEAD" or status == "NOT EXIST":
                        break
                    else:
                        live.update(
                            f":ice: Telegram Bot Server will be [light_coral]KILLED[/light_coral] soon.",
                            refresh=True,
                        )
                        time.sleep(0.02)

                live.update(
                    f":sun_with_face: Telegram Bot Server is [steel_blue1]{GNOTIFIER.telebot_status}[/steel_blue1] now."
                )

    if logpath is not None:
        GCONF.set_logging_path(logpath)
        console.print(f"LOGGING PATH: {GCONF.LOGGING_PATH}")
    if workpath is not None:
        GCONF.set_work_path(workpath)
        console.print(f"WORK DIR: {GCONF.WORKING_PATH}")


@main_app.command()
def run(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID.")],
    debug: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    :poultry_leg: Run Backtest. [grey62]Duplication fo `ginkgo backtest run`.[/grey62]
    """
    from ginkgo.client.backtest_cli import run as backtest_run

    backtest_run(id, debug)


@main_app.command()
def cat(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="File id.")],
):
    """
    :see_no_evil: Show File content. [grey62]Duplication of `ginkgo backtest cat`. [/grey62]
    """
    from ginkgo.client.backtest_cli import cat as backtest_cat

    backtest_cat(id)


@main_app.command()
def edit(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="File ID")],
):
    """
    :orange_book: Edit File. [grey62]Duplication of `ginkgo backtest edit`.[/grey62]
    """
    from ginkgo.client.backtest_cli import edit as backtest_edit

    backtest_edit(id)


@main_app.command()
def rm(
    ids: Annotated[
        typing_list[str],
        typer.Argument(case_sensitive=True, help="File ID"),
    ],
):
    """
    :boom: Delete [light_coral]FILE[/light_coral] or [light_coral]BACKTEST RECORD[/light_coral] in database. [grey62]Duplication of `ginkgo backtest rm`.[/grey62]
    """
    from ginkgo.client.backtest_cli import rm as backtest_rm

    backtest_rm(ids)


@main_app.command()
def ls(
    filter: Annotated[
        str, typer.Option(case_sensitive=False, help="File filter")
    ] = None,
    a: Annotated[
        bool,
        typer.Option(case_sensitive=False, help="Show All Data, include removed file."),
    ] = False,
):
    """
    :open_file_folder: Show backtest file summary. [grey62]Duplication of `ginkgo backtest ls`.[/grey62]
    """
    from ginkgo.client.backtest_cli import ls as backtest_ls

    backtest_ls(filter, a)


@main_app.command()
def res(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID")] = "",
    index: Annotated[
        typing_list[str],
        typer.Argument(
            case_sensitive=True,
            help="Type the analyzer_id to plot.",
        ),
    ] = None,
    compare: Annotated[
        str,
        typer.Option(case_sensitive=False, help="Do Compare with other backtest."),
    ] = "",
):
    """
    :one-piece_swimsuit: Show the backtest result. [grey62]Duplication of `ginkgo backtest res`.[/grey62]
    """
    from ginkgo.client.backtest_cli import res as backtest_res

    backtest_res(id, index, compare)


@main_app.command()
def update(
    a: Annotated[
        bool, typer.Option(case_sensitive=False, help="Update StockInfo")
    ] = False,
    # data: Annotated[DataType, typer.Argument(case_sensitive=False)],
    stockinfo: Annotated[
        bool, typer.Option(case_sensitive=False, help="Update StockInfo")
    ] = False,
    calendar: Annotated[
        bool, typer.Option(case_sensitive=False, help="Update Calendar")
    ] = False,
    adjust: Annotated[
        bool, typer.Option(case_sensitive=False, help="Update adjustfactor")
    ] = False,
    day: Annotated[
        bool, typer.Option(case_sensitive=False, help="Update day bar")
    ] = False,
    tick: Annotated[
        bool, typer.Option(case_sensitive=False, help="Update tick data")
    ] = False,
    fast: Annotated[
        bool,
        typer.Option(
            case_sensitive=False, help="If set, ginkgo will try update in fast mode."
        ),
    ] = False,
    code: Annotated[
        typing_list[str],
        typer.Argument(
            case_sensitive=True,
            help="If set,ginkgo will try to update the data of specific code.",
        ),
    ] = None,
    debug: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    :raccoon: Data Update. [grey62]Duplication of `ginkgo data update`. [/grey62]
    """
    from ginkgo.client.data_cli import update as data_update

    data_update(a, stockinfo, calendar, adjust, day, tick, fast, code, debug)


@main_app.command()
def rebuild(
    order: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Order Table")
    ] = False,
    record: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Backtest Record Table")
    ] = False,
    file: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild File Table")
    ] = False,
    backtest: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Backtest Table")
    ] = False,
    analyzer: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Analyzer Table")
    ] = False,
    stockinfo: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild StockInfo Table")
    ] = False,
    calendar: Annotated[
        bool, typer.Option(case_sensitive=False, help="Rebuild Calendar Table")
    ] = False,
):
    """
    :fox_face: Rebuild [light_coral]TABLE[/light_coral] in database. [grey62]Duplication of `ginkgo data rebuild`. [/grey62]

    """
    from ginkgo.client.data_cli import rebuild as data_rebuild

    data_rebuild(order, record, file, backtest, analyzer, stockinfo, calendar)


@main_app.command()
def recall(
    id: Annotated[str, typer.Argument(case_sensitive=True, help="Backtest ID")],
    name: Annotated[str, typer.Option(case_sensitive=True, help="File Name")] = "",
):
    from ginkgo.client.backtest_cli import recall as backtest_recall

    backtest_recall(id, name)


@main_app.command()
def log(
    n: Annotated[int, typer.Option(case_sensitive=False)] = 10,
    stream: Annotated[bool, typer.Option(case_sensitive=False)] = False,
    data: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    file_name = "data_worker.log" if data else "ginkgo.log"
    follow = "-f" if stream else ""
    cmd = f"tail -n {n} {follow} {GCONF.LOGGING_PATH}/{file_name}"
    os.system(cmd)


if __name__ == "__main__":
    main_app()
