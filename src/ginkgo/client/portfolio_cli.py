# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: 投资组合管理CLI，提供list查看、create创建、bind/unbind组件绑定、status状态查询等Portfolio操作






"""
Ginkgo Portfolio CLI - 投资组合管理命令
"""

import typer
from typing import Optional, List
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
    portfolio_id: str = typer.Argument(..., help="Portfolio UUID or name"),
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

        # 先尝试按 UUID 查找
        result = portfolio_service.get(portfolio_id=portfolio_id)
        # 如果 UUID 查找失败，尝试按名称查找
        if not result.success or not result.data or (hasattr(result.data, '__len__') and len(result.data) == 0):
            result = portfolio_service.get(name=portfolio_id)

        if result.success and result.data:
            # 获取第一个 portfolio 实体（ModelList 支持）
            if hasattr(result.data, '__len__') and len(result.data) > 0:
                portfolio = result.data[0]
            elif hasattr(result.data, 'uuid'):
                portfolio = result.data
            else:
                console.print(":x: Portfolio data format error")
                raise typer.Exit(1)

            table = Table(title=f":bank: Portfolio Details")
            table.add_column("Property", style="cyan", width=15)
            table.add_column("Value", style="white", width=50)

            table.add_row("ID", str(portfolio.uuid))
            table.add_row("Name", str(portfolio.name))
            table.add_row("Initial Capital", f"¥{portfolio.initial_capital:,.2f}")
            table.add_row("Current Capital", f"¥{portfolio.current_capital:,.2f}")
            table.add_row("Cash", f"¥{portfolio.cash:,.2f}")
            table.add_row("Is Live", "Yes" if portfolio.is_live else "No")
            table.add_row("Description", str(portfolio.desc or "No description"))

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
    portfolio_id: str = typer.Argument(..., help="Portfolio UUID or name"),
):
    """
    :gear: Get portfolio status.
    """
    from ginkgo.data.containers import container

    console.print(f":gear: Getting portfolio {portfolio_id} status...")

    try:
        portfolio_service = container.portfolio_service()

        # 先尝试按 UUID 查找，失败后按名称查找
        result = portfolio_service.get(portfolio_id=portfolio_id)
        if not result.success or not result.data or (hasattr(result.data, '__len__') and len(result.data) == 0):
            result = portfolio_service.get(name=portfolio_id)

        if result.success and result.data:
            # 获取第一个 portfolio 实体（ModelList 支持）
            if hasattr(result.data, '__len__') and len(result.data) > 0:
                portfolio = result.data[0]
            elif hasattr(result.data, 'uuid'):
                portfolio = result.data
            else:
                console.print(":x: Portfolio data format error")
                raise typer.Exit(1)

            # 使用 is_live 作为状态（MPortfolio 没有 status 字段）
            status_str = "Live" if portfolio.is_live else "Backtest"
            console.print(f":gear: Portfolio Status: {status_str}")
            console.print(f"  - Name: {portfolio.name}")
            console.print(f"  - UUID: {portfolio.uuid}")
            console.print(f"  - Initial Capital: ¥{portfolio.initial_capital:,.2f}")
            console.print(f"  - Current Capital: ¥{portfolio.current_capital:,.2f}")
            console.print(f"  - Cash: ¥{portfolio.cash:,.2f}")
            # TODO: Add more detailed status information
        else:
            console.print(f":x: Portfolio not found: {portfolio_id}")
            console.print(":information: Use 'ginkgo portfolio list' to see available portfolios")
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


