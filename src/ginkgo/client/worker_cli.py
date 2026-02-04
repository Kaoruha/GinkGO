"""
Ginkgo Worker CLI - Worker管理命令
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

app = typer.Typer(help=":gear: Worker management", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


# ==================== Data Worker 子命令 ====================

data_app = typer.Typer(help=":page_facing_up: DataWorker management", rich_markup_mode="rich")


@data_app.command("run")
def data_run(
    debug: bool = typer.Option(False, "--debug", "-d", help="Run worker in debug mode"),
):
    """
    :gear: Run a data worker in foreground.

    Examples:
      ginkgo worker data run
      ginkgo worker data run --debug
    """
    try:
        from ginkgo.libs.core.threading import GinkgoThreadManager
        from ginkgo.libs.core.logger import GinkgoLogger

        if debug:
            print("Starting worker in debug mode...")

        # 创建ThreadManager实例
        gtm = GinkgoThreadManager()

        # 在前台运行单个worker
        console.print(":gear: Starting data worker in foreground mode...")
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


@data_app.command("status")
def data_status(
    pid: Optional[str] = typer.Option(None, "--pid", "-p", help="Show status for specific worker PID"),
    detailed: bool = typer.Option(False, "--detailed", help="Show detailed worker information"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw data as JSON"),
):
    """
    :bar_chart: Show data worker status.

    Examples:
      ginkgo worker data status
      ginkgo worker data status --pid 123
      ginkgo worker data status --detailed
      ginkgo worker data status --raw
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
            worker_list = gtm.get_workers_status()

            if raw:
                import json
                console.print(json.dumps(worker_list, indent=2, ensure_ascii=False, default=str))
                return

            # 汇总统计
            total_workers = len(worker_list)
            active_workers = len([w for w in worker_list if w.get("status") == "running"])

            # 创建汇总表格
            table = Table(title=":gear: Data Worker Status Summary")
            table.add_column("Metric", style="cyan", width=25)
            table.add_column("Count", justify="center", style="green")
            table.add_column("Details", style="dim")

            table.add_row("Total Workers", str(total_workers), f"{active_workers} active")
            table.add_row("Status", "OK" if active_workers > 0 else "IDLE", f"{total_workers - active_workers} idle")

            console.print(table)

            if detailed and total_workers > 0:
                console.print("\n")
                detailed_table = Table(title=":gear: All Data Workers")
                detailed_table.add_column("PID", justify="right", style="cyan")
                detailed_table.add_column("Status")
                detailed_table.add_column("CPU", justify="right")
                detailed_table.add_column("Memory", justify="right")
                detailed_table.add_column("Tasks", justify="center")

                for w in worker_list:
                    pid = w.get("pid", "N/A")
                    status = w.get("status", "unknown")
                    cpu = f"{w.get('cpu_percent', 0):.1f}%" if "cpu_percent" in w else "N/A"
                    mem = f"{w.get('memory_mb', 0):.1f} MB" if "memory_mb" in w else "N/A"
                    tasks = w.get("tasks", "N/A")

                    # 状态样式
                    if status == "running":
                        status_style = "green"
                    elif status == "idle":
                        status_style = "yellow"
                    else:
                        status_style = "red"

                    detailed_table.add_row(str(pid), f"[{status_style}]{status}[/{status_style}]", cpu, mem, str(tasks))

                console.print(detailed_table)

    except ImportError as e:
        console.print(f":x: Failed to import ThreadManager: {e}")
        raise typer.Exit(1)


# ==================== Backtest Worker 子命令 ====================

backtest_app = typer.Typer(help=":backtest: BacktestWorker management", rich_markup_mode="rich")


