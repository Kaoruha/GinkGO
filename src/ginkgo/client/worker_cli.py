import typer
from enum import Enum
from typing_extensions import Annotated
from rich.console import Console

# All heavy imports moved to function level for faster CLI startup

app = typer.Typer(
    help=":construction_worker: Module for [bold medium_spring_green]WORKER[/]. [grey62]Worker process management.[/grey62]",
    no_args_is_help=True,
)

console = Console()


class ToggleType(str, Enum):
    ON = "on"
    OFF = "off"


@app.command("status")
def worker_status():
    """
    :bar_chart: Show worker process status summary.
    """
    import datetime
    from ginkgo.libs import GCONF, GTM
    from ginkgo.libs.utils.display import display_dataframe
    
    GTM.clean_worker_pool()
    GTM.clean_thread_pool()
    GTM.clean_worker_status()
    
    total_workers = GTM.get_worker_count()
    target_workers = int(GCONF.CPURATIO * 12)
    cpu_usage = GCONF.CPURATIO * 100
    
    console.print(f"[bold]Worker Status Summary:[/bold]")
    console.print(f"Total Workers    : {total_workers}")
    console.print(f"Target Workers   : {target_workers}")
    console.print(f"CPU Ratio        : {cpu_usage:.1f}%")
    
    status = GTM.get_workers_status()
    
    if len(status) > 0:
        running = sum(1 for item in status.values() if item["status"] == "RUNNING")
        idle = sum(1 for item in status.values() if item["status"] == "IDLE")
        complete = sum(1 for item in status.values() if item["status"] == "COMPLETE")
        error = sum(1 for item in status.values() if item["status"] == "ERROR")
        other = len(status) - running - idle - complete - error
        
        console.print(f"Running Workers  : {running}")
        console.print(f"Idle Workers     : {idle}")
        console.print(f"Complete Workers : {complete}")
        if error > 0:
            console.print(f"Error Workers    : {error}")
        if other > 0:
            console.print(f"Other Status     : {other}")
        
        # Create detailed worker status table
        console.print("")
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
                title="Worker Process Details",
                console=console
            )
        else:
            console.print("No worker status data available.")
    else:
        console.print("No detailed worker status available.")


@app.command("list")
def worker_list():
    """
    :clipboard: List all worker processes.
    """
    from ginkgo.libs import GTM
    
    GTM.clean_worker_pool()
    GTM.clean_thread_pool()
    GTM.clean_worker_status()

    console.print(f"Total Workers: {GTM.get_worker_count()}")

    # Create worker status table
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
            title="Worker Processes",
            console=console
        )
    else:
        console.print("No worker status data available.")


@app.command("start")
def worker_start(
    count: Annotated[int, typer.Option(help=":1234: Number of workers to start")] = None,
    auto: Annotated[bool, typer.Option(help=":robot: Auto-calculate worker count based on CPU ratio")] = False,
):
    """
    :green_circle: Start worker processes.
    """
    from ginkgo.libs import GCONF, GTM
    
    current_count = GTM.get_worker_count()

    if auto:
        target_count = int(GCONF.CPURATIO * 12)
        count = target_count - current_count
        console.print(f":penguin: Target Worker: {target_count}, Current Worker: {current_count}")
    elif count is None:
        console.print("Specify either --count or --auto option.")
        return

    if count > 0:
        GTM.start_multi_worker(count)
        console.print(f":construction_worker: Started {count} worker processes.")
    elif count < 0:
        from ginkgo.data.containers import container
        kafka_service = container.kafka_service()

        for i in range(abs(count)):
            kafka_service.send_worker_kill_signal()
        console.print(f":stop_sign: Stopped {abs(count)} worker processes.")
    else:
        console.print("No action needed. Worker count is already at target.")

    console.print(f"Total Workers: {GTM.get_worker_count()}")


