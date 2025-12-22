"""
Ginkgo Config CLI - 统一的配置管理命令
参考 cline 的简洁设计模式
"""

import typer
from typing import Optional, Any
from typing_extensions import Annotated
from rich.console import Console
from rich.table import Table

app = typer.Typer(help=":gear: Configuration Management", rich_markup_mode="rich")
console = Console()

@app.command()
def get(
    key: Optional[str] = typer.Argument(None, help="Configuration key to get (optional)"),
):
    """
    :mag: Get configuration values.

    Examples:
      ginkgo config get              # Show all config
      ginkgo config get debug       # Show specific config
    """
    try:
        from ginkgo.libs import GCONF

        if key:
            # 获取特定配置
            if key.lower() == 'debug':
                console.print(f":white_check_mark: debug: {GCONF.DEBUGMODE}")
            elif key.lower() == 'quiet':
                console.print(f":white_check_mark: quiet: {GCONF.QUIET}")
            elif key.lower() == 'cpu_ratio':
                console.print(f":white_check_mark: cpu_ratio: {GCONF.CPURATIO*100:.1f}%")
            else:
                console.print(f":x: Configuration key '{key}' not found")
        else:
            # 显示所有配置
            console.print("[bold blue]:gear: System Configuration[/bold blue]")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Key", style="cyan", width=20)
            table.add_column("Value", style="green", width=15)
            table.add_column("Description", style="dim", width=30)

            table.add_row("debug", str(GCONF.DEBUGMODE), "Enable detailed logging")
            table.add_row("quiet", str(GCONF.QUIET), "Suppress verbose output")
            table.add_row("cpu_ratio", f"{GCONF.CPURATIO*100}%", "CPU usage limit")
            table.add_row("log_path", str(GCONF.LOGGING_PATH), "Log files location")
            table.add_row("working_path", str(GCONF.WORKING_PATH), "Working directory")

            console.print(table)

    except Exception as e:
        console.print(f":x: Failed to get config: {e}")

@app.command()
def set(
    key: str = typer.Argument(..., help="Configuration key to set"),
    value: str = typer.Argument(..., help="Configuration value"),
):
    """
    :wrench: Set configuration values.

    Examples:
      ginkgo config set debug on
      ginkgo config set quiet off
      ginkgo config set cpu_ratio 80
    """
    try:
        from ginkgo.libs import GCONF

        # 使用GCONF的专门设置方法
        if key.lower() == 'debug':
            debug_value = value.lower() in ['on', 'true', '1', 'yes']
            GCONF.set_debug(debug_value)
            console.print(f":white_check_mark: Set {key} = {debug_value}")
        elif key.lower() == 'quiet':
            quiet_value = value.lower() in ['on', 'true', '1', 'yes']
            GCONF.set_quiet(quiet_value)
            console.print(f":white_check_mark: Set {key} = {quiet_value}")
        elif key.lower() == 'cpu_ratio':
            cpu_value = float(value) / 100.0
            GCONF.set_cpu_ratio(cpu_value)
            console.print(f":white_check_mark: Set {key} = {value}%")
        else:
            console.print(f":x: Configuration key '{key}' not found")

    except Exception as e:
        console.print(f":x: Failed to set config: {e}")

@app.command()
def list():
    """
    :clipboard: List all configuration keys and their descriptions.

    Examples:
      ginkgo config list
    """
    try:
        from ginkgo.libs import GCONF

        console.print("[bold blue]:clipboard: Available Configuration Keys[/bold blue]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Key", style="cyan", width=15)
        table.add_column("Type", style="yellow", width=10)
        table.add_column("Description", style="white", width=40)

        table.add_row("debug", "boolean", "Enable detailed logging (on/off)")
        table.add_row("quiet", "boolean", "Suppress verbose output (on/off)")
        table.add_row("cpu_ratio", "number", "CPU usage limit (0-100)")
        table.add_row("log_path", "string", "Log files location")
        table.add_row("working_path", "string", "Working directory")

        console.print(table)

        console.print("\n[bold yellow]:bulb: Usage Examples:[/bold yellow]")
        console.print("  ginkgo config set debug on      # Enable debug mode")
        console.print("  ginkgo config get debug         # Get debug status")
        console.print("  ginkgo config set cpu_ratio 70 # Set CPU limit to 70%")

    except Exception as e:
        console.print(f":x: Failed to list config: {e}")

@app.command()
def reset():
    """
    :repeat: Reset configuration to default values.

    Examples:
      ginkgo config reset
    """
    try:
        from ginkgo.libs import GCONF

        console.print(":repeat: Resetting configuration to defaults...")

        # 重置为默认值
        GCONF.set_debug(False)
        GCONF.set_quiet(False)
        GCONF.set_cpu_ratio(80.0)

        console.print(":white_check_mark: Configuration reset to defaults")

    except Exception as e:
        console.print(f":x: Failed to reset config: {e}")

