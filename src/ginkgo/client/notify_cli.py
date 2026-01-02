# Upstream: CLI主入口(ginkgo notify命令调用)
# Downstream: NotificationService(通知服务)、UserCRUD(用户CRUD)、UserContactCRUD(联系方式CRUD)
# Role: 通知发送CLI，提供send发送、template模板发送、history历史查询等命令，支持基于用户和用户组的通知功能


"""
Ginkgo Notification CLI - 通知发送命令
"""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
import json

app = typer.Typer(help=":bell: Notification sending", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


# ============================================================================
# Notification Commands
# ============================================================================

@app.command("send")
def send_notification(
    user: Optional[List[str]] = typer.Option(None, "--user", "-u", help="User UUID(s) or Name(s) - can be repeated"),
    group: Optional[List[str]] = typer.Option(None, "--group", "-g", help="Group ID(s) or Name(s) - can be repeated"),
    content: str = typer.Option(..., "--content", "-c", help="Notification content"),
    title: Optional[str] = typer.Option(None, "--title", "-t", help="Notification title"),
    priority: int = typer.Option(1, "--priority", "-p", min=0, max=3, help="Priority (0=low, 1=normal, 2=high, 3=urgent)"),
    color: Optional[int] = typer.Option(None, "--color", help="Embed color (decimal, e.g., 3447003 for blue)"),
    fields: Optional[str] = typer.Option(None, "--fields", "-f", help="Fields as JSON array, e.g., '[{\"name\":\"Status\",\"value\":\"OK\",\"inline\":true}]'"),
    footer: Optional[str] = typer.Option(None, "--footer", help="Footer as JSON, e.g., '{\"text\":\"Footer text\",\"icon_url\":\"https://...\"}'"),
    author: Optional[str] = typer.Option(None, "--author", help="Author as JSON, e.g., '{\"name\":\"Author\",\"url\":\"https://...\"}'"),
    url: Optional[str] = typer.Option(None, "--url", help="Title URL (makes title clickable)"),
    async_mode: bool = typer.Option(False, "--async", "-a", help="Send via Kafka (async mode)"),
):
    """
    :mailbox: Send a notification to users and/or groups.

    Examples:
      ginkgo notify send --user "Alice" --content "Hello"
      ginkgo notify send -u <uuid> --title "Alert" --content "Warning!"
      ginkgo notify send -g traders --title "Trade Signal" --fields '[{"name":"Symbol","value":"AAPL"},{"name":"Price","value":"$150"}]'
      ginkgo notify send --user "Bob" --footer '{"text":"Ginkgo System"}' --color 3447003
      ginkgo notify send --user "Alice" --content "Hello" --async  # Send via Kafka
    """
    try:
        from ginkgo import service_hub

        # 验证参数
        if not user and not group:
            console.print("[red]:x: Either --user or --group is required[/red]")
            raise typer.Exit(1)

        # Get service from notifier container (new architecture)
        service = service_hub.notifier.notification_service()

        # 收集所有唯一的用户 UUID
        unique_user_uuids = set()
        resolved_users = {}  # {uuid: original_input} 用于错误提示

        # 解析用户输入（UUID 或 name）
        if user:
            for user_input in user:
                resolved_uuid = service._resolve_user_uuid(user_input)
                if resolved_uuid:
                    unique_user_uuids.add(resolved_uuid)
                    resolved_users[resolved_uuid] = user_input
                else:
                    console.print(f"[yellow]:warning: User not found: {user_input}[/yellow]")

        # 解析组输入（name 或 uuid），获取组内用户
        if group:
            for group_input in group:
                group_user_uuids = service._resolve_group_uuids(group_input)
                if group_user_uuids:
                    unique_user_uuids.update(group_user_uuids)
                else:
                    console.print(f"[yellow]:warning: Group not found: {group_input}[/yellow]")

        if not unique_user_uuids:
            console.print("[red]:x: No valid users found[/red]")
            raise typer.Exit(1)

        # 解析 JSON 格式的参数
        parsed_fields = None
        parsed_footer = None
        parsed_author = None

        if fields:
            try:
                parsed_fields = json.loads(fields)
                if not isinstance(parsed_fields, list):
                    console.print("[red]:x: --fields must be a JSON array[/red]")
                    raise typer.Exit(1)
            except json.JSONDecodeError as e:
                console.print(f"[red]:x: Invalid JSON in --fields: {e}[/red]")
                raise typer.Exit(1)

        if footer:
            try:
                parsed_footer = json.loads(footer)
                if not isinstance(parsed_footer, dict):
                    console.print("[red]:x: --footer must be a JSON object[/red]")
                    raise typer.Exit(1)
            except json.JSONDecodeError as e:
                console.print(f"[red]:x: Invalid JSON in --footer: {e}[/red]")
                raise typer.Exit(1)

        if author:
            try:
                parsed_author = json.loads(author)
                if not isinstance(parsed_author, dict):
                    console.print("[red]:x: --author must be a JSON object[/red]")
                    raise typer.Exit(1)
            except json.JSONDecodeError as e:
                console.print(f"[red]:x: Invalid JSON in --author: {e}[/red]")
                raise typer.Exit(1)

        # 准备发送参数
        send_kwargs = {
            "content": content,
            "title": title,
            "priority": priority,
        }

        # 添加可选参数
        if color is not None:
            send_kwargs["color"] = color
        if parsed_fields:
            send_kwargs["fields"] = parsed_fields
        if parsed_footer:
            send_kwargs["footer"] = parsed_footer
        if parsed_author:
            send_kwargs["author"] = parsed_author
        if url:
            send_kwargs["url"] = url

        # 发送通知
        results = []
        success_count = 0
        failed_count = 0

        if async_mode:
            # 使用 Kafka 异步发送
            console.print("[cyan]:mailbox: Async mode - Sending via Kafka[/cyan]")

            for user_uuid in unique_user_uuids:
                result = service.send_async(
                    user_uuid=user_uuid,
                    channels=["webhook"],  # 默认使用 webhook，会根据用户配置自动选择
                    **send_kwargs
                )

                results.append({
                    "user_uuid": user_uuid,
                    "success": result.is_success,
                    "message": result.message,
                    "message_id": result.data.get("message_id") if result.data else None
                })

                if result.is_success:
                    success_count += 1
                    console.print(f"[green]:white_check_mark: Queued for {user_uuid[:16]}...[/green]")
                else:
                    failed_count += 1
                    console.print(f"[red]:x: Failed to queue for {user_uuid[:16]}...: {result.message}[/red]")
        else:
            # 同步发送（直接调用渠道）
            console.print("[dim]:mailbox: Sync mode - Sending directly to channels[/dim]")

            for user_uuid in unique_user_uuids:
                result = service.send_to_user(
                    user_uuid=user_uuid,
                    **send_kwargs
                )

                results.append({
                    "user_uuid": user_uuid,
                    "success": result.is_success,
                    "message_id": result.data.get("message_id") if result.data else None
                })

                if result.is_success:
                    success_count += 1
                else:
                    failed_count += 1

        # 显示结果
        mode_str = "[cyan]Async (Kafka)[/cyan]" if async_mode else "[dim]Sync (Direct)[/dim]"
        console.print(Panel.fit(
            f"[cyan]Mode:[/cyan] {mode_str}\n"
            f"[cyan]Total Recipients:[/cyan] {len(unique_user_uuids)}\n"
            f"[green]:white_check_mark: Success:[/green] {success_count}\n"
            f"[red]:x: Failed:[/red] {failed_count}",
            title="[bold]Notification Summary[/bold]",
            border_style="green" if failed_count == 0 else "yellow"
        ))

        if failed_count > 0 and not async_mode:
            console.print("\n[yellow]Failed recipients:[/yellow]")
            for r in results:
                if not r["success"]:
                    console.print(f"  [red]:x: {r['user_uuid'][:16]}... - {r.get('message', 'Unknown error')}[/red]")

    except Exception as e:
        console.print(f"[red]:x: Error sending notification: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@app.command("template")
def send_template_notification(
    user: Optional[List[str]] = typer.Option(None, "--user", "-u", help="User UUID(s) or Name(s) - can be repeated"),
    group: Optional[List[str]] = typer.Option(None, "--group", "-g", help="Group ID(s) or Name(s) - can be repeated"),
    template_id: str = typer.Option(..., "--id", "-t", help="Template ID"),
    variables: Optional[List[str]] = typer.Option(None, "--var", "-v", help="Template variables as key=value (can be repeated)"),
    priority: int = typer.Option(1, "--priority", "-p", min=0, max=3, help="Priority"),
):
    """
    :page_facing_up: Send a notification using a template.

    Examples:
      ginkgo notify template --user "Alice" --id alert_template
      ginkgo notify template -g traders -t welcome -v name="Team"
      ginkgo notify template -u <uuid> -g "Admins" -t alert
    """
    try:
        from ginkgo.data.containers import container

        # 验证参数
        if not user and not group:
            console.print("[red]:x: Either --user or --group is required[/red]")
            raise typer.Exit(1)

        # Get service from container
        service = container.notification_service()

        # Register console channel
        from ginkgo.notifier.channels.console_channel import ConsoleChannel
        service.register_channel(ConsoleChannel())

        # Parse variables
        context = {}
        if variables:
            for var in variables:
                if "=" in var:
                    key, value = var.split("=", 1)
                    try:
                        context[key] = json.loads(value)
                    except:
                        context[key] = value

        # 收集所有唯一的用户 UUID
        unique_user_uuids = set()

        # 解析用户输入（UUID 或 name）
        if user:
            for user_input in user:
                resolved_uuid = service._resolve_user_uuid(user_input)
                if resolved_uuid:
                    unique_user_uuids.add(resolved_uuid)
                else:
                    console.print(f"[yellow]:warning: User not found: {user_input}[/yellow]")

        # 解析组输入（name 或 uuid），获取组内用户
        if group:
            for group_input in group:
                group_user_uuids = service._resolve_group_uuids(group_input)
                if group_user_uuids:
                    unique_user_uuids.update(group_user_uuids)
                else:
                    console.print(f"[yellow]:warning: Group not found: {group_input}[/yellow]")

        if not unique_user_uuids:
            console.print("[red]:x: No valid users found[/red]")
            raise typer.Exit(1)

        # 向所有唯一用户发送模板通知
        results = []
        success_count = 0
        failed_count = 0

        for user_uuid in unique_user_uuids:
            result = service.send_template_to_user(
                user_uuid=user_uuid,
                template_id=template_id,
                context=context,
                priority=priority
            )

            results.append({
                "user_uuid": user_uuid,
                "success": result.is_success,
                "message_id": result.data.get("message_id") if result.data else None
            })

            if result.is_success:
                success_count += 1
            else:
                failed_count += 1

        # 显示结果
        console.print(Panel.fit(
            f"[cyan]Template:[/cyan] {template_id}\n"
            f"[cyan]Total Recipients:[/cyan] {len(unique_user_uuids)}\n"
            f"[green]:white_check_mark: Success:[/green] {success_count}\n"
            f"[red]:x: Failed:[/red] {failed_count}",
            title="[bold]Template Notification Summary[/bold]",
            border_style="green" if failed_count == 0 else "yellow"
        ))

        if failed_count > 0:
            console.print("\n[yellow]Failed recipients:[/yellow]")
            for r in results:
                if not r["success"]:
                    console.print(f"  [red]:x: {r['user_uuid'][:16]}...[/red]")

    except Exception as e:
        console.print(f"[red]:x: Error sending template: {e}[/red]")
        raise typer.Exit(1)


@app.command("history")
def get_notification_history(
    user_uuid: Optional[str] = typer.Option(None, "--user", "-u", help="User UUID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (pending/sent/failed)"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results"),
    failed: bool = typer.Option(False, "--failed", "-f", help="Show only failed notifications"),
):
    """
    :bookmark_tabs: Show notification history.

    Examples:
      ginkgo notify history --user <uuid>
      ginkgo notify history --failed
      ginkgo notify history -l 20
    """
    try:
        from ginkgo.data.containers import container
        from ginkgo.enums import NOTIFICATION_STATUS_TYPES

        # Get service from container
        service = container.notification_service()

        # Get history
        if failed:
            result = service.get_failed_notifications(limit=limit)
        elif user_uuid:
            status_filter = None
            if status:
                status_map = {
                    "pending": NOTIFICATION_STATUS_TYPES.PENDING.value,
                    "sent": NOTIFICATION_STATUS_TYPES.SENT.value,
                    "failed": NOTIFICATION_STATUS_TYPES.FAILED.value
                }
                status_filter = status_map.get(status.lower())

            result = service.get_notification_history(
                user_uuid=user_uuid,
                limit=limit,
                status=status_filter
            )
        else:
            console.print("[yellow]:warning: Please specify --user or use --failed[/yellow]")
            raise typer.Exit(1)

        if result.is_success:
            data = result.data
            records = data.get("records", [])
            count = data.get("count", 0)

            if count == 0:
                console.print(":memo: No notification records found.")
                return

            table = Table(title=f":bell: Notification History ({count} records)")
            table.add_column("Message ID", style="cyan", max_width=20)
            table.add_column("Status", style="yellow")
            table.add_column("Channels", style="green")
            table.add_column("Content", style="white", max_width=30)
            table.add_column("Created", style="dim")

            for rec in records[:limit]:
                content = rec.get("content", "")[:30] + "..." if len(rec.get("content", "")) > 30 else rec.get("content", "")

                status_val = rec.get("status", 0)
                status_map = {
                    0: "[dim]PENDING[/dim]",
                    1: "[green]SENT[/green]",
                    2: "[red]FAILED[/red]"
                }
                status_str = status_map.get(status_val, str(status_val))

                channels = ", ".join(rec.get("channels", []))
                created = str(rec.get("create_at", ""))[:16] if rec.get("create_at") else "N/A"

                table.add_row(
                    rec.get("message_id", "")[:18] + "...",
                    status_str,
                    channels,
                    content,
                    created
                )

            console.print(table)
        else:
            console.print(f"[red]:x: Failed to get history: {result.message}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error getting history: {e}[/red]")
        raise typer.Exit(1)


@app.command("search")
def search_recipients(
    keyword: str = typer.Argument(..., help="Search keyword (user name or group name)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Max results per category"),
):
    """
    :mag: Search for users and groups by keyword.

    Examples:
      ginkgo notify search "alice"
      ginkgo notify search "traders" -l 20
    """
    try:
        from ginkgo.data.containers import container

        user_service = container.user_service()
        group_service = container.user_group_service()

        # 搜索用户
        users_result = user_service.list_users(limit=limit)
        users = []
        if users_result.success:
            all_users = users_result.data.get("users", [])
            # 模糊匹配用户名
            keyword_lower = keyword.lower()
            users = [
                u for u in all_users
                if keyword_lower in u.get("name", "").lower() or
                   keyword_lower in u.get("uuid", "").lower()
            ][:limit]

        # 搜索组
        groups_result = group_service.list_groups(limit=limit)
        groups = []
        if groups_result.success:
            all_groups = groups_result.data.get("groups", [])
            # 模糊匹配组名
            keyword_lower = keyword.lower()
            groups = [
                g for g in all_groups
                if keyword_lower in g.get("name", "").lower() or
                   keyword_lower in g.get("uuid", "").lower()
            ][:limit]

        # 显示结果
        if not users and not groups:
            console.print(f":mag: No results found for '{keyword}'")
            return

        # 用户结果
        if users:
            table = Table(title=f":bust_in_silhouette: Users ({len(users)} found)")
            table.add_column("UUID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Type", style="yellow")
            table.add_column("Active", justify="center")

            for u in users:
                active_style = "green" if u.get("is_active") else "red"
                table.add_row(
                    u.get("uuid", ""),
                    u.get("name", ""),
                    u.get("user_type", ""),
                    f"[{active_style}]{u.get('is_active')}[/{active_style}]"
                )
            console.print(table)

        # 组结果
        if groups:
            console.print()  # 空行分隔
            table = Table(title=f":people_hugging: Groups ({len(groups)} found)")
            table.add_column("UUID", style="cyan")
            table.add_column("Name", style="yellow")
            table.add_column("Active", justify="center")

            for g in groups:
                active_style = "green" if g.get("is_active") else "red"
                table.add_row(
                    g.get("uuid", ""),
                    g.get("name", ""),
                    f"[{active_style}]{g.get('is_active')}[/{active_style}]"
                )
            console.print(table)

    except Exception as e:
        console.print(f"[red]:x: Error searching: {e}[/red]")
        raise typer.Exit(1)


@app.command("history")
def notification_history(
    user: Optional[str] = typer.Option(None, "--user", "-u", help="Filter by user UUID or name"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum number of records to show", min=1, max=500),
    status: Optional[int] = typer.Option(None, "--status", "-s", help="Filter by status (0=pending, 1=sent, 2=failed)"),
    offset: int = typer.Option(0, "--offset", "-o", help="Offset for pagination", min=0),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw JSON data"),
):
    """
    :book: Query notification history records.

    Examples:
      ginkgo notify history                    # Show recent 50 records
      ginkgo notify history --user "Alice"     # Show records for user Alice
      ginkgo notify history -u <uuid> -l 100   # Show last 100 records for user
      ginkgo notify history --status 1         # Show only sent notifications
      ginkgo notify history --raw              # Output JSON format
    """
    try:
        from ginkgo import service_hub
        from ginkgo.enums import NOTIFICATION_STATUS_TYPES

        service = service_hub.notifier.notification_service()

        # 解析用户输入
        user_uuid = None
        if user:
            user_uuid = service._resolve_user_uuid(user)
            if not user_uuid:
                console.print(f"[red]:x: User not found: {user}[/red]")
                raise typer.Exit(1)

        # 查询通知记录
        if user_uuid:
            result = service.get_notification_history(
                user_uuid=user_uuid,
                limit=limit,
                status=status
            )
        else:
            # 如果没有指定用户，查询最近的记录（使用 get_failed_notifications 或其他方法）
            # 注意：这里需要实现一个通用的查询方法，暂时只支持按用户查询
            console.print("[yellow]:warning: Currently only --user filtering is supported[/yellow]")
            console.print("[yellow]Usage: ginkgo notify history --user <uuid_or_name>[/yellow]")
            raise typer.Exit(1)

        if not result.is_success:
            console.print(f"[red]:x: Failed to query history: {result.error}[/red]")
            raise typer.Exit(1)

        data = result.data
        records = data.get("records", [])

        if not records:
            console.print("[yellow]:memo: No notification records found[/yellow]")
            return

        # Raw output mode
        if raw:
            import json
            console.print(json.dumps(records, indent=2, ensure_ascii=False, default=str))
            return

        # 表格输出模式
        console.print(f"\n[bold]Notification History[/bold]")
        console.print(f"[dim]User: {user} | Total: {data.get('count', 0)} records[/dim]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="cyan", width=16)
        table.add_column("Message ID", style="white", width=28)
        table.add_column("Channel", style="yellow", width=10)
        table.add_column("Status", justify="center", width=8)
        table.add_column("Title", style="green", width=20)
        table.add_column("Content", style="white", width=30)

        status_map = {
            NOTIFICATION_STATUS_TYPES.PENDING.value: "[yellow]PENDING[/yellow]",
            NOTIFICATION_STATUS_TYPES.SENT.value: "[green]SENT[/green]",
            NOTIFICATION_STATUS_TYPES.FAILED.value: "[red]FAILED[/red]",
        }

        for record in records:
            # 格式化时间戳
            timestamp = record.get("timestamp", "")
            if timestamp:
                try:
                    from datetime import datetime
                    if isinstance(timestamp, str):
                        ts = datetime.fromisoformat(timestamp)
                    else:
                        ts = datetime.fromtimestamp(timestamp)
                    timestamp_str = ts.strftime("%Y-%m-%d %H:%M")
                except:
                    timestamp_str = str(timestamp)[:16]
            else:
                timestamp_str = "N/A"

            # 获取状态
            status_value = record.get("status", 0)
            status_str = status_map.get(status_value, f"[dim]{status_value}[/dim]")

            # 截断内容
            content = record.get("content", "")
            if len(content) > 27:
                content = content[:27] + "..."

            # 截断标题
            title = record.get("title", "")
            if len(title) > 18:
                title = title[:18] + "..."

            table.add_row(
                timestamp_str,
                str(record.get("message_id", ""))[:26],
                str(record.get("channel", "")),
                status_str,
                title,
                content
            )

        console.print(table)

        # 显示统计信息
        if records:
            console.print(f"\n[dim]Showing {len(records)} of {data.get('count', 0)} records[/dim]")

    except Exception as e:
        console.print(f"[red]:x: Error: {e}[/red]")
        raise typer.Exit(1)


@app.command("channels")
def list_channels():
    """
    :satellite: List available notification channels.

    Examples:
      ginkgo notify channels
    """
    console.print("\n[bold]Available Notification Channels:[/bold]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Channel", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Status", style="yellow")

    channels = [
        ("console", "Console output (for testing)", "[green]:white_check_mark: Available[/green]"),
        ("discord", "Discord Webhook", "[green]:white_check_mark: Available[/green]"),
        ("email", "Email (SMTP)", "[dim]Coming soon[/dim]"),
        ("kafka", "Kafka Queue", "[dim]Coming soon[/dim]"),
    ]

    for name, desc, status in channels:
        table.add_row(name, desc, status)

    console.print(table)
    console.print("\n[yellow]Usage:[/yellow]")
    console.print("  ginkgo notify send --user <uuid> --content \"message\"")
    console.print("  ginkgo notify send --group <id> --content \"Alert!\"")
