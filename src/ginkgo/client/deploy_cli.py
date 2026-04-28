# Upstream: CLI入口 (ginkgo deploy命令)
# Downstream: DeploymentService, trading_container.deployment_service()
# Role: 回测结果一键部署为纸上交易/实盘的CLI命令

import typer
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Deploy backtest to paper/live trading")
console = Console()


@app.command("")
def deploy(
    backtest_task_id: Annotated[str, typer.Argument(help="回测任务ID (task_id)")],
    mode: Annotated[str, typer.Option("--mode", "-m", help="部署模式: paper 或 live")] = "paper",
    account: Annotated[Optional[str], typer.Option("--account", "-a", help="实盘账号ID (live模式必填)")] = None,
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="新Portfolio名称")] = None,
):
    """一键部署：回测结果 → 纸上交易/实盘"""
    try:
        from ginkgo.trading.containers import trading_container
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        mode_map = {
            "paper": PORTFOLIO_MODE_TYPES.PAPER,
            "live": PORTFOLIO_MODE_TYPES.LIVE,
        }
        if mode not in mode_map:
            console.print(f"[red]无效的部署模式: {mode}[/red]")
            raise typer.Exit(1)

        if mode == "live" and not account:
            console.print("[red]实盘模式需要 --account 参数[/red]")
            raise typer.Exit(1)

        console.print(f"[bold]部署中...[/bold]")
        console.print(f"  回测任务: {backtest_task_id}")
        console.print(f"  模式: {mode}")

        svc = trading_container.deployment_service()
        result = svc.deploy(
            backtest_task_id=backtest_task_id,
            mode=mode_map[mode],
            account_id=account,
            name=name,
        )

        if result.success:
            data = result.data
            console.print(f"[green]部署成功![/green]")
            console.print(f"  Portfolio ID: [cyan]{data['portfolio_id']}[/cyan]")
            if data.get("deployment_id"):
                console.print(f"  Deployment ID: [cyan]{data['deployment_id']}[/cyan]")
        else:
            console.print(f"[red]部署失败: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("info")
def info(
    portfolio_id: Annotated[str, typer.Argument(help="部署后的Portfolio ID")],
):
    """查看部署详情"""
    try:
        from ginkgo.trading.containers import trading_container

        svc = trading_container.deployment_service()
        result = svc.get_deployment_info(portfolio_id)

        if result.success:
            data = result.data
            table = Table(title="部署详情")
            table.add_column("字段", style="cyan")
            table.add_column("值")
            table.add_row("源回测任务", data.get("source_task_id", ""))
            table.add_row("源Portfolio", data.get("source_portfolio_id", ""))
            table.add_row("目标Portfolio", data.get("target_portfolio_id", ""))
            mode_str = "纸上交易" if data.get("mode") == 1 else "实盘"
            table.add_row("模式", mode_str)
            table.add_row("实盘账号", data.get("account_id", "N/A"))
            table.add_row("状态", str(data.get("status", "")))
            table.add_row("创建时间", data.get("create_at", ""))
            console.print(table)
        else:
            console.print(f"[red]{result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_deployments(
    task_id: Annotated[Optional[str], typer.Option("--task", "-t", help="按回测任务ID筛选")] = None,
):
    """列出部署记录"""
    try:
        from ginkgo.trading.containers import trading_container

        svc = trading_container.deployment_service()
        result = svc.list_deployments(source_task_id=task_id)

        if result.success and result.data:
            table = Table(title="部署记录")
            table.add_column("Deployment ID", style="cyan")
            table.add_column("源任务")
            table.add_column("目标Portfolio")
            table.add_column("模式")
            table.add_column("状态")
            table.add_column("创建时间")

            for d in result.data:
                mode_str = "纸上" if d["mode"] == 1 else "实盘"
                table.add_row(
                    d["deployment_id"][:8] + "...",
                    d["source_task_id"],
                    d["target_portfolio_id"][:8] + "...",
                    mode_str,
                    str(d["status"]),
                    d.get("create_at", "")[:19] if d.get("create_at") else "",
                )
            console.print(table)
        else:
            console.print("[yellow]无部署记录[/yellow]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
