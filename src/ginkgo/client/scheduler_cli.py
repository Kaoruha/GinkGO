# Upstream: Scheduler（调度器）
# Downstream: Redis（状态存储）、Kafka（调度更新发布）
# Role: Scheduler CLI提供调度器管理命令支持


"""
Ginkgo Scheduler CLI - Portfolio调度器管理命令

Scheduler 是实盘交易的调度组件，负责：
- 动态分配 Portfolio 到 ExecutionNode
- ExecutionNode 心跳检测
- 负载均衡和故障恢复
- Portfolio 迁移管理
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON
import json
from datetime import datetime
from ginkgo.interfaces.kafka_topics import KafkaTopics

app = typer.Typer(help=":calendar: Scheduler - Portfolio Dynamic Scheduler", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


@app.command()
def start(
    interval: int = typer.Option(30, "--interval", "-i", help="Schedule interval in seconds (default: 30)"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Run in debug mode with verbose logging"),
):
    """
    :rocket: Start Scheduler for Portfolio dynamic scheduling.

    Scheduler monitors ExecutionNode health and redistributes Portfolios
    for load balancing and fault tolerance.

    Examples:
      ginkgo scheduler start
      ginkgo scheduler start --interval 60
      ginkgo scheduler start --debug
    """
    try:
        from ginkgo.livecore.scheduler import Scheduler
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo.data.crud import RedisCRUD

        # Display Scheduler info
        console.print(Panel.fit(
            f"[bold cyan]:calendar: Scheduler[/bold cyan]\\n"
            f"[dim]Configuration:[/dim]\\n"
            f"  • Schedule Interval: {interval}s\\n"
            f"  • Debug Mode: {'On' if debug else 'Off'}\\n"
            f"[dim]Features:[/dim]\\n"
            f"  • Heartbeat monitoring (TTL=30s)\\n"
            f"  • Load balancing algorithm\\n"
            f"  • Automatic failover\\n"
            f"  • Portfolio migration\\n",
            title="[bold]Portfolio Dynamic Scheduler[/bold]",
            border_style="cyan"
        ))

        if debug:
            console.print("\\n[yellow]:bug: Debug mode enabled - verbose logging active[/yellow]\\n")

        # Get Redis client
        console.print(f":hourglass: Connecting to Redis...")
        redis_crud = RedisCRUD()
        redis_client = redis_crud.redis
        if not redis_client:
            console.print("[red]:x: Failed to connect to Redis[/red]")
            raise typer.Exit(1)
        console.print(":white_check_mark: Redis connected")

        # Create Kafka producer
        console.print(f":satellite: Connecting to Kafka...")
        kafka_producer = GinkgoProducer()
        console.print(":white_check_mark: Kafka connected")

        # Create Scheduler instance
        console.print(f"\\n:rocket: [bold green]Creating Scheduler...[/bold green]")
        scheduler = Scheduler(
            redis_client=redis_client,
            kafka_producer=kafka_producer,
            schedule_interval=interval,
            node_id="cli_scheduler"
        )

        # Start Scheduler
        console.print(f":rocket: [bold green]Starting Scheduler...[/bold green]")
        console.print(":information: Press Ctrl+C to stop\\n")

        scheduler.start()

        console.print(":white_check_mark: [green]Scheduler started successfully[/green]")
        console.print(f":information: Node ID: {scheduler.node_id}")
        console.print(f":information: Schedule Interval: {scheduler.schedule_interval}s")
        console.print()

        # Wait for interrupt
        try:
            import time

            def signal_handler(signum, frame):
                console.print("\\n\\n:stop_button: [yellow]Stopping Scheduler...[/yellow]")
                scheduler.stop()

                # Show statistics
                healthy_nodes = scheduler._get_healthy_nodes()
                console.print(Panel.fit(
                    f"[bold green]:white_check_mark: Scheduler stopped[/bold green]\\n"
                    f"[dim]Runtime Statistics:[/dim]\\n"
                    f"  • Healthy Nodes: {len(healthy_nodes)}\\n"
                    f"  • Schedule Interval: {scheduler.schedule_interval}s",
                    title="[bold]Shutdown Complete[/bold]"
                ))
                raise SystemExit(0)

            # Register signal handlers
            import signal
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Keep running until interrupted
            console.print(":gear: [dim]Scheduler is running...[/dim]")
            console.print(":information: [dim]Monitoring ExecutionNode heartbeats[/dim]\\n")

            while scheduler.is_running:
                time.sleep(1)

                # Debug mode: 显示调度信息
                if debug and scheduler.total_event_count > 0:
                    healthy_nodes = scheduler._get_healthy_nodes()
                    console.print(
                        f"[dim]:memo: Nodes: {len(healthy_nodes)} | "
                        f"Interval: {scheduler.schedule_interval}s[/dim]"
                    )

        except SystemExit:
            raise
        except Exception as e:
            console.print(f"\\n[red]:x: Scheduler error: {e}[/red]")
            scheduler.stop()
            raise typer.Exit(1)

    except ImportError as e:
        console.print(f"[red]:x: Failed to import Scheduler: {e}[/red]")
        console.print(":information: Make sure the scheduler module is properly installed")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]:x: Error starting Scheduler: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status():
    """
    :bar_chart: Show Scheduler status.

    Display Scheduler information from Redis state.
    """
    console.print(":information: Scheduler status check")

    try:
        from ginkgo.data.crud import RedisCRUD

        redis_crud = RedisCRUD()
        redis_client = redis_crud.redis

        # Get scheduler info from Redis
        # Check for heartbeat keys to find active nodes
        heartbeat_keys = redis_client.keys("heartbeat:node:*")

        if not heartbeat_keys:
            console.print("[yellow]:warning: No ExecutionNodes found (no heartbeats)[/yellow]")
            return

        # Create table
        table = Table(title=":calendar: Scheduler Status", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan", width=30)
        table.add_column("Value", style="green")

        # Count healthy nodes
        healthy_count = len(heartbeat_keys)
        table.add_row("Healthy ExecutionNodes", str(healthy_count))

        # Get current schedule plan
        plan_data = redis_client.hgetall("schedule:plan")
        if plan_data:
            table.add_row("Scheduled Portfolios", str(len(plan_data)))
        else:
            table.add_row("Scheduled Portfolios", "0")

        # Get node metrics
        metric_keys = redis_client.keys("node:metrics:*")
        total_portfolios = 0
        total_queue_size = 0

        for key in metric_keys:
            metrics = redis_client.hgetall(key)
            if metrics:
                total_portfolios += int(metrics.get(b'portfolio_count', 0))
                total_queue_size += int(metrics.get(b'queue_size', 0))

        if metric_keys:
            table.add_row("Total Portfolios Running", str(total_portfolios))
            table.add_row("Average Queue Size", str(total_queue_size // len(metric_keys)))

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]:x: Error getting Scheduler status: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def plan():
    """
    :clipboard: Show current schedule plan.

    Display Portfolio to ExecutionNode assignments.
    """
    console.print(":information: Current schedule plan")

    try:
        from ginkgo.data.crud import RedisCRUD

        redis_crud = RedisCRUD()
        redis_client = redis_crud.redis

        # Get schedule plan
        plan_data = redis_client.hgetall("schedule:plan")

        if not plan_data:
            console.print("[yellow]:warning: No schedule plan found[/yellow]")
            return

        # Create table
        table = Table(title=":calendar: Schedule Plan", show_header=True, header_style="bold magenta")
        table.add_column("Portfolio ID", style="cyan", no_wrap=False)
        table.add_column("ExecutionNode", style="green")

        for portfolio_id_bytes, node_id_bytes in plan_data.items():
            portfolio_id = portfolio_id_bytes.decode('utf-8')
            node_id = node_id_bytes.decode('utf-8')

            # Shorten IDs for display
            portfolio_short = portfolio_id[:8] + "..." if len(portfolio_id) > 11 else portfolio_id
            node_short = node_id[:20] if len(node_id) > 20 else node_id

            table.add_row(portfolio_short, node_short)

        console.print(table)
        console.print(f"\\n:information: Total portfolios scheduled: [bold]{len(plan_data)}[/bold]")

    except Exception as e:
        console.print(f"[red]:x: Error getting schedule plan: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def nodes():
    """
    :desktop_computer: List healthy ExecutionNodes.

    Display all ExecutionNodes with active heartbeats and their metrics.
    """
    console.print(":information: Healthy ExecutionNodes")

    try:
        from ginkgo.data.crud import RedisCRUD

        redis_crud = RedisCRUD()
        redis_client = redis_crud.redis

        # Get all heartbeat keys
        heartbeat_keys = redis_client.keys("heartbeat:node:*")

        if not heartbeat_keys:
            console.print("[yellow]:warning: No healthy ExecutionNodes found[/yellow]")
            console.print(":information: Nodes may be offline or Scheduler not running")
            return

        # Create table
        table = Table(title=":desktop_computer: ExecutionNode Status", show_header=True, header_style="bold magenta")
        table.add_column("Node ID", style="cyan", no_wrap=False)
        table.add_column("Portfolios", justify="right", style="green")
        table.add_column("Queue Size", justify="right", style="yellow")
        table.add_column("CPU Usage", justify="right", style="blue")
        table.add_column("Last Heartbeat", style="dim")

        for key in heartbeat_keys:
            node_id = key.decode('utf-8').replace("heartbeat:node:", "")

            # Get heartbeat TTL
            ttl = redis_client.ttl(key)

            # Get metrics
            metrics_key = f"node:metrics:{node_id}"
            metrics = redis_client.hgetall(metrics_key)

            if metrics:
                portfolio_count = metrics.get(b'portfolio_count', b'0').decode('utf-8')
                queue_size = metrics.get(b'queue_size', b'0').decode('utf-8')
                cpu_usage = metrics.get(b'cpu_usage', b'0.0').decode('utf-8')
            else:
                portfolio_count = "0"
                queue_size = "0"
                cpu_usage = "0.0"

            # Format heartbeat time
            heartbeat_time = f"{ttl}s ago" if ttl > 0 else "expired"

            # Shorten node ID for display
            node_short = node_id[:30] if len(node_id) > 30 else node_id

            table.add_row(node_short, portfolio_count, queue_size, f"{cpu_usage}%", heartbeat_time)

        console.print(table)
        console.print(f"\\n:information: Total healthy nodes: [bold]{len(heartbeat_keys)}[/bold]")

    except Exception as e:
        console.print(f"[red]:x: Error listing ExecutionNodes: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def migrate(
    portfolio_id: str = typer.Argument(..., help="Portfolio ID to migrate"),
    target_node: str = typer.Option(None, "--target", "-t", help="Target ExecutionNode ID (if not specified, Scheduler will choose)"),
    force: bool = typer.Option(False, "--force", "-f", help="Force migration without confirmation"),
):
    """
    :left_right_arrow: Migrate a Portfolio to another ExecutionNode.

    Manually trigger Portfolio migration for load balancing or maintenance.

    Examples:
      ginkgo scheduler migrate portfolio_uuid --target node_1
      ginkgo scheduler migrate portfolio_uuid --force
    """
    try:
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo.data.crud import RedisCRUD
        from ginkgo.interfaces.dtos import ScheduleUpdateDTO

        console.print(f":information: Migrating portfolio [cyan]{portfolio_id[:8]}...[/cyan]")

        # If no target specified, get recommendation from Scheduler
        if not target_node:
            console.print(":information: No target specified, Scheduler will choose optimal node")
            # TODO: Implement load-based recommendation
            console.print("[yellow]:warning: Auto-selection not implemented, please specify --target[/yellow]")
            raise typer.Exit(1)

        # Create migration command using DTO
        migration_dto = ScheduleUpdateDTO(
            command=ScheduleUpdateDTO.Commands.PORTFOLIO_MIGRATE,
            portfolio_id=portfolio_id,
            target_node=target_node,
            source="cli"
        )

        # Show migration plan
        console.print(f"\\n:clipboard: Migration Plan:")
        console.print(f"  • Portfolio: [cyan]{portfolio_id}[/cyan]")
        console.print(f"  • Target Node: [green]{target_node}[/green]")
        console.print(f"  • Timestamp: {migration_dto.timestamp}")

        # Confirm unless force
        if not force:
            console.print("\\n[yellow]:warning: This will migrate the portfolio to a different node[/yellow]")
            confirm = typer.confirm("Are you sure you want to proceed?", default=False)
            if not confirm:
                console.print("[red]:x: Migration cancelled[/red]")
                raise typer.Exit(0)

        # Send migration command to Kafka
        console.print(f"\\n:satellite: Sending migration command to Kafka...")
        producer = GinkgoProducer()
        success = producer.send(KafkaTopics.SCHEDULE_UPDATES, migration_dto.model_dump_json())

        if success:
            console.print(":white_check_mark: [green]Migration command sent successfully[/green]")
            console.print(f":information: Portfolio {portfolio_id[:8]}... will migrate to {target_node}")
            console.print(":information: Check status with: [cyan]ginkgo scheduler plan[/cyan]")
        else:
            console.print("[red]:x: Failed to send migration command[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error migrating portfolio: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def reload(
    portfolio_id: str = typer.Argument(..., help="Portfolio ID to reload"),
    force: bool = typer.Option(False, "--force", "-f", help="Force reload without confirmation"),
):
    """
    :arrows_counterclockwise: Reload Portfolio configuration.

    Trigger a graceful reload of Portfolio configuration from database.

    Examples:
      ginkgo scheduler reload portfolio_uuid
      ginkgo scheduler reload portfolio_uuid --force
    """
    try:
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo.interfaces.dtos import ScheduleUpdateDTO

        console.print(f":information: Reloading portfolio [cyan]{portfolio_id[:8]}...[/cyan]")

        # Create reload command using DTO
        reload_dto = ScheduleUpdateDTO(
            command=ScheduleUpdateDTO.Commands.PORTFOLIO_RELOAD,
            portfolio_id=portfolio_id,
            source="cli"
        )

        # Show reload plan
        console.print(f"\\n:clipboard: Reload Plan:")
        console.print(f"  • Portfolio: [cyan]{portfolio_id}[/cyan]")
        console.print(f"  • Action: Reload from database")
        console.print(f"  • Timestamp: {reload_dto.timestamp}")

        # Confirm unless force
        if not force:
            console.print("\\n[yellow]:warning: This will reload the portfolio configuration[/yellow]")
            console.print("[yellow]:warning: The portfolio will be temporarily stopped[/yellow]")
            confirm = typer.confirm("Are you sure you want to proceed?", default=False)
            if not confirm:
                console.print("[red]:x: Reload cancelled[/red]")
                raise typer.Exit(0)

        # Send reload command to Kafka
        console.print(f"\\n:satellite: Sending reload command to Kafka...")
        producer = GinkgoProducer()
        success = producer.send(KafkaTopics.SCHEDULE_UPDATES, reload_dto.model_dump_json())

        if success:
            console.print(":white_check_mark: [green]Reload command sent successfully[/green]")
            console.print(f":information: Portfolio {portfolio_id[:8]}... will reload from database")
            console.print(":information: Check status with: [cyan]ginkgo portfolio status {portfolio_id}[/cyan]")
        else:
            console.print("[red]:x: Failed to send reload command[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error reloading portfolio: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def recalculate(
    force: bool = typer.Option(False, "--force", "-f", help="Force recalculation without confirmation"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show plan without executing"),
):
    """
    :chart_with_upwards_trend: Recalculate schedule plan (load balancing).

    Send a recalculate command to the Scheduler via Kafka.

    Examples:
      ginkgo scheduler recalculate
      ginkgo scheduler recalculate --dry-run
      ginkgo scheduler recalculate --force
    """
    try:
        from ginkgo.data.crud import RedisCRUD
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer

        console.print(f":chart: [bold]Sending recalculate command to Scheduler...[/bold]")

        # Show current state
        redis_crud = RedisCRUD()
        redis_client = redis_crud.redis

        # Get healthy nodes
        heartbeat_keys = redis_client.keys("heartbeat:node:*")
        healthy_nodes = []
        for key in heartbeat_keys:
            node_id = key.decode('utf-8').split(":")[-1]
            ttl = redis_client.ttl(key)
            if ttl > 0:
                healthy_nodes.append(node_id)

        # Get current plan
        plan_key = "schedule:plan"
        current_plan_json = redis_client.get(plan_key)
        current_plan = json.loads(current_plan_json) if current_plan_json else {}

        # Show current state
        console.print(f"\n:clipboard: [bold]Current State:[/bold]")
        console.print(f"  • Healthy Nodes: {len(healthy_nodes)}")
        console.print(f"  • Scheduled Portfolios: {len(current_plan)}")

        if len(healthy_nodes) == 0:
            console.print("[red]:x: No healthy nodes available[/red]")
            raise typer.Exit(1)

        if dry_run:
            console.print("\n:information: [dim]Dry run mode - command will not be sent[/dim]")
            raise typer.Exit(0)

        # Confirm unless force
        if not force:
            console.print("\n[yellow]:warning: This will trigger load balancing recalculation[/yellow]")
            confirm = typer.confirm("Are you sure you want to proceed?", default=False)
            if not confirm:
                console.print("[red]:x: Recalculation cancelled[/red]")
                raise typer.Exit(0)

        # Send recalculate command to Kafka
        console.print(f"\n:satellite: Sending recalculate command to [cyan]scheduler.commands[/cyan]...")

        from ginkgo.interfaces.dtos import SchedulerCommandDTO

        producer = GinkgoProducer()
        command_dto = SchedulerCommandDTO(
            command=SchedulerCommandDTO.Commands.RECALCULATE,
            params={"force": force},
            source="cli"
        )

        success = producer.send("scheduler.commands", command_dto.model_dump_json())

        if success:
            console.print(f":white_check_mark: [green]Recalculate command sent successfully[/green]")
            console.print(f":information: Scheduler will execute load balancing immediately")
        else:
            console.print("[red]:x: Failed to send recalculate command[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error recalculating schedule: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def schedule(
    force: bool = typer.Option(False, "--force", "-f", help="Force schedule without confirmation"),
):
    """
    :fast_forward: Trigger immediate schedule run.

    Send a schedule command to the Scheduler via Kafka to assign
    unassigned Portfolios to healthy ExecutionNodes.

    Examples:
      ginkgo scheduler schedule
      ginkgo scheduler schedule --force
    """
    try:
        from ginkgo.data.crud import RedisCRUD
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo import services

        console.print(f":fast_forward: [bold]Triggering immediate schedule run...[/bold]")

        # Get Redis client
        redis_crud = RedisCRUD()
        redis_client = redis_crud.redis

        # Get healthy nodes
        heartbeat_keys = redis_client.keys("heartbeat:node:*")
        healthy_nodes = []
        for key in heartbeat_keys:
            node_id = key.decode('utf-8').split(":")[-1]
            ttl = redis_client.ttl(key)
            if ttl > 0:
                healthy_nodes.append(node_id)

        console.print(f"\n:information: Healthy nodes: {len(healthy_nodes)}")

        if len(healthy_nodes) == 0:
            console.print("[red]:x: No healthy nodes available[/red]")
            raise typer.Exit(1)

        # Get current plan
        plan_key = "schedule:plan"
        current_plan_json = redis_client.get(plan_key)
        current_plan = json.loads(current_plan_json) if current_plan_json else {}

        # Get all live portfolios from database
        console.print(f"\n:database: Fetching live portfolios from database...")
        portfolio_service = services.data.portfolio_service()
        result = portfolio_service.get(is_live=True)

        if not result.is_success():
            console.print(f"[red]:x: Failed to fetch portfolios: {result.error}[/red]")
            raise typer.Exit(1)

        all_portfolios = result.data
        console.print(f":information: Found {len(all_portfolios)} live portfolios")

        # Find unassigned portfolios
        assigned_portfolio_ids = set(current_plan.keys())
        unassigned_portfolios = []

        for portfolio_model in all_portfolios:
            portfolio_id = portfolio_model.uuid
            if portfolio_id not in assigned_portfolio_ids:
                unassigned_portfolios.append(portfolio_model)

        console.print(f":information: Unassigned portfolios: {len(unassigned_portfolios)}")

        if len(unassigned_portfolios) == 0:
            console.print("\n:white_check_mark: [green]All portfolios are already assigned[/green]")
            raise typer.Exit(0)

        # Confirm unless force
        if not force:
            console.print(f"\n[yellow]:warning: This will assign {len(unassigned_portfolios)} portfolios[/yellow]")
            confirm = typer.confirm("Are you sure you want to proceed?", default=False)
            if not confirm:
                console.print("[red]:x: Schedule cancelled[/red]")
                raise typer.Exit(0)

        # Send schedule command to Kafka
        console.print(f"\n:satellite: Sending schedule command to [cyan]scheduler.commands[/cyan]...")

        from ginkgo.interfaces.dtos import SchedulerCommandDTO

        producer = GinkgoProducer()
        command_dto = SchedulerCommandDTO(
            command=SchedulerCommandDTO.Commands.SCHEDULE,
            params={"force": force},
            source="cli"
        )

        success = producer.send("scheduler.commands", command_dto.model_dump_json())

        if success:
            console.print(f":white_check_mark: [green]Schedule command sent successfully[/green]")
            console.print(f":information: Scheduler will assign {len(unassigned_portfolios)} portfolios immediately")
        else:
            console.print("[red]:x: Failed to send schedule command[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error triggering schedule: {e}[/red]")


@app.command()
def pause():
    """
    :pause_button: Pause Scheduler scheduling loop.

    Pauses the scheduling loop while keeping the Scheduler running.
    Commands will still be processed, but automatic scheduling will stop.

    Examples:
      ginkgo scheduler pause
    """
    try:
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo.interfaces.dtos import SchedulerCommandDTO

        console.print("\n:pause_button: [yellow]Pausing Scheduler...[/yellow]")

        # Send pause command to Kafka
        producer = GinkgoProducer()
        command_dto = SchedulerCommandDTO(
            command=SchedulerCommandDTO.Commands.PAUSE,
            source="cli"
        )

        success = producer.send("scheduler.commands", command_dto.model_dump_json())

        if success:
            console.print(":white_check_mark: [green]Pause command sent successfully[/green]")
            console.print(":information: Scheduler scheduling loop is now paused")
            console.print(":information: Commands will still be processed")
        else:
            console.print("[red]:x: Failed to send pause command[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error pausing scheduler: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def resume():
    """
    :play_button: Resume Scheduler scheduling loop.

    Resumes the automatic scheduling loop that was paused.

    Examples:
      ginkgo scheduler resume
    """
    try:
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo.interfaces.dtos import SchedulerCommandDTO

        console.print("\n:play_button: [green]Resuming Scheduler...[/green]")

        # Send resume command to Kafka
        producer = GinkgoProducer()
        command_dto = SchedulerCommandDTO(
            command=SchedulerCommandDTO.Commands.RESUME,
            source="cli"
        )

        success = producer.send("scheduler.commands", command_dto.model_dump_json())

        if success:
            console.print(":white_check_mark: [green]Resume command sent successfully[/green]")
            console.print(":information: Scheduler scheduling loop is now active")
        else:
            console.print("[red]:x: Failed to send resume command[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error resuming scheduler: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status():
    """
    :information: Query Scheduler status.

    Shows the current status of the Scheduler including:
    - Running state
    - Paused state
    - Schedule interval
    - Node ID

    Examples:
      ginkgo scheduler status
    """
    try:
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo.interfaces.dtos import SchedulerCommandDTO

        console.print("\n:information: Querying Scheduler status...")

        # Send status command to Kafka
        producer = GinkgoProducer()
        command_dto = SchedulerCommandDTO(
            command=SchedulerCommandDTO.Commands.STATUS,
            source="cli"
        )

        success = producer.send("scheduler.commands", command_dto.model_dump_json())

        if success:
            console.print(":white_check_mark: [green]Status command sent successfully[/green]")
            console.print(":information: Check Scheduler logs for detailed status information")
        else:
            console.print("[red]:x: Failed to send status command[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error querying scheduler status: {e}[/red]")
        raise typer.Exit(1)
