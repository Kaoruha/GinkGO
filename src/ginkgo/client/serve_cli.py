# Upstream: CLI主入口(ginkgo serve命令调用)
# Downstream: 各组件(LiveCore, ExecutionNode, Scheduler, TaskTimer, Worker)、Rich库
# Role: 统一的组件启动命令，所有前台运行组件都通过 serve 命令启动

"""
Ginkgo Serve CLI - 统一组件启动命令

所有组件前台运行都通过 serve 命令统一管理：
- ginkgo serve api            # API server (FastAPI)
- ginkgo serve webui          # Web UI (Vue 3 + Vite)
- ginkgo serve all            # 同时启动 API + Web UI
- ginkgo serve livecore       # LiveCore 实盘交易容器
- ginkgo serve execution      # ExecutionNode 执行节点
- ginkgo serve scheduler      # Scheduler 调度器
- ginkgo serve tasktimer      # TaskTimer 定时任务
- ginkgo serve worker-data    # DataWorker 数据工作器
- ginkgo serve worker-backtest # BacktestWorker 回测工作器
"""

import typer
from typing import Optional
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(help=":rocket: Start services in foreground", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


@app.command("api")
def serve_api(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind"),
    port: int = typer.Option(8000, "--port", "-p", help="Port to bind"),
    reload: bool = typer.Option(True, "--reload", "-r", help="Enable auto-reload for development"),
):
    """
    :globe_with_meridians: Start Ginkgo API server.

    Examples:
      ginkgo serve api
      ginkgo serve api --port 8080
      ginkgo serve api --reload
    """
    import os

    console.print(Panel.fit(
        f"[bold green]:globe_with_meridians: API Server[/bold green]\n"
        f"[dim]Host:[/dim] {host}\n"
        f"[dim]Port:[/dim] {port}\n"
        f"[dim]Reload:[/dim] {'On' if reload else 'Off'}",
        title="[bold]Ginkgo API[/bold]",
        border_style="green"
    ))

    # 获取 api/main.py 的路径
    api_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "api", "main.py")

    if not os.path.exists(api_path):
        console.print(f"[red]:x: API server not found at {api_path}[/red]")
        raise typer.Exit(1)

    console.print(f"\n:rocket: [bold green]Starting API Server...[/bold green]")
    console.print(f":information: API will be available at http://{host}:{port}")
    console.print(f":information: API docs at http://{host}:{port}/docs")
    console.print(":information: Press Ctrl+C to stop\n")

    try:
        import uvicorn

        api_dir = os.path.dirname(api_path)

        if reload:
            # 开发模式，只监听 api 目录下的变动
            uvicorn.run(
                "main:app",
                app_dir=api_dir,
                host=host,
                port=port,
                reload=True,
                reload_dirs=[api_dir],
            )
        else:
            # 生产模式
            uvicorn.run(
                "main:app",
                app_dir=api_dir,
                host=host,
                port=port,
            )
    except ImportError:
        console.print("[red]:x: uvicorn not installed. Install with: pip install uvicorn[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n:stop_button: [yellow]API Server stopped[/yellow]")


