"""
Ginkgo Worker CLI - Worker管理命令
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
import psutil

app = typer.Typer(help=":gear: Worker management", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


@app.command()
def run(
    debug: bool = typer.Option(False, "--debug", "-d", help="Run worker in debug mode"),
):
    """
    :gear: Run a worker in foreground.
    """
    try:
        from ginkgo.libs.core.threading import GinkgoThreadManager
        from ginkgo.libs.core.logger import GinkgoLogger

        if debug:
            print("Starting worker in debug mode...")

        # 创建ThreadManager实例
        gtm = GinkgoThreadManager()

        # 在前台运行单个worker
        console.print(":gear: Starting worker in foreground mode...")
        console.print(":information: Press Ctrl+C to stop the worker")

        try:
            gtm.run_data_worker()
        except KeyboardInterrupt:
            console.print("\n:information: Worker stopped by user")
        except Exception as e:
            console.print(f":x: Worker error: {e}")
            raise typer.Exit(1)

    except ImportError as e:
        console.print(f":x: Failed to import ThreadManager: {e}")
        raise typer.Exit(1)


@app.command()
def status(
    pid: Optional[str] = typer.Option(None, "--pid", "-p", help="Show status for specific worker PID"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed worker information"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw data as JSON"),
):
    """
    :bar_chart: Show worker status.
    """
    try:
        from ginkgo.libs.core.threading import GinkgoThreadManager
        import datetime

        gtm = GinkgoThreadManager()

        if pid:
            # 显示特定worker的状态
            worker_status = gtm.get_worker_status(pid)

            if not worker_status:
                console.print(f":x: Worker PID {pid} not found or has no status information")
                return

            # Raw output mode
            if raw:
                import json
                console.print(json.dumps(worker_status, indent=2, ensure_ascii=False, default=str))
                return

            console.print(f":magnifying_glass_tilted_left: Worker Status - PID: {pid}")

            # 显示worker详细信息
            table = Table(title=f":gear: Worker Details - PID {pid}")
            table.add_column("Property", style="cyan", width=20)
            table.add_column("Value", style="white", width=40)

            for key, value in worker_status.items():
                if key != "pid":
                    table.add_row(key.replace("_", " ").title(), str(value))

            console.print(table)

        else:
            # 显示所有worker的状态
            console.print(":magnifying_glass_tilted_left: All Workers Status")
            workers_status = gtm.get_workers_status()
            worker_count = gtm.get_worker_count()

            if not workers_status:
                console.print(":memo: No active workers found")
                return

            # Raw output mode
            if raw:
                import json
                console.print(json.dumps(workers_status, indent=2, ensure_ascii=False, default=str))
                return

            # 创建worker状态表格
            table = Table(title=f":gear: Worker Pool - Total: {worker_count}")
            table.add_column("PID", style="cyan", width=8)
            table.add_column("Task", style="green", width=20)
            table.add_column("Status", style="yellow", width=10)
            table.add_column("Running Time", style="blue", width=12)
            table.add_column("CPU", style="red", width=8)
            table.add_column("Memory", style="magenta", width=10)

            for pid, status in workers_status.items():
                try:
                    # 获取进程CPU和内存使用情况
                    if pid and pid.isdigit():
                        process = psutil.Process(int(pid))
                        cpu_percent = f"{process.cpu_percent():.1f}%"
                        memory_mb = f"{process.memory_info().rss / 1024 / 1024:.1f}MB"
                    else:
                        cpu_percent = "N/A"
                        memory_mb = "N/A"
                except (psutil.NoSuchProcess, psutil.AccessDenied, ValueError):
                    cpu_percent = "N/A"
                    memory_mb = "N/A"

                task_name = status.get("task_name", "N/A")
                worker_status = status.get("status", "N/A")
                running_time = status.get("running_time", "N/A")

                table.add_row(
                    str(pid)[:8],
                    str(task_name)[:18],
                    str(worker_status)[:8],
                    str(running_time)[:10],
                    str(cpu_percent)[:6],
                    str(memory_mb)[:8]
                )

            console.print(table)

            if detailed:
                console.print("\n:information: Detailed Worker Information:")
                for pid, status in workers_status.items():
                    console.print(f"  • PID {pid}: {status}")

    except ImportError as e:
        console.print(f":x: Failed to import ThreadManager: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f":x: Error getting worker status: {e}")
        raise typer.Exit(1)


@app.command()
def scale(
    count: int = typer.Argument(..., help="Target number of workers"),
    force: bool = typer.Option(False, "--force", "-f", help="Force scaling without confirmation"),
):
    """
    :arrows_counterclockwise: Scale workers to specified count.
    """
    try:
        from ginkgo.libs.core.threading import GinkgoThreadManager

        gtm = GinkgoThreadManager()
        current_count = gtm.get_worker_count()

        console.print(f":information: Current worker count: {current_count}")
        console.print(f":information: Target worker count: {count}")

        if count < 0:
            console.print(":x: Worker count cannot be negative")
            raise typer.Exit(1)

        if count == current_count:
            console.print(":information: Worker count is already at target")
            return

        if not force:
            # 请求确认
            if count > current_count:
                action = f"start {count - current_count} workers"
            else:
                action = f"stop {current_count - count} workers"

            console.print(f":warning: This will {action}. Are you sure?")
            try:
                from rich.prompt import Prompt
                confirmation = Prompt.ask("Type 'yes' to continue", default="no")
                if confirmation.lower() != 'yes':
                    console.print(":information: Operation cancelled")
                    return
            except (EOFError, KeyboardInterrupt):
                console.print(":information: Operation cancelled")
                return

        # 扩展worker数量
        if count > current_count:
            # 启动新workers
            workers_to_start = count - current_count
            console.print(f":information: Starting {workers_to_start} new workers...")
            gtm.start_multi_worker(count=workers_to_start)
            console.print(f":white_check_mark: Successfully started {workers_to_start} workers")

        elif count < current_count:
            # 停止多余的workers
            workers_to_stop = current_count - count
            console.print(f":warning: Stopping {workers_to_stop} workers...")
            gtm.reset_all_workers()
            # 重新启动需要的worker数量
            if count > 0:
                gtm.start_multi_worker(count=count)
            console.print(f":white_check_mark: Successfully scaled workers to {count}")

        # 显示新的状态
        new_count = gtm.get_worker_count()
        console.print(f":information: New worker count: {new_count}")

    except ImportError as e:
        console.print(f":x: Failed to import ThreadManager: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f":x: Error scaling workers: {e}")
        raise typer.Exit(1)


@app.command()
def stop():
    """
    :stop_button: Stop all workers.
    """
    try:
        from ginkgo.libs.core.threading import GinkgoThreadManager

        gtm = GinkgoThreadManager()
        current_count = gtm.get_worker_count()

        if current_count == 0:
            console.print(":information: No workers are currently running")
            return

        console.print(f":information: Stopping {current_count} workers...")
        gtm.reset_all_workers()
        console.print(":white_check_mark: All workers stopped successfully")

    except ImportError as e:
        console.print(f":x: Failed to import ThreadManager: {e}")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f":x: Error stopping workers: {e}")
        raise typer.Exit(1)