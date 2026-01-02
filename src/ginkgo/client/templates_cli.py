# Upstream: CLI主入口(ginkgo templates命令调用)
# Downstream: NotificationTemplateCRUD(模板CRUD操作)、TemplateEngine(模板渲染引擎)
# Role: 通知模板管理CLI，提供create创建、list列表、update更新、delete删除等命令，支持通知模板的CRUD操作


"""
Ginkgo Notification Template CLI - 通知模板管理命令
"""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from rich.syntax import Syntax
import json

app = typer.Typer(help=":memo: Notification template management", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


# ============================================================================
# Template Commands
# ============================================================================

@app.command("create")
def create_template(
    template_id: str = typer.Option(..., "--id", help="Template unique ID"),
    name: str = typer.Option(..., "--name", "-n", help="Template name"),
    template_type: str = typer.Option("text", "--type", "-t", help="Template type (text/markdown/embedded)"),
    content: str = typer.Option(..., "--content", "-c", help="Template content"),
    subject: Optional[str] = typer.Option(None, "--subject", "-s", help="Subject for email templates"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Comma-separated tags"),
    desc: Optional[str] = typer.Option("", "--desc", "-d", help="Template description"),
):
    """
    :plus: Create a new notification template.

    Examples:
      ginkgo templates create --id alert_template --name "Alert" --type markdown --content "**Alert:** {{ message }}"
      ginkgo templates create -id welcome -n "Welcome" -t text -c "Hello {{ name }}!" --tags user,onboarding
    """
    try:
        from ginkgo.data.containers import container
        from ginkgo.enums import TEMPLATE_TYPES, SOURCE_TYPES

        template_crud = container.notification_template_crud()

        # Convert string type to enum
        type_map = {
            "text": TEMPLATE_TYPES.TEXT,
            "markdown": TEMPLATE_TYPES.MARKDOWN,
            "embedded": TEMPLATE_TYPES.EMBEDDED
        }
        template_type_enum = type_map.get(template_type.lower(), TEMPLATE_TYPES.TEXT)

        # Parse tags
        tag_list = []
        if tags:
            tag_list = [t.strip() for t in tags.split(",")]

        # Create template
        from ginkgo.data.models import MNotificationTemplate

        template = MNotificationTemplate(
            template_id=template_id,
            template_name=name,
            template_type=template_type_enum.value,
            subject=subject,
            content=content,
            is_active=True,
            tags=tag_list,
            desc=desc,
            source=SOURCE_TYPES.OTHER.value
        )

        template_uuid = template_crud.add(template)

        if template_uuid:
            console.print(Panel.fit(
                f"[green]:white_check_mark: Template created successfully![/green]\n\n"
                f"[cyan]UUID:[/cyan] {template_uuid}\n"
                f"[cyan]ID:[/cyan] {template_id}\n"
                f"[cyan]Name:[/cyan] {name}\n"
                f"[cyan]Type:[/cyan] {template_type}\n"
                f"[cyan]Tags:[/cyan] {', '.join(tag_list) if tag_list else 'None'}",
                title="[bold green]Success[/bold green]",
                border_style="green"
            ))
        else:
            console.print(f"[red]:x: Failed to create template (ID may already exist)[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error creating template: {e}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_templates(
    template_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by template type"),
    is_active: Optional[bool] = typer.Option(None, "--active/--inactive", help="Filter by active status"),
    tags: Optional[str] = typer.Option(None, "--tags", help="Filter by tags (comma-separated)"),
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum number of results"),
):
    """
    :list: List notification templates with optional filters.

    Examples:
      ginkgo templates list
      ginkgo templates list --type markdown --active
      ginkgo templates list --tags alert,trading
      ginkgo templates list -l 50
    """
    try:
        from ginkgo.data.containers import container
        from ginkgo.enums import TEMPLATE_TYPES

        template_crud = container.notification_template_crud()

        # Convert string type to enum if provided
        template_type_enum = None
        if template_type:
            type_map = {
                "text": TEMPLATE_TYPES.TEXT,
                "markdown": TEMPLATE_TYPES.MARKDOWN,
                "embedded": TEMPLATE_TYPES.EMBEDDED
            }
            template_type_enum = type_map.get(template_type.lower())

        # Parse tags
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",")]

        # Get templates
        if tag_list:
            templates = template_crud.get_by_tags(tags=tag_list, match_all=False)
        elif template_type_enum is not None:
            templates = template_crud.get_by_template_type(template_type_enum.value)
        elif is_active is not None:
            templates = template_crud.get_active_templates() if is_active else []
        else:
            templates = template_crud.get_all(limit=limit)

        if not templates:
            console.print(":memo: No templates found.")
            return

        table = Table(title=f":memo: Templates ({len(templates)} found)")
        table.add_column("UUID", style="cyan", no_wrap=False, max_width=12)
        table.add_column("ID", style="green", max_width=15)
        table.add_column("Name", style="yellow")
        table.add_column("Type", style="blue")
        table.add_column("Active", justify="center")
        table.add_column("Tags", style="magenta")
        table.add_column("Created", style="dim", max_width=16)

        for t in templates[:limit]:
            active_style = "green" if t.is_active else "red"
            tags_str = ", ".join(t.tags[:3]) if t.tags else ""
            if len(t.tags) > 3:
                tags_str += "..."
            uuid_short = t.uuid[:8] + "..." if len(t.uuid) > 11 else t.uuid
            created_short = str(t.create_at)[:16] if t.create_at else "N/A"

            table.add_row(
                uuid_short,
                t.template_id,
                t.template_name,
                t.get_template_type_enum().name,
                f"[{active_style}]{t.is_active}[/{active_style}]",
                tags_str,
                created_short
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]:x: Error listing templates: {e}[/red]")
        raise typer.Exit(1)


