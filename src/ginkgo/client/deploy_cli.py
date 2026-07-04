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
    portfolio_id: Annotated[str, typer.Argument(help="Portfolio ID")],
    mode: Annotated[str, typer.Option("--mode", "-m", help="部署模式: paper 或 live")] = "paper",
    account: Annotated[Optional[str], typer.Option("--account", "-a", help="实盘账号ID (live模式必填)")] = None,
    name: Annotated[Optional[str], typer.Option("--name", "-n", help="新Portfolio名称")] = None,
    source_task: Annotated[Optional[str], typer.Option("--source-task", help="源回测任务ID (可选, 记录回测→部署链路)")] = None,
):
    """一键部署：Portfolio → 纸上交易/实盘"""
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
        console.print(f"  Portfolio: {portfolio_id}")
        console.print(f"  模式: {mode}")

        svc = trading_container.deployment_service()
        result = svc.deploy(
            portfolio_id=portfolio_id,
            mode=mode_map[mode],
            account_id=account,
            name=name,
            source_task_id=source_task,
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
    deployment_id: Annotated[str, typer.Argument(help="部署记录 ID 或 Portfolio ID（按部署 UUID / 源组合 / 目标组合 任一反查）")],
):
    """查看部署详情（#4982：支持按部署 UUID 或 portfolio_id 反查）"""
    try:
        from ginkgo.trading.containers import trading_container

        svc = trading_container.deployment_service()
        result = svc.get_deployment_by_id(deployment_id)

        # #4982: 按 deployment UUID 查无记录时，回退到 source/target portfolio_id 反查。
        # find_by_* 返回 list[dict]，取最近一条归一为单 dict，
        # 复用同一 ServiceResult 让后续展示逻辑与 get_deployment_by_id 形状对齐。
        if not result.success:
            for finder in (svc.find_by_source_portfolio, svc.find_by_target_portfolio):
                fb = finder(deployment_id)
                if fb.success and fb.data:
                    records = fb.data if isinstance(fb.data, list) else [fb.data]
                    fb.data = records[0]
                    result = fb
                    break

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
            table.add_row("状态", data.get("status_name") or str(data.get("status", "")))
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
    portfolio_id: Annotated[Optional[str], typer.Option("--portfolio", "-p", help="按Portfolio ID筛选")] = None,
):
    """列出部署记录"""
    try:
        from ginkgo.trading.containers import trading_container

        svc = trading_container.deployment_service()
        result = svc.list_deployments(portfolio_id=portfolio_id)

        if result.success and result.data:
            table = Table(title="部署记录")
            # #4719: id 列 overflow="fold"——rich 默认 ellipsis 会用 … 截断长 UUID，
            # 导致终端用户也看不到完整 id；fold 折行完整显示，终端宽时单行、窄时多行
            table.add_column("Deployment ID", style="cyan", overflow="fold")
            table.add_column("源任务")
            table.add_column("目标Portfolio", overflow="fold")
            table.add_column("模式")
            table.add_column("状态")
            table.add_column("创建时间")

            for d in result.data:
                mode_str = "纸上" if d["mode"] == 1 else "实盘"
                # #4719: 输出完整 UUID，list→info round-trip 可直接复制；rich Table 自适应列宽
                table.add_row(
                    d["deployment_id"],
                    d["source_task_id"],
                    d["target_portfolio_id"],
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
