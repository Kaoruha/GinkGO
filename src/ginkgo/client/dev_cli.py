# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: 开发工具CLI，提供dev_server开发服务器、dev_test测试、dev_build构建等开发辅助命令，支持开发环境管理和快速迭代






import typer
from typing_extensions import Annotated
from rich.console import Console

from ginkgo.libs import GLOG

# All heavy imports moved to function level for faster CLI startup

app = typer.Typer(
    help=":beetle: Module for [bold medium_spring_green]DEVELOPMENT[/]. [grey62]Development tools and utilities.[/grey62]",
    no_args_is_help=True,
)

console = Console()


@app.command("server")
def dev_server(
    daemon: Annotated[bool, typer.Option(case_sensitive=False, help=":wrench: Run as system service")] = False,
):
    """
    :green_circle: Start FastAPI server for web interface and API endpoints.
    """
    from ginkgo.libs import GTM

    if daemon:
        import os
        import subprocess
        console.print(f"Start API Server.")
        try:
            # Run systemctl start ginkgo command
            os.system("systemctl start ginkgo")
            result = subprocess.run(
                ["systemctl", "start", "ginkgo"],  # command and arguments
                check=True,  # throw CalledProcessError if command returns non-zero exit code
                text=True,  # treat input and output as strings
            )
            GLOG.INFO(result)
            GLOG.INFO("Command executed successfully.")
        except subprocess.CalledProcessError as e:
            GLOG.ERROR(f"Error occurred: {e}")
        except Exception as e:
            GLOG.ERROR(f"An unexpected error occurred: {e}")
            return

    import os
    import subprocess
    from ginkgo.libs import GCONF
    
    python_path = GCONF.PYTHONPATH
    dir1 = os.path.dirname(python_path)
    uvicorn_path = os.path.join(dir1, "uvicorn")

    uvicorn_command = [
        uvicorn_path,
        "main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
        "--app-dir",
        f"{GCONF.WORKING_PATH}/api",
        "--timeout-graceful-shutdown",
        "5",
    ]
    subprocess.run(uvicorn_command)


@app.command("jupyter")
def dev_jupyter(
    daemon: Annotated[
        bool, typer.Option(case_sensitive=False, help=":wrench: Run in background (not supported yet)")
    ] = False,
):
    """
    :notebook: Launch Jupyter Lab server for interactive data analysis.
    """
    import os
    import subprocess
    from ginkgo.libs import GCONF
    
    if daemon:
        GLOG.WARN("Daemon mode is not supported for jupyter yet.")

    jupyter_path = os.path.join(os.path.dirname(GCONF.PYTHONPATH), "jupyter")
    subprocess.run([jupyter_path, "lab"])


def _check_ollama_reachable(timeout: float = 2.0) -> bool:
    """#5366: 轻量探活 Ollama 服务（GET /api/tags）。

    返回 True 表示可连通且 HTTP 200；False 表示连不上或超时。
    仅吞 requests 层的连接/超时异常（这正是要友好处理的场景），
    其它异常原样抛出（避免静默掩盖编程错误，参见归因纪律）。
    """
    import requests
    from ginkgo.libs import GCONF

    url = f"{GCONF.OLLAMA_HOST}:{GCONF.OLLAMA_PORT}/api/tags"
    try:
        resp = requests.get(url, timeout=timeout)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        # ConnectionError / Timeout / 等连接层问题 → 友好提示而非 traceback
        return False


@app.command("chat")
def dev_chat():
    """
    :speech_balloon: Launch interactive command-line interface.
    """
    # #5366: 前置守卫——非交互终端 / Ollama 不可用时友好退出而非崩溃。
    # 守卫必须早于 os.system("clear") 与重 import，保证非 TTY 快速失败。
    import sys

    if not sys.stdin.isatty():
        console.print(
            ":warning: [yellow]检测到非交互终端。"
            "请在交互式终端中运行 [bold]ginkgo dev chat[/bold]。[/yellow]"
        )
        raise typer.Exit(1)

    if not _check_ollama_reachable():
        console.print(
            ":warning: [yellow]无法连接 Ollama 服务。"
            "请确认已安装并启动 Ollama（默认 http://localhost:11434）。[/yellow]"
        )
        raise typer.Exit(1)

    import os
    from ginkgo.client.interactive_cli import MyPrompt

    os.system("clear")
    p = MyPrompt()
    p.cmdloop()