@app.command("get")
def get_template(
    template_id: str = typer.Argument(..., help="Template ID"),
    show_content: bool = typer.Option(False, "--content", "-c", help="Show template content"),
):
    """
    :mag: Get template details by ID.

    Examples:
      ginkgo templates get alert_template
      ginkgo templates get welcome --content
    """
    try:
        from ginkgo.data.containers import container

        template_crud = container.notification_template_crud()
        template = template_crud.get_by_template_id(template_id)

        if not template:
            console.print(f"[red]:x: Template not found: {template_id}[/red]")
            raise typer.Exit(1)

        # Display template info
        console.print(Panel.fit(
            f"[cyan]UUID:[/cyan] {template.uuid}\n"
            f"[cyan]ID:[/cyan] {template.template_id}\n"
            f"[cyan]Name:[/cyan] {template.template_name}\n"
            f"[cyan]Type:[/cyan] {template.get_template_type_enum().name}\n"
            f"[cyan]Subject:[/cyan] {template.subject or 'N/A'}\n"
            f"[cyan]Active:[/cyan] {template.is_active}\n"
            f"[cyan]Tags:[/cyan] {', '.join(template.tags) if template.tags else 'None'}\n"
            f"[cyan]Description:[/cyan] {template.desc or 'N/A'}\n"
            f"[cyan]Variables:[/cyan] {template.get_required_variables() or '[]'}",
            title=f"[bold yellow]Template: {template.template_name}[/bold yellow]",
            border_style="yellow"
        ))

        # Show content if requested
        if show_content:
            console.print("\n[bold]Content:[/bold]")
            syntax = Syntax(template.content, "markdown" if template.get_template_type_enum().name == "MARKDOWN" else "text", theme="monokai", line_numbers=True)
            console.print(syntax)

    except Exception as e:
        console.print(f"[red]:x: Error getting template: {e}[/red]")
        raise typer.Exit(1)


@app.command("update")
def update_template(
    template_id: str = typer.Argument(..., help="Template ID"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="New name"),
    content: Optional[str] = typer.Option(None, "--content", "-c", help="New content"),
    subject: Optional[str] = typer.Option(None, "--subject", "-s", help="New subject"),
    active: Optional[bool] = typer.Option(None, "--active/--inactive", help="Set active status"),
    desc: Optional[str] = typer.Option(None, "--desc", "-d", help="New description"),
):
    """
    :wrench: Update an existing template.

    Examples:
      ginkgo templates update alert_template --content "New alert content"
      ginkgo templates update welcome --name "Welcome Message" --active
      ginkgo templates update alert_template --inactive
    """
    try:
        from ginkgo.data.containers import container

        template_crud = container.notification_template_crud()

        # Check if template exists
        existing = template_crud.get_by_template_id(template_id)
        if not existing:
            console.print(f"[red]:x: Template not found: {template_id}[/red]")
            raise typer.Exit(1)

        # Build update data (only include provided fields)
        update_data = {}
        if name is not None:
            update_data['template_name'] = name
        if content is not None:
            update_data['content'] = content
        if subject is not None:
            update_data['subject'] = subject
        if active is not None:
            update_data['is_active'] = active
        if desc is not None:
            update_data['desc'] = desc

        if not update_data:
            console.print("[yellow]:warning: No updates provided[/yellow]")
            return

        # Perform update
        count = template_crud.update_by_template_id(template_id, **update_data)

        if count > 0:
            console.print(f"[green]:white_check_mark: Template updated successfully ({count} record(s))[/green]")
        else:
            console.print("[red]:x: Failed to update template[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error updating template: {e}[/red]")
        raise typer.Exit(1)


