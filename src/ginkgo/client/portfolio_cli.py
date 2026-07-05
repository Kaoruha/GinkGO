# Upstream: CLI入口 (ginkgo portfolio 子命令)
# Downstream: PortfolioService (组合CRUD)、MappingService (组件绑定)、Kafka (deploy/unload通知)
# Role: 投资组合管理CLI，提供 list/create/get/delete/status/bind/unbind/deploy/unload/baseline 命令


"""
Ginkgo Portfolio CLI - 投资组合管理命令
"""

import json

import typer
import pandas as pd
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich import print as rprint

from ginkgo.enums import PORTFOLIO_MODE_TYPES, PORTFOLIO_RUNSTATE_TYPES
from ginkgo.libs import GLOG
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.client.cli_utils import build_list_result, format_result

app = typer.Typer(help=":bank: Portfolio management", rich_markup_mode="rich")
console = Console(emoji=True, legacy_windows=False)


def _format_portfolio_mode(mode_value) -> str:
    """将 Portfolio mode 字段格式化为可读文本。#5326"""
    if mode_value is None:
        return "N/A"
    enum_val = PORTFOLIO_MODE_TYPES.from_int(mode_value)
    return enum_val.name if enum_val else str(mode_value)


def _format_portfolio_status(portfolio) -> str:
    """Use explicit status when present, otherwise derive display status from state."""
    status_value = portfolio.get("status", None)
    if status_value is not None and not pd.isna(status_value):
        status_text = str(status_value).strip()
        if status_text and status_text.lower() != "unknown":
            return status_text

    enum_val = PORTFOLIO_RUNSTATE_TYPES.from_int(portfolio.get("state", None))
    return enum_val.name if enum_val else "Unknown"


def _portfolio_record(portfolio) -> dict:
    return {
        "uuid": str(getattr(portfolio, "uuid", "")),
        "name": str(getattr(portfolio, "name", "")),
        "initial_capital": getattr(portfolio, "initial_capital", None),
        "current_capital": getattr(portfolio, "current_capital", None),
        "cash": getattr(portfolio, "cash", None),
        "mode": _format_portfolio_mode(getattr(portfolio, "mode", None)),
        "description": str(getattr(portfolio, "desc", "") or ""),
    }


def display_component_tree(console, component_data: dict):
    """以文件树结构显示组件信息（与engine cat风格一致）"""

    # 计算总的组件类型数量
    component_types = []
    if component_data["selectors"]:
        component_types.append(("selectors", "🎯", "Selectors"))
    if component_data["strategies"]:
        component_types.append(("strategies", "🎯", "Strategies"))
    if component_data["sizers"]:
        component_types.append(("sizers", "📏", "Sizers"))
    if component_data["risk_managers"]:
        component_types.append(("risk_managers", "🛡️", "Risk Managers"))
    if component_data["analyzers"]:
        component_types.append(("analyzers", "📊", "Analyzers"))

    # 如果没有任何组件
    if not component_types:
        console.print("└── (No components bound to this portfolio)")
        return

    # 显示各种组件
    for i, (key, icon, label) in enumerate(component_types):
        items = component_data[key]
        is_last_component = i == len(component_types) - 1

        # 组件类型前缀
        component_prefix = "└──" if is_last_component else "├──"
        console.print(f"{component_prefix} {icon} {label} ({len(items)})")

        # 检查是否有组件有参数
        has_params_in_this_component = any(item.get("parameters") for item in items)

        for j, item in enumerate(items):
            is_last_file = j == len(items) - 1
            has_file_params = item.get("parameters")

            # 文件前缀：如果这个组件类型下有参数，或者这个文件有参数，需要保留垂直线
            if has_params_in_this_component or has_file_params:
                file_prefix = "│   └──" if is_last_file else "│   ├──"
            else:
                file_prefix = "    └──" if is_last_file else "    ├──"

            console.print(f"{file_prefix} {item['name']} (file_id: {item['file_id'][:8]}...)")

            # 显示该组件的参数
            if has_file_params:
                for k, param in enumerate(item["parameters"]):
                    is_last_param = k == len(item["parameters"]) - 1

                    # 参数前缀：只需要文件层的垂直线
                    if is_last_file and is_last_param:
                        param_prefix = "│       └──"
                    elif is_last_file:
                        param_prefix = "│       ├──"
                    elif is_last_param:
                        param_prefix = "│       └──"
                    else:
                        param_prefix = "│       ├──"

                    console.print(f"{param_prefix} [{param['index']}]: {param['value']}")

    # 结束标记（根据是否有组件决定缩进）
    if component_types:
        console.print(f"└── (End of component tree)")


