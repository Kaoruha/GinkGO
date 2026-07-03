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

import os
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

# #4945: heartbeat TTL < 此阈值视为 stale（节点即将离线/已停），可安全清理。
# 与 status 命令 (L352-360) 的 stale 判定阈值一致，避免 status 说活跃、cleanup 却清掉。
_STALE_HEARTBEAT_TTL_THRESHOLD = 5


@app.command()
def start(
    node_id: str = typer.Option(None, "--node-id", "-n", help="ExecutionNode unique identifier (default: GINKGO_NODE_ID env var or execution_node_1)"),
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
    # 使用环境变量、主机名或默认值
    if node_id is None:
        node_id = os.getenv("GINKGO_NODE_ID")
    if node_id is None:
        import socket
        node_id = socket.gethostname()

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
    # STUB: Portfolio 热管理功能尚未实现
    # See: https://github.com/Kaoruha/GinkGO/issues/4637
    console.print(
        f"[yellow]:warning: STUB: list_portfolios 尚未实现。[/yellow]\n"
        f"[dim]Portfolio 热加载/卸载/列表功能待开发，参见 #4637。[/dim]"
    )
    return


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
    # STUB: Portfolio 热加载功能尚未实现
    # See: https://github.com/Kaoruha/GinkGO/issues/4637
    console.print(
        f"[yellow]:warning: STUB: load 尚未实现。[/yellow]\n"
        f"[dim]Portfolio 热加载/卸载/列表功能待开发，参见 #4637。[/dim]"
    )
    return


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
    # STUB: Portfolio 热卸载功能尚未实现
    # See: https://github.com/Kaoruha/GinkGO/issues/4637
    console.print(
        f"[yellow]:warning: STUB: unload 尚未实现。[/yellow]\n"
        f"[dim]Portfolio 热加载/卸载/列表功能待开发，参见 #4637。[/dim]"
    )
    return


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

        success = producer.send(KafkaTopics.SCHEDULE_UPDATES, command_dto.model_dump())

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

        success = producer.send(KafkaTopics.SCHEDULE_UPDATES, command_dto.model_dump())

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
    limit: int = typer.Option(100, "--limit", help="Max nodes to scan/display (SCAN count hint, production-safe, #5519)"),
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
            from ginkgo.data.redis_schema import RedisKeyBuilder
            heartbeat_key = RedisKeyBuilder.execution_node_heartbeat(node_id)
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
            from ginkgo.data.redis_schema import RedisKeyPattern, extract_id_from_key, RedisKeyPrefix, RedisKeyBuilder
            # #5519: scan_iter 游标式非阻塞扫描；keys() 是 O(N) 阻塞 Redis 单线程。
            # count=limit 作 SCAN COUNT hint（批次大小），[:limit] 截断结果上限。
            heartbeat_keys = list(redis_client.scan_iter(
                match=RedisKeyPattern.EXECUTION_NODE_HEARTBEAT_ALL,
                count=limit,
            ))[:limit]

            if not heartbeat_keys:
                console.print("[yellow]:warning: No ExecutionNodes running (no heartbeats found)[/yellow]")
                return

            # Extract node IDs
            node_ids = [extract_id_from_key(key.decode('utf-8'), f"{RedisKeyPrefix.EXECUTION_NODE_HEARTBEAT}:") for key in heartbeat_keys]

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
                heartbeat_key = RedisKeyBuilder.execution_node_heartbeat(node_id)
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


def _is_node_active(redis_client, node_id: str) -> bool:
    """判断节点是否活跃（运行中，不应清理）（#4945 deep module）。

    复用 status 命令的判活口径：heartbeat 存在且 TTL ≥ 阈值 = 活跃；
    TTL < 阈值（即将过期）或无 heartbeat = stale/已停，可清理。
    """
    from ginkgo.data.redis_schema import RedisKeyBuilder

    heartbeat_key = RedisKeyBuilder.execution_node_heartbeat(node_id)
    if not redis_client.exists(heartbeat_key):
        return False
    heartbeat_ttl = redis_client.ttl(heartbeat_key)
    return heartbeat_ttl >= _STALE_HEARTBEAT_TTL_THRESHOLD


def _cleanup_node(redis_client, node_id: str, force: bool = False) -> tuple:
    """清理单个 ExecutionNode 的 heartbeat + metrics（#5980 deep module，#4945 加活跃守卫）。

    返回 (skipped_active, heartbeat_deleted, metrics_deleted)：
    - skipped_active=True：节点活跃（fresh heartbeat）且非 force，已拒绝清理，调用方应警告用户。
    - 其余情况按 key 是否存在删除，返回删除标志，供调用方统计/输出。

    force=True 跳过活跃守卫，强制清理（用于运维明确知道要清的场景）。
    """
    from ginkgo.data.redis_schema import RedisKeyBuilder

    # #4945: 活跃守卫——fresh heartbeat 表示节点在运行，删它会让调度器误判离线。
    if not force and _is_node_active(redis_client, node_id):
        return (True, False, False)

    heartbeat_key = RedisKeyBuilder.execution_node_heartbeat(node_id)
    metrics_key = f"node:metrics:{node_id}"
    heartbeat_exists = redis_client.exists(heartbeat_key)
    metrics_exists = redis_client.exists(metrics_key)
    if heartbeat_exists:
        redis_client.delete(heartbeat_key)
    if metrics_exists:
        redis_client.delete(metrics_key)
    return (False, bool(heartbeat_exists), bool(metrics_exists))


@app.command()
def cleanup(
    node_id: Optional[str] = typer.Option(None, "--node-id", "-n", help="ExecutionNode ID to cleanup (default: scan all nodes from heartbeats)"),
    force: bool = typer.Option(False, "--force", help="Force cleanup even if heartbeat is still fresh (node appears running). Use only for stuck/zombie nodes."),
):
    """
    :broom: Cleanup stale data for an ExecutionNode.

    Remove heartbeat and metrics data from Redis for a node that has stopped.
    Useful when a process exits abnormally and leaves stale data.

    #4945: Refuses to clean a node whose heartbeat is still fresh (running) unless
    --force is given, since deleting a live heartbeat makes the scheduler mark the
    node offline while it is actually still running.

    Without --node-id, scans all heartbeat keys and cleans every stale node
    (consistent with `execution status`); running nodes are skipped.
    With --node-id, cleans only that node (also guarded by --force).

    Examples:
      ginkgo execution cleanup                      # Clean all stale nodes
      ginkgo execution cleanup --node-id node_1     # Clean specific node only
      ginkgo execution cleanup --node-id node_1 --force  # Force clean a running node
    """
    try:
        from ginkgo.data.crud import RedisCRUD
        from ginkgo.data.redis_schema import (
            RedisKeyPattern,
            RedisKeyPrefix,
            extract_id_from_key,
        )

        # Get Redis client
        redis_crud = RedisCRUD()
        redis_client = redis_crud.redis

        if node_id is None:
            # #5980: 扫描所有 heartbeat keys（与 status 一致），逐个清理
            console.print(":information: Cleaning up data for [bold]all[/bold] ExecutionNodes...")
            heartbeat_keys = redis_client.keys(RedisKeyPattern.EXECUTION_NODE_HEARTBEAT_ALL)

            if not heartbeat_keys:
                console.print("[yellow]:warning: No ExecutionNodes running (no heartbeats found)[/yellow]")
                return

            node_ids = [
                extract_id_from_key(key.decode('utf-8'), f"{RedisKeyPrefix.EXECUTION_NODE_HEARTBEAT}:")
                for key in heartbeat_keys
            ]

            total_hb = 0
            total_mt = 0
            total_skipped = 0
            for nid in node_ids:
                # #4945: 三元组 (skipped_active, hb_deleted, mt_deleted)
                skipped, hb_deleted, mt_deleted = _cleanup_node(redis_client, nid, force=force)
                if skipped:
                    total_skipped += 1
                    console.print(
                        f"[yellow]:warning: ExecutionNode '{nid}' still running (fresh heartbeat). "
                        f"Skipped. Use --force to clean anyway.[/yellow]"
                    )
                    continue
                if hb_deleted:
                    total_hb += 1
                if mt_deleted:
                    total_mt += 1
                console.print(f":white_check_mark: [green]Cleaned ExecutionNode '{nid}'[/green]")

            cleaned_count = len(node_ids) - total_skipped
            console.print(
                f"\n:information: Cleanup completed: {total_hb} heartbeat(s), "
                f"{total_mt} metrics removed across {cleaned_count} node(s)"
            )
            if total_skipped:
                console.print(
                    f"[yellow]:warning: {total_skipped} running node(s) skipped "
                    f"(fresh heartbeat). Re-run with --force to clean them.[/yellow]"
                )
            # 仅在确实清理了 stale 节点时才提示调度器将判定离线（语义对这些节点成立）
            if cleaned_count:
                console.print("[dim]Scheduler will detect cleaned nodes as offline on next schedule loop[/dim]")
        else:
            console.print(f":information: Cleaning up data for ExecutionNode '{node_id}'...")

            # #4945: 三元组 (skipped_active, hb_deleted, mt_deleted)
            skipped, hb_deleted, mt_deleted = _cleanup_node(redis_client, node_id, force=force)

            if skipped:
                # 节点仍在运行——拒绝清理，绝不声称"调度器会判定它离线"（那正是 bug 表象）
                console.print(
                    f"[yellow]:warning: ExecutionNode '{node_id}' still has a fresh heartbeat "
                    f"(it is running). Cleanup refused to avoid the scheduler falsely marking it offline.[/yellow]"
                )
                console.print(f"[dim]Re-run with --force if the node is genuinely stuck/zombie.[/dim]")
                return

            if not hb_deleted and not mt_deleted:
                console.print(f"[dim]:information: No data found for ExecutionNode '{node_id}'[/dim]")
                return

            if hb_deleted:
                console.print(":white_check_mark: [green]Deleted heartbeat data[/green]")
            if mt_deleted:
                console.print(":white_check_mark: [green]Deleted metrics data[/green]")

            console.print(f"\n:information: Cleanup completed for ExecutionNode '{node_id}'")
            console.print("[dim]Scheduler will detect this node as offline on next schedule loop[/dim]")

    except Exception as e:
        console.print(f"[red]:x: Error cleaning up ExecutionNode data: {e}[/red]")
        raise typer.Exit(1)