@app.command("webui")
def serve_webui(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind"),
    port: int = typer.Option(5173, "--port", "-p", help="Port to bind"),
    open_browser: bool = typer.Option(False, "--open", "-o", help="Open browser automatically"),
):
    """
    :desktop_computer: Start Ginkgo Web UI development server.

    Examples:
      ginkgo serve webui
      ginkgo serve webui --port 3000
      ginkgo serve webui --open
    """
    import os
    import subprocess
    import shutil

    # 获取 web-ui 目录路径
    webui_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "web-ui")

    if not os.path.exists(webui_path):
        console.print(f"[red]:x: Web UI not found at {webui_path}[/red]")
        raise typer.Exit(1)

    # 检查 node_modules 是否存在
    node_modules = os.path.join(webui_path, "node_modules")
    if not os.path.exists(node_modules):
        console.print("[yellow]:information: node_modules not found, running npm install...[/yellow]")
        npm_cmd = shutil.which("npm")
        if not npm_cmd:
            console.print("[red]:x: npm not found. Please install Node.js first.[/red]")
            raise typer.Exit(1)

        try:
            subprocess.run([npm_cmd, "install"], cwd=webui_path, check=True)
            console.print("[green]:white_check_mark: Dependencies installed[/green]")
        except subprocess.CalledProcessError:
            console.print("[red]:x: Failed to install dependencies[/red]")
            raise typer.Exit(1)

    console.print(Panel.fit(
        f"[bold green]:desktop_computer: Web UI[/bold green]\n"
        f"[dim]Host:[/dim] {host}\n"
        f"[dim]Port:[/dim] {port}\n"
        f"[dim]Path:[/dim] {webui_path}",
        title="[bold]Ginkgo Web UI[/bold]",
        border_style="green"
    ))

    console.print(f"\n:rocket: [bold green]Starting Web UI...[/bold green]")
    console.print(f":information: Web UI will be available at http://{host}:{port}")
    console.print(":information: Press Ctrl+C to stop\n")

    npm_cmd = shutil.which("npm")
    if not npm_cmd:
        console.print("[red]:x: npm not found. Please install Node.js first.[/red]")
        raise typer.Exit(1)

    try:
        env = os.environ.copy()
        env["HOST"] = host
        env["PORT"] = str(port)

        subprocess.run([npm_cmd, "run", "dev"], cwd=webui_path, env=env)
    except KeyboardInterrupt:
        console.print("\n:stop_button: [yellow]Web UI stopped[/yellow]")


@app.command("all")
def serve_all(
    api_port: int = typer.Option(8000, "--api-port", "-a", help="API server port"),
    webui_port: int = typer.Option(5173, "--webui-port", "-w", help="Web UI port"),
):
    """
    :rocket: Start both API server and Web UI.

    Examples:
      ginkgo serve all
      ginkgo serve all --api-port 8080 --webui-port 3000
    """
    import os
    import subprocess
    import signal
    import shutil

    console.print(Panel.fit(
        f"[bold green]:rocket: Full Stack Server[/bold green]\n"
        f"[dim]API Port:[/dim] {api_port}\n"
        f"[dim]Web UI Port:[/dim] {webui_port}",
        title="[bold]Ginkgo Full Stack[/bold]",
        border_style="green"
    ))

    processes = []

    def cleanup(signum=None, frame=None):
        console.print("\n:stop_button: [yellow]Stopping all services...[/yellow]")
        for p in processes:
            try:
                p.terminate()
                p.wait(timeout=5)
            except Exception:
                p.kill()
        console.print("[green]:white_check_mark: All services stopped[/green]")
        os._exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # 获取路径
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    api_path = os.path.join(base_path, "api", "main.py")
    webui_path = os.path.join(base_path, "web-ui")

    # 检查 API
    if not os.path.exists(api_path):
        console.print(f"[red]:x: API server not found at {api_path}[/red]")
        raise typer.Exit(1)

    # 检查 Web UI
    if not os.path.exists(webui_path):
        console.print(f"[red]:x: Web UI not found at {webui_path}[/red]")
        raise typer.Exit(1)

    # 启动 API Server
    console.print("\n:rocket: [bold]Starting API Server...[/bold]")
    try:
        import uvicorn
        from multiprocessing import Process

        api_dir = os.path.dirname(api_path)

        def run_api():
            uvicorn.run(
                "main:app",
                app_dir=api_dir,
                host="0.0.0.0",
                port=api_port,
            )

        api_process = Process(target=run_api)
        api_process.start()
        processes.append(api_process)
        console.print(f"[green]:white_check_mark: API Server started at http://0.0.0.0:{api_port}[/green]")
    except Exception as e:
        console.print(f"[red]:x: Failed to start API Server: {e}[/red]")
        cleanup()

    # 启动 Web UI
    console.print("\n:rocket: [bold]Starting Web UI...[/bold]")
    npm_cmd = shutil.which("npm")
    if npm_cmd:
        try:
            env = os.environ.copy()
            env["HOST"] = "0.0.0.0"
            env["PORT"] = str(webui_port)

            webui_process = subprocess.Popen(
                [npm_cmd, "run", "dev"],
                cwd=webui_path,
                env=env,
            )
            processes.append(webui_process)
            console.print(f"[green]:white_check_mark: Web UI started at http://0.0.0.0:{webui_port}[/green]")
        except Exception as e:
            console.print(f"[red]:x: Failed to start Web UI: {e}[/red]")
            cleanup()
    else:
        console.print("[yellow]:warning: npm not found, skipping Web UI[/yellow]")

    console.print(f"\n[bold green]:white_check_mark: All services started![/bold green]")
    console.print(f"[dim]API:[/dim] http://localhost:{api_port}")
    console.print(f"[dim]API Docs:[/dim] http://localhost:{api_port}/docs")
    console.print(f"[dim]Web UI:[/dim] http://localhost:{webui_port}")
    console.print("[dim]Press Ctrl+C to stop all services[/dim]\n")

    # 等待进程
    try:
        while True:
            import time
            time.sleep(1)
            # 检查进程状态
            for p in processes:
                if hasattr(p, 'poll') and p.poll() is not None:
                    console.print(f"[yellow]:warning: A process has stopped unexpectedly[/yellow]")
    except KeyboardInterrupt:
        cleanup()