@backtest_app.command("run")
def backtest_run(
    worker_id: str = typer.Option(None, "--worker-id", "-w", help="BacktestWorker unique identifier"),
    max_tasks: int = typer.Option(5, "--max-tasks", "-m", help="Maximum concurrent backtest tasks"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Run in debug mode"),
):
    """
    :backtest: Run a backtest worker in foreground.

    Examples:
      ginkgo worker backtest run
      ginkgo worker backtest run --worker-id worker_1
      ginkgo worker backtest run --max-tasks 10
      ginkgo worker backtest run --debug
    """
    # 使用环境变量或默认值
    if worker_id is None:
        import os
        worker_id = os.getenv("GINKGO_WORKER_ID")
    if worker_id is None:
        import socket
        worker_id = f"backtest_worker_{socket.gethostname()}"

    try:
        from ginkgo.workers.backtest_worker.node import BacktestWorker

        # 显示BacktestWorker信息
        console.print(Panel.fit(
            f"[bold cyan]:backtest: BacktestWorker[/bold cyan]\n"
            f"[dim]Configuration:[/dim]\n"
            f"  • Worker ID: {worker_id}\n"
            f"  • Max Tasks: {max_tasks}\n"
            f"[dim]Features:[/dim]\n"
            f"  • Kafka task assignment\n"
            f"  • Multi-task parallel execution\n"
            f"  • Progress tracking (2s interval)\n"
            f"  • Redis heartbeat (30s TTL)\n"
            f"[dim]Debug:[/dim] {'On' if debug else 'Off'}",
            title="[bold]Backtest Execution Engine[/bold]",
            border_style="cyan"
        ))

        if debug:
            console.print("\n[yellow]:bug: Debug mode enabled[/yellow]")

        # 创建BacktestWorker实例
        console.print(f"\n:rocket: [bold green]Creating BacktestWorker '{worker_id}'...[/bold green]")
        worker = BacktestWorker(worker_id=worker_id)
        worker.max_backtests = max_tasks

        # 注册信号处理
        import signal
        def signal_handler(sig, frame):
            console.print("\n\n[yellow]:warning: Received stop signal, shutting down...[/yellow]")
            worker.stop()
            import sys
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # 启动Worker
        console.print(f"\n:rocket: [bold green]Starting BacktestWorker...[/bold green]")
        console.print(":information: Press Ctrl+C to stop\n")

        worker.start()

        console.print(":white_check_mark: [green]BacktestWorker started successfully[/green]")
        console.print(f":information: Worker ID: {worker.worker_id}")
        console.print(f":information: Max tasks: {worker.max_backtests}")
        console.print(f":information: Ready to receive tasks from 'backtest.assignments' topic\n")

        # 保持运行
        console.print("[dim]Running... (Press Ctrl+C to stop)[/dim]\n")
        import time
        try:
            while worker.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n\n[yellow]:warning: Shutting down...[/yellow]")
            worker.stop()
            console.print("[green]:white_check_mark: BacktestWorker stopped[/green]")

    except Exception as e:
        console.print(f"\n[red]:x: Failed to start BacktestWorker: {e}[/red]")
        raise typer.Exit(code=1)


@backtest_app.command("status")
def backtest_status(
    worker_id: Optional[str] = typer.Option(None, "--worker-id", "-w", help="Worker ID to check"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw data as JSON"),
):
    """
    :bar_chart: Show backtest worker status.

    Examples:
      ginkgo worker backtest status
      ginkgo worker backtest status --worker-id worker_1
      ginkgo worker backtest status --raw
    """
    try:
        from ginkgo.data.drivers import create_redis_connection
        import json

        redis = create_redis_connection()

        if worker_id:
            # 显示特定worker的状态
            key = f"backtest:worker:{worker_id}"
            data = redis.get(key)

            if not data:
                console.print(f":x: BacktestWorker '{worker_id}' not found (offline or never started)")
                return

            status = json.loads(data)

            # Raw output mode
            if raw:
                console.print(json.dumps(status, indent=2, ensure_ascii=False, default=str))
                return

            # 显示状态面板
            console.print(Panel.fit(
                f"[bold cyan]BacktestWorker Status[/bold cyan]\n\n"
                f"[dim]Worker ID:[/dim] {status['worker_id']}\n"
                f"[dim]Status:[/dim] {'[green]:white_check_mark: Running[/green]' if status['status'] == 'running' else '[red]:x: Stopped[/red]'}\n"
                f"[dim]Tasks:[/dim] {status['running_tasks']} / {status['max_tasks']}\n"
                f"[dim]Started At:[/dim] {status.get('started_at', 'N/A')}\n"
                f"[dim]Last Heartbeat:[/dim] {status.get('last_heartbeat', 'N/A')}\n",
                border_style="cyan"
            ))
        else:
            # 显示所有backtest worker的状态
            pattern = "backtest:worker:*"
            keys = redis.keys(pattern)

            if raw:
                workers = []
                for key in keys:
                    workers.append(json.loads(redis.get(key)))
                console.print(json.dumps(workers, indent=2, ensure_ascii=False, default=str))
                return

            if not keys:
                console.print("[yellow]:warning: No active BacktestWorkers found[/yellow]")
                return

            # 汇总统计
            workers = []
            for key in keys:
                workers.append(json.loads(redis.get(key)))

            total_workers = len(workers)
            active_workers = len([w for w in workers if w.get("status") == "running"])

            # 创建汇总表格
            table = Table(title=":gear: BacktestWorker Status Summary")
            table.add_column("Metric", style="cyan", width=25)
            table.add_column("Count", justify="center", style="green")
            table.add_column("Details", style="dim")

            table.add_row("Total Workers", str(total_workers), f"{active_workers} active")
            table.add_row("Status", "OK" if active_workers > 0 else "IDLE", f"{total_workers - active_workers} idle")

            console.print(table)

            # 详细worker列表
            if total_workers > 0:
                console.print("\n")
                detailed_table = Table(title=":gear: All BacktestWorkers")
                detailed_table.add_column("Worker ID", style="cyan")
                detailed_table.add_column("Status")
                detailed_table.add_column("Tasks", justify="center")
                detailed_table.add_column("Max Tasks", justify="center")
                detailed_table.add_column("Last Heartbeat", style="dim")

                for w in workers:
                    wid = w.get("worker_id", "N/A")
                    status = w.get("status", "unknown")
                    running_tasks = w.get("running_tasks", 0)
                    max_tasks = w.get("max_tasks", 0)
                    last_heartbeat = w.get("last_heartbeat", "N/A")

                    # 状态样式
                    if status == "running":
                        status_display = "[green]:white_check_mark: Running[/green]"
                    else:
                        status_display = "[red]:x: Stopped[/red]"

                    detailed_table.add_row(
                        str(wid),
                        status_display,
                        f"{running_tasks}",
                        f"{max_tasks}",
                        last_heartbeat[:19] if last_heartbeat != "N/A" else "N/A"
                    )

                console.print(detailed_table)

    except Exception as e:
        console.print(f"\n[red]:x: Error getting status: {e}[/red]")
        raise typer.Exit(code=1)


# ==================== 注册子命令 ====================

app.add_typer(data_app, name="data", help=":page_facing_up: DataWorker")
app.add_typer(backtest_app, name="backtest", help=":backtest: BacktestWorker")
