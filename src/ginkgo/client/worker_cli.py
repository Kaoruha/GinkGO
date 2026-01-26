# Upstream: CLI主入口(ginkgo worker命令调用)
# Downstream: GinkgoThreadManager(线程管理器run_data_worker/start_multi_worker/reset_all_workers/get_worker_status/get_worker_count)、Rich库(表格/进度显示)、psutil(进程CPU/内存监控)
# Role: Worker进程管理CLI提供状态/启动/停止/重启等命令支持Kafka驱动的分布式worker线程管理






"""
Ginkgo Worker CLI - Worker管理命令
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
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


@app.command("start")
def start_worker(
    notification: bool = typer.Option(False, "--notification", help="Start notification worker for Kafka message processing"),
    data: bool = typer.Option(False, "--data", help="Start data worker for Kafka message processing"),
    group_id: Optional[str] = typer.Option(None, "--group-id", "-g", help="Consumer group ID"),
    auto_offset: str = typer.Option("earliest", "--auto-offset", "-a", help="Kafka auto offset reset (earliest/latest)"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Run worker in debug mode"),
):
    """
    :rocket: Start a specialized worker.

    Examples:
      ginkgo worker start --notification
      ginkgo worker start --data
      ginkgo worker start --notification --group-id custom_group
      ginkgo worker start --data --debug
    """
    try:
        if data:
            _start_data_worker(group_id, auto_offset, debug)
        elif notification:
            _start_notification_worker(group_id, auto_offset, debug)
        else:
            console.print(":x: Please specify worker type (--notification or --data)")
            console.print(":information: Available worker types:")
            console.print("  --notification  Start notification worker (Kafka consumer)")
            console.print("  --data         Start data worker (Kafka consumer)")
            console.print(":information: For LiveCore, use: [cyan]ginkgo livecore start[/cyan]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error starting worker: {e}")
        raise typer.Exit(1)


def _start_notification_worker(
    group_id: Optional[str],
    auto_offset: str,
    debug: bool
):
    """
    Start notification worker for Kafka message processing.

    Args:
        group_id: Consumer group ID
        auto_offset: Kafka auto offset reset policy
        debug: Enable debug mode
    """
    try:
        from ginkgo.notifier.workers.notification_worker import NotificationWorker, WorkerStatus
        from ginkgo import service_hub

        # Get services from service_hub
        notification_service = service_hub.notifier.notification_service()
        record_crud = service_hub.data.cruds.notification_record()

        # Create worker
        worker = NotificationWorker(
            notification_service=notification_service,
            record_crud=record_crud,
            group_id=group_id or "notification_worker_group",
            auto_offset_reset=auto_offset
        )

        # Display worker info
        console.print(Panel.fit(
            f"[bold cyan]:gear: Notification Worker[/bold cyan]\n"
            f"[dim]Group ID:[/dim] {worker._group_id}\n"
            f"[dim]Topic:[/dim] {worker.NOTIFICATIONS_TOPIC}\n"
            f"[dim]Auto Offset:[/dim] {auto_offset}\n"
            f"[dim]Debug:[/dim] {'On' if debug else 'Off'}",
            title="[bold]Worker Configuration[/bold]",
            border_style="cyan"
        ))

        if debug:
            console.print("\n[yellow]:bug: Debug mode enabled - verbose logging active[/yellow]")

        # Start worker
        console.print("\n:rocket: [bold green]Starting worker...[/bold green]")
        console.print(":information: Press Ctrl+C to stop the worker\n")

        if not worker.start():
            console.print("[red]:x: Failed to start worker[/red]")
            raise typer.Exit(1)

        # Wait for interrupt
        try:
            import signal
            import time

            def signal_handler(signum, frame):
                console.print("\n\n:stop_button: [yellow]Stopping worker...[/yellow]")
                console.print(":information: Waiting for messages to finish processing...")

                worker.stop(timeout=30.0)

                # Show final stats
                stats = worker.stats
                console.print(Panel.fit(
                    f"[bold]Final Statistics[/bold]\n"
                    f"[cyan]Messages Consumed:[/cyan] {stats['messages_consumed']}\n"
                    f"[green]Messages Sent:[/green] {stats['messages_sent']}\n"
                    f"[red]Messages Failed:[/red] {stats['messages_failed']}\n"
                    f"[yellow]Messages Retried:[/yellow] {stats['messages_retried']}",
                    title="[bold]Worker Summary[/bold]"
                ))
                console.print(":white_check_mark: Worker stopped successfully")
                raise SystemExit(0)

            # Register signal handlers
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Debug mode: 显示统计信息
            last_shown_count = 0
            last_shown_time = time.time()
            stats_interval = 60  # 每60秒显示一次
            message_interval = 10  # 每消费10条消息显示一次

            # Keep running until interrupted
            while worker.is_running:
                time.sleep(1)

                # Debug mode: 周期性显示统计
                if debug:
                    current_time = time.time()
                    current_count = worker.stats['messages_consumed']

                    # 检查是否需要显示统计
                    should_show = False
                    reason = ""

                    # 条件1: 每消费 message_interval 条消息显示一次
                    if current_count > 0 and current_count >= last_shown_count + message_interval:
                        should_show = True
                        reason = f"every {message_interval} messages"

                    # 条件2: 每隔 stats_interval 秒显示一次
                    elif current_time - last_shown_time >= stats_interval:
                        should_show = True
                        reason = f"every {stats_interval}s"

                    if should_show:
                        stats = worker.stats
                        console.print(f"[dim]:memo: [{reason}] Processed: {stats['messages_consumed']} | "
                                   f"Sent: {stats['messages_sent']} | "
                                   f"Failed: {stats['messages_failed']}[/dim]")
                        last_shown_count = current_count
                        last_shown_time = current_time

        except SystemExit:
            raise
        except Exception as e:
            console.print(f"\n[red]:x: Worker error: {e}[/red]")
            worker.stop(timeout=5.0)
            raise typer.Exit(1)

    except ImportError as e:
        console.print(f"[red]:x: Failed to import NotificationWorker: {e}[/red]")
        console.print(":information: Make sure the notifier module is properly installed")
        raise typer.Exit(1)


def _start_data_worker(
    group_id: Optional[str],
    auto_offset: str,
    debug: bool
):
    """
    Start data worker for Kafka message processing.

    Args:
        group_id: Consumer group ID
        auto_offset: Kafka auto offset reset policy
        debug: Enable debug mode
    """
    try:
        from ginkgo.data.worker.worker import DataWorker
        from ginkgo import service_hub
        from ginkgo.enums import WORKER_STATUS_TYPES

        # Get services from service_hub
        bar_crud = service_hub.data.cruds.bar()

        # Create worker
        worker = DataWorker(
            bar_crud=bar_crud,
            group_id=group_id or "data_worker_group",
            auto_offset_reset=auto_offset
        )

        # Display worker info
        console.print(Panel.fit(
            f"[bold cyan]:gear: Data Worker[/bold cyan]\n"
            f"[dim]Group ID:[/dim] {worker._group_id}\n"
            f"[dim]Topic:[/dim] ginkgo.live.control.commands\n"
            f"[dim]Auto Offset:[/dim] {auto_offset}\n"
            f"[dim]Debug:[/dim] {'On' if debug else 'Off'}",
            title="[bold]Worker Configuration[/bold]",
            border_style="cyan"
        ))

        if debug:
            console.print("\n[yellow]:bug: Debug mode enabled - verbose logging active[/yellow]")

        # Start worker
        console.print("\n:rocket: [bold green]Starting worker...[/bold green]")
        console.print(":information: Press Ctrl+C to stop the worker\n")

        if not worker.start():
            console.print("[red]:x: Failed to start worker[/red]")
            raise typer.Exit(1)

        # Wait for interrupt
        try:
            import signal
            import time

            def signal_handler(signum, frame):
                console.print("\n\n:stop_button: [yellow]Stopping worker...[/yellow]")
                console.print(":information: Waiting for messages to finish processing...")

                worker.stop(timeout=30.0)

                # Show final stats
                stats = worker.get_stats()
                console.print(Panel.fit(
                    f"[bold]Final Statistics[/bold]\n"
                    f"[cyan]Messages Processed:[/cyan] {stats.get('messages_processed', 0)}\n"
                    f"[green]Bars Written:[/green] {stats.get('bars_written', 0)}\n"
                    f"[red]Errors:[/red] {stats.get('errors', 0)}",
                    title="[bold]Worker Summary[/bold]"
                ))
                console.print(":white_check_mark: Worker stopped successfully")
                raise SystemExit(0)

            # Register signal handlers
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Debug mode: 显示统计信息
            last_shown_count = 0
            last_shown_time = time.time()
            stats_interval = 60  # 每60秒显示一次
            message_interval = 10  # 每处理10条消息显示一次

            # Keep running until interrupted
            while worker.is_running:
                time.sleep(1)

                # Debug mode: 周期性显示统计
                if debug:
                    current_time = time.time()
                    current_count = worker.get_stats().get('messages_processed', 0)

                    # 检查是否需要显示统计
                    should_show = False
                    reason = ""

                    # 条件1: 每消费 message_interval 条消息显示一次
                    if current_count > 0 and current_count >= last_shown_count + message_interval:
                        should_show = True
                        reason = f"every {message_interval} messages"

                    # 条件2: 每隔 stats_interval 秒显示一次
                    elif current_time - last_shown_time >= stats_interval:
                        should_show = True
                        reason = f"every {stats_interval}s"

                    if should_show:
                        stats = worker.get_stats()
                        console.print(f"[dim]:memo: [{reason}] Processed: {stats.get('messages_processed', 0)} | "
                                   f"Bars: {stats.get('bars_written', 0)} | "
                                   f"Errors: {stats.get('errors', 0)}[/dim]")
                        last_shown_count = current_count
                        last_shown_time = current_time

        except SystemExit:
            raise
        except Exception as e:
            console.print(f"\n[red]:x: Worker error: {e}[/red]")
            worker.stop(timeout=5.0)
            raise typer.Exit(1)

    except ImportError as e:
        console.print(f"[red]:x: Failed to import DataWorker: {e}[/red]")
        console.print(":information: Make sure the data.worker module is properly installed")
        raise typer.Exit(1)