@app.command("livecore")
def serve_livecore():
    """
    :rocket: Start LiveCore container for live trading.

    Examples:
      ginkgo serve livecore
    """
    import signal
    import time

    try:
        from ginkgo.livecore.main import LiveCore

        console.print(Panel.fit(
            f"[bold cyan]:rocket: LiveCore[/bold cyan]\n"
            f"[dim]Components:[/dim]\n"
            f"  • DataManager (market data publisher)\n"
            f"  • TradeGatewayAdapter (order executor)\n"
            f"  • Scheduler (portfolio dispatcher)\n"
            f"[dim]Note: ExecutionNode is separate[/dim]",
            title="[bold]Live Trading Container[/bold]",
            border_style="cyan"
        ))

        livecore = LiveCore()
        console.print(f"\n:rocket: [bold green]Starting LiveCore...[/bold green]")
        console.print(":information: Press Ctrl+C to stop\n")

        livecore.start()

        console.print(":white_check_mark: [green]LiveCore started[/green]")
        console.print(f":information: Active components: {len(livecore.threads)}\n")

        def signal_handler(signum, frame):
            console.print("\n\n:stop_button: [yellow]Stopping LiveCore...[/yellow]")
            livecore.stop()
            console.print("[green]:white_check_mark: LiveCore stopped[/green]")
            import os
            os._exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        while livecore.is_running:
            time.sleep(1)

    except ImportError as e:
        console.print(f"[red]:x: Failed to import LiveCore: {e}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n\n:stop_button: [yellow]Stopping LiveCore...[/yellow]")
        livecore.stop()
        console.print("[green]:white_check_mark: LiveCore stopped[/green]")
    except Exception as e:
        console.print(f"[red]:x: Error starting LiveCore: {e}[/red]")
        raise typer.Exit(1)


