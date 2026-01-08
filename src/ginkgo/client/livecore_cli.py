# Upstream: CLI主入口(ginkgo livecore命令调用)
# Downstream: LiveCore(实盘交易容器)、Rich库(格式化输出)
# Role: LiveCore CLI提供启动/状态/停止等命令支持实盘交易系统管理


"""
Ginkgo LiveCore CLI - 实盘交易容器管理命令

LiveCore 是实盘交易的业务逻辑层容器，负责管理：
- DataManager: 数据源管理器，发布市场数据
- TradeGatewayAdapter: 交易网关适配器，执行订单
- Scheduler: 调度器，负责Portfolio分配
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import signal
import sys

app = typer.Typer(help=":rocket: LiveCore - Live Trading Container", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


@app.command()
def start(
    debug: bool = typer.Option(False, "--debug", "-d", help="Run in debug mode with verbose logging"),
):
    """
    :rocket: Start LiveCore container for live trading.

    This will start all LiveCore components:
    - DataManager (market data publisher)
    - TradeGatewayAdapter (order executor)
    - Scheduler (portfolio dispatcher)

    Examples:
      ginkgo livecore start
      ginkgo livecore start --debug
    """
    try:
        from ginkgo.livecore.main import LiveCore

        # Display LiveCore info
        console.print(Panel.fit(
            f"[bold cyan]:rocket: LiveCore[/bold cyan]\n"
            f"[dim]Components:[/dim]\n"
            f"  • ExecutionNode (Portfolio execution engine)\n"
            f"  • DataManager (market data publisher)\n"
            f"  • TradeGatewayAdapter (order executor)\n"
            f"  • Scheduler (portfolio dispatcher)\n"
            f"[dim]Debug:[/dim] {'On' if debug else 'Off'}",
            title="[bold]Live Trading Container[/bold]",
            border_style="cyan"
        ))

        if debug:
            console.print("\n[yellow]:bug: Debug mode enabled - verbose logging active[/yellow]")

        # Create LiveCore instance
        livecore = LiveCore()

        # Start LiveCore
        console.print("\n:rocket: [bold green]Starting LiveCore...[/bold green]")
        console.print(":information: Press Ctrl+C to stop\n")

        livecore.start()

        # Show component status
        console.print(":white_check_mark: [green]LiveCore started successfully[/green]")
        console.print(f":information: Active components: {len(livecore.threads)}")
        for i, thread in enumerate(livecore.threads, 1):
            thread_name = getattr(thread, 'name', thread.__class__.__name__)
            is_alive = thread.is_alive()
            status = "[green]✅ Running[/green]" if is_alive else "[red]❌ Stopped[/red]"
            console.print(f"  [{i}] {thread_name}: {status}")
        console.print()

        # Wait for interrupt
        try:
            import time

            def signal_handler(signum, frame):
                console.print("\n\n:stop_button: [yellow]Stopping LiveCore...[/yellow]")
                console.print(":information: Waiting for components to finish...")

                livecore.stop()

                console.print(Panel.fit(
                    f"[bold green]:white_check_mark: LiveCore stopped[/bold green]\n"
                    f"[dim]All threads terminated gracefully[/dim]",
                    title="[bold]Shutdown Complete[/bold]"
                ))
                raise SystemExit(0)

            # Register signal handlers
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

            # Keep running until interrupted
            console.print(":gear: [dim]LiveCore is running...[/dim]")
            console.print(":information: [dim]Monitoring active components[/dim]\n")

            while livecore.is_running:
                time.sleep(1)

                # Debug mode: 显示线程状态（每30秒显示一次）
                if debug and int(time.time()) % 30 == 0:
                    console.print(f"[dim]:memo: Component Status:[/dim]")
                    for i, thread in enumerate(livecore.threads, 1):
                        thread_name = getattr(thread, 'name', thread.__class__.__name__)
                        is_alive = thread.is_alive()
                        status = "✅" if is_alive else "❌"
                        console.print(f"[dim]  [{i}] {thread_name}: {status}[/dim]")
                    console.print("")

        except SystemExit:
            raise
        except Exception as e:
            console.print(f"\n[red]:x: LiveCore error: {e}[/red]")
            livecore.stop()
            raise typer.Exit(1)

    except ImportError as e:
        console.print(f"[red]:x: Failed to import LiveCore: {e}[/red]")
        console.print(":information: Make sure the livecore module is properly installed")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]:x: Error starting LiveCore: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status():
    """
    :bar_chart: Show LiveCore status.

    Display information about running LiveCore components.
    """
    console.print(":information: LiveCore status check")
    console.print(":information: (Status tracking will be implemented in Phase 4)")

    # TODO: Phase 4 - 实现状态检查逻辑
    # 1. 检查 LiveCore 进程是否运行
    # 2. 检查各组件状态（DataManager、TradeGatewayAdapter、Scheduler）
    # 3. 显示线程状态、队列状态、Kafka连接状态


@app.command()
def stop():
    """
    :stop_button: Stop LiveCore gracefully.

    Send shutdown signal to running LiveCore instance.
    """
    console.print(":information: LiveCore stop command")
    console.print(":information: (Remote stop will be implemented in Phase 4)")

    # TODO: Phase 4 - 实现远程停止逻辑
    # 1. 通过 PID 或 socket 发送停止信号
    # 2. 等待优雅关闭完成
    # 3. 验证所有组件已停止
