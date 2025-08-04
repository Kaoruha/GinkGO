import typer
from enum import Enum
from typing_extensions import Annotated
from rich.console import Console
from rich.live import Live

# All heavy imports moved to function level for faster CLI startup

app = typer.Typer(
    help=":bee: Module for [bold medium_spring_green]SYSTEM[/]. [grey62]System configuration and management.[/grey62]",
    no_args_is_help=True,
)

console = Console()


class ToggleType(str, Enum):
    ON = "on"
    OFF = "off"


@app.command()
def status(
    stream: Annotated[
        bool, typer.Option(case_sensitive=False, help=":arrows_counterclockwise: Stream mode for real-time updates")
    ] = False,
):
    """
    :bar_chart: Display system status and worker information.
    """
    import os
    from ginkgo.libs import GCONF, GTM
    from ginkgo.libs.utils.display import display_dataframe
    
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

    # Display worker status table
    console.print("")
    status = GTM.get_workers_status()
    if status:
        # 转换为status dict为dataframe
        import pandas as pd
        status_data = []
        for worker_id, worker_info in status.items():
            status_data.append({
                "worker_id": worker_id,
                "task_name": worker_info.get("task_name", "N/A"),
                "status": worker_info.get("status", "UNKNOWN"),
                "memory_mb": worker_info.get("memory_mb", "N/A"),
                "running_time": worker_info.get("running_time", "N/A")
            })
        
        status_df = pd.DataFrame(status_data)
        
        # 配置列显示
        worker_status_columns_config = {
            "worker_id": {"display_name": "Worker ID", "style": "cyan"},
            "task_name": {"display_name": "Task Name", "style": "blue"},
            "status": {"display_name": "Status", "style": "green"},
            "memory_mb": {"display_name": "Memory", "style": "yellow"},
            "running_time": {"display_name": "Running Time", "style": "magenta"}
        }
        
        display_dataframe(
            data=status_df,
            columns_config=worker_status_columns_config,
            title="Worker Status",
            console=console
        )
    else:
        console.print("No worker status data available.")

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
    # Show recent logs
    os.system(f"tail -n 10 {GCONF.LOGGING_PATH}/ginkgo.log")


# Configuration management subcommand group
config_app = typer.Typer(help=":wrench: System configuration management")


@config_app.command("show")
def config_show():
    """
    :eye: Display current system configuration.
    """
    from ginkgo.libs import GCONF, GTM
    
    console.print(f"[bold]System Configuration:[/bold]")
    console.print(f"DEBUGMODE : {GCONF.DEBUGMODE}")
    console.print(f"QUIETMODE : {GCONF.QUIET}")
    console.print(f"CPU LIMIT : {GCONF.CPURATIO*100}%")
    console.print(f"LOG  PATH : {GCONF.LOGGING_PATH}")
    console.print(f"WORK  DIR : {GCONF.WORKING_PATH}")
    console.print(f"MAINCONTRL: [medium_spring_green]{GTM.main_status}[/]")
    console.print(f"WATCHDOG  : [medium_spring_green]{GTM.watch_dog_status}[/]")
    console.print(f"WORKER    : {GTM.get_worker_count()}")


@config_app.command("set")
def config_set(
    cpu: Annotated[float, typer.Option(case_sensitive=False, help=":computer: Set CPU usage ratio (0.0-1.0)")] = None,
    debug: Annotated[ToggleType, typer.Option(case_sensitive=False, help=":bug: Toggle debug mode (on/off)")] = None,
    logpath: Annotated[str, typer.Option(case_sensitive=True, help=":file_folder: Set logging directory path")] = None,
    workpath: Annotated[
        str, typer.Option(case_sensitive=True, help=":open_file_folder: Set working directory path")
    ] = None,
):
    """
    :gear: Set system configuration parameters.
    """
    from ginkgo.libs import GCONF
    
    if cpu is None and debug is None and logpath is None and workpath is None:
        console.print("Specify at least one configuration parameter to set.")
        console.print("Use --help to see available options.")
        return

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
        if debug == ToggleType.ON:
            GCONF.set_debug(True)
        elif debug == ToggleType.OFF:
            GCONF.set_debug(False)
        console.print(f"DEBUG: {GCONF.DEBUGMODE}")

    if logpath is not None:
        GCONF.set_logging_path(logpath)
        console.print(f"LOGGING PATH: {GCONF.LOGGING_PATH}")

    if workpath is not None:
        GCONF.set_work_path(workpath)
        console.print(f"WORK DIR: {GCONF.WORKING_PATH}")