@app.command("execution")
def serve_execution(
    node_id: Optional[str] = typer.Option(None, "--id", "-id", help="ExecutionNode unique identifier"),
    portfolio_id: Optional[str] = typer.Option(None, "--portfolio", "-p", help="Specific portfolio ID to load"),
):
    """
    :execution: Start ExecutionNode for Portfolio execution.

    Examples:
      ginkgo serve execution
      ginkgo serve execution --id node_1
      ginkgo serve execution --portfolio portfolio_123
    """
    import signal
    import time
    import os
    import socket

    if node_id is None:
        node_id = os.getenv("GINKGO_NODE_ID")
    if node_id is None:
        node_id = socket.gethostname()

    try:
        from ginkgo.workers.execution_node.node import ExecutionNode

        console.print(Panel.fit(
            f"[bold cyan]:execution: ExecutionNode[/bold cyan]\n"
            f"[dim]Node ID:[/dim] {node_id}\n"
            f"[dim]Portfolio:[/dim] {portfolio_id or 'All (from database)'}",
            title="[bold]Portfolio Execution Engine[/bold]",
            border_style="cyan"
        ))

        console.print(f"\n:rocket: [bold green]Creating ExecutionNode '{node_id}'...[/bold green]")
        execution_node = ExecutionNode(node_id=node_id)

        if portfolio_id:
            console.print(f"\n:information: Loading portfolio: {portfolio_id}")
            load_result = execution_node.load_portfolio(portfolio_id)
            if load_result:
                console.print(f":white_check_mark: Portfolio loaded")
            else:
                console.print(f"[red]:x: Failed to load portfolio {portfolio_id}[/red]")

        console.print(f"\n:rocket: [bold green]Starting ExecutionNode...[/bold green]")
        console.print(":information: Press Ctrl+C to stop\n")

        execution_node.start()

        console.print(":white_check_mark: [green]ExecutionNode started[/green]")
        console.print(f":information: Node ID: {execution_node.node_id}")
        console.print(f":information: Portfolios loaded: {len(execution_node.portfolios)}\n")

        def signal_handler(signum, frame):
            console.print("\n\n:stop_button: [yellow]Stopping ExecutionNode...[/yellow]")
            execution_node.stop()
            console.print("[green]:white_check_mark: ExecutionNode stopped[/green]")
            os._exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        while execution_node.is_running:
            time.sleep(1)

    except ImportError as e:
        console.print(f"[red]:x: Failed to import ExecutionNode: {e}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n\n:stop_button: [yellow]Stopping ExecutionNode...[/yellow]")
        execution_node.stop()
        console.print("[green]:white_check_mark: ExecutionNode stopped[/green]")
    except Exception as e:
        console.print(f"[red]:x: Error starting ExecutionNode: {e}[/red]")
        raise typer.Exit(1)


@app.command("scheduler")
def serve_scheduler(
    interval: int = typer.Option(30, "--interval", "-i", help="Schedule interval in seconds"),
):
    """
    :calendar: Start Scheduler for Portfolio dynamic scheduling.

    Examples:
      ginkgo serve scheduler
      ginkgo serve scheduler --interval 60
    """
    import signal
    import time

    try:
        from ginkgo.livecore.scheduler import Scheduler
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
        from ginkgo.data.crud import RedisCRUD

        console.print(Panel.fit(
            f"[bold cyan]:calendar: Scheduler[/bold cyan]\n"
            f"[dim]Schedule Interval:[/dim] {interval}s",
            title="[bold]Portfolio Dynamic Scheduler[/bold]",
            border_style="cyan"
        ))

        console.print(f"\n:hourglass: Connecting to Redis...")
        redis_crud = RedisCRUD()
        redis_client = redis_crud.redis
        if not redis_client:
            console.print("[red]:x: Failed to connect to Redis[/red]")
            raise typer.Exit(1)
        console.print(":white_check_mark: Redis connected")

        console.print(f":satellite: Connecting to Kafka...")
        kafka_producer = GinkgoProducer()
        console.print(":white_check_mark: Kafka connected")

        console.print(f"\n:rocket: [bold green]Creating Scheduler...[/bold green]")
        scheduler = Scheduler(
            redis_client=redis_client,
            kafka_producer=kafka_producer,
            schedule_interval=interval,
            node_id="cli_scheduler"
        )

        console.print(f":rocket: [bold green]Starting Scheduler...[/bold green]")
        console.print(":information: Press Ctrl+C to stop\n")

        scheduler.start()

        console.print(":white_check_mark: [green]Scheduler started[/green]")
        console.print(f":information: Node ID: {scheduler.node_id}")
        console.print(f":information: Schedule Interval: {scheduler.schedule_interval}s\n")

        def signal_handler(signum, frame):
            console.print("\n\n:stop_button: [yellow]Stopping Scheduler...[/yellow]")
            scheduler.stop()
            console.print("[green]:white_check_mark: Scheduler stopped[/green]")
            import os
            os._exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        while scheduler.is_running:
            time.sleep(1)

    except ImportError as e:
        console.print(f"[red]:x: Failed to import Scheduler: {e}[/red]")
        raise typer.Exit(1)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        console.print("\n\n:stop_button: [yellow]Stopping Scheduler...[/yellow]")
        scheduler.stop()
        console.print("[green]:white_check_mark: Scheduler stopped[/green]")
    except Exception as e:
        console.print(f"[red]:x: Error starting Scheduler: {e}[/red]")
        raise typer.Exit(1)