@app.command("bind-component")
def bind_component(
    portfolio_id: str = typer.Argument(..., help="Portfolio UUID or name"),
    file_id: str = typer.Argument(..., help="File UUID or name"),
    component_type: str = typer.Option(..., "--type", "-t", help="Component type (strategy/risk/selector/sizer/analyzer)"),
    params: List[str] = typer.Option([], "--param", "-p", help="Component parameters in format 'index:value', can be used multiple times"),
):
    """
    :link: Bind a component to a portfolio.

    Examples:
        ginkgo portfolio bind-component my_portfolio my_strategy --type strategy
        ginkgo portfolio bind-component my_portfolio my_strategy --type strategy --param 0:0.5 --param 1:100
    """
    from ginkgo.data.containers import container
    from ginkgo.enums import FILE_TYPES

    console.print(f":link: Binding component {file_id} to portfolio {portfolio_id}...")

    try:
        # 解析 portfolio_id
        portfolio_service = container.portfolio_service()

        # 先尝试按UUID精确查找
        portfolio_result = portfolio_service.get(portfolio_id=portfolio_id)
        if portfolio_result.success and portfolio_result.data and len(portfolio_result.data) > 0:
            resolved_portfolio_uuid = portfolio_result.data[0].uuid
            portfolio_name = portfolio_result.data[0].name
        else:
            # 尝试按name查找
            portfolio_result = portfolio_service.get(name=portfolio_id)
            if portfolio_result.success and portfolio_result.data and len(portfolio_result.data) > 0:
                resolved_portfolio_uuid = portfolio_result.data[0].uuid
                portfolio_name = portfolio_result.data[0].name
            else:
                console.print(f":x: Portfolio not found: '{portfolio_id}'")
                raise typer.Exit(1)

        # 解析 file_id
        file_service = container.file_service()

        # 先尝试按UUID精确查找
        file_result = file_service.get_by_uuid(file_id)
        if file_result.success and file_result.data:
            # 处理字典格式 {"file": MFile, "exists": True}
            if isinstance(file_result.data, dict) and 'file' in file_result.data:
                mfile = file_result.data['file']
                resolved_file_uuid = mfile.uuid
                file_name = mfile.name
            else:
                resolved_file_uuid = file_result.data.uuid
                file_name = file_result.data.name
        else:
            # 尝试按name查找
            file_result = file_service.get_by_name(file_id)
            if file_result.success and file_result.data and len(file_result.data) > 0:
                resolved_file_uuid = file_result.data[0].uuid
                file_name = file_result.data[0].name
            else:
                console.print(f":x: File not found: '{file_id}'")
                raise typer.Exit(1)

        # 解析 component_type
        type_mapping = {
            "strategy": FILE_TYPES.STRATEGY,
            "risk": FILE_TYPES.RISKMANAGER,
            "riskmanager": FILE_TYPES.RISKMANAGER,
            "selector": FILE_TYPES.SELECTOR,
            "sizer": FILE_TYPES.SIZER,
            "analyzer": FILE_TYPES.ANALYZER,
        }

        file_type = type_mapping.get(component_type.lower())
        if file_type is None:
            console.print(f":x: Invalid component type: '{component_type}'")
            console.print("Valid types: strategy, risk, selector, sizer, analyzer")
            raise typer.Exit(1)

        # 解析参数
        parameters = {}
        if params:
            for param in params:
                if ':' not in param:
                    console.print(f":x: Invalid parameter format: '{param}'. Use 'index:value' format.")
                    raise typer.Exit(1)
                try:
                    index_str, value = param.split(':', 1)
                    index = int(index_str)
                    parameters[index] = value
                except ValueError:
                    console.print(f":x: Invalid parameter format: '{param}'. Index must be an integer.")
                    raise typer.Exit(1)

        # 使用 MappingService 创建绑定
        mapping_service = container.mapping_service()
        result = mapping_service.create_portfolio_file_binding(
            portfolio_uuid=resolved_portfolio_uuid,
            file_uuid=resolved_file_uuid,
            file_name=file_name,
            file_type=file_type
        )

        if result.success:
            console.print(f":white_check_mark: Component binding created successfully")
            console.print(f"  • Portfolio: {portfolio_name} ({resolved_portfolio_uuid[:8]}...)")
            console.print(f"  • Component: {file_name} ({resolved_file_uuid[:8]}...)")
            console.print(f"  • Type: {component_type}")

            # 如果有参数，创建参数
            if parameters:
                mapping = result.data  # MPortfolioFileMapping 对象
                param_result = mapping_service.create_component_parameters(
                    mapping_uuid=mapping.uuid,
                    file_uuid=resolved_file_uuid,
                    parameters=parameters
                )

                if param_result.success:
                    console.print(f"  • Parameters: {len(parameters)} parameter(s) set")
                    for idx, val in sorted(parameters.items()):
                        console.print(f"    - [{idx}]: {val}")
                else:
                    console.print(f":warning: Binding created but parameter setting failed: {param_result.error}")
        else:
            console.print(f":white_check_mark: {result.message}")

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


@app.command("unbind-component")
def unbind_component(
    portfolio_id: str = typer.Argument(..., help="Portfolio UUID or name"),
    file_id: str = typer.Argument(..., help="File UUID or name"),
    confirm: bool = typer.Option(False, "--confirm", help="Confirm unbinding"),
):
    """
    :broken_link: Unbind a component from a portfolio.
    """
    if not confirm:
        console.print(":x: Please use --confirm to unbind component")
        raise typer.Exit(1)

    from ginkgo.data.containers import container

    console.print(f":broken_link: Unbinding component {file_id} from portfolio {portfolio_id}...")

    try:
        # 解析 portfolio_id
        portfolio_service = container.portfolio_service()

        # 先尝试按UUID精确查找
        portfolio_result = portfolio_service.get(portfolio_id=portfolio_id)
        if portfolio_result.success and portfolio_result.data and len(portfolio_result.data) > 0:
            resolved_portfolio_uuid = portfolio_result.data[0].uuid
        else:
            # 尝试按name查找
            portfolio_result = portfolio_service.get(name=portfolio_id)
            if portfolio_result.success and portfolio_result.data and len(portfolio_result.data) > 0:
                resolved_portfolio_uuid = portfolio_result.data[0].uuid
            else:
                console.print(f":x: Portfolio not found: '{portfolio_id}'")
                raise typer.Exit(1)

        # 解析 file_id
        file_service = container.file_service()

        # 先尝试按UUID精确查找
        file_result = file_service.get_by_uuid(file_id)
        if file_result.success and file_result.data:
            # 处理字典格式 {"file": MFile, "exists": True}
            if isinstance(file_result.data, dict) and 'file' in file_result.data:
                resolved_file_uuid = file_result.data['file'].uuid
            else:
                resolved_file_uuid = file_result.data.uuid
        else:
            # 尝试按name查找
            file_result = file_service.get_by_name(file_id)
            if file_result.success and file_result.data and len(file_result.data) > 0:
                resolved_file_uuid = file_result.data[0].uuid
            else:
                console.print(f":x: File not found: '{file_id}'")
                raise typer.Exit(1)

        # 使用 MappingService 删除绑定
        mapping_service = container.mapping_service()
        result = mapping_service.delete_portfolio_file_binding(
            portfolio_uuid=resolved_portfolio_uuid,
            file_uuid=resolved_file_uuid
        )

        if result.success:
            console.print(f":white_check_mark: Component binding deleted successfully")
        else:
            console.print(f":x: Failed to delete binding: {result.error}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)