@config_app.command("reset")
def config_reset():
    """
    :recycle: Reset configuration to default values.
    """
    console.print("Configuration reset functionality not implemented yet.")


# Service management subcommand group
service_app = typer.Typer(help=":service_dog: System service management")


@service_app.command("status")
def service_status():
    """
    :bar_chart: Show service status.
    """
    from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
    
    console.print(f"MAINCONTRL: [medium_spring_green]{GTM.main_status}[/]")
    console.print(f"WATCHDOG  : [medium_spring_green]{GTM.watch_dog_status}[/]")
    console.print(f"TELEBOT   : [medium_spring_green]{GNOTIFIER.telebot_status}[/]")


@service_app.command("start")
def service_start(
    maincontrol: Annotated[bool, typer.Option(help=":control_knobs: Start main controller")] = False,
    watchdog: Annotated[bool, typer.Option(help=":dog: Start watchdog")] = False,
    telebot: Annotated[bool, typer.Option(help=":robot: Start telegram bot")] = False,
):
    """
    :green_circle: Start system services.
    """
    from ginkgo.libs import GTM
    
    if maincontrol:
        GTM.run_main_control_daemon()
        console.print(f"MAINCONTRL: [medium_spring_green]{GTM.main_status}[/]")

    if watchdog:
        GTM.run_watch_dog_daemon()
        console.print(f"WATCHDOG  : [medium_spring_green]{GTM.watch_dog_status}[/]")

    if telebot:
        _start_telebot()


@service_app.command("stop")
def service_stop(
    maincontrol: Annotated[bool, typer.Option(help=":control_knobs: Stop main controller")] = False,
    watchdog: Annotated[bool, typer.Option(help=":dog: Stop watchdog")] = False,
    telebot: Annotated[bool, typer.Option(help=":robot: Stop telegram bot")] = False,
):
    """
    :red_circle: Stop system services.
    """
    from ginkgo.libs import GTM
    
    if maincontrol:
        GTM.kill_maincontrol()
        console.print(f"MAINCONTRL: [medium_spring_green]{GTM.main_status}[/]")

    if watchdog:
        GTM.kill_watch_dog()
        console.print(f"WATCHDOG  : [medium_spring_green]{GTM.watch_dog_status}[/]")

    if telebot:
        _stop_telebot()


# Logs management subcommand group
logs_app = typer.Typer(help=":scroll: System logs management")


@logs_app.command("show")
def logs_show(
    n: Annotated[int, typer.Option(case_sensitive=False, help=":1234: Number of lines to show")] = 10,
    data: Annotated[bool, typer.Option(case_sensitive=False, help=":bar_chart: Show data worker logs")] = False,
):
    """
    :scroll: Show system logs.
    """
    import os
    from ginkgo.libs import GCONF
    
    file_name = "ginkgo_data.log" if data else "ginkgo.log"
    cmd = f"tail -n {n} {GCONF.LOGGING_PATH}/{file_name}"
    os.system(cmd)


@logs_app.command("tail")
def logs_tail(
    data: Annotated[bool, typer.Option(case_sensitive=False, help=":bar_chart: Show data worker logs")] = False,
):
    """
    :arrows_counterclockwise: Follow logs in real-time.
    """
    import os
    from ginkgo.libs import GCONF
    
    file_name = "ginkgo_data.log" if data else "ginkgo.log"
    cmd = f"tail -f {GCONF.LOGGING_PATH}/{file_name}"
    os.system(cmd)


@logs_app.command("clear")
def logs_clear():
    """
    :wastebasket: Clear log files.
    """
    console.print("Log clearing functionality not implemented yet.")


def _start_telebot():
    """Helper function to start telegram bot"""
    import time
    import datetime
    import subprocess
    import os
    from ginkgo.libs import GCONF
    from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
    
    time_out = 8
    if GNOTIFIER.telebot_status == "RUNNING":
        console.print(
            f":sun_with_face: TeleBot is [medium_spring_green]RUNNING[/medium_spring_green].",
            end="\r",
        )
        return

    file_name = "telebot_run.py"
    content = """
from ginkgo.notifier.ginkgo_notifier import GNOTIFIER

if __name__ == "__main__":
    GNOTIFIER.run_telebot()
"""

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


def _stop_telebot():
    """Helper function to stop telegram bot"""
    import time
    import datetime
    from ginkgo.notifier.ginkgo_notifier import GNOTIFIER
    
    time_out = 8
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


# Add subcommands to main app
app.add_typer(config_app, name="config")
app.add_typer(service_app, name="service")
app.add_typer(logs_app, name="logs")