@app.command("shell")
def dev_shell():
    """
    :desktop_computer: Launch interactive Python shell with Ginkgo context.
    """
    console.print(":snake: [bold green]Starting Ginkgo Interactive Shell...[/bold green]")

    import tempfile
    import os
    import subprocess
    from ginkgo.libs import GCONF
    
    # Create startup script
    # #6018: 动态构建 src 路径，与 dev_server（GCONF.WORKING_PATH + "/api"）范式一致，
    # 不再硬编码旧路径 /home/kaoru/Applications/Ginkgo/src
    src_path = os.path.join(GCONF.WORKING_PATH, "src")
    startup_script = f"""
import sys
sys.path.insert(0, {src_path!r})

# Import commonly used Ginkgo modules
from ginkgo.libs import GCONF, GLOG, GTM
from ginkgo.data.containers import container
# Import key services for easy access
stockinfo_service = container.stockinfo_service()
bar_service = container.bar_service()
tick_service = container.tick_service()
portfolio_service = container.portfolio_service()

GLOG.INFO("\\n:sparkles: Ginkgo Interactive Shell (New Service Architecture)")
GLOG.INFO("Available imports:")
GLOG.INFO("  - GCONF, GLOG, GTM from ginkgo.libs")
GLOG.INFO("  - container from ginkgo.data.containers")
GLOG.INFO("  - stockinfo_service, bar_service, tick_service, portfolio_service")
GLOG.INFO("\\nService Usage Examples:")
GLOG.INFO("  - stockinfo_service.get()")
GLOG.INFO("  - bar_service.get_bars_page_filtered()")
GLOG.INFO("  - portfolio_service.get_portfolios()")
GLOG.INFO("  - All modules from ginkgo.data")
GLOG.INFO("  - All modules from ginkgo.trading")
GLOG.INFO("\\nType 'help()' for Python help, or 'exit()' to quit.\\n")
"""

    # Write startup script to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(startup_script)
        startup_file = f.name

    try:
        # Launch Python with startup script
        python_path = GCONF.PYTHONPATH
        subprocess.run([python_path, "-i", startup_file])
    finally:
        # Clean up temporary file
        os.unlink(startup_file)


@app.command("docs")
def dev_docs(
    serve: Annotated[bool, typer.Option(help=":globe_with_meridians: Serve documentation locally")] = False,
    build: Annotated[bool, typer.Option(help=":building_construction: Build documentation")] = False,
):
    """
    :books: Documentation tools for development.
    """
    if build:
        console.print(":building_construction: Building documentation...")
        # Add documentation build logic here
        console.print("Documentation build not implemented yet.")

    if serve:
        console.print(":globe_with_meridians: Serving documentation locally...")
        # Add documentation serve logic here
        console.print("Documentation serve not implemented yet.")

    if not build and not serve:
        console.print("Specify --build or --serve option.")


@app.command("test")
def dev_test(
    coverage: Annotated[bool, typer.Option(help=":bar_chart: Run with coverage report")] = False,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help=":loud_sound: Verbose output")] = False,
    pattern: Annotated[str, typer.Option(help=":mag: Test file pattern")] = None,
):
    """
    :test_tube: Run development tests with various options.
    """
    console.print(":test_tube: [bold blue]Running development tests...[/bold blue]")

    import subprocess
    from ginkgo.libs import GCONF
    
    # Ensure debug mode is enabled for testing
    if not GCONF.DEBUGMODE:
        console.print(":warning: [yellow]Debug mode is not enabled. Tests may fail.[/yellow]")
        console.print("Enable debug mode with: [bold]ginkgo system config set --debug on[/bold]")

    # Build pytest command
    cmd = ["python", "-m", "pytest"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(["--cov=src/ginkgo", "--cov-report=html", "--cov-report=term"])

    if pattern:
        cmd.extend(["-k", pattern])

    cmd.append("tests/")

    # Run tests
    subprocess.run(cmd, cwd=GCONF.WORKING_PATH)


@app.command("lint")
def dev_lint(
    fix: Annotated[bool, typer.Option(help=":wrench: Auto-fix issues where possible")] = False,
):
    """
    :mag: Run code linting and formatting checks.
    """
    console.print(":mag: [bold blue]Running code linting...[/bold blue]")

    import subprocess
    
    # Check if tools are available
    tools = ["black", "isort", "flake8"]
    missing_tools = []

    for tool in tools:
        try:
            subprocess.run([tool, "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing_tools.append(tool)

    if missing_tools:
        console.print(f":warning: [yellow]Missing tools: {', '.join(missing_tools)}[/yellow]")
        console.print("Install with: [bold]pip install black isort flake8[/bold]")
        return

    # Run formatting tools
    if fix:
        console.print(":wrench: Auto-fixing code formatting...")
        subprocess.run(["black", "src/", "tests/"])
        subprocess.run(["isort", "src/", "tests/"])

    # Run linting
    console.print(":mag: Checking code style...")
    subprocess.run(["flake8", "src/", "tests/"])


@app.command("profile")
def dev_profile(
    script: Annotated[str, typer.Argument(help="Python script to profile")],
    output: Annotated[str, typer.Option(help=":file_folder: Output file for profile results")] = "profile.stats",
):
    """
    :stopwatch: Profile Python script performance.
    """
    import subprocess
    
    console.print(f":stopwatch: [bold blue]Profiling {script}...[/bold blue]")

    cmd = ["python", "-m", "cProfile", "-o", output, script]

    subprocess.run(cmd)
    console.print(f":chart_with_upwards_trend: Profile results saved to {output}")
    console.print(f"View with: [bold]python -m pstats {output}[/bold]")
