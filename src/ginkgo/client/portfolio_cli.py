"""
Ginkgo Portfolio CLI - 投资组合管理命令
"""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table

app = typer.Typer(help=":bank: Portfolio management", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


@app.command()
def list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-l", help="Page size"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw data as JSON"),
):
    """
    :clipboard: List all portfolios.
    """
    from ginkgo.data.containers import container

    console.print(":clipboard: Listing portfolios...")

    try:
        portfolio_service = container.portfolio_service()
        result = portfolio_service.get()

        if result.success:
            portfolios_data = result.data

            # Raw output mode
            if raw:
                import json
                if hasattr(portfolios_data, 'to_dataframe'):
                    portfolios_df = portfolios_data.to_dataframe()
                    raw_data = portfolios_df.to_dict('records')
                elif isinstance(portfolios_data, list):
                    raw_data = [item.__dict__ if hasattr(item, '__dict__') else item for item in portfolios_data]
                else:
                    raw_data = portfolios_data

                console.print(json.dumps(raw_data, indent=2, ensure_ascii=False, default=str))
                return

            if hasattr(portfolios_data, 'to_dataframe'):
                import pandas as pd
                portfolios_df = portfolios_data.to_dataframe()
            elif isinstance(portfolios_data, list):
                portfolios_df = pd.DataFrame(portfolios_data)
            else:
                portfolios_df = pd.DataFrame()

            if portfolios_df.empty:
                console.print(":memo: No portfolios found.")
                return

            # Display portfolios
            table = Table(title=":bank: Portfolios")
            table.add_column("UUID", style="dim", width=36)
            table.add_column("Name", style="cyan", width=20)
            table.add_column("Initial Capital", style="green", width=15)
            table.add_column("Type", style="yellow", width=10)
            table.add_column("Status", style="white", width=10)

            for _, portfolio in portfolios_df.iterrows():
                initial_capital = f"¥{float(portfolio.get('initial_capital', 0)):,.2f}"
                portfolio_type = "Live" if portfolio.get('is_live', False) else "Backtest"
                status = portfolio.get('status', 'Unknown')

                table.add_row(
                    str(portfolio.get('uuid', ''))[:36],
                    str(portfolio.get('name', ''))[:18],
                    initial_capital,
                    portfolio_type,
                    status
                )

            console.print(table)
        else:
            console.print(f":x: Failed to get portfolios: {result.error}")

    except Exception as e:
        console.print(f":x: Error: {e}")


@app.command()
def create(
    name: str = typer.Option(..., "--name", "-n", help="Portfolio name"),
    initial_capital: float = typer.Option(1000000.0, "--capital", "-c", help="Initial capital"),
    is_live: bool = typer.Option(False, "--live", help="Live portfolio"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Portfolio description"),
):
    """
    :heavy_plus_sign: Create a new portfolio.
    """
    from ginkgo.data.containers import container

    console.print(f":heavy_plus_sign: Creating portfolio: {name}")

    try:
        portfolio_service = container.portfolio_service()
        result = portfolio_service.create(
            name=name,
            initial_capital=initial_capital,
            is_live=is_live,
            description=description or ""
        )

        if result.success:
            portfolio_uuid = result.data.uuid if hasattr(result.data, 'uuid') else result.data
            console.print(f":white_check_mark: Portfolio '{name}' created successfully")
            console.print(f"  • Portfolio ID: {portfolio_uuid}")
            console.print(f"  • Initial Capital: ¥{initial_capital:,.2f}")
            console.print(f"  • Type: {'Live' if is_live else 'Backtest'}")
            console.print(f"  • Description: {description or 'No description'}")
        else:
            console.print(f":x: Portfolio creation failed: {result.error}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


@app.command()
def get(
    portfolio_id: str = typer.Argument(..., help="Portfolio UUID"),
    details: bool = typer.Option(False, "--details", "-d", help="Show detailed portfolio information"),
    performance: bool = typer.Option(False, "--performance", "-p", help="Show performance metrics"),
):
    """
    :eyes: Show portfolio details and composition.
    """
    from ginkgo.data.containers import container

    console.print(f":eyes: Showing portfolio {portfolio_id}...")

    try:
        portfolio_service = container.portfolio_service()
        result = portfolio_service.get(portfolio_id=portfolio_id)

        if result.success:
            portfolio = result.data
            table = Table(title=f":bank: Portfolio Details")
            table.add_column("Property", style="cyan", width=15)
            table.add_column("Value", style="white", width=50)

            table.add_row("ID", str(portfolio.uuid))
            table.add_row("Name", str(portfolio.name))
            table.add_row("Initial Capital", f"¥{portfolio.initial_capital:,.2f}")
            table.add_row("Start Date", str(portfolio.backtest_start_date))
            table.add_row("End Date", str(portfolio.backtest_end_date))
            table.add_row("Is Live", "Yes" if portfolio.is_live else "No")
            table.add_row("Description", str(portfolio.description or "No description"))

            console.print(table)

            if details:
                # TODO: Show portfolio composition
                console.print("\n:gear: Portfolio Composition:")
                console.print(":information: Portfolio composition details not yet implemented")

            if performance:
                # TODO: Show performance metrics
                console.print("\n:chart_with_upwards_trend: Performance Metrics:")
                console.print(":information: Performance metrics not yet implemented")

        else:
            console.print(f":x: Failed to get portfolio: {result.error}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


@app.command()
def status(
    portfolio_id: str = typer.Argument(..., help="Portfolio UUID"),
):
    """
    :gear: Get portfolio status.
    """
    from ginkgo.data.containers import container

    console.print(f":gear: Getting portfolio {portfolio_id} status...")

    try:
        portfolio_service = container.portfolio_service()
        result = portfolio_service.get(portfolio_id=portfolio_id)

        if result.success:
            portfolio = result.data
            console.print(f":gear: Portfolio Status: {portfolio.status}")
            # TODO: Add more detailed status information
        else:
            console.print(f":x: Failed to get portfolio status: {result.error}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


@app.command()
def delete(
    portfolio_id: str = typer.Argument(..., help="Portfolio UUID"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm deletion"),
):
    """
    :wastebasket: Delete portfolio.
    """
    if not confirm:
        console.print(":x: Please use --confirm to delete portfolio")
        raise typer.Exit(1)

    console.print(f":wastebasket: Deleting portfolio: {portfolio_id}")

    try:
        from ginkgo.data.containers import container
        portfolio_service = container.portfolio_service()
        result = portfolio_service.delete(portfolio_id)

        if result.success:
            console.print(":white_check_mark: Portfolio deleted successfully")
        else:
            console.print(f":x: Failed to delete portfolio: {result.error}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)