@app.command("stop")
def worker_stop(
    count: Annotated[int, typer.Option(help=":1234: Number of workers to stop")] = None,
    all: Annotated[bool, typer.Option(help=":octagonal_sign: Stop all workers")] = False,
):
    """
    :red_circle: Stop worker processes.
    """
    from ginkgo.libs import GTM
    
    if all:
        GTM.reset_all_workers()
        console.print(":octagonal_sign: All workers stopped.")
    elif count is not None:
        from ginkgo.data.containers import container
        kafka_service = container.kafka_service()

        for i in range(count):
            kafka_service.send_worker_kill_signal()
        console.print(f":stop_sign: Stopped {count} worker processes.")
    else:
        console.print("Specify either --count or --all option.")
        return

    console.print(f"Remaining Workers: {GTM.get_worker_count()}")


@app.command("restart")
def worker_restart(
    count: Annotated[int, typer.Option(help=":1234: Number of workers to restart")] = None,
):
    """
    :arrows_counterclockwise: Restart worker processes.
    """
    from ginkgo.libs import GTM
    
    if count is None:
        # Restart all workers
        current_count = GTM.get_worker_count()
        GTM.reset_all_workers()
        console.print(f":octagonal_sign: Stopped all {current_count} workers.")

        if current_count > 0:
            GTM.start_multi_worker(current_count)
            console.print(f":construction_worker: Restarted {current_count} workers.")
    else:
        # Restart specific number of workers
        from ginkgo.data.containers import container
        kafka_service = container.kafka_service()

        for i in range(count):
            kafka_service.send_worker_kill_signal()
        console.print(f":stop_sign: Stopped {count} workers.")

        GTM.start_multi_worker(count)
        console.print(f":construction_worker: Started {count} new workers.")

    console.print(f"Total Workers: {GTM.get_worker_count()}")


@app.command("scale")
def worker_scale(
    target: Annotated[int, typer.Argument(help="Target number of workers")],
):
    """
    :chart_with_upwards_trend: Scale worker processes to target count.
    """
    from ginkgo.libs import GTM
    
    current_count = GTM.get_worker_count()
    difference = target - current_count

    console.print(f"Current Workers: {current_count}")
    console.print(f"Target Workers : {target}")

    if difference > 0:
        GTM.start_multi_worker(difference)
        console.print(f":construction_worker: Started {difference} additional workers.")
    elif difference < 0:
        from ginkgo.data.containers import container
        kafka_service = container.kafka_service()

        for i in range(abs(difference)):
            kafka_service.send_worker_kill_signal()
        console.print(f":stop_sign: Stopped {abs(difference)} workers.")
    else:
        console.print("Worker count is already at target.")

    console.print(f"Final Worker Count: {GTM.get_worker_count()}")


@app.command("run")
def worker_run(
    debug: Annotated[bool, typer.Option("--debug", "-d", help="Enable debug logging")] = False,
    worker_id: Annotated[str, typer.Option("--id", help="Custom worker ID for identification")] = None
):
    """
    :play_button: Run a single worker in foreground mode for debugging.
    """
    from ginkgo.libs import GTM, GLOG
    import signal
    import sys
    
    # 设置日志级别
    if debug:
        GLOG.set_level("DEBUG")
        console.print("[bold yellow]Debug mode enabled[/bold yellow]")
    
    # 显示启动信息
    if worker_id:
        console.print(f"[bold blue]Starting worker '{worker_id}' in foreground...[/bold blue]")
    else:
        console.print("[bold blue]Starting worker in foreground...[/bold blue]")
    
    console.print("[yellow]Press Ctrl+C to stop the worker[/yellow]")
    
    # 设置信号处理
    def signal_handler(signum, frame):
        console.print("\n[bold red]Received interrupt signal, stopping worker...[/bold red]")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 直接运行worker（不创建daemon进程）
        gtm = GTM
        gtm.run_data_worker()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Worker stopped by user[/bold yellow]")
    except Exception as e:
        console.print(f"[bold red]Worker error: {e}[/bold red]")
        if debug:
            import traceback
            console.print(f"[red]{traceback.format_exc()}[/red]")
        sys.exit(1)