@app.command("tasktimer")
def serve_tasktimer(
    config: Optional[str] = typer.Option(None, "--config", "-c", help="Path to config file"),
    node_id: Optional[str] = typer.Option(None, "--id", "-id", help="Node ID"),
):
    """
    :alarm_clock: Start TaskTimer scheduled task manager.

    Examples:
      ginkgo serve tasktimer
      ginkgo serve tasktimer --config /path/to/config.yml
      ginkgo serve tasktimer --node-id timer_1
    """
    import signal
    import time
    import os
    import socket

    if node_id is None:
        node_id = os.getenv("GINKGO_NODE_ID")
    if node_id is None:
        node_id = f"tasktimer_{socket.gethostname()}"

    try:
        from ginkgo.livecore.task_timer import TaskTimer

        console.print(Panel.fit(
            f"[bold cyan]:alarm_clock: TaskTimer[/bold cyan]\n"
            f"[dim]Node ID:[/dim] {node_id}\n"
            f"[dim]Config:[/dim] {config or '~/.ginkgo/task_timer.yml'}",
            title="[bold]Scheduled Task Manager[/bold]",
            border_style="cyan"
        ))

        timer = TaskTimer(config_path=config, node_id=node_id)

        console.print(f"\n:rocket: [bold green]Starting TaskTimer...[/bold green]")
        console.print(":information: Press Ctrl+C to stop\n")

        success = timer.start()

        if not success:
            console.print("[red]:x: Failed to start TaskTimer[/red]")
            raise typer.Exit(1)

        jobs_status = timer.get_jobs_status()
        console.print(f":white_check_mark: [green]TaskTimer started with {len(jobs_status)} jobs[/green]\n")

        def signal_handler(signum, frame):
            console.print("\n\n:stop_button: [yellow]Stopping TaskTimer...[/yellow]")
            timer.stop()
            console.print("[green]:white_check_mark: TaskTimer stopped[/green]")
            import os
            os._exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        while timer.is_running:
            time.sleep(1)

    except ImportError as e:
        console.print(f"[red]:x: Failed to import TaskTimer: {e}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n\n:stop_button: [yellow]Stopping TaskTimer...[/yellow]")
        timer.stop()
        console.print("[green]:white_check_mark: TaskTimer stopped[/green]")
    except Exception as e:
        console.print(f"[red]:x: Error starting TaskTimer: {e}[/red]")
        raise typer.Exit(1)


@app.command("worker-data")
def serve_worker_data(
    node_id: Optional[str] = typer.Option(None, "--id", "-id", help="Node unique identifier"),
):
    """
    :gear: Start DataWorker in foreground.

    Examples:
      ginkgo serve worker-data
      ginkgo serve worker-data --node-id data_1
    """
    import os
    import socket

    if node_id is None:
        node_id = os.getenv("GINKGO_NODE_ID")
    if node_id is None:
        node_id = f"data_worker_{socket.gethostname()}"

    try:
        from ginkgo.libs.core.threading import GinkgoThreadManager

        gtm = GinkgoThreadManager()

        console.print(Panel.fit(
            f"[bold cyan]:gear: DataWorker[/bold cyan]\n"
            f"[dim]Node ID:[/dim] {node_id}",
            title="[bold]Data Collection Worker[/bold]",
            border_style="cyan"
        ))

        console.print(f"\n:rocket: [bold green]Starting DataWorker '{node_id}'...[/bold green]")
        console.print(":information: Press Ctrl+C to stop\n")

        try:
            gtm.run_data_worker(node_id=node_id)
        except KeyboardInterrupt:
            console.print("\n:information: Worker stopped by user")
        except Exception as e:
            console.print(f"[red]:x: Worker error: {e}[/red]")
            raise typer.Exit(1)

    except ImportError as e:
        console.print(f"[red]:x: Failed to import ThreadManager: {e}[/red]")
        raise typer.Exit(1)


