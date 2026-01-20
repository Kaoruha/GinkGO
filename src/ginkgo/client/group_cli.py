# Upstream: CLI主入口(ginkgo groups命令调用)
# Downstream: UserGroupService(用户组管理业务逻辑)、Rich库(表格/进度条显示)
# Role: 用户组管理CLI，提供create创建、list列表、add-user添加用户、remove-user移除用户等命令，支持用户组的多维度管理


"""
Ginkgo User Group Management CLI - 用户组管理命令
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

app = typer.Typer(help=":people_hugging: User group management", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


# ============================================================================
# System 组保护辅助函数
# ============================================================================

SYSTEM_GROUP_NAME = "System"

def _handle_system_group_protection(console: Console) -> None:
    """
    处理 System 组保护错误，显示友好的提示信息并退出

    Args:
        console: Rich Console 实例
    """
    console.print("[red]:lock: [bold]Error:[/bold] Cannot create 'System' group manually[/red]")
    console.print("")
    console.print("[yellow]:bulb: The 'System' group is reserved for system-level operations[/yellow]")
    console.print("[yellow]It is automatically created by [cyan bold]ginkgo init[/cyan][/yellow]")
    console.print("")
    console.print("[dim]To create the System group, run:[/dim]")
    console.print("[cyan]  ginkgo init[/cyan]")
    raise typer.Exit(1)


def is_system_group_protected(name: str) -> bool:
    """
    判断指定名称是否受 System 组保护

    Args:
        name: 要检查的组名

    Returns:
        如果是受保护的 System 组名，返回 True
    """
    return name == SYSTEM_GROUP_NAME


# ============================================================================
# Group Commands
# ============================================================================

@app.command("create")
def create_group(
    name: str = typer.Option(..., "--name", "-n", help="Group name (unique)"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="Group description"),
    is_active: bool = typer.Option(True, "--active/--inactive", help="Group active status"),
):
    """
    :plus: Create a new user group.

    Example:
      ginkgo group create --name "Administrators" --desc "Admin users"
      ginkgo group create -n "Traders" -d "Trading team"
    """
    try:
        from ginkgo.data.containers import container

        # System 组保护检查
        if is_system_group_protected(name):
            _handle_system_group_protection(console)

        group_service = container.user_group_service()

        result = group_service.create_group(
            name=name,
            description=description,
            is_active=is_active
        )

        if result.success:
            console.print(Panel.fit(
                f"[green]:white_check_mark: Group created successfully![/green]\n\n"
                f"[cyan]UUID:[/cyan] {result.data['uuid']}\n"
                f"[cyan]Name:[/cyan] {result.data['name']}\n"
                f"[cyan]Description:[/cyan] {result.data['description'] or 'N/A'}\n"
                f"[cyan]Active:[/cyan] {result.data['is_active']}",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error creating group: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_groups(
    is_active: Optional[bool] = typer.Option(None, "--active/--inactive", help="Filter by active status"),
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum number of results"),
):
    """
    :list: List groups with optional filters.

    Example:
      ginkgo groups list
      ginkgo groups list --active
      ginkgo groups list -l 50
    """
    try:
        from ginkgo.data.containers import container

        group_service = container.user_group_service()
        result = group_service.list_groups(is_active=is_active, limit=limit)

        if result.success:
            groups = result.data["groups"]

            if not groups:
                console.print(":memo: No groups found.")
                return

            table = Table(title=f":people_hugging: Groups ({result.data['count']} found)")
            table.add_column("UUID", style="cyan", no_wrap=True)
            table.add_column("Name", style="yellow")
            table.add_column("Description", style="dim")
            table.add_column("Active", justify="center")
            table.add_column("Updated", style="dim")

            for group in groups:
                active_style = "green" if group["is_active"] else "red"
                table.add_row(
                    group["uuid"],
                    group["name"],
                    (group.get("description") or "")[:30],
                    f"[{active_style}]{group['is_active']}[/{active_style}]",
                    str(group.get("update_at", "") or "N/A")
                )

            console.print(table)
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error listing groups: {e}[/red]")
        raise typer.Exit(1)


@app.command("cat")
def cat_group(
    group_uuid: str = typer.Argument(..., help="Group UUID"),
):
    """
    :cat: Get group details by UUID.

    Example:
      ginkgo group cat abc123...
    """
    try:
        from ginkgo.data.containers import container

        group_service = container.user_group_service()
        result = group_service.get_group(group_uuid)

        if result.success:
            data = result.data
            console.print(Panel.fit(
                f"[cyan]UUID:[/cyan] {data['uuid']}\n"
                f"[cyan]Name:[/cyan] {data['name']}\n"
                f"[cyan]Description:[/cyan] {data['description'] or 'N/A'}\n"
                f"[cyan]Active:[/cyan] {data['is_active']}\n"
                f"[cyan]Source:[/cyan] {data['source']}\n"
                f"[cyan]Created:[/cyan] {data['create_at'] or 'N/A'}\n"
                f"[cyan]Updated:[/cyan] {data['update_at'] or 'N/A'}",
                title=f"[bold blue]:people_hugging: {data['name']}[/bold blue]",
                border_style="blue"
            ))
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error getting group: {e}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_group(
    group_uuid: str = typer.Argument(..., help="Group UUID"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt"),
):
    """
    :wastebasket: Delete a group (cascades to user mappings).

    Example:
      ginkgo groups delete abc123... --confirm
    """
    try:
        from ginkgo.data.containers import container

        if not confirm:
            confirm_delete = typer.confirm(f"Are you sure you want to delete group {group_uuid}?")
            if not confirm_delete:
                console.print(":x: Deletion cancelled.")
                raise typer.Exit(0)

        group_service = container.user_group_service()
        result = group_service.delete_group(group_uuid)

        if result.success:
            console.print(
                f"[green]:white_check_mark: Group deleted successfully "
                f"({result.data['mappings_removed']} mappings removed)[/green]"
            )
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error deleting group: {e}[/red]")
        raise typer.Exit(1)


@app.command("add")
def add_user_to_group(
    user_uuid: Optional[str] = typer.Option(None, "--user", "-u", help="User UUID"),
    group_uuid: Optional[str] = typer.Option(None, "--group", "-g", help="Group UUID"),
):
    """
    :plus: Add a user to a group.

    Example:
      ginkgo group add --user abc123... --group def456...
    """
    try:
        from ginkgo.data.containers import container

        # 如果没有提供 group_uuid，显示组列表
        if group_uuid is None:
            console.print("\n[yellow]:information_source: Available groups:[/yellow]\n")
            list_groups(is_active=None, limit=100)
            console.print("\n[cyan]Usage: ginkgo group add --user <user_uuid> --group <group_uuid>[/cyan]\n")
            import sys
            sys.exit(0)

        # 如果没有提供 user_uuid，显示用户列表
        if user_uuid is None:
            console.print("\n[yellow]:information_source: Available users:[/yellow]\n")
            # 直接调用 UserService 获取用户列表
            from ginkgo.data.containers import container
            from rich.table import Table

            user_service = container.user_service()
            result = user_service.list_users(limit=100)

            if result.success:
                users = result.data["users"]

                if not users:
                    console.print(":memo: No users found.")
                else:
                    table = Table(title=f":busts_in_silhouette: Users ({result.data['count']} found)")
                    table.add_column("UUID", style="cyan", no_wrap=True)
                    table.add_column("Name", style="green")
                    table.add_column("Type", style="yellow")
                    table.add_column("Active", justify="center")

                    for user in users:
                        active_style = "green" if user["is_active"] else "red"
                        table.add_row(
                            user["uuid"],
                            user["name"],
                            user["user_type"],
                            f"[{active_style}]{user['is_active']}[/{active_style}]"
                        )

                    console.print(table)
            else:
                console.print(f"[red]:x: {result.error}[/red]")

            console.print("\n[cyan]Usage: ginkgo group add --user <user_uuid> --group <group_uuid>[/cyan]\n")
            import sys
            sys.exit(0)

        group_service = container.user_group_service()
        result = group_service.add_user_to_group(user_uuid, group_uuid)

        if result.success:
            console.print(Panel.fit(
                f"[green]:white_check_mark: User added to group successfully![/green]\n\n"
                f"[cyan]Mapping UUID:[/cyan] {result.data['mapping_uuid']}\n"
                f"[cyan]User UUID:[/cyan] {result.data['user_uuid']}\n"
                f"[cyan]Group UUID:[/cyan] {result.data['group_uuid']}",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error adding user to group: {e}[/red]")
        raise typer.Exit(1)


@app.command("remove")
def remove_user_from_group(
    user_uuid: Optional[str] = typer.Option(None, "--user", "-u", help="User UUID"),
    group_uuid: Optional[str] = typer.Option(None, "--group", "-g", help="Group UUID"),
):
    """
    :minus: Remove a user from a group.

    Example:
      ginkgo group remove --user abc123... --group def456...
    """
    try:
        from ginkgo.data.containers import container

        # 如果没有提供 group_uuid，显示组列表
        if group_uuid is None:
            console.print("\n[yellow]:information_source: Available groups:[/yellow]\n")
            list_groups(is_active=None, limit=100)
            console.print("\n[cyan]Usage: ginkgo group remove --user <user_uuid> --group <group_uuid>[/cyan]\n")
            import sys
            sys.exit(0)

        # 如果没有提供 user_uuid，显示用户列表
        if user_uuid is None:
            console.print("\n[yellow]:information_source: Available users:[/yellow]\n")
            # 直接调用 UserService 获取用户列表
            from ginkgo.data.containers import container
            from rich.table import Table

            user_service = container.user_service()
            result = user_service.list_users(limit=100)

            if result.success:
                users = result.data["users"]

                if not users:
                    console.print(":memo: No users found.")
                else:
                    table = Table(title=f":busts_in_silhouette: Users ({result.data['count']} found)")
                    table.add_column("UUID", style="cyan", no_wrap=True)
                    table.add_column("Name", style="green")
                    table.add_column("Type", style="yellow")
                    table.add_column("Active", justify="center")

                    for user in users:
                        active_style = "green" if user["is_active"] else "red"
                        table.add_row(
                            user["uuid"],
                            user["name"],
                            user["user_type"],
                            f"[{active_style}]{user['is_active']}[/{active_style}]"
                        )

                    console.print(table)
            else:
                console.print(f"[red]:x: {result.error}[/red]")

            console.print("\n[cyan]Usage: ginkgo group remove --user <user_uuid> --group <group_uuid>[/cyan]\n")
            import sys
            sys.exit(0)

        group_service = container.user_group_service()
        result = group_service.remove_user_from_group(user_uuid, group_uuid)

        if result.success:
            console.print(
                f"[green]:white_check_mark: User removed from group successfully "
                f"({result.data['deleted_count']} mapping)[/green]"
            )
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error removing user from group: {e}[/red]")
        raise typer.Exit(1)


@app.command("members")
def list_group_members(
    group_uuid: Optional[str] = typer.Argument(None, help="Group UUID"),
):
    """
    :list: List all members of a group.

    Example:
      ginkgo group members abc123...
    """
    try:
        from ginkgo.data.containers import container

        # 如果没有提供 group_uuid，显示组列表
        if group_uuid is None:
            console.print("\n[yellow]:information_source: Available groups:[/yellow]\n")
            list_groups(is_active=None, limit=100)
            console.print("\n[cyan]Usage: ginkgo group members <group_uuid>[/cyan]\n")
            import sys
            sys.exit(0)

        group_service = container.user_group_service()

        # 获取组信息以显示组名
        group_info_result = group_service.get_group(group_uuid)
        group_name = "Unknown"
        if group_info_result.success:
            group_name = group_info_result.data["name"]

        result = group_service.get_group_members(group_uuid)

        if result.success:
            members = result.data["members"]

            if not members:
                console.print(f":memo: No members found in group '{group_name}'.")
                return

            table = Table(title=f":busts_in_silhouette: {group_name} Members ({result.data['count']} found)")
            table.add_column("User Name", style="green")
            table.add_column("User UUID", style="cyan", no_wrap=True)
            table.add_column("Mapping UUID", style="dim", no_wrap=True)

            for member in members:
                table.add_row(
                    member["user_name"],
                    member["user_uuid"],
                    member["mapping_uuid"]
                )

            console.print(table)
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error listing group members: {e}[/red]")
        raise typer.Exit(1)


@app.command("user-groups")
def list_user_groups(
    user_uuid: str = typer.Argument(..., help="User UUID"),
):
    """
    :list: List all groups for a user.

    Example:
      ginkgo groups user-groups abc123...
    """
    try:
        from ginkgo.data.containers import container

        group_service = container.user_group_service()
        result = group_service.get_user_groups(user_uuid)

        if result.success:
            groups = result.data["groups"]

            if not groups:
                console.print(":memo: User is not a member of any groups.")
                return

            table = Table(title=f":people_hugging: User Groups ({result.data['count']} found)")
            table.add_column("Group UUID", style="cyan", no_wrap=True)
            table.add_column("Name", style="yellow")
            table.add_column("Description", style="dim")

            for group in groups:
                table.add_row(
                    group["group_uuid"],
                    group["name"],
                    (group.get("description") or "")[:30]
                )

            console.print(table)
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error listing user groups: {e}[/red]")
        raise typer.Exit(1)
