# Upstream: CLI主入口(ginkgo mongo命令调用)
# Downstream: GinkgoMongo驱动(连接池/健康检查)、Rich库(表格/进度条显示)
# Role: MongoDB CLI命令提供status状态查询等MongoDB管理功能


"""
Ginkgo MongoDB CLI - MongoDB 数据库命令
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich import print

app = typer.Typer(help=":page_facing_up: MongoDB management", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


@app.command()
def status():
    """
    :gear: Show MongoDB connection and database status.
    """
    try:
        from ginkgo.data.drivers import get_connection_status
        from ginkgo.libs import GCONF

        console.print("[bold blue]:gear:  MongoDB Status[/bold blue]\n")

        # 主动初始化MongoDB连接以获取准确状态
        try:
            from ginkgo.data.drivers import _connection_manager
            _connection_manager.get_mongo_connection()
        except Exception:
            pass  # 连接失败，继续获取错误状态

        # 获取连接状态
        conn_status = get_connection_status()
        mongo_status = conn_status.get("mongodb", {})

        # 创建状态表格
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Property", style="cyan", width=25)
        table.add_column("Value", style="green")

        # 连接状态
        is_healthy = mongo_status.get("healthy", False)
        status_icon = ":white_check_mark:" if is_healthy else ":x:"
        status_text = "[green]Connected[/green]" if is_healthy else "[red]Disconnected[/red]"
        table.add_row("Connection", f"{status_icon} {status_text}")

        # 连接信息
        if is_healthy:
            table.add_row("Host", f"{GCONF.MONGOHOST}")
            table.add_row("Port", f"{GCONF.MONGOPORT}")
            table.add_row("Database", f"{GCONF.MONGODB}")
            table.add_row("User", f"{GCONF.MONGOUSER}")

            # 获取集合信息
            try:
                from ginkgo.data.drivers import _connection_manager
                mongo_conn = _connection_manager.get_mongo_connection()
                collections = mongo_conn.list_collections()
                table.add_row("Collections", f"{len(collections)}")

                # 统计索引数量
                total_indexes = 0
                for coll_name in collections:
                    coll = mongo_conn.get_collection(coll_name)
                    indexes = coll.list_indexes()
                    total_indexes += len(list(indexes)) - 1  # 减去默认的 _id_ 索引
                table.add_row("Indexes", f"{total_indexes}")

            except Exception as e:
                table.add_row("Collections", f"[red]Error: {str(e)[:20]}...[/red]")
        else:
            # 显示错误信息
            error = mongo_status.get("error", "Unknown error")
            status_desc = mongo_status.get("status", "")
            if status_desc:
                table.add_row("Status", f"[yellow]{status_desc}[/yellow]")
            if error:
                table.add_row("Error", f"[red]{error}[/red]")

        console.print(table)

        # 如果连接成功，显示集合列表
        if is_healthy:
            try:
                from ginkgo.data.drivers import _connection_manager
                mongo_conn = _connection_manager.get_mongo_connection()
                collections = mongo_conn.list_collections()

                if collections:
                    console.print("\n[bold]Collections:[/bold]")
                    for coll_name in sorted(collections):
                        count = mongo_conn.get_collection_size(coll_name)
                        console.print(f"  • {coll_name}: {count} documents")
                else:
                    console.print("\n[dim]No collections found. Run 'ginkgo data init' to create collections.[/dim]")

            except Exception as e:
                console.print(f"\n[yellow]Could not list collections: {e}[/yellow]")

    except Exception as e:
        console.print(f"[red]:x: Error getting MongoDB status: {e}[/red]")
        console.print("[dim]Tip: Ensure MongoDB is running and credentials are configured in ~/.ginkgo/secure.yml[/dim]")
        raise typer.Exit(1)
