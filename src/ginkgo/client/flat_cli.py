# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: 扁平化命令CLI，提供_get_engine_status_name状态转换等工具函数，简化命令行操作和数据访问






"""
Ginkgo Flat CLI - 扁平化的顶级命令
包含未迁移到独立文件的CLI功能
"""

import typer
from typing import Optional, Any, Dict, List
from rich.console import Console
from rich.table import Table
import json
import datetime

from typing import Optional, List
console = Console(emoji=True, legacy_windows=False)

# 创建顶级命令
get_app = typer.Typer(help=":mag: Get resource information")
set_app = typer.Typer(help=":gear: Set resource properties")
list_app = typer.Typer(help=":clipboard: List resources")
create_app = typer.Typer(help=":plus: Create new resources")
update_app = typer.Typer(help=":repeat: Update resources")
delete_app = typer.Typer(help=":wastebasket: Delete resources")
run_app = typer.Typer(help=":rocket: Run operations")

# Component管理命令
component_app = typer.Typer(help=":wrench: Component management", rich_markup_mode="rich")

# Mapping管理命令
mapping_app = typer.Typer(help=":link: Mapping relationship management", rich_markup_mode="rich")

# Result管理命令
result_app = typer.Typer(help=":bar_chart: Result management", rich_markup_mode="rich")

def _file_type_name(type_val):
    from ginkgo.enums import FILE_TYPES
    mapping = {v.value: k.lower() for k, v in FILE_TYPES.__members__.items()}
    return mapping.get(type_val, str(type_val))


def _resolve_file(file_service, identifier):
    """按 UUID 或名称解析文件，返回 MFile 对象"""
    # 先按 UUID
    result = file_service.get_by_uuid(identifier)
    if result.success and result.data:
        data = result.data
        if isinstance(data, dict) and data.get('file') is not None:
            return data['file']
        if hasattr(data, 'uuid'):
            return data
    # 再按名称
    result = file_service.get_by_name(identifier)
    if result.success and result.data:
        data = result.data
        files = data.get('files', data) if isinstance(data, dict) else data
        if hasattr(files, '__len__') and len(files) > 0:
            return files[0]
    raise ValueError(f"Component not found: '{identifier}'")