@app.command("worker-backtest")
def serve_worker_backtest(
    node_id: Optional[str] = typer.Option(None, "--id", "-id", help="Node unique identifier"),
    max_tasks: int = typer.Option(5, "--max-tasks", "-m", help="Maximum concurrent tasks"),
):
    """
    :back: Start BacktestWorker in foreground.

    Examples:
      ginkgo serve worker-backtest
      ginkgo serve worker-backtest --node-id backtest_1
      ginkgo serve worker-backtest --max-tasks 10
    """
    import signal
    import time
    import os
    import socket

    if node_id is None:
        node_id = os.getenv("GINKGO_NODE_ID")
    if node_id is None:
        node_id = f"backtest_worker_{socket.gethostname()}"

    try:
        from ginkgo.workers.backtest_worker.node import BacktestWorker
        from ginkgo.interfaces.kafka_topics import KafkaTopics

        console.print(Panel.fit(
            f"[bold cyan]:backtest: BacktestWorker[/bold cyan]\n"
            f"[dim]Node ID:[/dim] {node_id}\n"
            f"[dim]Max Tasks:[/dim] {max_tasks}",
            title="[bold]Backtest Execution Engine[/bold]",
            border_style="cyan"
        ))

        console.print(f"\n:rocket: [bold green]Creating BacktestWorker '{node_id}'...[/bold green]")
        worker = BacktestWorker(worker_id=node_id)
        worker.max_backtests = max_tasks

        def signal_handler(sig, frame):
            console.print("\n\n[yellow]:warning: Stopping...[/yellow]")
            worker.stop()
            console.print("[green]:white_check_mark: BacktestWorker stopped[/green]")
            os._exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        console.print(f"\n:rocket: [bold green]Starting BacktestWorker...[/bold green]")
        console.print(":information: Press Ctrl+C to stop\n")

        worker.start()

        console.print(":white_check_mark: [green]BacktestWorker started[/green]")
        console.print(f":information: Node ID: {worker.worker_id}")
        console.print(f":information: Max tasks: {worker.max_backtests}\n")

        while worker.is_running:
            time.sleep(1)

    except ImportError as e:
        console.print(f"[red]:x: Failed to import BacktestWorker: {e}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]:warning: Stopping...[/yellow]")
        worker.stop()
        console.print("[green]:white_check_mark: BacktestWorker stopped[/green]")
    except Exception as e:
        console.print(f"[red]:x: Error starting BacktestWorker: {e}[/red]")
        raise typer.Exit(1)


@app.command("worker-notify")
def serve_worker_notify(
    node_id: Optional[str] = typer.Option(None, "--id", "-id", help="Node unique identifier"),
):
    """
    :bell: Start NotificationWorker in foreground.

    Examples:
      ginkgo serve worker-notify
      ginkgo serve worker-notify --node-id notify_1
    """
    import signal
    import time
    import os
    import socket

    if node_id is None:
        node_id = os.getenv("GINKGO_NODE_ID")
    if node_id is None:
        node_id = f"notify_worker_{socket.gethostname()}"

    try:
        from ginkgo.notifier.core.notification_worker import NotificationWorker

        console.print(Panel.fit(
            f"[bold cyan]:bell: NotificationWorker[/bold cyan]\n"
            f"[dim]Node ID:[/dim] {node_id}",
            title="[bold]Notification Service[/bold]",
            border_style="cyan"
        ))

        console.print(f"\n:rocket: [bold green]Creating NotificationWorker '{node_id}'...[/bold green]")
        worker = NotificationWorker(node_id=node_id)

        def signal_handler(sig, frame):
            console.print("\n\n[yellow]:warning: Stopping...[/yellow]")
            worker.stop()
            console.print("[green]:white_check_mark: NotificationWorker stopped[/green]")
            os._exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        console.print(f"\n:rocket: [bold green]Starting NotificationWorker...[/bold green]")
        console.print(":information: Press Ctrl+C to stop\n")

        worker.start()

        console.print(":white_check_mark: [green]NotificationWorker started[/green]")
        console.print(f":information: Node ID: {node_id}\n")

        while worker.is_running:
            time.sleep(1)

    except ImportError as e:
        console.print(f"[red]:x: Failed to import NotificationWorker: {e}[/red]")
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n\n[yellow]:warning: Stopping...[/yellow]")
        worker.stop()
        console.print("[green]:white_check_mark: NotificationWorker stopped[/green]")
    except Exception as e:
        console.print(f"[red]:x: Error starting NotificationWorker: {e}[/red]")
        raise typer.Exit(1)