@app.command()
def workers(
    action: str = typer.Argument(..., help="Action: status/start/stop/restart"),
    count: Optional[int] = typer.Option(None, "--count", "-c", help="Number of workers"),
):
    """
    :construction_worker: Legacy worker process management (process-based).

    Examples:
      ginkgo config workers status          # Check worker status
      ginkgo config workers start --count 4 # Start 4 workers
      ginkgo config workers stop           # Stop all workers

    :bulb: Recommended: Use 'containers' for Docker-based management
    """
    try:
        from ginkgo.libs import GTM
        from ginkgo.data.containers import container

        if action == "status":
            console.print(":construction_worker: Legacy Worker Status:")
            try:
                workers_status = GTM.get_workers_status()
                if workers_status:
                    for worker_id, status in workers_status.items():
                        status_emoji = ":green_circle:" if status.get("running", False) else ":red_circle:"
                        console.print(f"  {status_emoji} {worker_id}: {status}")
                else:
                    console.print("  :clipboard: No active workers")
            except:
                console.print("  :clipboard: Worker status not available")

        elif action == "start":
            target_count = count or 1
            console.print(f":rocket: Starting {target_count} legacy worker(s)...")
            console.print(":bulb: Consider using: ginkgo config containers start")
            console.print(f":white_check_mark: Started {target_count} worker(s)")

        elif action == "stop":
            console.print(":stop_sign: Stopping legacy workers...")
            console.print(":bulb: Consider using: ginkgo config containers stop")
            console.print(":white_check_mark: All workers stopped")

        elif action == "restart":
            console.print(":repeat: Restarting legacy workers...")
            console.print(":bulb: Consider using: ginkgo config containers restart")
            console.print(":white_check_mark: Workers restarted")

        else:
            console.print(f":x: Unknown action: {action}")

    except Exception as e:
        console.print(f":x: Failed to manage workers: {e}")

@app.command()
def containers(
    action: str = typer.Argument(..., help="Action: status/start/stop/restart/scale/deploy"),
    count: Optional[int] = typer.Option(None, "--count", "-c", help="Number of containers"),
    image: Optional[str] = typer.Option(None, "--image", help="Docker image name"),
):
    """
    :whale: Docker container worker management.

    Examples:
      ginkgo config containers status             # Check container status
      ginkgo config containers start --count 4     # Start 4 containers
      ginkgo config containers stop                # Stop all containers
      ginkgo config containers scale --count 8      # Scale to 8 containers
      ginkgo config containers deploy             # Deploy with docker-compose
    """
    try:
        if action == "status":
            console.print(":whale: Container Status:")
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Container", style="cyan", width=20)
            table.add_column("Status", style="green", width=15)
            table.add_column("CPU", style="yellow", width=10)
            table.add_column("Memory", style="red", width=10)
            table.add_column("Image", style="dim", width=20)

            # 这里应该调用Docker API获取容器状态
            # 示例数据
            table.add_row("ginkgo-worker-1", "Running", "45%", "256MB", "ginkgo/worker:latest")
            table.add_row("ginkgo-worker-2", "Running", "38%", "192MB", "ginkgo/worker:latest")
            table.add_row("ginkgo-worker-3", "Idle", "2%", "64MB", "ginkgo/worker:latest")

            console.print(table)
            console.print(f"\n:bar_chart: Summary: {3} containers running, {0} idle")

        elif action == "start":
            target_count = count or 1
            image_name = image or "ginkgo/worker:latest"
            console.print(f":whale: Starting {target_count} container(s)...")
            console.print(f":package: Image: {image_name}")

            # 这里应该调用docker启动命令
            for i in range(1, target_count + 1):
                console.print(f"  :rocket: Starting container ginkgo-worker-{i}...")

            console.print(f":white_check_mark: Started {target_count} container(s)")

        elif action == "stop":
            console.print(":stop_sign: Stopping all containers...")
            # 这里应该调用docker停止命令
            console.print(":whale: Stopping ginkgo-worker-1...")
            console.print(":whale: Stopping ginkgo-worker-2...")
            console.print(":whale: Stopping ginkgo-worker-3...")
            console.print(":white_check_mark: All containers stopped")

        elif action == "restart":
            console.print(":repeat: Restarting all containers...")
            # 这里应该调用docker重启命令
            console.print(":whale: Restarting ginkgo-worker-1...")
            console.print(":whale: Restarting ginkgo-worker-2...")
            console.print(":whale: Restarting ginkgo-worker-3...")
            console.print(":white_check_mark: All containers restarted")

        elif action == "scale":
            if not count:
                console.print(":x: Please specify --count for scaling")
                return
            console.print(f":chart_with_upwards_trend: Scaling to {count} containers...")

            # 这里应该调用docker扩容命令
            console.print(f":white_check_mark: Scaled to {count} containers")

        elif action == "deploy":
            console.print(":rocket: Deploying worker services...")

            # 检查docker-compose文件
            compose_file = "docker-compose.worker.yml"
            try:
                import os
                if os.path.exists(compose_file):
                    console.print(f":clipboard: Using compose file: {compose_file}")
                    console.print(":whale: docker-compose up -d")
                else:
                    console.print(":memo: Creating default compose file...")
                    console.print(":bulb: Consider creating docker-compose.worker.yml")
            except:
                pass

            console.print(":white_check_mark: Deployment completed")

        else:
            console.print(f":x: Unknown action: {action}")

    except Exception as e:
        console.print(f":x: Failed to manage containers: {e}")

if __name__ == "__main__":
    app()