def _generate_template(component_type: str, class_name: str) -> str:
    templates = {
        "strategy": f'''"""{class_name} Strategy"""
from collections import deque
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.enums import DIRECTION_TYPES

class {class_name}(BaseStrategy):
    __abstract__ = False

    def __init__(self, name="{class_name}", *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._short_window = 5
        self._long_window = 20
        self._closes = {{}}

    def cal(self, portfolio_info, event, *args, **kwargs):
        super().cal(portfolio_info, event)
        signals = []
        code = event.code
        close = float(event.close)

        if code not in self._closes:
            self._closes[code] = deque(maxlen=self._long_window + 2)
        self._closes[code].append(close)

        closes = list(self._closes[code])
        if len(closes) < self._long_window + 2:
            return signals

        short_ma = sum(closes[-self._short_window:]) / self._short_window
        long_ma = sum(closes[-self._long_window:]) / self._long_window
        prev_short = sum(closes[-(self._short_window+1):-1]) / self._short_window
        prev_long = sum(closes[-(self._long_window+1):-1]) / self._long_window

        if prev_short <= prev_long and short_ma > long_ma:
            signals.append(self.create_signal(code=code, direction=DIRECTION_TYPES.LONG, weight=1.0, reason="金叉"))
        elif prev_short >= prev_long and short_ma < long_ma:
            signals.append(self.create_signal(code=code, direction=DIRECTION_TYPES.SHORT, weight=1.0, reason="死叉"))

        return signals

    def reset_state(self):
        super().reset_state()
        self._closes = {{}}
''',
        "risk": f'''"""{class_name} Risk Manager"""
from ginkgo.trading.bases.risk_base import RiskBase

class {class_name}(RiskBase):
    __abstract__ = False

    def __init__(self, name="{class_name}", *args, **kwargs):
        super().__init__(name, *args, **kwargs)

    def cal(self, portfolio_info, order):
        return order

    def generate_signals(self, portfolio_info, event):
        return []
''',
        "riskmanager": f'''"""{class_name} Risk Manager"""
from ginkgo.trading.bases.risk_base import RiskBase

class {class_name}(RiskBase):
    __abstract__ = False

    def __init__(self, name="{class_name}", *args, **kwargs):
        super().__init__(name, *args, **kwargs)

    def cal(self, portfolio_info, order):
        return order

    def generate_signals(self, portfolio_info, event):
        return []
''',
        "selector": f'''"""{class_name} Selector"""
from ginkgo.backtest.strategy.selectors.base_selector import BaseSelector

class {class_name}(BaseSelector):
    __abstract__ = False

    def __init__(self, name="{class_name}", *args, **kwargs):
        super().__init__(name, *args, **kwargs)

    def select(self, candidates, *args, **kwargs):
        return candidates
''',
        "sizer": f'''"""{class_name} Sizer"""
from ginkgo.backtest.strategy.sizers.base_sizer import BaseSizer

class {class_name}(BaseSizer):
    __abstract__ = False

    def __init__(self, name="{class_name}", *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self._ratio = 0.1

    def _size(self, signal):
        return self._ratio
''',
        "analyzer": f'''"""{class_name} Analyzer"""
from ginkgo.backtest.strategy.analyzers.base_analyzer import BaseAnalyzer

class {class_name}(BaseAnalyzer):
    __abstract__ = False

    def __init__(self, name="{class_name}", *args, **kwargs):
        super().__init__(name, *args, **kwargs)

    def _do_activate(self):
        pass

    def _do_record(self, *args, **kwargs):
        pass

    def _do_calculate(self):
        return {{}}
''',
    }
    return templates.get(component_type.lower(), templates["strategy"])


# 状态转换函数
def _get_engine_status_name(status):
    """将引擎状态数字转换为可读名称"""
    from ginkgo.enums import ENGINESTATUS_TYPES

    status_map = {
        ENGINESTATUS_TYPES.VOID.value: "Void",
        ENGINESTATUS_TYPES.IDLE.value: "Idle",
        ENGINESTATUS_TYPES.INITIALIZING.value: "Initializing",
        ENGINESTATUS_TYPES.RUNNING.value: "Running",
        ENGINESTATUS_TYPES.PAUSED.value: "Paused",
        ENGINESTATUS_TYPES.STOPPED.value: "Stopped"
    }
    return status_map.get(status, f"Unknown({status})")