@app.command()
def list(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-l", help="Page size"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output raw data as JSON"),
    format: str = typer.Option("text", "--format", "-f", help="Output format: text/json"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable color output"),
):
    """
    :clipboard: List all portfolios.
    """
    from ginkgo.data.containers import container

    if format != "json":
        console.print(":clipboard: Listing portfolios...")

    try:
        portfolio_service = container.portfolio_service()
        result = portfolio_service.get_portfolios_df()

        if result.success:
            portfolios_data = result.data

            # Raw output mode
            if raw:
                import json

                # ADR-010 R2a: get_portfolios_df 出口已保证 data 为 DataFrame
                portfolios_df = portfolios_data if isinstance(portfolios_data, pd.DataFrame) else pd.DataFrame()
                raw_data = portfolios_df.to_dict("records")

                console.print(json.dumps(raw_data, indent=2, ensure_ascii=False, default=str))
                return

            # ADR-010 R2a: get_portfolios_df 出口已保证 data 为 DataFrame（类型即契约，无需鸭子探测）
            portfolios_df = portfolios_data if isinstance(portfolios_data, pd.DataFrame) else pd.DataFrame()

            if format == "json":
                total = len(portfolios_df)
                records = portfolios_df.head(limit).to_dict("records")
                json_result = build_list_result(records, total=total, limit=limit, offset=0)
                format_result(json_result, format="json", command="list")
                return

            if portfolios_df.empty:
                console.print(":memo: No portfolios found.")
                return

            # Display portfolios
            table = Table(title=":bank: Portfolios")
            table.add_column("UUID", style="cyan")
            table.add_column("Name", style="cyan", width=20)
            table.add_column("Initial Capital", style="green", width=15)
            table.add_column("Type", style="yellow", width=10)
            table.add_column("Status", style="white", width=10)

            for _, portfolio in portfolios_df.iterrows():
                initial_capital = f"¥{float(portfolio.get('initial_capital', 0)):,.2f}"
                portfolio_type = "Live" if portfolio.get('is_live', False) else "Backtest"
                status = _format_portfolio_status(portfolio)

                table.add_row(
                    str(portfolio.get("uuid", "")),
                    str(portfolio.get("name", ""))[:18],
                    initial_capital,
                    portfolio_type,
                    status,
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

    # #5984: 初始资本必须为正，拒绝非正输入（负数/零）。
    if initial_capital <= 0:
        console.print(f":x: Invalid --capital: must be greater than 0 (got {initial_capital})")
        raise typer.Exit(1)

    console.print(f":heavy_plus_sign: Creating portfolio: {name}")

    try:
        portfolio_service = container.portfolio_service()
        result = portfolio_service.add(
            name=name,
            description=description or "",
            initial_capital=initial_capital,
        )

        if result.success:
            data = result.data
            portfolio_uuid = (
                data.get("uuid", data)
                if isinstance(data, dict)
                else (data.uuid if hasattr(data, "uuid") else str(data))
            )
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
    format: str = typer.Option("text", "--format", "-f", help="Output format: text/json"),
    no_color: bool = typer.Option(False, "--no-color", help="Disable color output"),
):
    """
    :eyes: Show portfolio details and composition.
    """
    from ginkgo.data.containers import container

    if format != "json":
        console.print(f":eyes: Showing portfolio {portfolio_id}...")

    try:
        portfolio_service = container.portfolio_service()

        # 先尝试按 UUID 查找
        result = portfolio_service.get(portfolio_id=portfolio_id)
        # 如果 UUID 查找失败，尝试按名称查找
        if not result.success or not result.data or (hasattr(result.data, "__len__") and len(result.data) == 0):
            result = portfolio_service.get(name=portfolio_id)

        if result.success and result.data:
            # 获取第一个 portfolio 实体（ModelList 支持）
            if hasattr(result.data, "__len__") and len(result.data) > 0:
                portfolio = result.data[0]
            elif hasattr(result.data, "uuid"):
                portfolio = result.data
            else:
                console.print(":x: Portfolio data format error")
                raise typer.Exit(1)

            if format == "json":
                format_result(ServiceResult.success(data=_portfolio_record(portfolio)), format="json", command="get")
                return

            table = Table(title=f":bank: Portfolio Details")
            table.add_column("Property", style="cyan", width=15)
            table.add_column("Value", style="white", width=50)

            table.add_row("ID", str(portfolio.uuid))
            table.add_row("Name", str(portfolio.name))
            table.add_row("Initial Capital", f"¥{portfolio.initial_capital:,.2f}")
            table.add_row("Current Capital", f"¥{portfolio.current_capital:,.2f}")
            table.add_row("Cash", f"¥{portfolio.cash:,.2f}")
            table.add_row("Mode", _format_portfolio_mode(getattr(portfolio, "mode", None)))
            table.add_row("Description", str(portfolio.desc or "No description"))

            console.print(table)

            if details:
                # 显示Portfolio的组件绑定和参数
                console.print("\n📁 Component Bindings:")
                # #6448: 通过 PortfolioService，不再调用 client 层旧函数
                result = container.portfolio_service().collect_portfolio_components(portfolio.uuid)
                if result.is_success():
                    component_data = result.data
                else:
                    console.print(f"[yellow]:warning: Failed to collect components: {result.error}[/yellow]")
                    component_data = {
                        "strategies": [],
                        "risk_managers": [],
                        "analyzers": [],
                        "selectors": [],
                        "sizers": [],
                    }

                # 检查是否有任何组件绑定
                total_components = sum(len(component_data[key]) for key in component_data.keys())

                if total_components == 0:
                    console.print(":information: No component bindings found for this portfolio")
                    console.print(":information: Use 'ginkgo portfolio bind-component' to add components")
                else:
                    display_component_tree(console, component_data)

            if performance:
                # TODO: Show performance metrics
                console.print("\n:chart_with_upwards_trend: Performance Metrics:")
                console.print(":information: Performance metrics not yet implemented")

        else:
            if format == "json":
                format_result(
                    ServiceResult.failure(message=f"Portfolio not found: {portfolio_id}", code="NOT_FOUND"),
                    format="json",
                    command="get",
                )
                return
            console.print(f":x: Failed to get portfolio: {result.error}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
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
        if not result.success or not result.data or (hasattr(result.data, "__len__") and len(result.data) == 0):
            result = portfolio_service.get(name=portfolio_id)

        if result.success and result.data:
            # 获取第一个 portfolio 实体（ModelList 支持）
            if hasattr(result.data, "__len__") and len(result.data) > 0:
                portfolio = result.data[0]
            elif hasattr(result.data, "uuid"):
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


def _resolve_portfolio_identifier(portfolio_service, identifier: str):
    """#5995: 将 名称/部分UUID/完整UUID 解析为具体 UUID。

    解析链：精确 UUID → 精确名称 → fuzzy（uuid/name 片段）。
    与同文件 ``get``/``status`` 的 UUID→name 回退模式对齐，新增部分 UUID fuzzy 兜底。

    注：本模块存在 ``def list(...)`` 命令函数遮蔽 builtin ``list``，故此处避免 ``list()``，
    改用 ``len()`` + 直接索引（data 为 list/ModelList，支持 ``__len__``/``__getitem__``）。

    Returns:
        (uuid, None) 命中唯一；(None, error_msg) 未命中或歧义。
    """

    def _has_match(r) -> bool:
        return r is not None and getattr(r, "success", False) and bool(getattr(r, "data", None))

    def _first_uuid(data):
        if not data:
            return None
        return data[0].uuid

    # 1. 精确 UUID
    r = portfolio_service.get(portfolio_id=identifier)
    if _has_match(r):
        return _first_uuid(r.data), None

    # 2. 精确名称
    r = portfolio_service.get(name=identifier)
    if _has_match(r):
        return _first_uuid(r.data), None

    # 3. fuzzy: uuid/name 片段
    r = portfolio_service.fuzzy_search(identifier)
    if _has_match(r):
        count = len(r.data)
        if count == 1:
            return r.data[0].uuid, None
        return None, f"Multiple portfolios match '{identifier}' ({count} found), use full UUID"

    return None, f"投资组合不存在: {identifier}"


@app.command()
def delete(
    portfolio_id: str = typer.Argument(..., help="Portfolio UUID, name, or partial UUID (fuzzy)"),
    confirm: bool = typer.Option(False, "--yes", "-y", "--confirm", help="Skip confirmation"),
):
    """
    :wastebasket: Delete portfolio. Accepts full UUID, name, or partial UUID (fuzzy match).
    """
    if not confirm:
        console.print(":x: Please use --confirm to delete portfolio")
        raise typer.Exit(1)

    try:
        from ginkgo.data.containers import container

        portfolio_service = container.portfolio_service()

        # #5995: 名称/部分UUID 解析（精确 UUID → 名称 → fuzzy）
        resolved_uuid, error = _resolve_portfolio_identifier(portfolio_service, portfolio_id)
        if resolved_uuid is None:
            console.print(f":x: {error}")
            raise typer.Exit(1)

        if resolved_uuid != portfolio_id:
            console.print(f":wastebasket: Resolved '{portfolio_id}' -> {resolved_uuid}")
        console.print(f":wastebasket: Deleting portfolio: {resolved_uuid}")
        result = portfolio_service.delete(resolved_uuid)

        if result.success:
            console.print(":white_check_mark: Portfolio deleted successfully")
        else:
            console.print(f":x: Failed to delete portfolio: {result.error}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


@app.command("bind-component")
def bind_component(
    portfolio_id: str = typer.Argument(..., help="Portfolio UUID or name"),
    file_id: str = typer.Argument(..., help="File UUID or name"),
    component_type: str = typer.Option(
        ..., "--type", "-t", help="Component type (strategy/risk/selector/sizer/analyzer)"
    ),
    params: List[str] = typer.Option(
        [], "--param", "-p", help="Component parameters in format 'index:value', can be used multiple times"
    ),
):
    """
    :link: Bind a component to a portfolio.

    Examples:
        ginkgo portfolio bind-component my_portfolio my_strategy --type strategy
        ginkgo portfolio bind-component my_portfolio my_strategy --type strategy --param 0:MyStrategy --param 1:14
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
        _file_resolved = False

        # 先尝试按UUID精确查找
        file_result = file_service.get_by_uuid(file_id)
        if file_result.success and file_result.data:
            data = file_result.data
            if isinstance(data, dict) and data.get("file") is not None:
                resolved_file_uuid = data["file"].uuid
                file_name = data["file"].name
                _file_resolved = True
            elif hasattr(data, "uuid"):
                resolved_file_uuid = data.uuid
                file_name = data.name
                _file_resolved = True

        # 再尝试按name查找
        if not _file_resolved:
            file_result = file_service.get_by_name(file_id)
            if file_result.success and file_result.data:
                data = file_result.data
                files = data.get("files", data) if isinstance(data, dict) else data
                if hasattr(files, "__len__") and len(files) > 0:
                    resolved_file_uuid = files[0].uuid
                    file_name = files[0].name
                    _file_resolved = True

        if not _file_resolved:
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

        # 解析参数（ADR-020: 仅支持整数 index:value 位置格式）
        # index0 = 构造器首参（通常为 name），按位置从 0 连续存；详见 docs/adrs/ADR-020
        parameters = {}
        if params:
            for param in params:
                if ":" not in param:
                    console.print(f":x: Invalid parameter format: '{param}'. Use 'index:value' format.")
                    raise typer.Exit(1)
                key_str, value = param.split(":", 1)
                try:
                    index = int(key_str)
                except ValueError:
                    console.print(f":x: 仅支持整数 index 格式 (如 0:14)，不支持关键字 '{key_str}'。见 ADR-020。")
                    raise typer.Exit(1)
                parameters[index] = value

        # 使用 MappingService 创建绑定
        mapping_service = container.mapping_service()
        result = mapping_service.create_portfolio_file_binding(
            portfolio_uuid=resolved_portfolio_uuid,
            file_uuid=resolved_file_uuid,
            file_name=file_name,
            file_type=file_type,
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
                    mapping_uuid=mapping.uuid, file_uuid=resolved_file_uuid, parameters=parameters
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
    confirm: bool = typer.Option(False, "--yes", "-y", "--confirm", help="Skip confirmation"),
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
            if isinstance(file_result.data, dict) and "file" in file_result.data:
                resolved_file_uuid = file_result.data["file"].uuid
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
            portfolio_uuid=resolved_portfolio_uuid, file_uuid=resolved_file_uuid
        )

        if result.success:
            console.print(f":white_check_mark: Component binding deleted successfully")
        else:
            console.print(f":x: Failed to delete binding: {result.error}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


# ========== Paper Trading (Deploy/Unload) ==========


@app.command(name="deploy")
def deploy_portfolio(
    source: str = typer.Option(..., "--source", "-s", help="源 Portfolio ID（回测）"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="新 Portfolio 名称"),
):
    """从回测 Portfolio 创建纸上交易实例（纯 DB + Kafka 通知）"""
    from rich.panel import Panel

    GLOG.INFO(f"[DEPLOY] Creating paper trading from {source}")

    try:
        portfolio_id = _deploy_paper_trading(
            source_portfolio_id=source,
            name=name,
        )

        console.print(
            Panel(
                f"[bold green]Paper trading deployed[/bold green]\n\n"
                f"Portfolio ID: {portfolio_id}\n"
                f"Source: {source}\n"
                f"Mode: PAPER\n"
                f"Notification sent to PaperTradingWorker via Kafka",
                title="Deploy Success",
            )
        )
    except Exception as e:
        GLOG.ERROR(f"[DEPLOY] Deploy failed: {e}")
        console.print(f"[bold red]Deploy failed: {e}[/bold red]")
        raise typer.Exit(1)


@app.command(name="unload")
def unload_portfolio(
    portfolio_id: str = typer.Argument(..., help="Paper Portfolio ID to unload"),
):
    """卸载纸上交易实例（Kafka 通知 Worker）"""
    from rich.panel import Panel

    GLOG.INFO(f"[UNLOAD] Unloading paper trading {portfolio_id}")

    try:
        success = _send_unload_command(portfolio_id)

        if success:
            console.print(
                Panel(
                    f"[bold yellow]Unload command sent[/bold yellow]\n\n"
                    f"Portfolio ID: {portfolio_id}\n"
                    f"Notification sent to PaperTradingWorker via Kafka",
                    title="Unload Success",
                )
            )
        else:
            console.print(f"[bold red]Failed to send unload command via Kafka[/bold red]")
            raise typer.Exit(1)
    except Exception as e:
        GLOG.ERROR(f"[UNLOAD] Unload failed: {e}")
        console.print(f"[bold red]Unload failed: {e}[/bold red]")
        raise typer.Exit(1)


def _deploy_paper_trading(
    source_portfolio_id: str,
    name: Optional[str] = None,
) -> str:
    """
    执行纸上交易部署（纯 DB 操作 + Kafka 通知）

    流程：
    1. 从源 Portfolio 读取配置
    2. 创建新 Portfolio（mode=PAPER）
    3. 复制组件文件映射到新 Portfolio
    4. 发送 Kafka deploy 通知

    Args:
        source_portfolio_id: 源回测 Portfolio ID
        name: 新 Portfolio 名称（可选）

    Returns:
        str: 新 Portfolio UUID
    """
    from ginkgo import services
    from ginkgo.enums import PORTFOLIO_MODE_TYPES, SOURCE_TYPES

    portfolio_service = services.data.portfolio_service()
    mapping_crud = services.data.cruds.portfolio_file_mapping()

    # 1. 读取源 Portfolio 信息
    source_result = portfolio_service.get(portfolio_id=source_portfolio_id)
    if not source_result.success or not source_result.data:
        raise ValueError(f"Source portfolio not found: {source_portfolio_id}")

    source_data = source_result.data
    if hasattr(source_data, "__len__") and not isinstance(source_data, dict):
        source_portfolio = source_data[0]
    else:
        source_portfolio = source_data

    # 2. 创建新 Portfolio（PAPER 模式）
    new_name = name or f"paper_{source_portfolio.name}"
    description = f"Paper trading from {source_portfolio_id}"
    create_result = portfolio_service.add(
        name=new_name,
        mode=PORTFOLIO_MODE_TYPES.PAPER,
        description=description,
    )

    if not create_result.success:
        raise ValueError(f"Failed to create paper portfolio: {create_result.error}")

    new_portfolio_id = create_result.data["uuid"]
    GLOG.INFO(f"[DEPLOY] Created paper portfolio: {new_portfolio_id} ({new_name})")

    # 3. 复制组件文件映射 + 参数
    param_crud = services.data.cruds.param()
    mappings = mapping_crud.find(filters={"portfolio_id": source_portfolio_id, "is_del": False})
    param_count = 0
    for mapping in mappings:
        mapping_type = mapping.type.value if hasattr(mapping.type, "value") else mapping.type
        # create(**kwargs) 返回带 uuid 的新 mapping（add 收 model 对象，传 kwargs 会 TypeError）
        new_mapping = mapping_crud.create(
            portfolio_id=new_portfolio_id,
            file_id=mapping.file_id,
            name=mapping.name,
            type=mapping_type,
        )
        # 复制源 mapping 的参数到新 mapping（mapping_id 指向新 uuid）
        src_params = param_crud.find(filters={"mapping_id": mapping.uuid, "is_del": False})
        for p in src_params:
            param_crud.create(
                mapping_id=new_mapping.uuid,
                index=p.index,
                value=p.value,
                source=getattr(p, "source", SOURCE_TYPES.SIM),
            )
            param_count += 1

    GLOG.INFO(
        f"[DEPLOY] Copied {len(mappings)} component mapping(s) " f"and {param_count} param(s) to {new_portfolio_id}"
    )

    # 4. 存储 source_portfolio_id 映射 + 计算 baseline
    _store_deploy_source(new_portfolio_id, source_portfolio_id)
    _generate_baseline_if_possible(new_portfolio_id, source_portfolio_id)

    # 5. 发送 Kafka deploy 通知
    _send_deploy_notification(new_portfolio_id)

    return new_portfolio_id


def _send_deploy_notification(portfolio_id: str) -> None:
    """发送 deploy 命令到 Kafka（ControlCommand DTO 格式）。

    历史：68b749e5 为修消息格式（portfolio_id 须在 params 内）内联此处并删除该
    helper，但漏改 patch 它的测试，导致 TestDeployPaperTrading 全部 AttributeError。
    此处恢复 seam，用正确的 ControlCommand.deploy().to_dict() 实现，而非被删的旧手搓 dict。
    """
    from ginkgo.messages.control_command import ControlCommand
    from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
    from ginkgo.interfaces.kafka_topics import KafkaTopics

    cmd = ControlCommand.deploy(portfolio_id)
    producer = GinkgoProducer()
    producer.send(KafkaTopics.CONTROL_COMMANDS, cmd.to_dict())


def _send_unload_command(portfolio_id: str) -> bool:
    """发送 unload 命令到 Kafka（ControlCommand DTO 格式），返回是否发送成功。

    与 _send_deploy_notification 同根（68b749e5 内联删除），一并恢复。
    """
    from ginkgo.messages.control_command import ControlCommand
    from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
    from ginkgo.interfaces.kafka_topics import KafkaTopics

    cmd = ControlCommand.unload(portfolio_id)
    producer = GinkgoProducer()
    return producer.send(KafkaTopics.CONTROL_COMMANDS, cmd.to_dict())


def _store_deploy_source(paper_portfolio_id: str, source_portfolio_id: str) -> None:
    """将 source_portfolio_id 映射存入 Redis"""
    try:
        from ginkgo import services

        redis_svc = services.data.redis_service()
        if redis_svc:
            redis_svc.set_cache(f"deviation:source:{paper_portfolio_id}", source_portfolio_id)
            GLOG.INFO(f"[DEPLOY] Stored source mapping: {source_portfolio_id[:8]} -> {paper_portfolio_id[:8]}")
    except Exception as e:
        GLOG.WARN(f"[DEPLOY] Failed to store source mapping in Redis: {e}")


def _generate_baseline_if_possible(paper_portfolio_id: str, source_portfolio_id: str) -> None:
    """从源 portfolio 的回测数据计算 baseline 并缓存到 Redis"""
    try:
        from ginkgo import services
        from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator

        # 查找源 portfolio 最近完成的回测任务
        task_service = services.data.backtest_task_service()
        task_result = task_service.list(
            portfolio_id=source_portfolio_id,
            status="completed",
            page_size=1,
        )

        if not task_result.is_success() or not task_result.data:
            GLOG.WARN(f"[DEPLOY] No completed backtest found for source {source_portfolio_id[:8]}, skipping baseline")
            return

        # task_service.list() returns paginated dict: {"data": [...], "total": N, ...}
        tasks = task_result.data.get("data", []) if isinstance(task_result.data, dict) else task_result.data
        if not tasks:
            GLOG.WARN(f"[DEPLOY] No completed backtest found for source {source_portfolio_id[:8]}, skipping baseline")
            return

        latest_task = tasks[0]
        task_id = getattr(latest_task, "task_id", None)

        if not task_id:
            GLOG.WARN(f"[DEPLOY] Backtest task has no task_id, skipping baseline")
            return

        GLOG.INFO(f"[DEPLOY] Computing baseline from backtest task_id={task_id[:8]}...")

        evaluator = BacktestEvaluator()
        eval_result = evaluator.evaluate_backtest_stability(
            portfolio_id=source_portfolio_id,
            task_id=task_id,
        )

        if eval_result.get("status") != "success":
            GLOG.WARN(f"[DEPLOY] Baseline evaluation failed: {eval_result.get('reason', 'unknown')}")
            return

        baseline = eval_result.get("monitoring_baseline", {})
        if not baseline:
            GLOG.WARN(f"[DEPLOY] No monitoring_baseline in evaluation result")
            return

        # 缓存到 Redis
        redis_svc = services.data.redis_service()
        if redis_svc:
            redis_svc.set_cache(f"deviation:baseline:{paper_portfolio_id}", json.dumps(baseline, default=str))
            GLOG.INFO(
                f"[DEPLOY] Baseline cached: slice_period={baseline.get('slice_period_days')}, "
                f"metrics={len(baseline.get('baseline_stats', {}))}"
            )

    except Exception as e:
        GLOG.WARN(f"[DEPLOY] Baseline generation failed (non-blocking): {e}")


# ========== Analysis Baseline ==========


@app.command(name="baseline")
def generate_baseline(
    portfolio_id: str = typer.Argument(..., help="Paper/Live Portfolio ID"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="源回测 Portfolio ID（覆盖 Redis 中的映射）"),
):
    """手动生成/刷新偏差检测 baseline"""
    from rich.panel import Panel

    # 如果提供了 source，先更新映射
    if source:
        _store_deploy_source(portfolio_id, source)

    # 从 Redis 读取 source_portfolio_id
    from ginkgo import services

    redis_svc = services.data.redis_service()
    source_id = None
    if redis_svc:
        src_result = redis_svc.get_cache(f"deviation:source:{portfolio_id}")
        source_id = src_result.data if src_result and src_result.is_success() else None

    if not source_id:
        source_id = source

    if not source_id:
        console.print(f"[red]No source portfolio found. Use --source to specify, or deploy first.[/red]")
        raise typer.Exit(1)

    try:
        _generate_baseline_if_possible(portfolio_id, source_id)
        console.print(
            Panel(
                f"[bold green]Baseline generated/refreshed[/bold green]\n\n"
                f"Portfolio ID: {portfolio_id}\n"
                f"Source: {source_id}",
                title="Baseline",
            )
        )
    except Exception as e:
        GLOG.ERROR(f"[BASELINE] Generation failed: {e}")
        console.print(f"[bold red]Failed: {e}[/bold red]")
        raise typer.Exit(1)
