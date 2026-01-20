# Upstream: CLI主入口(ginkgo tasktimer命令调用)
# Downstream: TaskTimer(定时任务调度器)、Rich库(格式化输出)
# Role: TaskTimer CLI提供启动/状态/重载/验证等命令支持定时任务管理


"""
Ginkgo TaskTimer CLI - 定时任务调度器管理命令

TaskTimer 是定时任务调度器，负责：
- 每分钟心跳测试（验证运行状态）
- 每小时 Selector 更新
- 每天 21:00 K线快照
- 自定义定时任务（通过配置文件）

配置文件：~/.ginkgo/task_timer.yml
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import signal
import sys
import time

app = typer.Typer(help=":alarm_clock: TaskTimer - Scheduled Task Manager", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


@app.command()
def start(
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file (default: ~/.ginkgo/task_timer.yml)"),
    node_id: str = typer.Option("task_timer_1", "--node-id", "-n", help="Node ID for this TaskTimer instance"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Run in debug mode with verbose logging"),
):
    """
    :rocket: Start TaskTimer scheduled task manager.

    This will start the TaskTimer with configured cron jobs:
    - heartbeat_test (every minute) - Verify TaskTimer is running
    - update_selector (every hour) - Trigger selector.pick() in ExecutionNode
    - bar_snapshot (daily 21:00) - Push daily bar data via DataManager

    Examples:
      ginkgo tasktimer start
      ginkgo tasktimer start --config /path/to/config.yml
      ginkgo tasktimer start --node-id task_timer_2 --debug
    """
    try:
        from ginkgo.livecore.task_timer import TaskTimer

        # Display TaskTimer info
        console.print(Panel.fit(
            f"[bold cyan]:alarm_clock: TaskTimer[/bold cyan]\n"
            f"[dim]Node ID:[/dim] {node_id}\n"
            f"[dim]Config:[/dim] {config or '~/.ginkgo/task_timer.yml'}\n"
            f"[dim]Features:[/dim]\n"
            f"  • Cron-based scheduled tasks\n"
            f"  • Kafka control commands\n"
            f"  • Redis heartbeat monitoring\n"
            f"  • Hot config reload\n"
            f"[dim]Debug:[/dim] {'On' if debug else 'Off'}",
            title="[bold]Scheduled Task Manager[/bold]",
            border_style="cyan"
        ))

        if debug:
            console.print("\n[yellow]:bug: Debug mode enabled - verbose logging active[/yellow]")

        # Create TaskTimer instance
        timer = TaskTimer(config_path=config, node_id=node_id)

        # Start TaskTimer
        console.print("\n:rocket: [bold green]Starting TaskTimer...[/bold green]")
        console.print(":information: Press Ctrl+C to stop\n")

        success = timer.start()

        if not success:
            console.print("[red]:x: Failed to start TaskTimer[/red]")
            raise typer.Exit(1)

        # Show job status
        jobs_status = timer.get_jobs_status()
        console.print(f":white_check_mark: [green]TaskTimer started with {len(jobs_status)} jobs[/green]")

        if jobs_status:
            table = Table(title="Scheduled Jobs", show_header=True, header_style="bold magenta")
            table.add_column("Job Name", style="cyan", no_wrap=True)
            table.add_column("Next Run", style="green")
            table.add_column("Trigger", style="yellow")

            for job_name, status in jobs_status.items():
                next_run = status.get("next_run_time", "N/A")
                trigger = status.get("trigger", "N/A")
                table.add_row(job_name, str(next_run), trigger)

            console.print(table)

        console.print()

        # Wait for interrupt
        def signal_handler(signum, frame):
            console.print("\n\n:stop_button: [yellow]Stopping TaskTimer...[/yellow]")
            timer.stop()
            console.print(Panel.fit(
                f"[bold green]:white_check_mark: TaskTimer stopped[/bold green]\n"
                f"[dim]All jobs finished gracefully[/dim]",
                title="[bold]Shutdown Complete[/bold]"
            ))
            raise SystemExit(0)

        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Keep running until interrupted
        console.print(":gear: [dim]TaskTimer is running...[/dim]")
        console.print(":information: [dim]Monitoring scheduled jobs[/dim]\n")

        try:
            while timer.is_running:
                time.sleep(1)
        except SystemExit:
            raise
        except Exception as e:
            console.print(f"\n[red]:x: TaskTimer error: {e}[/red]")
            timer.stop()
            raise typer.Exit(1)

    except ImportError as e:
        console.print(f"[red]:x: Failed to import TaskTimer: {e}[/red]")
        console.print(":information: Make sure the livecore module is properly installed")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]:x: Error starting TaskTimer: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    node_id: str = typer.Option("task_timer_1", "--node-id", "-n", help="Node ID to check"),
):
    """
    :bar_chart: Show TaskTimer status.

    Display information about TaskTimer jobs and heartbeat status.
    Checks Redis for heartbeat information.

    Examples:
      ginkgo tasktimer status
      ginkgo tasktimer status --node-id task_timer_2
    """
    try:
        from redis import Redis
        from ginkgo.libs import GCONF
        from datetime import datetime

        redis_client = Redis(
            host=GCONF.REDISHOST,
            port=GCONF.REDISPORT,
            db=0,
            decode_responses=True
        )

        heartbeat_key = f"heartbeat:task_timer:{node_id}"

        # Check heartbeat
        exists = redis_client.exists(heartbeat_key)
        ttl = redis_client.ttl(heartbeat_key)

        console.print(f":information: TaskTimer Status Check")
        console.print(f":information: Node ID: {node_id}\n")

        if exists and ttl > 0:
            # Get heartbeat value
            heartbeat_value = redis_client.get(heartbeat_key)

            console.print(f"[green]:white_check_mark: TaskTimer is [bold]ALIVE[/bold][/green]")
            console.print(f"[dim]Heartbeat TTL: {ttl}s[/dim]")

            # Try to parse JSON heartbeat
            try:
                import json
                heartbeat_data = json.loads(heartbeat_value)

                console.print(f"[dim]Host: {heartbeat_data.get('host', 'N/A')}[/dim]")
                console.print(f"[dim]PID: {heartbeat_data.get('pid', 'N/A')}[/dim]")
                console.print(f"[dim]Jobs: {heartbeat_data.get('jobs_count', 'N/A')}[/dim]")
                console.print(f"[dim]Last Heartbeat: {heartbeat_data.get('timestamp', 'N/A')}[/dim]")
            except:
                console.print(f"[dim]Last Heartbeat: {heartbeat_value}[/dim]")
        else:
            console.print(f"[red]:x: TaskTimer is [bold]DEAD[/bold] or not running[/red]")
            console.print(f"[dim]Heartbeat key not found or expired[/dim]")

    except ImportError as e:
        console.print(f"[red]:x: Failed to import Redis: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]:x: Error checking status: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def reload(
    node_id: str = typer.Option("task_timer_1", "--node-id", "-n", help="Node ID to reload"),
):
    """
    :recycle: Reload TaskTimer configuration.

    Reload the task_timer.yml configuration file and restart all scheduled jobs.
    Requires TaskTimer to be running.

    Examples:
      ginkgo tasktimer reload
      ginkgo tasktimer reload --node-id task_timer_2
    """
    console.print(":information: TaskTimer config reload")
    console.print(":warning: [yellow]This feature requires running TaskTimer as a service[/yellow]")
    console.print(":information: For now, restart TaskTimer manually:")
    console.print("  1. Stop TaskTimer (Ctrl+C)")
    console.print("  2. Edit ~/.ginkgo/task_timer.yml")
    console.print("  3. Start TaskTimer again")


@app.command()
def validate(
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file (default: ~/.ginkgo/task_timer.yml)"),
):
    """
    :checkered_flag: Validate TaskTimer configuration.

    Check if the configuration file is valid and all cron expressions are correct.

    Examples:
      ginkgo tasktimer validate
      ginkgo tasktimer validate --config /path/to/config.yml
    """
    try:
        from ginkgo.livecore.task_timer import TaskTimer

        config_path = config or TaskTimer.CONFIG_PATH

        console.print(f":information: Validating TaskTimer configuration")
        console.print(f":information: Config file: {config_path}\n")

        timer = TaskTimer(config_path=config_path)
        is_valid = timer.validate_config()

        if is_valid:
            console.print("[green]:white_check_mark: Configuration is [bold]VALID[/bold][/green]")

            # Show parsed jobs
            jobs_status = timer.get_jobs_status()
            if jobs_status:
                console.print(f"\n:information: Found {len(jobs_status)} configured jobs:")
                for job_name, status in jobs_status.items():
                    console.print(f"  • [cyan]{job_name}[/cyan] - {status.get('trigger', 'N/A')}")
        else:
            console.print("[red]:x: Configuration is [bold]INVALID[/bold][/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error validating config: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def heartbeat(
    watch: bool = typer.Option(False, "--watch", "-w", help="Watch mode (continuous monitoring)"),
    interval: int = typer.Option(5, "--interval", "-i", help="Refresh interval in seconds (default: 5)"),
):
    """
    :heart_pulse: Monitor TaskTimer heartbeat.

    Display real-time heartbeat information from Redis.
    Shows all LiveCore components' heartbeat status.

    Examples:
      ginkgo tasktimer heartbeat
      ginkgo tasktimer heartbeat --watch
      ginkgo tasktimer heartbeat --watch --interval 10
    """
    try:
        from redis import Redis
        from ginkgo.libs import GCONF
        from datetime import datetime
        import json

        redis_client = Redis(
            host=GCONF.REDISHOST,
            port=GCONF.REDISPORT,
            db=0,
            decode_responses=True
        )

        def print_heartbeat():
            console.print("\n" + "=" * 60)
            console.print("[bold cyan]LiveCore Heartbeat Monitor[/bold cyan]")
            console.print("=" * 60)
            console.print(f"Checked at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

            # Get all heartbeat keys
            heartbeat_keys = redis_client.keys("heartbeat:*")

            if not heartbeat_keys:
                console.print("[yellow]No heartbeat data found. Components may not be running.[/yellow]")
                return

            # Group by component type
            grouped = {}
            for key in heartbeat_keys:
                try:
                    parts = key.split(":")
                    if len(parts) >= 3:
                        component_type = parts[1]
                        component_id = parts[2]

                        if component_type not in grouped:
                            grouped[component_type] = []

                        ttl = redis_client.ttl(key)
                        value = redis_client.get(key)

                        # Parse heartbeat data
                        try:
                            heartbeat_data = json.loads(value)
                            last_time = heartbeat_data.get("timestamp", "N/A")
                            host = heartbeat_data.get("host", "N/A")
                            pid = heartbeat_data.get("pid", "N/A")
                        except:
                            last_time = value
                            host = "N/A"
                            pid = "N/A"

                        is_alive = ttl > 0 and ttl < 40

                        grouped[component_type].append({
                            "id": component_id,
                            "alive": is_alive,
                            "ttl": ttl,
                            "last_time": last_time,
                            "host": host,
                            "pid": pid,
                        })
                except Exception as e:
                    continue

            # Print status by component type
            if not grouped:
                console.print("[yellow]No valid heartbeat data found[/yellow]")
                return

            for component_type, components in sorted(grouped.items()):
                console.print(f"\n[bold]{component_type.upper()}:[/bold]")
                for comp in components:
                    status_icon = "[green]✓[/green]" if comp["alive"] else "[red]✗[/red]"
                    status_text = "[green]ALIVE[/green]" if comp["alive"] else "[red]DEAD[/red]"

                    console.print(f"  {status_icon} {comp['id']}: {status_text}")
                    console.print(f"      TTL: {comp['ttl']}s")
                    console.print(f"      Host: {comp['host']}, PID: {comp['pid']}")

            # Summary
            alive_count = sum(
                1 for components in grouped.values()
                for comp in components if comp["alive"]
            )
            total_count = sum(len(components) for components in grouped.values())
            console.print(f"\n[bold]Summary: {alive_count}/{total_count} components alive[/bold]")

        if watch:
            console.print(":alarm_clock: [bold]Heartbeat Monitor (Watch Mode)[/bold]")
            console.print(":information: Press Ctrl+C to stop\n")

            try:
                while True:
                    print_heartbeat()
                    console.print(f"\n:information: Refreshing in {interval} seconds...")
                    time.sleep(interval)
            except KeyboardInterrupt:
                console.print("\n\n:stop_button: Monitor stopped")
        else:
            print_heartbeat()

    except Exception as e:
        console.print(f"[red]:x: Error monitoring heartbeat: {e}[/red]")
        raise typer.Exit(1)