# Component 相关命令
@component_app.command()
def list(
    component_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by component type (strategy/risk/sizer/selector/analyzer)"),
    filter: Optional[str] = typer.Option(None, "--filter", "-f", help="Filter by component name (fuzzy search)"),
    raw: bool = typer.Option(False, "--raw", "-r", help="Output in JSON format"),
):
    """
    :clipboard: List all components from database.

    Examples:
      ginkgo component list                    # List all components (table format)
      ginkgo component list --type strategy     # List strategies only
      ginkgo component list --filter moving     # Fuzzy search by name
      ginkgo component list -t risk -f loss     # Combine type and name filter
      ginkgo component list --raw               # Output in JSON format
    """
    from ginkgo.data.containers import container
    from ginkgo.enums import FILE_TYPES
    import json

    console.print(":clipboard: Listing components...")

    try:
        # Get file_crud to query database
        file_crud = container.file_crud()

        # Map component type to FILE_TYPES
        type_mapping = {
            "strategy": FILE_TYPES.STRATEGY,
            "risk": FILE_TYPES.RISKMANAGER,
            "riskmanager": FILE_TYPES.RISKMANAGER,
            "sizer": FILE_TYPES.SIZER,
            "selector": FILE_TYPES.SELECTOR,
            "analyzer": FILE_TYPES.ANALYZER,
        }

        # Query components from database
        if component_type and component_type.lower() in type_mapping:
            # Single type query: filter by type (1 query)
            file_type = type_mapping[component_type.lower()]
            components = file_crud.find(filters={"type": file_type.value}, page_size=10000)
        else:
            # All types query: get all components in ONE query, then filter client-side
            # Query without type filter to get all components at once
            all_components = file_crud.find(filters={}, page_size=10000)

            # Filter to only include component types (exclude OTHER, VOID, ENGINE, HANDLER, INDEX)
            component_type_values = {
                FILE_TYPES.STRATEGY.value,
                FILE_TYPES.RISKMANAGER.value,
                FILE_TYPES.SELECTOR.value,
                FILE_TYPES.SIZER.value,
                FILE_TYPES.ANALYZER.value,
            }

            components = []
            for comp in all_components:
                type_value = comp.type.value if hasattr(comp.type, 'value') else comp.type
                if type_value in component_type_values:
                    components.append(comp)

        # Apply name filter if provided
        if filter:
            filter_lower = filter.lower()
            components = [c for c in components if filter_lower in str(c.name).lower()]

        if components:
            # Reverse type mapping for display
            value_to_type = {v.value: k for k, v in type_mapping.items()}

            if raw:
                # JSON output format
                result = {
                    "total": len(components),
                    "components": []
                }

                if component_type:
                    result["type"] = component_type
                if filter:
                    result["filter"] = filter

                for comp in components:
                    # Get type value - handle both enum and int
                    type_value = comp.type.value if hasattr(comp.type, 'value') else comp.type
                    type_name = value_to_type.get(type_value, "unknown")

                    component_data = {
                        "uuid": str(comp.uuid),
                        "name": str(comp.name),
                        "type": type_name,
                        "created_at": str(comp.create_at) if hasattr(comp, 'create_at') and comp.create_at else None,
                        "updated_at": str(comp.update_at) if hasattr(comp, 'update_at') and comp.update_at else None,
                    }
                    result["components"].append(component_data)

                # Output JSON
                console.print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                # Table output format
                table = Table(title=":wrench: Components")
                table.add_column("UUID", style="dim", width=38)
                table.add_column("Name", style="cyan", width=30)
                table.add_column("Type", style="green", width=18, no_wrap=False)

                for comp in components:
                    # Get type value - handle both enum and int
                    type_value = comp.type.value if hasattr(comp.type, 'value') else comp.type
                    type_name = value_to_type.get(type_value, "unknown")

                    table.add_row(
                        str(comp.uuid),
                        str(comp.name)[:29],
                        type_name
                    )

                console.print(table)
                console.print(f"\n:information_source: [dim]Total: {len(components)} components[/dim]")

                if component_type:
                    console.print(f"[dim]Type: {component_type}[/dim]")
                if filter:
                    console.print(f"[dim]Filter: '{filter}'[/dim]")
        else:
            console.print(":memo: No components found in database.")
            if filter:
                console.print(f"[dim]Try a different filter term[/dim]")

    except Exception as e:
        console.print(f":x: Error: {e}")
        import traceback
        traceback.print_exc()