@app.command("delete")
def delete_template(
    template_id: str = typer.Argument(..., help="Template ID"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
):
    """
    :wastebasket: Delete a template (soft delete).

    Examples:
      ginkgo templates delete alert_template --confirm
      ginkgo templates delete old_template -y
    """
    try:
        from ginkgo.data.containers import container

        template_crud = container.notification_template_crud()

        # Check if template exists
        existing = template_crud.get_by_template_id(template_id)
        if not existing:
            console.print(f"[red]:x: Template not found: {template_id}[/red]")
            raise typer.Exit(1)

        # Confirm deletion
        if not confirm:
            console.print(f"[yellow]:warning: You are about to delete template: {template_id}[/yellow]")
            confirm = typer.confirm("Are you sure?", default=False)
            if not confirm:
                console.print("[dim]Deletion cancelled.[/dim]")
                raise typer.Exit()

        # Perform soft delete
        result = template_crud.delete(existing.uuid)

        if result:
            console.print(f"[green]:white_check_mark: Template deleted successfully[/green]")
        else:
            console.print("[red]:x: Failed to delete template[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error deleting template: {e}[/red]")
        raise typer.Exit(1)


@app.command("render")
def render_template(
    template_id: str = typer.Option(..., "--id", "-t", help="Template ID"),
    variables: Optional[str] = typer.Option(None, "--var", "-v", help="Variables as key=value (can be repeated)"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Preview template without rendering"),
):
    """
    :play_button: Render a template with variables.

    Examples:
      ginkgo templates render --id alert_template --var name="User" --var message="Test"
      ginkgo templates render -t welcome -p
    """
    try:
        from ginkgo.data.containers import container
        from ginkgo.notifier.core.template_engine import TemplateEngine

        template_crud = container.notification_template_crud()
        template_engine = TemplateEngine(template_crud=template_crud)

        # Get template
        template = template_crud.get_by_template_id(template_id)
        if not template:
            console.print(f"[red]:x: Template not found: {template_id}[/red]")
            raise typer.Exit(1)

        # Preview only
        if preview:
            result = template_engine.preview_template(template_id)
            console.print(Panel.fit(
                f"[cyan]Variables:[/cyan] {result['variables']}\n\n"
                f"[cyan]Content:[/cyan]\n{result['content'][:100]}...",
                title=f"[bold yellow]Template Preview: {template.template_name}[/bold yellow]",
                border_style="yellow"
            ))
            return

        # Parse variables
        context = {}
        if variables:
            for var in variables:
                if "=" in var:
                    key, value = var.split("=", 1)
                    # Try to parse as JSON for complex values
                    try:
                        context[key] = json.loads(value)
                    except:
                        context[key] = value

        # Render template
        rendered = template_engine.render_from_template_id(template_id, context=context)

        console.print(Panel.fit(
            rendered,
            title=f"[bold green]Rendered Output[/bold green]",
            border_style="green"
        ))

    except ValueError as e:
        console.print(f"[red]:x: Template error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]:x: Error rendering template: {e}[/red]")
        raise typer.Exit(1)


@app.command("validate")
def validate_template(
    content: str = typer.Option(..., "--content", "-c", help="Template content to validate"),
):
    """
    :white_check_mark: Validate template syntax without saving.

    Examples:
      ginkgo templates validate --content "Hello {{ name }}, score: {{ score }}"
      ginkgo templates validate -c "**Alert:** {{ message }}"
    """
    try:
        from ginkgo.notifier.core.template_engine import TemplateEngine

        template_engine = TemplateEngine()
        result = template_engine.validate_template(content)

        if result["valid"]:
            console.print(Panel.fit(
                f"[green]:white_check_mark: Template syntax is valid![/green]\n\n"
                f"[cyan]Variables found:[/cyan] {', '.join(result['variables']) if result['variables'] else 'None'}",
                title="[bold green]Validation Success[/bold green]",
                border_style="green"
            ))
        else:
            console.print(Panel.fit(
                f"[red]:x: Template syntax error[/red]\n\n"
                f"[cyan]Error:[/cyan] {result['error']}",
                title="[bold red]Validation Failed[/bold red]",
                border_style="red"
            ))
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]:x: Error validating template: {e}[/red]")
        raise typer.Exit(1)
