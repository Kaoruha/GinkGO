# Upstream: CLI主入口(ginkgo execution命令调用)
# Downstream: ExecutionNode(Portfolio执行引擎)、Rich库(格式化输出)
# Role: ExecutionNode CLI提供启动/状态/停止等命令支持Portfolio执行节点管理


"""
Ginkgo ExecutionNode CLI - Portfolio执行节点管理命令

ExecutionNode 是实盘交易的执行引擎，负责：
- 运行多个 Portfolio 实例
- 从 Kafka 订阅市场数据和订单反馈
- 使用 InterestMap 路由事件到 Portfolio
- 收集订单并提交到 Kafka
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import signal
import sys
from ginkgo.interfaces.kafka_topics import KafkaTopics

app = typer.Typer(help=":execution: ExecutionNode - Portfolio Execution Engine", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


@app.command()
def start(
    node_id: str = typer.Option("execution_node_1", "--node-id", "-n", help="ExecutionNode unique identifier"),
    portfolio_id: Optional[str] = typer.Option(None, "--portfolio", "-p", help="Specific portfolio ID to load"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Run in debug mode with verbose logging"),
):
    """
    :rocket: Start ExecutionNode for Portfolio execution.

    ExecutionNode is the core component that runs multiple Portfolio instances,
    subscribes to market data from Kafka, routes events to Portfolios using InterestMap,
    and submits orders to Kafka.

    Examples:
      ginkgo execution start
      ginkgo execution start --node-id node_1
      ginkgo execution start --portfolio portfolio_123
      ginkgo execution start --debug
    """
    try:
        from ginkgo.workers.execution_node.node import ExecutionNode

        # Display ExecutionNode info
        console.print(Panel.fit(
            f"[bold cyan]:execution: ExecutionNode[/bold cyan]\n"
            f"[dim]Configuration:[/dim]\n"
            f"  • Node ID: {node_id}\n"
            f"  • Portfolio: {portfolio_id or 'All (from database)'}\n"
            f"[dim]Features:[/dim]\n"
            f"  • InterestMap (O(1) routing)\n"
            f"  • Multi-Portfolio parallel execution\n"
            f"  • Backpressure monitoring\n"
            f"  • Kafka integration\n"
            f"[dim]Debug:[/dim] {'On' if debug else 'Off'}",
            title="[bold]Portfolio Execution Engine[/bold]",
            border_style="cyan"
        ))

        if debug:
            console.print("\n[yellow]:bug: Debug mode enabled - verbose logging active[/yellow]")

        # Create ExecutionNode instance
        console.print(f"\n:rocket: [bold green]Creating ExecutionNode '{node_id}'...[/bold green]")
        execution_node = ExecutionNode(node_id=node_id)

        # Load specific portfolio if requested
        if portfolio_id:
            console.print(f"\n:information: Loading portfolio: {portfolio_id}")
            load_result = execution_node.load_portfolio(portfolio_id)
            if load_result:
                console.print(f":white_check_mark: Portfolio loaded successfully")
            else:
                console.print(f"[red]:x: Failed to load portfolio {portfolio_id}[/red]")
                console.print(":information: Continuing ExecutionNode startup...")

        # Start ExecutionNode
        console.print(f"\n:rocket: [bold green]Starting ExecutionNode...[/bold green]")
        console.print(":information: Press Ctrl+C to stop\n")

        execution_node.start()

        console.print(":white_check_mark: [green]ExecutionNode started successfully[/green]")
        console.print(f":information: Node ID: {execution_node.node_id}")
        if portfolio_id:
            console.print(f":information: Portfolios loaded: {len(execution_node.portfolios)}")
            if portfolio_id in execution_node.portfolios:
                console.print(f":white_check_mark: Portfolio '{portfolio_id[:8]}...' is running")
        else:
            console.print(f":information: Portfolios loaded: {len(execution_node.portfolios)}")
        console.print()

        # Wait for interrupt
        try:
            import time

            def signal_handler(signum, frame):
                console.print("\n\n:stop_button: [yellow]Stopping ExecutionNode...[/yellow]")
                console.print(":information: Waiting for Portfolios to finish...")

                execution_node.stop()

                # Show statistics
                console.print(Panel.fit(
                    f"[bold green]:white_check_mark: ExecutionNode stopped[/bold green]\n"
                    f"[dim]Statistics:[/dim]\n"
                    f"  Total events: {execution_node.total_event_count}\n"
                    f"  Backpressure events: {execution_node.backpressure_count}\n"
                    f"  Dropped events: {execution_node.dropped_event_count}",
                    title="[bold]Shutdown Complete[/bold]"
                ))
                raise SystemExit(0)

            # Register signal handlers
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Keep running until interrupted
            console.print(":gear: [dim]ExecutionNode is running...[/dim]")
            console.print(":information: [dim]Consuming events from Kafka[/dim]\n")

            while execution_node.is_running:
                time.sleep(1)

                # Debug mode: 显示统计信息
                if debug:
                    if execution_node.total_event_count > 0:
                        console.print(
                            f"[dim]:memo: Events: {execution_node.total_event_count} | "
                            f"Backpressure: {execution_node.backpressure_count} | "
                            f"Portfolios: {len(execution_node.portfolios)}[/dim]"
                        )

        except SystemExit:
            raise
        except Exception as e:
            console.print(f"\n[red]:x: ExecutionNode error: {e}[/red]")
            execution_node.stop()
            raise typer.Exit(1)

    except ImportError as e:
        console.print(f"[red]:x: Failed to import ExecutionNode: {e}[/red]")
        console.print(":information: Make sure the execution_node module is properly installed")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]:x: Error starting ExecutionNode: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def list_portfolios(
    node_id: str = typer.Option("execution_node_1", "--node-id", "-n", help="ExecutionNode ID"),
):
    """
    :clipboard: List all Portfolios loaded in ExecutionNode.

    Display Portfolio IDs and their subscription status.
    """
    console.print(f":information: Listing Portfolios for ExecutionNode '{node_id}'")
    console.print(":information: (Portfolio listing will be implemented with database integration)")

    # TODO: 实现 Portfolio 列表逻辑
    # 1. 从数据库查询 Portfolio 配置
    # 2. 显示每个 Portfolio 的订阅股票
    # 3. 显示 Portfolio 运行状态


@app.command()
def load(
    portfolio_id: str = typer.Argument(..., help="Portfolio ID to load"),
    node_id: str = typer.Option("execution_node_1", "--node-id", "-n", help="ExecutionNode ID"),
):
    """
    :download: Load a Portfolio into ExecutionNode.

    Load Portfolio configuration from database and start processing.

    Examples:
      ginkgo execution load portfolio_123
      ginkgo execution load portfolio_123 --node-id node_1
    """
    console.print(f":information: Loading Portfolio '{portfolio_id}' into ExecutionNode '{node_id}'")
    console.print(":information: (Portfolio loading will be implemented with database integration)")

    # TODO: 实现 Portfolio 加载逻辑
    # 1. 从数据库读取 Portfolio 配置
    # 2. 创建 PortfolioLive 实例
    # 3. 添加策略、Sizer、RiskManager
    # 4. 创建 PortfolioProcessor
    # 5. 添加到 ExecutionNode


@app.command()
def unload(
    portfolio_id: str = typer.Argument(..., help="Portfolio ID to unload"),
    node_id: str = typer.Option("execution_node_1", "--node-id", "-n", help="ExecutionNode ID"),
):
    """
    :eject: Unload a Portfolio from ExecutionNode.

    Stop Portfolio processing and remove from ExecutionNode.

    Examples:
      ginkgo execution unload portfolio_123
      ginkgo execution unload portfolio_123 --node-id node_1
    """
    console.print(f":information: Unloading Portfolio '{portfolio_id}' from ExecutionNode '{node_id}'")
    console.print(":information: (Portfolio unloading will be implemented)")

    # TODO: 实现 Portfolio 卸载逻辑
    # 1. 停止 PortfolioProcessor
    # 2. 从 InterestMap 移除订阅
    # 3. 从 ExecutionNode 移除


@app.command()
def pause(
    node_id: str = typer.Option("execution_node_1", "--node-id", "-n", help="ExecutionNode ID"),
):
    """
    :pause_button: Pause ExecutionNode.

    Pause event processing while keeping the node running.
    Heartbeat continues, but events are not processed.

    Examples:
      ginkgo execution pause
      ginkgo execution pause --node-id node_1
    """
    try:
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo.interfaces.dtos import ScheduleUpdateDTO

        console.print(f":pause_button: [yellow]Pausing ExecutionNode '{node_id}'...[/yellow]")

        # Send pause command to Kafka
        producer = GinkgoProducer()
        command_dto = ScheduleUpdateDTO(
            command=ScheduleUpdateDTO.Commands.NODE_PAUSE,
            node_id=node_id,
            source="cli"
        )

        success = producer.send(KafkaTopics.SCHEDULE_UPDATES, command_dto.model_dump_json())

        if success:
            console.print(":white_check_mark: [green]Pause command sent successfully[/green]")
            console.print(f":information: ExecutionNode '{node_id}' will pause event processing")
            console.print(":information: Heartbeat will continue (node remains discoverable)")
        else:
            console.print("[red]:x: Failed to send pause command[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error pausing ExecutionNode: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def resume(
    node_id: str = typer.Option("execution_node_1", "--node-id", "-n", help="ExecutionNode ID"),
):
    """
    :play_button: Resume ExecutionNode.

    Resume event processing for a paused node.

    Examples:
      ginkgo execution resume
      ginkgo execution resume --node-id node_1
    """
    try:
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo.interfaces.dtos import ScheduleUpdateDTO

        console.print(f":play_button: [green]Resuming ExecutionNode '{node_id}'...[/green]")

        # Send resume command to Kafka
        producer = GinkgoProducer()
        command_dto = ScheduleUpdateDTO(
            command=ScheduleUpdateDTO.Commands.NODE_RESUME,
            node_id=node_id,
            source="cli"
        )

        success = producer.send(KafkaTopics.SCHEDULE_UPDATES, command_dto.model_dump_json())

        if success:
            console.print(":white_check_mark: [green]Resume command sent successfully[/green]")
            console.print(f":information: ExecutionNode '{node_id}' will resume event processing")
        else:
            console.print("[red]:x: Failed to send resume command[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error resuming ExecutionNode: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status(
    node_id: Optional[str] = typer.Option(None, "--node-id", "-n", help="Query specific ExecutionNode (default: show all)"),
):
    """
    :bar_chart: Query ExecutionNode status.

    Display the current status of ExecutionNodes including:
    - Running state (from heartbeat)
    - Portfolio count
    - Queue sizes
    - Total events processed

    Examples:
      ginkgo execution status              # Show all ExecutionNodes
      ginkgo execution status --node-id node_1  # Show specific node
    """
    try:
        from ginkgo.data.crud import RedisCRUD

        # Get Redis client
        redis_crud = RedisCRUD()
        redis_client = redis_crud.redis

        if node_id:
            # Query specific node
            console.print(f":information: Querying status of ExecutionNode '{node_id}'...")

            # Check heartbeat
            heartbeat_key = f"heartbeat:node:{node_id}"
            heartbeat_exists = redis_client.exists(heartbeat_key)

            if not heartbeat_exists:
                console.print(f"[yellow]:warning: ExecutionNode '{node_id}' is [red]NOT RUNNING[/red] (no heartbeat)[/yellow]")
                return

            # Check heartbeat TTL to detect stale heartbeats
            heartbeat_ttl = redis_client.ttl(heartbeat_key)
            if heartbeat_ttl < 0:
                # Key exists but has no expiration (shouldn't happen with proper setup)
                console.print(f"[red]:x: ExecutionNode '{node_id}' heartbeat has no expiration (may be stale)[/red]")
                return
            elif heartbeat_ttl < 5:
                # TTL < 5 seconds: heartbeat is about to expire, node likely stopped
                console.print(f"[yellow]:warning: ExecutionNode '{node_id}' heartbeat is [red]STALE[/red] (TTL: {heartbeat_ttl}s)[/yellow]")
                return

            # Get metrics
            metrics_key = f"node:metrics:{node_id}"
            metrics = redis_client.hgetall(metrics_key)

            if not metrics:
                console.print(f"[yellow]:warning: No metrics found for ExecutionNode '{node_id}'[/yellow]")
                return

            # Display single node status
            _display_single_node_status(node_id, heartbeat_ttl, metrics)

        else:
            # Query all nodes
            console.print(":information: Querying [bold]all[/bold] ExecutionNodes...")

            # Get all heartbeat keys
            heartbeat_keys = redis_client.keys("heartbeat:node:*")

            if not heartbeat_keys:
                console.print("[yellow]:warning: No ExecutionNodes running (no heartbeats found)[/yellow]")
                return

            # Extract node IDs
            node_ids = [key.decode('utf-8').replace("heartbeat:node:", "") for key in heartbeat_keys]

            # Create table for all nodes
            table = Table(title=f":execution: ExecutionNode Status ({len(node_ids)} nodes)", show_header=True)
            table.add_column("Node ID", style="cyan", no_wrap=True)
            table.add_column("Status", style="green")
            table.add_column("Portfolios", style="blue")
            table.add_column("Queue", style="yellow")
            table.add_column("Events", style="magenta")
            table.add_column("Heartbeat TTL", style="dim")

            for node_id in node_ids:
                # Get heartbeat TTL
                heartbeat_key = f"heartbeat:node:{node_id}"
                heartbeat_ttl = redis_client.ttl(heartbeat_key)

                # Get metrics
                metrics_key = f"node:metrics:{node_id}"
                metrics = redis_client.hgetall(metrics_key)

                if not metrics:
                    continue

                # Parse metrics
                status_str = metrics.get(b'status', b'UNKNOWN').decode('utf-8')
                portfolio_count = metrics.get(b'portfolio_count', b'0').decode('utf-8')
                queue_size = metrics.get(b'queue_size', b'0').decode('utf-8')
                total_events = metrics.get(b'total_events', b'0').decode('utf-8')

                # Status icon
                if status_str == "RUNNING":
                    status_icon = ":rocket:"
                elif status_str == "PAUSED":
                    status_icon = ":pause_button:"
                else:
                    status_icon = ":stop_button:"

                table.add_row(
                    node_id,
                    f"{status_icon} {status_str}",
                    portfolio_count,
                    queue_size,
                    total_events,
                    f"{heartbeat_ttl}s"
                )

            console.print("\n")
            console.print(table)

    except Exception as e:
        console.print(f"[red]:x: Error querying ExecutionNode status: {e}[/red]")
        raise typer.Exit(1)


def _display_single_node_status(node_id: str, heartbeat_ttl: int, metrics: dict):
    """Display status for a single ExecutionNode"""
    console.print(f"\n:information: [bold]ExecutionNode Status[/bold]")
    console.print(f"  [bold]Node ID:[/bold] {node_id}")
    console.print(f"  [dim]Heartbeat TTL: {heartbeat_ttl}s[/dim]")

    # Parse metrics
    status_str = metrics.get(b'status', b'UNKNOWN').decode('utf-8')
    portfolio_count = metrics.get(b'portfolio_count', b'0').decode('utf-8')
    queue_size = metrics.get(b'queue_size', b'0').decode('utf-8')
    total_events = metrics.get(b'total_events', b'0').decode('utf-8')

    # Status color
    if status_str == "RUNNING":
        status_emoji = ":rocket:"
        status_color = "[green]"
    elif status_str == "PAUSED":
        status_emoji = ":pause_button:"
        status_color = "[yellow]"
    else:
        status_emoji = ":stop_button:"
        status_color = "[red]"

    console.print(f"  {status_emoji} Status: {status_color}{status_str}[/]")
    console.print(f"  :file_folder: Portfolios: {portfolio_count}")
    console.print(f"  :inbox_tray: Queue Size: {queue_size}")
    console.print(f"  :chart_with_upwards_trend: Total Events: {total_events}")


@app.command()
def cleanup(
    node_id: str = typer.Option("execution_node_1", "--node-id", "-n", help="ExecutionNode ID to cleanup"),
):
    """
    :broom: Cleanup stale data for an ExecutionNode.

    Remove heartbeat and metrics data from Redis for a node that has stopped.
    Useful when a process exits abnormally and leaves stale data.

    Examples:
      ginkgo execution cleanup
      ginkgo execution cleanup --node-id execution_node_1
    """
    try:
        from ginkgo.data.crud import RedisCRUD

        console.print(f":information: Cleaning up data for ExecutionNode '{node_id}'...")

        # Get Redis client
        redis_crud = RedisCRUD()
        redis_client = redis_crud.redis

        # Keys to cleanup
        heartbeat_key = f"heartbeat:node:{node_id}"
        metrics_key = f"node:metrics:{node_id}"

        # Check what exists
        heartbeat_exists = redis_client.exists(heartbeat_key)
        metrics_exists = redis_client.exists(metrics_key)

        if not heartbeat_exists and not metrics_exists:
            console.print(f"[dim]:information: No data found for ExecutionNode '{node_id}'[/dim]")
            return

        # Delete heartbeat
        if heartbeat_exists:
            redis_client.delete(heartbeat_key)
            console.print(f":white_check_mark: [green]Deleted heartbeat data[/green]")

        # Delete metrics
        if metrics_exists:
            redis_client.delete(metrics_key)
            console.print(f":white_check_mark: [green]Deleted metrics data[/green]")

        console.print(f"\n:information: Cleanup completed for ExecutionNode '{node_id}'")
        console.print(f"[dim]Scheduler will detect this node as offline on next schedule loop[/dim]")

    except Exception as e:
        console.print(f"[red]:x: Error cleaning up ExecutionNode data: {e}[/red]")
        raise typer.Exit(1)