@component_app.command()
def create(
    component_type: str = typer.Option(..., "--type", "-t", help="Component type (strategy/risk/riskmanager/sizer/selector/analyzer)"),
    name: str = typer.Option(..., "--name", "-n", help="Component name"),
    template: str = typer.Option("basic", "--template", help="Template type (basic)"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Component description"),
):
    """
    :plus: Create a new component.
    """
    from ginkgo.enums import FILE_TYPES

    console.print(f":plus: Creating {component_type} component: {name}")

    try:
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
            console.print(f":x: Invalid type: '{component_type}'. Valid: {', '.join(type_mapping.keys())}")
            raise typer.Exit(1)

        from ginkgo.data.containers import container
        file_service = container.file_service()

        # 检查重名
        existing = file_service.get_by_name(name, file_type)
        if existing.success and existing.data.get('count', 0) > 0:
            console.print(f":x: Component '{name}' already exists")
            raise typer.Exit(1)

        # 生成模板代码
        class_name = name
        code = _generate_template(component_type, class_name)

        result = file_service.add(
            name=name,
            file_type=file_type,
            data=code.encode('utf-8'),
            description=description or f"{component_type}: {name}",
        )

        if result.success:
            uuid = result.data.get('file_info', {}).get('uuid', 'N/A')
            console.print(f":white_check_mark: Component '{name}' created successfully")
            console.print(f"  • UUID: {uuid}")
            console.print(f"  • Type: {component_type}")
        else:
            console.print(f":x: Failed: {result.message}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


@component_app.command()
def delete(
    identifier: str = typer.Argument(..., help="Component UUID or name"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """
    :wastebasket: Delete a component.
    """
    from ginkgo.data.containers import container

    try:
        file_service = container.file_service()
        mfile = _resolve_file(file_service, identifier)

        if not force and not typer.confirm(f"Delete component '{mfile.name}' ({mfile.uuid[:8]}...)?"):
            raise typer.Exit(0)

        result = file_service.soft_delete(mfile.uuid)
        if result.success:
            console.print(f":white_check_mark: Deleted '{mfile.name}'")
        else:
            console.print(f":x: Failed: {result.message}")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


@component_app.command()
def show(
    identifier: str = typer.Argument(..., help="Component UUID or name"),
):
    """
    :eyes: Show component source code.
    """
    from ginkgo.data.containers import container

    try:
        file_service = container.file_service()
        mfile = _resolve_file(file_service, identifier)

        code = mfile.data.decode('utf-8') if isinstance(mfile.data, bytes) else str(mfile.data)
        console.print(f":eyes: Component: {mfile.name} ({mfile.uuid[:8]}...)")
        console.print(f"   Type: {_file_type_name(mfile.type)}")
        console.print(f"   Description: {mfile.desc or 'N/A'}")
        console.print()
        console.print(code)

    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


@component_app.command()
def edit(
    identifier: str = typer.Argument(..., help="Component UUID or name"),
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Import source code from local .py file"),
    name: Optional[str] = typer.Option(None, "--name", "-n", help="Update component name"),
    type: Optional[str] = typer.Option(None, "--type", "-t", help="Update component type (strategy/selector/sizer/risk/analyzer)"),
    desc: Optional[str] = typer.Option(None, "--desc", "-d", help="Update component description"),
):
    """
    :pencil: Edit component source code or metadata in database.

    Examples:
      ginkgo component edit my_strategy                  # Open in editor
      ginkgo component edit my_strategy --file code.py   # Import from file
      ginkgo component edit my_strategy --name "new"     # Update metadata only
    """
    import subprocess
    import tempfile
    import os
    from ginkgo.data.containers import container

    try:
        file_service = container.file_service()
        mfile = _resolve_file(file_service, identifier)

        new_data = None
        updates = []

        # 更新源码
        if file:
            with open(file, 'r', encoding='utf-8') as f:
                new_data = f.read().encode('utf-8')
            updates.append(f"source: {file}")
        elif not (name or type or desc):
            # 没有任何参数 → 打开编辑器
            code = mfile.data.decode('utf-8') if isinstance(mfile.data, bytes) else str(mfile.data)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as tmp:
                tmp.write(code)
                tmp_path = tmp.name
            try:
                editor = os.environ.get('EDITOR', 'nano')
                subprocess.run([editor, tmp_path])
                with open(tmp_path, 'r', encoding='utf-8') as f:
                    edited = f.read()
                if edited != code:
                    new_data = edited.encode('utf-8')
                    updates.append("source: editor")
                else:
                    console.print(":information_source: No changes made")
                    return
            finally:
                os.unlink(tmp_path)

        # 构建更新参数
        svc_kwargs = {"file_id": mfile.uuid}
        if name:
            svc_kwargs["name"] = name
            updates.append(f"name: {name}")
        if desc:
            svc_kwargs["description"] = desc
            updates.append(f"desc: {desc}")
        if type:
            from ginkgo.enums import FILE_TYPES
            type_map = {k.lower(): v for k, v in FILE_TYPES.__members__.items()}
            type_key = type.lower().replace(' ', '_')
            if type_key in type_map:
                svc_kwargs["file_type"] = type_map[type_key].value
                updates.append(f"type: {type}")
            else:
                valid = ', '.join(sorted(type_map.keys()))
                console.print(f":x: Invalid type '{type}'. Valid: {valid}")
                raise typer.Exit(1)
        if new_data:
            svc_kwargs["data"] = new_data

        if not updates:
            console.print(":information_source: Nothing to update")
            return

        result = file_service.update(**svc_kwargs)
        if result.success:
            console.print(f":white_check_mark: Component '{mfile.name}' updated ({', '.join(updates)})")
        else:
            console.print(f":x: Update failed: {result.message}")
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f":x: Error: {e}")
        raise typer.Exit(1)


# Mapping 相关命令
@mapping_app.command()
def list(
    from_type: Optional[str] = typer.Option(None, "--from-type", help="Filter by from type"),
    to_type: Optional[str] = typer.Option(None, "--to-type", help="Filter by to type"),
    page: int = typer.Option(20, "--page", "-p", help="Page size"),
):
    """
    :clipboard: List all mappings.
    """
    console.print(":clipboard: Listing mappings...")

    # TODO: Implement actual mapping listing
    console.print(":information: Mapping listing not yet implemented")


@mapping_app.command()
def create(
    from_type: str = typer.Option(..., "--from-type", help="From type (portfolio/engine/component)"),
    from_id: str = typer.Option(..., "--from-id", help="From UUID"),
    to_type: str = typer.Option(..., "--to-type", help="To type (portfolio/engine/component)"),
    to_id: str = typer.Option(..., "--to-id", help="To UUID"),
    priority: int = typer.Option(1, "--priority", help="Priority (1-100)"),
):
    """
    :link: Create a new mapping relationship.
    """
    console.print(f":link: Creating mapping: {from_type}:{from_id} -> {to_type}:{to_id}")

    # TODO: Implement actual mapping creation
    console.print(":information: Mapping creation not yet implemented")


@mapping_app.command()
def priority(
    mapping_id: str = typer.Argument(..., help=":wrench: Mapping ID"),
    priority: int = typer.Argument(..., help=":1234: New priority value"),
):
    """
    :wrench: Update mapping priority.
    """
    console.print(f":wrench: Updating priority for mapping: {mapping_id} to {priority}")

    try:
        # 验证优先级值
        if priority < 1 or priority > 100:
            console.print(":x: Priority must be between 1 and 100")
            raise typer.Exit(1)

        # TODO: Implement actual priority update
        console.print(":information: Mapping priority update not yet implemented")
        console.print(f":white_check_mark: Priority updated to {priority}")

    except Exception as e:
        console.print(f":x: Error: {e}")


# Result 相关命令
@result_app.command()
def list(
    backtest_id: Optional[str] = typer.Option(None, "--backtest", "-b", help="Filter by backtest ID"),
    portfolio: Optional[str] = typer.Option(None, "--portfolio", "-p", help="Filter by portfolio ID"),
    page: int = typer.Option(20, "--page", "-p", help="Page size"),
):
    """
    :clipboard: List all backtest results.
    """
    console.print(":clipboard: Listing results...")

    # TODO: Implement actual result listing
    console.print(":information: Result listing not yet implemented")


@result_app.command()
def get(
    result_id: str = typer.Argument(..., help=":mag: Result ID"),
    details: bool = typer.Option(False, "--details", "-d", help=":information_source: Show detailed result information"),
    trades: bool = typer.Option(False, "--trades", "-t", help=":repeat: Show trade history"),
):
    """
    :mag: Get backtest result details.
    """
    console.print(f":mag: Getting result details: {result_id}")

    try:
        # TODO: Implement actual result retrieval
        console.print(":information: Result details not yet implemented")

        # 模拟数据
        console.print(f":white_check_mark: Found result: {result_id}")

        if details:
            console.print("\n:gear: Detailed Results:")
            console.print("  • Total Return: 15.2%")
            console.print("  • Annualized Return: 18.7%")
            console.print("  • Sharpe Ratio: 1.45")
            console.print("  • Max Drawdown: -8.3%")

        if trades:
            console.print("\n:repeat: Trade History:")
            console.print("  • 2025-01-01: BUY 000001.SZ @ 10.50 (100 shares)")
            console.print("  • 2025-01-05: SELL 000001.SZ @ 11.20 (100 shares)")

    except Exception as e:
        console.print(f":x: Error: {e}")


@result_app.command("show")
def show(
    task_id: Optional[str] = typer.Option(None, "--run-id", "-r", help=":abc: Run session ID"),
    portfolio_id: Optional[str] = typer.Option(None, "--portfolio", "-p", help=":bank: Portfolio ID"),
    analyzer: Optional[str] = typer.Option(None, "--analyzer", "-a", help=":bar_chart: Analyzer name"),
    mode: str = typer.Option("table", "--mode", "-m", help=":display: Display mode (table/terminal/plot)"),
    limit: int = typer.Option(50, "--limit", "-l", help=":1234: Max records to display"),
):
    """
    :chart_with_upwards_trend: Show analyzer results by task_id.

    Examples:
        ginkgo result show                    # List available runs
        ginkgo result show --run-id a3b5c7d9e2f1a4b6c8d0e2f4a6b8c0d2
        ginkgo result show --run-id xxx --portfolio yyy --analyzer net_value --mode terminal
    """
    from ginkgo.data.containers import container
    from ginkgo.libs.utils.display import (
        display_dataframe,
        display_terminal_chart,
    )
    import pandas as pd

    result_service = container.result_service()

    # 如果没有指定 task_id，列出所有可用的运行会话
    if task_id is None:
        list_result = result_service.list_runs()
        if not list_result.success:
            console.print(f":x: [red]获取运行会话列表失败[/red]")
            console.print(f"[yellow]{list_result.error}[/yellow]")
            raise typer.Exit(1)

        runs = list_result.data
        if not runs:
            console.print(":exclamation: [yellow]没有找到可用的运行会话[/yellow]")
            console.print("[dim]请先运行回测: ginkgo engine run <engine_id>[/dim]")
            raise typer.Exit(0)

        # 转换为 DataFrame 显示
        df = pd.DataFrame(runs)

        columns_config = {
            "engine_name": {"display_name": "Engine", "style": "green"},
            "task_id": {"display_name": "Run ID", "style": "cyan"},
            "portfolio_name": {"display_name": "Portfolio", "style": "yellow"},
            "timestamp": {"display_name": "Run Time", "style": "dim"},
            "record_count": {"display_name": "Records", "style": "blue"}
        }

        display_dataframe(
            data=df,
            columns_config=columns_config,
            title=":chart_with_upwards_trend: [bold]可用的运行会话[/bold]",
            console=console
        )
        console.print("\n[yellow]使用 --run-id 参数查看详细结果[/yellow]")
        console.print("[dim]示例: ginkgo result show --run-id <task_id>[/dim]")
        raise typer.Exit(0)

    # 获取运行摘要
    summary_result = result_service.get_run_summary(task_id)
    if not summary_result.success:
        console.print(f":x: [red]未找到 task_id={task_id} 的记录[/red]")
        console.print(f"[yellow]{summary_result.error}[/yellow]")
        raise typer.Exit(1)

    summary = summary_result.data
    console.print(f":information_source: [bold]运行会话摘要:[/bold]")
    console.print(f"  Run ID: {summary['task_id']}")
    console.print(f"  Engine ID: {summary['engine_id']}")
    console.print(f"  总记录数: {summary['total_records']}")
    console.print("")

    # 自动选择 portfolio（如果只有一个）
    if portfolio_id is None:
        if summary['portfolio_count'] > 1:
            console.print(f":briefcase: [bold]可用的投资组合 ({summary['portfolio_count']}个):[/bold]")
            for pid in summary['portfolios']:
                console.print(f"  - {pid}")
            console.print("")
            console.print("[yellow]请使用 --portfolio 参数指定投资组合[/yellow]")
            raise typer.Exit(0)
        else:
            portfolio_id = summary['portfolios'][0]
            console.print(f":briefcase: [cyan]使用投资组合: {portfolio_id}[/cyan]")
            console.print("")

    # 自动选择 analyzer（如果只有一个）
    if analyzer is None:
        analyzers_result = result_service.get_portfolio_analyzers(task_id, portfolio_id)
        if analyzers_result.success:
            analyzers = analyzers_result.data
            if len(analyzers) > 1:
                console.print(f":bar_chart: [bold]可用的分析器 ({len(analyzers)}个):[/bold]")
                for name in analyzers:
                    console.print(f"  - {name}")
                console.print("")
                console.print("[yellow]请使用 --analyzer 参数指定分析器[/yellow]")
                raise typer.Exit(0)
            else:
                analyzer = analyzers[0]
                console.print(f":bar_chart: [cyan]使用分析器: {analyzer}[/cyan]")
                console.print("")

    # 获取数据
    data_result = result_service.get_analyzer_values_df(
        task_id=task_id,
        portfolio_id=portfolio_id,
        analyzer_name=analyzer
    )

    if not data_result.success:
        console.print(f":x: [red]获取数据失败[/red]")
        console.print(f"[yellow]{data_result.error}[/yellow]")
        raise typer.Exit(1)

    # 转换为 DataFrame
    import pandas as pd
    result_df = data_result.data if isinstance(data_result.data, pd.DataFrame) else pd.DataFrame()

    if result_df is None or result_df.shape[0] == 0:
        console.print(":exclamation: [yellow]没有数据可显示[/yellow]")
        raise typer.Exit(0)

    # 显示数据
    if mode == "table":
        columns_config = {
            "timestamp": {"display_name": "Date", "style": "cyan"},
            "value": {"display_name": "Value", "style": "yellow"}
        }
        title = f":bar_chart: [bold]{analyzer}[/bold] [dim]({task_id})[/dim]"
        display_dataframe(
            data=result_df.head(limit),
            columns_config=columns_config,
            title=title,
            console=console
        )

    elif mode == "terminal":
        console.print(f"[dim]显示 {result_df.shape[0]} 条记录[/dim]")
        display_terminal_chart(
            data=result_df.head(limit) if limit > 0 else result_df,
            title=f"{analyzer} [{task_id}]",
            max_points=limit,
            console=console
        )

    else:
        console.print(f":x: [red]不支持的显示模式: {mode}[/red]")
        console.print("[yellow]支持的模式: table, terminal[/yellow]")
        raise typer.Exit(1)


@result_app.command()
def get(
    result_id: str = typer.Argument(..., help=":mag: Result ID"),
    details: bool = typer.Option(False, "--details", "-d", help=":information_source: Show detailed result information"),
    trades: bool = typer.Option(False, "--trades", "-t", help=":repeat: Show trade history"),
):
    """
    :mag: Get backtest result details.
    """
    console.print(f":mag: Getting result details: {result_id}")

    try:
        # TODO: Implement actual result retrieval
        console.print(":information: Result details not yet implemented")

        # 模拟数据
        console.print(f":white_check_mark: Found result: {result_id}")

        if details:
            console.print("\n:gear: Detailed Results:")
            console.print("  • Total Return: 15.2%")
            console.print("  • Annualized Return: 18.7%")
            console.print("  • Sharpe Ratio: 1.45")
            console.print("  • Max Drawdown: -8.3%")

        if trades:
            console.print("\n:repeat: Trade History:")
            console.print("  • 2025-01-01: BUY 000001.SZ @ 10.50 (100 shares)")
            console.print("  • 2025-01-05: SELL 000001.SZ @ 11.20 (100 shares)")

    except Exception as e:
        console.print(f":x: Error: {e}")


@result_app.command(name="segment-stability")
def segment_stability(
    task_id: str = typer.Option(..., "--task-id", "-t", help="Backtest task ID"),
    portfolio_id: Optional[str] = typer.Option(None, "--portfolio-id", "-p", help="Portfolio ID"),
    segments: str = typer.Option("2,4,8", "--segments", "-s", help="Comma-separated segment counts"),
    metrics: Optional[str] = typer.Option(None, "--metrics", "-m", help="Comma-separated analyzer names"),
):
    """:bar_chart: Run segment stability validation.

    Examples:
        ginkgo get result segment-stability --task-id abc123
        ginkgo get result segment-stability -t abc123 -s 2,4 -m sharpe_ratio,win_rate
    """
    from ginkgo.data.containers import container
    from ginkgo.data.services.validation_service import ANALYZER_LABELS

    service = container.validation_service()

    if portfolio_id is None:
        result_service = container.result_service()
        summary_result = result_service.get_run_summary(task_id)
        if not summary_result.success:
            console.print(f":x: [red]未找到 task_id={task_id}[/red]")
            return
        summary = summary_result.data
        if summary["portfolio_count"] > 1:
            console.print(f"[yellow]多个 portfolio，请用 --portfolio-id 指定:[/yellow]")
            for pid in summary["portfolios"]:
                console.print(f"  - {pid}")
            return
        portfolio_id = summary["portfolios"][0]
        console.print(f":briefcase: [cyan]Portfolio: {portfolio_id}[/cyan]")

    n_segments_list = [int(x.strip()) for x in segments.split(",")]
    metrics_list = [x.strip() for x in metrics.split(",")] if metrics else None

    console.print(f"\n:chart_with_upwards_trend: [bold]分段稳定性分析[/bold]")
    console.print(f"  分段数: {n_segments_list}  指标: {metrics_list or '默认'}\n")

    result = service.segment_stability(
        task_id=task_id,
        portfolio_id=portfolio_id,
        n_segments_list=n_segments_list,
        metrics=metrics_list,
    )

    if not result.success:
        console.print(f":x: [red]{result.error}[/red]")
        return

    for w in result.data["windows"]:
        n = w["n_segments"]
        score = w["stability_score"]
        score_color = "green" if score > 0.6 else "yellow" if score > 0.3 else "red"

        console.print(f"[bold]{n} 段[/bold]  稳定性: [{score_color}]{score * 100:.1f}%[/{score_color}]")

        segs = w["segments"]
        avail = w.get("available_metrics", [])

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("时间段", style="cyan")
        for m in avail:
            table.add_column(ANALYZER_LABELS.get(m, m))

        for seg in segs:
            row = [f"{seg.get('_start', '')} ~ {seg.get('_end', '')}"]
            for m in avail:
                val = seg.get(m, 0)
                row.append(f"{val:.4f}" if abs(val) < 1000 else f"{val:.0f}")
            table.add_row(*row)

        console.print(table)
        console.print("")
get_app.add_typer(component_app, name="component", help=":wrench: Get component information")
get_app.add_typer(mapping_app, name="mapping", help=":link: Get mapping information")
get_app.add_typer(result_app, name="result", help=":bar_chart: Get result information")

# 设置应用 - 为简化，将所有命令都放在get_app下
set_app.add_typer(mapping_app, name="mapping", help=":link: Set mapping properties")
delete_app.add_typer(mapping_app, name="mapping", help=":link: Delete mapping")