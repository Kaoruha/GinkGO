# Upstream: CLI主入口(ginkgo users命令调用)
# Downstream: UserService(用户管理业务逻辑)、UserGroupService(用户组管理业务逻辑)、Rich库(表格/进度条显示)
# Role: 用户管理CLI，提供create创建、list列表、update更新、delete删除、contacts联系方式管理等命令，支持用户和用户组的多维度管理


"""
Ginkgo User Management CLI - 用户管理命令
"""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich import print as rprint
from ginkgo.client.cli_utils import announce_dry_run

app = typer.Typer(help=":bust_in_silhouette: User management", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


# ============================================================================
# User Commands
# ============================================================================

@app.command("create")
def create_user(
    name: str = typer.Option(..., "--name", "-n", help="User name"),
    user_type: str = typer.Option("person", "--type", "-t", help="User type (person/channel/organization)"),
    description: str = typer.Option("", "--desc", "-d", help="User description"),
    is_active: bool = typer.Option(True, "--active/--inactive", help="User active status"),
):
    """
    :plus: Create a new user.

    Example:
      ginkgo users create --name "John Doe" --type person
      ginkgo users create -n "Trading Bot" -t channel
    """
    try:
        from ginkgo.data.containers import container
        from ginkgo.enums import USER_TYPES

        user_service = container.user_service()

        # Convert string to enum
        type_map = {
            "person": USER_TYPES.PERSON,
            "channel": USER_TYPES.CHANNEL,
            "organization": USER_TYPES.ORGANIZATION
        }
        user_type_enum = type_map.get(user_type.lower(), USER_TYPES.PERSON)

        result = user_service.add_user(name=name, user_type=user_type_enum, description=description, is_active=is_active)

        if result.success:
            console.print(Panel.fit(
                f"[green]:white_check_mark: User created successfully![/green]\n\n"
                f"[cyan]UUID:[/cyan] {result.data['uuid']}\n"
                f"[cyan]Username:[/cyan] {result.data.get('username', '')}\n"
                f"[cyan]Display Name:[/cyan] {result.data.get('display_name', '')}\n"
                f"[cyan]Description:[/cyan] {result.data['description']}\n"
                f"[cyan]Type:[/cyan] {result.data['user_type']}\n"
                f"[cyan]Active:[/cyan] {result.data['is_active']}",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error creating user: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_users(
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name (partial match)"),
    user_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by user type"),
    is_active: Optional[bool] = typer.Option(None, "--active/--inactive", help="Filter by active status"),
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum number of results"),
):
    """
    :list: List users with optional filters.

    Example:
      ginkgo users list
      ginkgo users list --name John
      ginkgo users list --type person --active
      ginkgo users list -l 50
    """
    try:
        from ginkgo.data.containers import container
        from ginkgo.enums import USER_TYPES

        user_service = container.user_service()

        # Convert string type to enum if provided
        user_type_enum = None
        if user_type:
            type_map = {
                "person": USER_TYPES.PERSON,
                "channel": USER_TYPES.CHANNEL,
                "organization": USER_TYPES.ORGANIZATION
            }
            user_type_enum = type_map.get(user_type.lower())

        result = user_service.list_users(user_type=user_type_enum, is_active=is_active, name=name, limit=limit)

        if result.success:
            users = result.data["users"]

            if not users:
                console.print(":memo: No users found.")
                return

            table = Table(title=f":bust_in_silhouette: Users ({result.data['count']} found)")
            table.add_column("UUID", style="cyan", no_wrap=True)
            table.add_column("Username", style="green", no_wrap=True, max_width=24)
            table.add_column("Display Name", style="blue")
            table.add_column("Description", style="dim", max_width=30)
            table.add_column("Type", style="yellow")
            table.add_column("Active", justify="center")
            table.add_column("Created", style="dim")

            for user in users:
                active_style = "green" if user["is_active"] else "red"
                table.add_row(
                    user["uuid"],
                    user.get("username", "")[:24],
                    user.get("display_name", "")[:20],
                    (user.get("description") or "")[:30],
                    user["user_type"],
                    f"[{active_style}]{user['is_active']}[/{active_style}]",
                    str(user.get("create_at", "") or "N/A")
                )

            console.print(table)
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error listing users: {e}[/red]")
        raise typer.Exit(1)


@app.command("cat")
def cat_user(
    user_uuid: str = typer.Argument(..., help="User UUID"),
):
    """
    :cat: Display complete user information including contacts and groups.

    Example:
      ginkgo user cat abc123...
    """
    try:
        from ginkgo.data.containers import container

        user_service = container.user_service()
        result = user_service.get_user_full_info(user_uuid)

        if result.success:
            data = result.data

            # Use display_name or username as the title
            display_name = data.get('display_name') or data.get('username') or data.get('uuid', 'Unknown')
            tree = Tree(f":kissing: [bold blue]{display_name}[/bold blue]")

            # Basic Info Branch
            info_branch = tree.add(":bookmark_tabs: [bold]Basic Info[/bold]")
            info_branch.add(f"[cyan]UUID:[/cyan] {data['uuid']}")
            info_branch.add(f"[cyan]Type:[/cyan] {data['user_type']}")
            info_branch.add(f"[cyan]Description:[/cyan] {data['description'] or 'N/A'}")
            info_branch.add(f"[cyan]Active:[/cyan] {'[green]True[/green]' if data['is_active'] else '[red]False[/red]'}")
            info_branch.add(f"[cyan]Source:[/cyan] {data['source']}")
            info_branch.add(f"[cyan]Created:[/cyan] {data['create_at'] or 'N/A'}")
            info_branch.add(f"[cyan]Updated:[/cyan] {data['update_at'] or 'N/A'}")

            # Contacts Branch
            contacts = data.get("contacts", [])
            contacts_branch = tree.add(f":mailbox_with_mail: [bold]Contacts[/bold] [dim]({len(contacts)})[/dim]")

            if contacts:
                for contact in contacts:
                    # Active status indicator - use same symbol ● for both, different colors
                    active_symbol = "●"
                    active_color = "green" if contact["is_active"] else "dark_gray"

                    # Primary indicator (right side)
                    primary_mark = " :bookmark:" if contact["is_primary"] else ""

                    # Format: ● TYPE address 🔖
                    # Separate formatting for active vs inactive contacts
                    if contact["is_active"]:
                        contact_line = f"[{active_color}]{active_symbol}[/{active_color}] [blue]{contact['contact_type']}[/blue] {contact['address']}{primary_mark}"
                    else:
                        # Inactive: grey symbol + dimmed text
                        contact_line = f"[{active_color}]{active_symbol}[/{active_color}] [dim]{contact['contact_type']}[/dim] [dim]{contact['address']}[/dim]{primary_mark}"
                    contacts_branch.add(contact_line)
            else:
                contacts_branch.add("[dim]No contacts[/dim]")

            # Groups Branch
            groups = data.get("groups", [])
            groups_branch = tree.add(f":man_mage: [bold]Groups[/bold] [dim]({len(groups)})[/dim]")

            if groups:
                for group in groups:
                    # Format: GROUP_NAME (group_uuid)
                    group_line = f"[yellow]{group['name']}[/yellow] [dim]({group['group_uuid']})[/dim]"
                    groups_branch.add(group_line)
            else:
                groups_branch.add("[dim]No groups[/dim]")

            console.print(tree)

        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error getting user info: {e}[/red]")
        raise typer.Exit(1)


@app.command("update")
def update_user(
    user_uuid: str = typer.Argument(..., help="User UUID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New name"),
    description: Optional[str] = typer.Option(None, "--desc", "-d", help="New description"),
    is_active: Optional[bool] = typer.Option(None, "--active/--inactive", help="New active status"),
):
    """
    :pencil: Update user information.

    Example:
      ginkgo user update abc123... --name "New Name"
      ginkgo user update abc123... --desc "Updated description" --inactive
    """
    try:
        from ginkgo.data.containers import container

        user_service = container.user_service()
        result = user_service.update_user(
            user_uuid=user_uuid,
            name=name,
            description=description,
            is_active=is_active
        )

        if result.success:
            console.print(Panel.fit(
                f"[green]:white_check_mark: User updated successfully![/green]\n\n"
                f"[cyan]UUID:[/cyan] {result.data['uuid']}\n"
                f"[cyan]Username:[/cyan] {result.data.get('username', '')}\n"
                f"[cyan]Display Name:[/cyan] {result.data.get('display_name', '')}\n"
                f"[cyan]Type:[/cyan] {result.data['user_type']}\n"
                f"[cyan]Description:[/cyan] {result.data['description'] or 'N/A'}\n"
                f"[cyan]Active:[/cyan] {result.data['is_active']}",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error updating user: {e}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_user(
    user_uuid: str = typer.Argument(..., help="User UUID"),
    confirm: bool = typer.Option(False, "--yes", "-y", "--confirm", help="Skip confirmation"),
):
    """
    :wastebasket: Delete a user (cascades to contacts and group mappings).

    Example:
      ginkgo users delete abc123... -y
    """
    try:
        from ginkgo.data.containers import container

        if not confirm:
            confirm_delete = typer.confirm(f"Are you sure you want to delete user {user_uuid}?")
            if not confirm_delete:
                console.print(":x: Deletion cancelled.")
                raise typer.Exit(0)

        user_service = container.user_service()
        result = user_service.delete_user(user_uuid)

        if result.success:
            console.print(f"[green]:white_check_mark: User deleted successfully ({result.data['deleted_count']} record(s))[/green]")
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error deleting user: {e}[/red]")
        raise typer.Exit(1)


# ============================================================================
# Contact Commands
# ============================================================================

contact_app = typer.Typer(help=":email: Contact management", rich_markup_mode="rich")
app.add_typer(contact_app, name="contact")


@contact_app.command("add")
def add_contact(
    user_uuid: str = typer.Option(..., "--user", "-u", help="User UUID"),
    contact_type: str = typer.Option(..., "--type", "-t", help="Contact type (email/webhook)"),
    address: str = typer.Option(..., "--address", "-a", help="Contact address (email or webhook URL)"),
):
    """
    :plus: Add contact information for a user.

    Example:
      ginkgo user contact add --user abc123... --type email --address user@example.com
      ginkgo user contact add -u abc123... -t webhook -a https://discord.com/api/webhooks/...
    """
    try:
        from ginkgo.data.containers import container
        from ginkgo.enums import CONTACT_TYPES

        user_service = container.user_service()

        # Convert string to enum
        type_map = {
            "email": CONTACT_TYPES.EMAIL,
            "webhook": CONTACT_TYPES.WEBHOOK
        }
        contact_type_enum = type_map.get(contact_type.lower(), CONTACT_TYPES.EMAIL)

        result = user_service.add_contact(
            user_uuid=user_uuid,
            contact_type=contact_type_enum,
            address=address
        )

        if result.success:
            console.print(Panel.fit(
                f"[green]:white_check_mark: Contact added successfully![/green]\n\n"
                f"[cyan]UUID:[/cyan] {result.data['uuid']}\n"
                f"[cyan]User:[/cyan] {result.data['user_uuid']}\n"
                f"[cyan]Type:[/cyan] {result.data['contact_type']}\n"
                f"[cyan]Address:[/cyan] {result.data['address']}\n"
                f"[cyan]Primary:[/cyan] {result.data['is_primary']}",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error adding contact: {e}[/red]")
        raise typer.Exit(1)


@contact_app.command("list")
def list_contacts(
    user_uuid: str = typer.Option(..., "--user", "-u", help="User UUID"),
):
    """
    :list: List all contacts for a user.

    Example:
      ginkgo user contact list --user abc123...
    """
    try:
        from ginkgo.data.containers import container

        user_service = container.user_service()
        result = user_service.get_user_contacts(user_uuid)

        if result.success:
            contacts = result.data["contacts"]

            if not contacts:
                console.print(":memo: No contacts found for this user.")
                return

            table = Table(title=f":email: Contacts ({result.data['count']} found)")
            table.add_column("UUID", style="cyan", no_wrap=True)
            table.add_column("Type", style="yellow")
            table.add_column("Address", style="green")
            table.add_column("Primary", justify="center")
            table.add_column("Active", justify="center")

            for contact in contacts:
                primary_style = "green" if contact["is_primary"] else "dim"
                active_style = "green" if contact["is_active"] else "red"
                table.add_row(
                    contact["uuid"],
                    contact["contact_type"],
                    contact["address"][:50] + "..." if len(contact["address"]) > 50 else contact["address"],
                    f"[{primary_style}]{contact['is_primary']}[/{primary_style}]",
                    f"[{active_style}]{contact['is_active']}[/{active_style}]"
                )

            console.print(table)
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error listing contacts: {e}[/red]")
        raise typer.Exit(1)


@contact_app.command("update")
def update_contact(
    contact_uuid: str = typer.Argument(..., help="Contact UUID"),
    contact_type: Optional[str] = typer.Option(None, "--type", "-t", help="New contact type (email/webhook)"),
    address: Optional[str] = typer.Option(None, "--address", "-a", help="New address"),
    is_active: Optional[bool] = typer.Option(None, "--active/--inactive", help="Active status"),
):
    """
    :pencil: Update contact information (type, address and active status).
    Use 'set-primary' command to change primary status.

    Example:
      ginkgo user contact update abc123... --type webhook
      ginkgo user contact update abc123... --address new@example.com
      ginkgo user contact update abc123... --inactive
    """
    try:
        from ginkgo.data.containers import container
        from ginkgo.enums import CONTACT_TYPES

        user_service = container.user_service()

        # Convert string to enum if provided
        contact_type_enum = None
        if contact_type:
            type_map = {
                "email": CONTACT_TYPES.EMAIL,
                "webhook": CONTACT_TYPES.WEBHOOK
            }
            contact_type_enum = type_map.get(contact_type.lower(), CONTACT_TYPES.EMAIL)

        result = user_service.update_contact(
            contact_uuid=contact_uuid,
            contact_type=contact_type_enum,
            address=address,
            is_active=is_active
        )

        if result.success:
            console.print(Panel.fit(
                f"[green]:white_check_mark: Contact updated successfully![/green]\n\n"
                f"[cyan]UUID:[/cyan] {result.data['uuid']}\n"
                f"[cyan]Type:[/cyan] {result.data['contact_type']}\n"
                f"[cyan]Address:[/cyan] {result.data['address']}\n"
                f"[cyan]Primary:[/cyan] {result.data['is_primary']}\n"
                f"[cyan]Active:[/cyan] {result.data['is_active']}",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error updating contact: {e}[/red]")
        raise typer.Exit(1)


@contact_app.command("set-primary")
def set_primary_contact(
    contact_uuid: str = typer.Argument(..., help="Contact UUID"),
):
    """
    :star: Set a contact as the primary contact.

    This will set is_primary=False for all other contacts of the same user.

    Example:
      ginkgo user contact set-primary abc123...
    """
    try:
        from ginkgo.data.containers import container

        user_service = container.user_service()
        result = user_service.set_primary(contact_uuid)

        if result.success:
            console.print(Panel.fit(
                f"[green]:white_check_mark: Primary contact set successfully![/green]\n\n"
                f"[cyan]UUID:[/cyan] {result.data['uuid']}\n"
                f"[cyan]User:[/cyan] {result.data['user_uuid']}\n"
                f"[cyan]Primary:[/cyan] {result.data['is_primary']}",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error setting primary contact: {e}[/red]")
        raise typer.Exit(1)


@contact_app.command("delete")
def delete_contact(
    contact_uuid: str = typer.Argument(..., help="Contact UUID"),
    confirm: bool = typer.Option(False, "--yes", "-y", "--confirm", help="Skip confirmation"),
    dry_run: bool = typer.Option(False, "--dry-run", help=":eye: Preview without deleting (skips confirm)"),
):
    """
    :wastebasket: Delete a contact.

    Example:
      ginkgo user contact delete abc123... -y
    """
    try:
        from ginkgo.data.containers import container

        if dry_run:
            announce_dry_run(f"删除 contact {contact_uuid}", console=console)
            console.print(f"[cyan]:eye: Would delete contact {contact_uuid}.[/cyan]")
            return

        if not confirm:
            confirm_delete = typer.confirm(f"Are you sure you want to delete contact {contact_uuid}?")
            if not confirm_delete:
                console.print(":x: Deletion cancelled.")
                raise typer.Exit(0)

        user_service = container.user_service()
        result = user_service.delete_contact(contact_uuid)

        if result.success:
            console.print(f"[green]:white_check_mark: Contact deleted successfully[/green]")
        else:
            console.print(f"[red]:x: {result.error}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error deleting contact: {e}[/red]")
        raise typer.Exit(1)


@contact_app.command("enable")
def enable_contact(
    contact_uuid: str = typer.Argument(..., help="Contact UUID"),
):
    """
    :toggle: Enable a contact (placeholder - requires update implementation).

    Example:
      ginkgo user contact enable abc123...
    """
    console.print("[yellow]:warning: Enable/disable contact feature requires update implementation[/yellow]")
    console.print(":information_source: Use database update to change is_active field")
