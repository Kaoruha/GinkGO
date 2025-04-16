import typer
import subprocess
import time
import math
import datetime
import click
import os
from enum import Enum
from typing import List as typing_list
from typing_extensions import Annotated
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich import print

from ginkgo.client import data_cli
from ginkgo.client import backtest_cli
from ginkgo.client import unittest_cli
from ginkgo.client.interactive_cli import MyPrompt
from ginkgo.client.backtest_cli import LogLevelType
from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
from ginkgo.libs import GCONF


main_app = typer.Typer(rich_markup_mode="rich", no_args_is_help=True)
main_app.add_typer(data_cli.app, name="data")
main_app.add_typer(backtest_cli.app, name="backtest")
main_app.add_typer(unittest_cli.app, name="unittest")

console = Console()


class DEBUG_TYPE(str, Enum):
    ON = "on"
    OFF = "off"


@main_app.command()
def version():
    """
    :sheep: Show the version of Client.
    """
    from ginkgo.config.package import PACKAGENAME, VERSION

    print(f":sparkles: [bold medium_spring_green]{PACKAGENAME}[/] [light_goldenrod2]{VERSION}[/light_goldenrod2]")


@main_app.command(name="status")
def status(
    stream: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    :bullet_train: Check the [bold medium_spring_green]MODULE STATUS[/].
    """
    from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
    from ginkgo.libs import GTM

    GTM.clean_worker_pool()
    GTM.clean_thread_pool()
    GTM.clean_worker_status()
    console.print(f"DEBUGMODE : {GCONF.DEBUGMODE}")
    console.print(f"QUIETMODE : {GCONF.QUIET}")
    console.print(f"MAINCONTRL: [medium_spring_green]{GTM.main_status}[/]")
    console.print(f"WATCHDOG  : [medium_spring_green]{GTM.watch_dog_status}[/]")
    console.print(f"API Entry : TODO")
    console.print(f"CPU LIMIT : {GCONF.CPURATIO*100}%")
    console.print(f"LOG  PATH : {GCONF.LOGGING_PATH}")
    console.print(f"WORK  DIR : {GCONF.WORKING_PATH}")
    console.print(f"WORKER    : {GTM.get_worker_count()}")
    # 创建表格
    # table = Table(title="Worker Status")
    table = Table()
    # 添加列
    table.add_column("PID", justify="center", style="cyan", no_wrap=True)
    table.add_column("TASK", justify="center", style="magenta")
    table.add_column("STATUS", justify="center", style="green")
    table.add_column("STARTAT", justify="center", style="green")
    table.add_column("ELAPSED", justify="center", style="green")
    # 添加行
    console.print("")
    status = GTM.get_workers_status()
    current_time = datetime.datetime.now()
    for i in status.keys():
        item = status[i]
        start_time = datetime.datetime.strptime(item["time_stamp"], "%Y%m%d%H%M%S")
        elapsed_time = (current_time - start_time).total_seconds()
        running_time = (
            f"{int(elapsed_time // 3600):02}:{int((elapsed_time % 3600) // 60):02}:{int(elapsed_time % 60):02}"
        )
        dt = datetime.datetime.strptime(item["time_stamp"], "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        table.add_row(i, item["task_name"], item["status"], dt, running_time)
    # 输出表格
    if len(status.keys()) > 0:
        console.print(table)
    if stream:
        os.system(
            "docker stats redis_master clickhouse_master mysql_master clickhouse_test mysql_test kafka1 kafka2 kafka3"
        )
    else:
        os.system(
            "docker stats redis_master clickhouse_master mysql_master clickhouse_test mysql_test kafka1 kafka2 kafka3 --no-stream"
        )
    console.print("")
    console.print(f"RECENT LOG:")
    log()


@main_app.command(name="chat")
def interactive():
    """
    :robot: Active interactive mode.
    """
    os.system("clear")
    p = MyPrompt()
    p.cmdloop()


@main_app.command(name="jupyter")
def jupyter(
    daemon: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    :kaaba: Start [bold medium_spring_green]JUPYTER LAB SERVER[/].
    """
    from ginkgo.libs import GCONF

    if daemon:
        print("Damon is not support for jupyter now.")
    jupyter_path = os.path.join(os.path.dirname(GCONF.PYTHONPATH), "jupyter")
    subprocess.run([jupyter_path, "lab"])


@main_app.command(name="server")
def serve(
    daemon: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    :kaaba: Run [bold medium_spring_green]API SERVER[/].
    """
    from ginkgo.libs import GTM
    from ginkgo.libs import GCONF
    import os

    if daemon:
        console.print(f"Start API Server.")
        try:
            # 运行 systemctl start ginkgo 命令
            os.system("systemctl start ginkgo")
            result = subprocess.run(
                ["systemctl", "start", "ginkgo"],  # 命令和参数
                check=True,  # 如果命令返回非零退出码，抛出 CalledProcessError
                text=True,  # 将输入和输出作为字符串处理
            )
            print(result)
            print("Command executed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error occurred: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return

    python_path = GCONF.PYTHONPATH
    dir1 = os.path.dirname(python_path)
    uvicorn_path = os.path.join(dir1, "uvicorn")

    uvicorn_command = [
        uvicorn_path,
        "main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--app-dir",
        f"{GCONF.WORKING_PATH}/api",
        "--timeout-graceful-shutdown",
        "5",
    ]
    subprocess.run(uvicorn_command)


@main_app.command(name="config")
def config(
    cpu: Annotated[float, typer.Option(case_sensitive=False)] = None,
    debug: Annotated[DEBUG_TYPE, typer.Option(case_sensitive=False)] = None,
    maincontrol: Annotated[DEBUG_TYPE, typer.Option(case_sensitive=False)] = None,
    watchdog: Annotated[DEBUG_TYPE, typer.Option(case_sensitive=False)] = None,
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
        and maincontrol is None
        and watchdog is None
        and worker is None
        and workpath is None
    ):
        console.print("You could set cpu usage by --cpu, switch the debug mode by --debug.")

    from ginkgo.libs import GCONF, GTM
    import datetime

    if cpu is not None:
        if isinstance(cpu, float):
            if cpu < 0:
                cpu = 0.4
            if cpu > 1:
                cpu = cpu / 100
            if cpu > 1:
                cpu = 1
            GCONF.set_cpu_ratio(cpu)
        else:
            console.print("CPU RATIO only support number.")
        console.print(f"CPU RATIO: {GCONF.CPURATIO*100}%")

    if debug is not None:
        if debug == DEBUG_TYPE.ON:
            GCONF.set_debug(True)
        elif debug == DEBUG_TYPE.OFF:
            GCONF.set_debug(False)
        console.print(f"DEBUE: {GCONF.DEBUGMODE}")

    if worker is not None:
        if worker == DEBUG_TYPE.ON:
            """
            $SHELL_FOLD/venv/bin/python $SHELL_FOLDER/main.py
            """
            current_count = GTM.get_worker_count()
            target_count = GCONF.CPURATIO * 12
            target_count = int(target_count)
            console.print(f":penguin: Target Worker: {target_count}, Current Worker: {current_count}")

            count = target_count - current_count
            if count > 0:
                GTM.start_multi_worker(count)
            else:
                from ginkgo.data import send_signal_kill_a_worker

                for i in range(count):
                    send_signal_kill_a_worker()
        elif worker == DEBUG_TYPE.OFF:
            GTM.reset_all_workers()
        console.print(f"WORKER    : {GTM.get_worker_count()}")

    if telebot is not None:
        time_out = 8
        if telebot == DEBUG_TYPE.ON:
            """
            $SHELL_FOLDER/venv/bin/python $SHELL_FOLDER/main.py
            """
            if GNOTIFIER.telebot_status == "RUNNING":
                console.print(
                    f":sun_with_face: TeleBot is [medium_spring_green]RUNNING[/medium_spring_green].",
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
            command = [
                "nohup",
                f"{work_dir}/venv/bin/python",
                "-u",
                f"{work_dir}/{file_name}",
            ]
            with open("/dev/null", "w") as devnull:
                subprocess.Popen(command, stdout=devnull, stderr=devnull)

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
                            f":sun_with_face: TeleBot is [medium_spring_green]STARTING[/medium_spring_green] now. {count}",
                            refresh=True,
                        )
                        time.sleep(0.02)

                live.update(
                    f":sun_with_face: TeleBot is [medium_spring_green]{GNOTIFIER.telebot_status}[/medium_spring_green] now."
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
                    f":sun_with_face: Telegram Bot Server is [medium_spring_green]{GNOTIFIER.telebot_status}[/medium_spring_green] now."
                )

    if maincontrol is not None:
        if maincontrol == DEBUG_TYPE.ON:
            GTM.run_main_control_daemon()
        else:
            GTM.kill_maincontrol()

    if watchdog is not None:
        if watchdog == DEBUG_TYPE.ON:
            GTM.run_watch_dog_daemon()
        else:
            GTM.kill_watch_dog()

    if logpath is not None:
        GCONF.set_logging_path(logpath)
        console.print(f"LOGGING PATH: {GCONF.LOGGING_PATH}")

    if workpath is not None:
        GCONF.set_work_path(workpath)
        console.print(f"WORK DIR: {GCONF.WORKING_PATH}")


@main_app.command()
def log(
    n: Annotated[int, typer.Option(case_sensitive=False)] = 10,
    stream: Annotated[bool, typer.Option(case_sensitive=False)] = False,
    data: Annotated[bool, typer.Option(case_sensitive=False)] = False,
):
    """
    :spiral_note_pad:  Show [bold medium_spring_green]LOG[/].
    """
    file_name = "ginkgo_data.log" if data else "ginkgo.log"
    follow = "-f" if stream else ""
    cmd = f"tail -n {n} {follow} {GCONF.LOGGING_PATH}/{file_name}"
    os.system(cmd)


if __name__ == "__main__":
    main_app()
