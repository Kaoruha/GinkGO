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
from ginkgo.client.cli_utils import announce_dry_run

app = typer.Typer(help=":execution: ExecutionNode - Portfolio Execution Engine", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


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

    Display Portfolio IDs assigned to the given ExecutionNode.
    Source of truth: schedule:plan Redis hash ({portfolio_id -> node_id}),
    same key the scheduler inverts to map node -> portfolios.

    Examples:
      ginkgo execution list-portfolios
      ginkgo execution list-portfolios --node-id node_1
    """
    try:
        from ginkgo import services

        redis_svc = services.data.redis_service()

        # schedule:plan hash: {portfolio_id -> node_id}（Scheduler 写入）
        # 收口至 redis_service.get_schedule_plan（内部 hgetall，已 decode 为 str）。#6300
        plan_result = redis_svc.get_schedule_plan()
        if not plan_result.is_success():
            console.print(f"[red]:x: Error getting schedule plan: {plan_result.error}[/red]")
            raise typer.Exit(1)
        plan = plan_result.data or {}

        portfolios_on_node = [
            pid for pid, assigned_node in plan.items() if assigned_node == node_id
        ]

        if not portfolios_on_node:
            console.print(
                f"[yellow]:information: No portfolios assigned to ExecutionNode '{node_id}'[/yellow]"
            )
            # 信息性心跳提示（不阻断；调度计划为空也可能是节点未启动）
            ttl_result = redis_svc.get_node_heartbeat_ttl(node_id)
            heartbeat_ttl = ttl_result.data if ttl_result.is_success() else -2
            if heartbeat_ttl < 0:
                console.print(
                    f"[dim]  (node '{node_id}' 心跳未检出 — TTL={heartbeat_ttl}；"
                    f"若节点未运行，调度计划自然为空)[/dim]"
                )
            return

        table = Table(
            title=f":clipboard: Portfolios on ExecutionNode '{node_id}' "
            f"({len(portfolios_on_node)})",
            show_header=True,
        )
        table.add_column("#", style="dim", no_wrap=True)
        table.add_column("Portfolio ID", style="cyan")
        for idx, pid in enumerate(portfolios_on_node, 1):
            table.add_row(str(idx), pid)
        console.print("\n")
        console.print(table)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]:x: Error listing portfolios: {e}[/red]")
        raise typer.Exit(1)


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
        from ginkgo import services

        redis_svc = services.data.redis_service()

        if node_id:
            # Query specific node
            console.print(f":information: Querying status of ExecutionNode '{node_id}'...")

            # 心跳 TTL 收口至 redis_service.get_node_heartbeat_ttl（#6300）
            ttl_result = redis_svc.get_node_heartbeat_ttl(node_id)
            if not ttl_result.is_success():
                console.print(f"[red]:x: Error querying heartbeat: {ttl_result.error}[/red]")
                raise typer.Exit(1)
            heartbeat_ttl = ttl_result.data

            if heartbeat_ttl == -2:
                # TTL=-2: 心跳键不存在（节点未运行）
                console.print(f"[yellow]:warning: ExecutionNode '{node_id}' is [red]NOT RUNNING[/red] (no heartbeat)[/yellow]")
                return
            if heartbeat_ttl < 0:
                # TTL=-1: 键存在但无过期（异常，可能 stale）
                console.print(f"[red]:x: ExecutionNode '{node_id}' heartbeat has no expiration (may be stale)[/red]")
                return
            elif heartbeat_ttl < 5:
                # TTL < 5 秒：心跳即将过期，节点可能已停
                console.print(f"[yellow]:warning: ExecutionNode '{node_id}' heartbeat is [red]STALE[/red] (TTL: {heartbeat_ttl}s)[/yellow]")
                return

            # Get metrics（service 已 decode 为 str dict）
            metrics_result = redis_svc.get_execution_node_metrics(node_id)
            if not metrics_result.is_success():
                console.print(f"[red]:x: Error querying metrics: {metrics_result.error}[/red]")
                raise typer.Exit(1)
            metrics = metrics_result.data or {}

            if not metrics:
                console.print(f"[yellow]:warning: No metrics found for ExecutionNode '{node_id}'[/yellow]")
                return

            # Display single node status
            _display_single_node_status(node_id, heartbeat_ttl, metrics)

        else:
            # Query all nodes
            console.print(":information: Querying [bold]all[/bold] ExecutionNodes...")

            # #5519: scan_iter 游标式非阻塞扫描收口至 redis_service.scan_execution_node_ids
            # （内部 SCAN，非 keys() 的 O(N) 阻塞）。limit 作 COUNT hint + 结果上限。
            ids_result = redis_svc.scan_execution_node_ids(limit=limit)
            if not ids_result.is_success():
                console.print(f"[red]:x: Error scanning nodes: {ids_result.error}[/red]")
                raise typer.Exit(1)
            node_ids = ids_result.data or []

            if not node_ids:
                console.print("[yellow]:warning: No ExecutionNodes running (no heartbeats found)[/yellow]")
                return

            # Create table for all nodes
            table = Table(title=f":execution: ExecutionNode Status ({len(node_ids)} nodes)", show_header=True)
            table.add_column("Node ID", style="cyan", no_wrap=True)
            table.add_column("Status", style="green")
            table.add_column("Portfolios", style="blue")
            table.add_column("Queue", style="yellow")
            table.add_column("Events", style="magenta")
            table.add_column("Heartbeat TTL", style="dim")

            for nid in node_ids:
                ttl_r = redis_svc.get_node_heartbeat_ttl(nid)
                heartbeat_ttl = ttl_r.data if ttl_r.is_success() else -2

                mt_r = redis_svc.get_execution_node_metrics(nid)
                metrics = mt_r.data if mt_r.is_success() else {}

                if not metrics:
                    continue

                # Parse metrics（service 已 decode 为 str，无需 bytes 解码）
                status_str = metrics.get('status', 'UNKNOWN')
                portfolio_count = metrics.get('portfolio_count', '0')
                queue_size = metrics.get('queue_size', '0')
                total_events = metrics.get('total_events', '0')

                # Status icon
                if status_str == "RUNNING":
                    status_icon = ":rocket:"
                elif status_str == "PAUSED":
                    status_icon = ":pause_button:"
                else:
                    status_icon = ":stop_button:"

                table.add_row(
                    nid,
                    f"{status_icon} {status_str}",
                    portfolio_count,
                    queue_size,
                    total_events,
                    f"{heartbeat_ttl}s"
                )

            console.print("\n")
            console.print(table)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]:x: Error querying ExecutionNode status: {e}[/red]")
        raise typer.Exit(1)


def _display_single_node_status(node_id: str, heartbeat_ttl: int, metrics: dict):
    """Display status for a single ExecutionNode"""
    console.print(f"\n:information: [bold]ExecutionNode Status[/bold]")
    console.print(f"  [bold]Node ID:[/bold] {node_id}")
    console.print(f"  [dim]Heartbeat TTL: {heartbeat_ttl}s[/dim]")

    # Parse metrics（service 已 decode 为 str，无需 bytes 解码）
    status_str = metrics.get('status', 'UNKNOWN')
    portfolio_count = metrics.get('portfolio_count', '0')
    queue_size = metrics.get('queue_size', '0')
    total_events = metrics.get('total_events', '0')

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


# cleanup 的判活（#4945）与删除（#5980）逻辑已下沉至 redis_service：
#   is_execution_node_active / cleanup_execution_node（#6300/#6115 收口，消除 CLI→Redis 直连）。


@app.command()
def cleanup(
    node_id: Optional[str] = typer.Option(None, "--node-id", "-n", help="ExecutionNode ID to cleanup (default: scan all nodes from heartbeats)"),
    force: bool = typer.Option(False, "--force", help="Force cleanup even if heartbeat is still fresh (node appears running). Use only for stuck/zombie nodes."),
    dry_run: bool = typer.Option(False, "--dry-run", help=":eye: Preview which nodes/keys would be cleaned without deleting (skips confirm; no writes)."),
):
    """
    :broom: Cleanup stale data for an ExecutionNode.

    Remove heartbeat and metrics data from Redis for a node that has stopped.
    Useful when a process exits abnormally and leaves stale data.

    #4945: Refuses to clean a node whose heartbeat is still fresh (running) unless
    --force is given, since deleting a live heartbeat makes the scheduler mark the
    node offline while it is actually still running.

    --dry-run: enumerate heartbeat/metrics keys and report what WOULD be removed
    without touching Redis (active-node guard still applies, so running nodes are
    still reported as skipped). Useful to audit before a real cleanup.

    Without --node-id, scans all heartbeat keys and cleans every stale node
    (consistent with `execution status`); running nodes are skipped.
    With --node-id, cleans only that node (also guarded by --force).

    Examples:
      ginkgo execution cleanup                      # Clean all stale nodes
      ginkgo execution cleanup --node-id node_1     # Clean specific node only
      ginkgo execution cleanup --node-id node_1 --force  # Force clean a running node
      ginkgo execution cleanup --dry-run            # Preview without deleting
    """
    if dry_run:
        announce_dry_run("清理 ExecutionNode 残留数据", console=console)
    # dry-run 下"已清理/已删除"统一改为"将清理/将删除"，动词随 dry_run 切换
    verb_done = "would remove" if dry_run else "removed"
    verb_node = "Would clean" if dry_run else "Cleaned"
    verb_hb = "Would delete" if dry_run else "Deleted"

    try:
        from ginkgo import services
        svc = services.data.redis_service()

        if node_id is None:
            # #5980: 扫描所有 heartbeat keys（与 status 一致），逐个清理。
            # #5519: 节点枚举走 scan_execution_node_ids（scan_iter 非阻塞），不再 keys（O(N) 阻塞）。
            console.print(":information: Cleaning up data for [bold]all[/bold] ExecutionNodes...")
            scan_result = svc.scan_execution_node_ids()
            if not scan_result.is_success():
                console.print(f"[red]:x: Failed to enumerate execution nodes: {scan_result.error}[/red]")
                raise typer.Exit(1)
            node_ids = scan_result.data or []

            if not node_ids:
                console.print("[yellow]:warning: No ExecutionNodes running (no heartbeats found)[/yellow]")
                return

            total_hb = 0
            total_mt = 0
            total_skipped = 0
            for nid in node_ids:
                # #4945/#5980: 清理逻辑下沉 service（cleanup_execution_node），CLI 仅做输出/统计。
                res = svc.cleanup_execution_node(nid, force=force, dry_run=dry_run)
                if not res.is_success():
                    console.print(f"[red]:x: Failed to clean ExecutionNode '{nid}': {res.error}[/red]")
                    continue
                if res.data["skipped_active"]:
                    total_skipped += 1
                    console.print(
                        f"[yellow]:warning: ExecutionNode '{nid}' still running (fresh heartbeat). "
                        f"Skipped. Use --force to clean anyway.[/yellow]"
                    )
                    continue
                if res.data["heartbeat_deleted"]:
                    total_hb += 1
                if res.data["metrics_deleted"]:
                    total_mt += 1
                console.print(f":white_check_mark: [green]{verb_node} ExecutionNode '{nid}'[/green]")

            cleaned_count = len(node_ids) - total_skipped
            console.print(
                f"\n:information: Cleanup completed: {total_hb} heartbeat(s), "
                f"{total_mt} metrics {verb_done} across {cleaned_count} node(s)"
            )
            if total_skipped:
                console.print(
                    f"[yellow]:warning: {total_skipped} running node(s) skipped "
                    f"(fresh heartbeat). Re-run with --force to clean them.[/yellow]"
                )
            # 仅在确实清理了 stale 节点时才提示调度器将判定离线（语义对这些节点成立）
            # dry_run 下不删除，调度器判定不受影响，不打印此提示避免误导。
            if cleaned_count and not dry_run:
                console.print("[dim]Scheduler will detect cleaned nodes as offline on next schedule loop[/dim]")
        else:
            console.print(f":information: Cleaning up data for ExecutionNode '{node_id}'...")

            res = svc.cleanup_execution_node(node_id, force=force, dry_run=dry_run)
            if not res.is_success():
                console.print(f"[red]:x: Error cleaning up ExecutionNode data: {res.error}[/red]")
                raise typer.Exit(1)

            if res.data["skipped_active"]:
                # 节点仍在运行——拒绝清理，绝不声称"调度器会判定它离线"（那正是 bug 表象）
                console.print(
                    f"[yellow]:warning: ExecutionNode '{node_id}' still has a fresh heartbeat "
                    f"(it is running). Cleanup refused to avoid the scheduler falsely marking it offline.[/yellow]"
                )
                console.print(f"[dim]Re-run with --force if the node is genuinely stuck/zombie.[/dim]")
                return

            if not res.data["heartbeat_deleted"] and not res.data["metrics_deleted"]:
                console.print(f"[dim]:information: No data found for ExecutionNode '{node_id}'[/dim]")
                return

            if res.data["heartbeat_deleted"]:
                console.print(f":white_check_mark: [green]{verb_hb} heartbeat data[/green]")
            if res.data["metrics_deleted"]:
                console.print(f":white_check_mark: [green]{verb_hb} metrics data[/green]")

            console.print(f"\n:information: Cleanup completed for ExecutionNode '{node_id}'")
            if not dry_run:
                console.print("[dim]Scheduler will detect this node as offline on next schedule loop[/dim]")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]:x: Error cleaning up ExecutionNode data: {e}[/red]")
        raise typer.Exit(1)

