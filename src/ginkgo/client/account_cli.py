# Upstream: CLI入口 (ginkgo account 命令组)
# Downstream: data_container.live_account_service()
# Role: 实盘账户管理 CLI — 创建/列出/查看实盘账户
#
# #6284: LiveAccountService/CRUD 已就绪，补 CLI 层。
# 创建的 account_uuid 供 `ginkgo deploy --mode live --account <uuid>` 使用（见 deploy_cli.py）。

import typer
from typing import Optional
from typing_extensions import Annotated
from rich.console import Console
from rich.table import Table

app = typer.Typer(help="Live account management (实盘账户管理)")
console = Console()


@app.command("create")
def create(
    user_id: Annotated[str, typer.Argument(help="用户ID")],
    exchange: Annotated[str, typer.Option("--exchange", "-e", help="交易所: okx / binance")],
    name: Annotated[str, typer.Option("--name", "-n", help="账号名称")],
    api_key: Annotated[str, typer.Option("--api-key", help="API Key")],
    api_secret: Annotated[str, typer.Option("--api-secret", help="API Secret")],
    passphrase: Annotated[Optional[str], typer.Option("--passphrase", help="Passphrase (OKX 必填)")] = None,
    environment: Annotated[str, typer.Option("--environment", help="环境: production / testnet")] = "testnet",
    description: Annotated[Optional[str], typer.Option("--description", help="账号描述")] = None,
    auto_validate: Annotated[bool, typer.Option("--auto-validate", help="创建时自动验证凭证")] = False,
):
    """创建实盘账户（凭证经 EncryptionService 加密入库）"""
    try:
        from ginkgo.data.containers import container

        svc = container.live_account_service()
        result = svc.create_account(
            user_id=user_id,
            exchange=exchange,
            name=name,
            api_key=api_key,
            api_secret=api_secret,
            passphrase=passphrase,
            environment=environment,
            description=description,
            auto_validate=auto_validate,
        )

        if result.get("success"):
            account_uuid = result.get("data", {}).get("account_uuid", "")
            console.print(f"[green]实盘账户创建成功[/green]")
            console.print(f"  Account UUID: [cyan]{account_uuid}[/cyan]")
            console.print(f"  交易所: {exchange}  环境: {environment}")
            console.print(f"  (供 [dim]ginkgo deploy --mode live --account {account_uuid}[/dim] 使用)")
        else:
            console.print(f"[red]创建失败: {result.get('error') or result.get('message')}[/red]")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_accounts(
    user_id: Annotated[str, typer.Argument(help="用户ID")],
    page: Annotated[int, typer.Option("--page", help="页码（从1开始）")] = 1,
    page_size: Annotated[int, typer.Option("--page-size", help="每页数量")] = 20,
    exchange: Annotated[Optional[str], typer.Option("--exchange", "-e", help="按交易所筛选")] = None,
    environment: Annotated[Optional[str], typer.Option("--environment", help="按环境筛选")] = None,
    status: Annotated[Optional[str], typer.Option("--status", help="按状态筛选")] = None,
):
    """列出用户的实盘账户（不回显凭据）"""
    try:
        from ginkgo.data.containers import container

        svc = container.live_account_service()
        result = svc.get_user_accounts(
            user_id=user_id,
            page=page,
            page_size=page_size,
            exchange=exchange,
            environment=environment,
            status=status,
        )

        if not result.get("success"):
            console.print(f"[red]查询失败: {result.get('error') or result.get('message')}[/red]")
            raise typer.Exit(1)

        data = result.get("data", {})
        accounts = data.get("accounts", [])
        if not accounts:
            console.print("[yellow]无实盘账户记录[/yellow]")
            return

        table = Table(title=f"实盘账户 (共 {data.get('total', 0)} 条)")
        table.add_column("UUID", style="cyan")
        table.add_column("名称")
        table.add_column("交易所")
        table.add_column("环境")
        table.add_column("状态")
        for acc in accounts:
            table.add_row(
                str(acc.get("uuid", ""))[:12],
                str(acc.get("name", "")),
                str(acc.get("exchange", "")),
                str(acc.get("environment", "")),
                str(acc.get("status", "")),
            )
        console.print(table)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("get")
def get_account(
    account_uuid: Annotated[str, typer.Argument(help="实盘账户 UUID")],
):
    """查看实盘账户详情（不回显凭据）"""
    try:
        from ginkgo.data.containers import container

        svc = container.live_account_service()
        result = svc.get_account_by_uuid(account_uuid)

        if not result.get("success"):
            console.print(f"[red]查询失败: {result.get('error') or result.get('message')}[/red]")
            raise typer.Exit(1)

        acc = result.get("data") or {}
        table = Table(title="实盘账户详情")
        table.add_column("字段", style="cyan")
        table.add_column("值")
        for key in ("uuid", "name", "exchange", "environment", "status",
                    "description", "validation_status", "last_validated_at", "create_at"):
            if key in acc:
                table.add_row(key, str(acc.get(key, "")))
        console.print(table)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
