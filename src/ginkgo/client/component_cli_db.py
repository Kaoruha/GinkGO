# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: Component Cli Db模块提供提供 get_file_service 等工具函数支持相关业务功能






"""
Ginkgo Component Management CLI - Database-based System
基于数据库File表的组件管理CLI系统

组件管理功能：
- 创建：基于模板生成组件代码，存储到数据库File表
- 编辑：从数据库加载组件代码，编辑后更新回数据库
- 删除：从数据库删除组件记录
- 列表：从数据库查询组件列表
- 验证：验证组件代码的语法和结构

组件类型映射：
- strategy -> FILE_TYPES.STRATEGY
- riskmanager -> FILE_TYPES.RISKMANAGER
- selector -> FILE_TYPES.SELECTOR
- sizer -> FILE_TYPES.SIZER
- analyzer -> FILE_TYPES.ANALYZER
"""

import typer
from typing import Optional, List
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
# from rich.editor import Editor  # 暂时注释，使用subprocess代替
import subprocess
import os
import tempfile
from pathlib import Path

console = Console()

# 创建组件管理应用
app = typer.Typer(help="[blue]🔧[/blue] Database-based Component Management")

# 组件类型到FILE_TYPES的映射
COMPONENT_TYPE_MAP = {
    "strategy": "STRATEGY",
    "riskmanager": "RISKMANAGER",
    "selector": "SELECTOR",
    "sizer": "SIZER",
    "analyzer": "ANALYZER"
}

# 反向映射
FILE_TYPE_TO_COMPONENT = {v: k for k, v in COMPONENT_TYPE_MAP.items()}


def get_file_service():
    """获取FileService实例"""
    from ginkgo.data.containers import container
    return container.file_service()


def get_component_type_from_str(component_type: str) -> Optional[str]:
    """将字符串组件类型转换为FILE_TYPES枚举值"""
    return COMPONENT_TYPE_MAP.get(component_type.lower())


def get_template_code(component_type: str, template: str, name: str) -> str:
    """获取组件模板代码"""

    # 基础模板
    if template == "basic":
        if component_type == "strategy":
            return f'''"""
{name} Strategy
基础策略模板
"""

import datetime
from ginkgo.backtest.execution.events import EventSignalGeneration
from ginkgo.backtest.entities.signal import Signal
from ginkgo.backtest.strategy.strategies.base_strategy import StrategyBase
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.data import get_bars


class {name}(StrategyBase):
    """
    {name} 策略
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", *args, **kwargs):
        super({name}, self).__init__(name, *args, **kwargs)
        # 初始化策略参数
        self._window = 20

    def cal(self, portfolio_info, event, *args, **kwargs):
        """策略计算逻辑"""
        super({name}, self).cal(portfolio_info, event)

        # 获取历史数据
        date_start = self.now + datetime.timedelta(days=-self._window - 5)
        date_end = self.now
        df = get_bars(event.code, date_start, date_end, as_dataframe=True)

        if len(df) < self._window:
            return []  # 数据不足

        # 策略逻辑示例
        current_price = df['close'].iloc[-1]
        ma = df['close'].rolling(window=self._window).mean().iloc[-1]

        signals = []
        if current_price > ma:
            signal = Signal(
                code=event.code,
                direction=DIRECTION_TYPES.LONG,
                source=SOURCE_TYPES.STRATEGY,
                datetime=self.now,
                price=current_price,
                weight=1.0,
                reason="Price > Moving Average"
            )
            signals.append(signal)

        return signals

    def reset_state(self):
        """重置策略状态"""
        super().reset_state()
        # 重置自定义状态变量
        pass
'''
        elif component_type == "riskmanager":
            return f'''"""
{name} Risk Manager
基础风险管理模板
"""

from ginkgo.backtest.strategy.risk_managements.base_risk_management import BaseRiskManagement
from ginkgo.backtest.entities.signal import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


class {name}(BaseRiskManagement):
    """
    {name} 风险管理器
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", *args, **kwargs):
        super({name}, self).__init__(name, *args, **kwargs)
        # 初始化风控参数
        self._max_position_ratio = 0.2

    def cal(self, portfolio_info: dict, order):
        """被动风控：订单拦截和修改"""
        # 在这里实现订单风控逻辑
        return order

    def generate_signals(self, portfolio_info: dict, event) -> list:
        """主动风控：生成风控信号"""
        signals = []
        # 在这里实现主动风控逻辑
        return signals

    def reset_state(self):
        """重置风控状态"""
        super().reset_state()
        pass
'''
        elif component_type == "selector":
            return f'''"""
{name} Selector
基础选股器模板
"""

from ginkgo.backtest.strategy.selectors.base_selector import BaseSelector


class {name}(BaseSelector):
    """
    {name} 选股器
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", *args, **kwargs):
        super({name}, self).__init__(name, *args, **kwargs)
        # 初始化选股参数
        self._pool_size = 10

    def select(self, candidates: list, *args, **kwargs):
        """选股逻辑"""
        # 在这里实现选股逻辑
        return candidates[:self._pool_size]

    def reset_state(self):
        """重置选股状态"""
        super().reset_state()
        pass
'''
        elif component_type == "sizer":
            return f'''"""
{name} Sizer
基础仓位管理模板
"""

from ginkgo.backtest.strategy.sizers.base_sizer import BaseSizer


class {name}(BaseSizer):
    """
    {name} 仓位管理器
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", *args, **kwargs):
        super({name}, self).__init__(name, *args, **kwargs)
        # 初始化仓位参数
        self._default_ratio = 0.1

    def _size(self, signal):
        """仓位计算"""
        # 在这里实现仓位计算逻辑
        return self._default_ratio

    def reset_state(self):
        """重置仓位状态"""
        super().reset_state()
        pass
'''
        elif component_type == "analyzer":
            return f'''"""
{name} Analyzer
基础分析器模板
"""

from ginkgo.backtest.strategy.analyzers.base_analyzer import BaseAnalyzer


class {name}(BaseAnalyzer):
    """
    {name} 分析器
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", *args, **kwargs):
        super({name}, self).__init__(name, *args, **kwargs)
        # 初始化分析参数

    def _do_activate(self):
        """激活分析器"""
        pass

    def _do_record(self, *args, **kwargs):
        """记录数据"""
        pass

    def _do_calculate(self):
        """计算分析结果"""
        return {{}}

    def reset_state(self):
        """重置分析状态"""
        super().reset_state()
        pass
'''

    # 如果没有找到对应模板，返回基础模板
    return f'''"""
{name} Component
基础组件模板
"""

# 请根据组件类型实现相应的逻辑
# Strategy: 继承 StrategyBase
# RiskManager: 继承 BaseRiskManagement
# Selector: 继承 BaseSelector
# Sizer: 继承 BaseSizer
# Analyzer: 继承 BaseAnalyzer

class {name}:
    """
    {name} 组件
    """
    __abstract__ = False

    def __init__(self, name: str = "{name}", *args, **kwargs):
        pass

    def reset_state(self):
        """重置状态"""
        pass
'''


@app.command()
def create(
    component_type: str = typer.Argument(..., help="Component type (strategy/riskmanager/selector/sizer/analyzer)"),
    name: str = typer.Option(..., "--name", "-n", help="Component name"),
    template: str = typer.Option("basic", "--template", "-t", help="Template type (basic/ma/rsi)"),
    description: str = typer.Option("", "--description", "-d", help="Component description"),
):
    """[green]➕[/green] Create a new component and save to database.

    Examples:
      ginkgo component create strategy --name MyStrategy --template ma
      ginkgo component create riskmanager --name StopLoss --template basic
      ginkgo component create selector --name MomentumSelector --template basic
    """
    try:
        # 验证组件类型
        file_type_str = get_component_type_from_str(component_type)
        if not file_type_str:
            console.print(f"[red]❌[/red] Invalid component type: {component_type}")
            console.print(f"[green]✅[/green] Valid types: {', '.join(COMPONENT_TYPE_MAP.keys())}")
            raise typer.Exit(1)

        # 获取FileService
        file_service = get_file_service()

        # 检查组件是否已存在
        from ginkgo.enums import FILE_TYPES
        file_type = getattr(FILE_TYPES, file_type_str)
        existing_result = file_service.get_by_name(name, file_type)

        if existing_result.success and existing_result.data:
            console.print(f"[yellow]⚠️[/yellow] Component '{name}' already exists")
            if not typer.confirm("Overwrite existing component?"):
                console.print("[red]❌[/red] Component creation cancelled")
                raise typer.Exit(0)

        # 生成模板代码
        class_name = name  # 直接使用名称作为类名
        template_code = get_template_code(component_type, template, class_name)

        # 保存到数据库
        description = description or f"{component_type.title()} component: {name}"
        result = file_service.add(
            name=name,
            file_type=file_type,
            data=template_code.encode('utf-8'),
            description=description
        )

        if result.success:
            file_info = result.data.get("file_info", {})
            console.print(f"[green]✅[/green] Component created successfully!")
            console.print(f"[blue]📋[/blue] Name: {name}")
            console.print(f"[blue]🏷️[/blue]  Type: {component_type}")
            console.print(f"[blue]🆔[/blue] UUID: {file_info.get('uuid', 'N/A')}")
            console.print(f"[yellow]📝[/yellow] Description: {description}")
            console.print(f"[blue]💾[/blue] Stored in database (File table)")
        else:
            console.print(f"[red]❌[/red] Failed to create component: {result.message}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌[/red] Error creating component: {str(e)}")
        raise typer.Exit(1)


@app.command()
def list(
    component_type: Optional[str] = typer.Argument(None, help="Filter by component type"),
    name_filter: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name"),
):
    """[blue]📋[/blue] List components from database.

    Examples:
      ginkgo component list                          # List all components
      ginkgo component list strategy                 # List strategies only
      ginkgo component list --name MyStrategy        # Filter by name
      ginkgo component list strategy --name Test     # Filter by type and name
    """
    try:
        file_service = get_file_service()

        if component_type:
            # 按类型查询
            file_type_str = get_component_type_from_str(component_type)
            if not file_type_str:
                console.print(f"[red]❌[/red] Invalid component type: {component_type}")
                raise typer.Exit(1)

            from ginkgo.enums import FILE_TYPES
            file_type = getattr(FILE_TYPES, file_type_str)
            result = file_service.get_by_type(file_type)
        else:
            # 查询所有组件类型
            result = file_service.get()

        if not result.success:
            console.print(f"[red]❌[/red] Failed to list components: {result.message}")
            raise typer.Exit(1)

        # 提取文件列表
        data = result.data
        if isinstance(data, dict):
            components = data.get("files", [])
        else:
            components = data if data else []

        if not components:
            console.print("[blue]📭[/blue] No components found")
            return

        # 应用名称过滤
        if name_filter:
            components = [c for c in components if name_filter.lower() in c.name.lower()]

        if not components:
            console.print(f"[blue]📭[/blue] No components found matching filter: {name_filter}")
            return

        # 显示组件表格
        table = Table(title=f"[blue]📋[/blue] Components ({'All' if not component_type else component_type.title()})")
        table.add_column("UUID", style="cyan", width=36)
        table.add_column("Name", style="green", width=25)
        table.add_column("Type", style="yellow", width=15)
        table.add_column("Description", style="white", width=40)
        table.add_column("Size", style="dim", width=10)

        for component in components:
            # 处理不同的数据格式
            comp_uuid = getattr(component, 'uuid', getattr(component, 'id', 'N/A'))
            comp_name = getattr(component, 'name', 'Unknown')
            comp_desc = getattr(component, 'description', '') or ''

            # 获取类型信息
            comp_type = getattr(component, 'type', None)
            if comp_type:
                if hasattr(comp_type, 'name'):
                    component_type_name = FILE_TYPE_TO_COMPONENT.get(comp_type.name, comp_type.name.lower())
                elif isinstance(comp_type, str):
                    component_type_name = FILE_TYPE_TO_COMPONENT.get(comp_type, comp_type.lower())
                else:
                    component_type_name = str(comp_type)
            else:
                component_type_name = 'unknown'

            table.add_row(
                str(comp_uuid)[:36],
                str(comp_name)[:23],
                component_type_name,
                str(comp_desc)[:37],
                "N/A"  # File数据可能不在列表查询中返回
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌[/red] Error listing components: {str(e)}")
        raise typer.Exit(1)


@app.command()
def edit(
    identifier: str = typer.Argument(..., help="Component UUID or name"),
    component_type: Optional[str] = typer.Option(None, "--type", "-t", help="Component type (required if using name)"),
):
    """[yellow]✏️[/yellow] Edit component code from database.

    Examples:
      ginkgo component edit 123e4567-e89b-12d3-a456-426614174000    # Edit by UUID
      ginkgo component edit MyStrategy --type strategy              # Edit by name
    """
    try:
        file_service = get_file_service()

        # 查找组件
        component = None
        if len(identifier.replace('-', '')) >= 30:  # UUID格式（至少30个字符）
            # 按UUID查询
            result = file_service.get_by_uuid(identifier)
            if result.success and result.data:
                # get_by_uuid返回格式: {"file": files[0], "exists": True}
                data = result.data
                if isinstance(data, dict):
                    component = data.get("file")
                else:
                    component = data
        else:
            # 按名称查询，需要指定类型
            if not component_type:
                console.print("[red]❌[/red] Component type required when using name")
                console.print("[yellow]💡[/yellow] Use: ginkgo component edit NAME --type TYPE")
                raise typer.Exit(1)

            file_type_str = get_component_type_from_str(component_type)
            if not file_type_str:
                console.print(f"[red]❌[/red] Invalid component type: {component_type}")
                raise typer.Exit(1)

            from ginkgo.enums import FILE_TYPES
            file_type = getattr(FILE_TYPES, file_type_str)
            result = file_service.get_by_name(identifier, file_type)
            if result.success:
                component = result.data

        if not component:
            console.print(f"[red]❌[/red] Component not found: {identifier}")
            raise typer.Exit(1)

        # 获取组件代码
        content_result = file_service.get_content(component.uuid)
        content = content_result.data if content_result.is_success() else None
        if not content:
            console.print(f"[red]❌[/red] Failed to load component content")
            raise typer.Exit(1)

        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(content.decode('utf-8'))
            temp_file = f.name

        try:
            # 打开编辑器
            editor_cmd = os.environ.get('EDITOR', 'nano')  # 默认使用nano
            console.print(f"[yellow]📝[/yellow] Opening editor ({editor_cmd}) for component: {component.name}")
            console.print(f"[yellow]💡[/yellow] Save and exit editor to update component in database")

            # 使用subprocess打开编辑器
            result = subprocess.run([editor_cmd, temp_file], capture_output=False)
            if result.returncode == 0:
                # 读取编辑后的内容
                with open(temp_file, 'r', encoding='utf-8') as f:
                    edited_content = f.read()
            else:
                console.print("[red]❌[/red] Editor cancelled or failed")
                return

            if edited_content and edited_content != content.decode('utf-8'):
                # 内容已更改，更新数据库
                update_result = file_service.update(
                    file_id=component.uuid,
                    name=component.name,
                    file_type=component.type,
                    data=edited_content.encode('utf-8'),
                    description=component.description
                )

                if update_result.success:
                    console.print(f"[green]✅[/green] Component updated successfully!")
                    console.print(f"[blue]📋[/blue] Name: {component.name}")
                    console.print(f"[blue]🆔[/blue] UUID: {component.uuid}")
                else:
                    console.print(f"[red]❌[/red] Failed to update component: {update_result.message}")
                    console.print("[yellow]⚠️[/yellow] Changes not saved to database")
            else:
                console.print("[blue]ℹ️[/blue] No changes made")

        finally:
            # 清理临时文件
            try:
                os.unlink(temp_file)
            except:
                pass

    except Exception as e:
        console.print(f"[red]❌[/red] Error editing component: {str(e)}")
        raise typer.Exit(1)


@app.command()
def delete(
    identifier: str = typer.Argument(..., help="Component UUID or name"),
    component_type: Optional[str] = typer.Option(None, "--type", "-t", help="Component type (required if using name)"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation"),
):
    """[red]🗑️[/red] Delete component from database.

    Examples:
      ginkgo component delete 123e4567-e89b-12d3-a456-426614174000    # Delete by UUID
      ginkgo component delete MyStrategy --type strategy              # Delete by name
    """
    try:
        file_service = get_file_service()

        # 查找组件
        component = None
        if len(identifier.replace('-', '')) >= 30:  # UUID格式（至少30个字符）
            # 按UUID查询
            result = file_service.get_by_uuid(identifier)
            if result.success and result.data:
                # get_by_uuid返回格式: {"file": files[0], "exists": True}
                data = result.data
                if isinstance(data, dict):
                    component = data.get("file")
                else:
                    component = data
        else:
            # 按名称查询，需要指定类型
            if not component_type:
                console.print("[red]❌[/red] Component type required when using name")
                console.print("[yellow]💡[/yellow] Use: ginkgo component delete NAME --type TYPE")
                raise typer.Exit(1)

            file_type_str = get_component_type_from_str(component_type)
            if not file_type_str:
                console.print(f"[red]❌[/red] Invalid component type: {component_type}")
                raise typer.Exit(1)

            from ginkgo.enums import FILE_TYPES
            file_type = getattr(FILE_TYPES, file_type_str)
            result = file_service.get_by_name(identifier, file_type)
            if result.success:
                component = result.data

        if not component:
            console.print(f"[red]❌[/red] Component not found: {identifier}")
            raise typer.Exit(1)

        # 确认删除
        if not confirm:
            console.print(f"[blue]🔍[/blue] Component to delete:")
            console.print(f"[blue]📋[/blue] Name: {component.name}")
            console.print(f"[blue]🏷️[/blue]  Type: {component.type.name}")
            console.print(f"[blue]🆔[/blue] UUID: {component.uuid}")
            console.print(f"[yellow]📝[/yellow] Description: {component.description or 'No description'}")

            if not typer.confirm(f"Delete component '{component.name}'?"):
                console.print("[red]❌[/red] Component deletion cancelled")
                raise typer.Exit(0)

        # 执行删除
        result = file_service.delete(component.uuid)

        if result.success:
            console.print(f"[green]✅[/green] Component deleted successfully!")
            console.print(f"[blue]📋[/blue] Name: {component.name}")
            console.print(f"[blue]🆔[/blue] UUID: {component.uuid}")
        else:
            console.print(f"[red]❌[/red] Failed to delete component: {result.message}")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌[/red] Error deleting component: {str(e)}")
        raise typer.Exit(1)


@app.command()
def validate(
    identifier: str = typer.Argument(..., help="Component UUID or name"),
    component_type: Optional[str] = typer.Option(None, "--type", "-t", help="Component type (required if using name)"),
):
    """[blue]🔍[/blue] Validate component syntax and structure.

    Examples:
      ginkgo component validate 123e4567-e89b-12d3-a456-426614174000    # Validate by UUID
      ginkgo component validate MyStrategy --type strategy              # Validate by name
    """
    try:
        file_service = get_file_service()

        # 查找组件
        component = None
        if len(identifier.replace('-', '')) >= 30:  # UUID格式（至少30个字符）
            # 按UUID查询
            result = file_service.get_by_uuid(identifier)
            if result.success and result.data:
                # get_by_uuid返回格式: {"file": files[0], "exists": True}
                data = result.data
                if isinstance(data, dict):
                    component = data.get("file")
                else:
                    component = data
        else:
            # 按名称查询，需要指定类型
            if not component_type:
                console.print("[red]❌[/red] Component type required when using name")
                console.print("[yellow]💡[/yellow] Use: ginkgo component validate NAME --type TYPE")
                raise typer.Exit(1)

            file_type_str = get_component_type_from_str(component_type)
            if not file_type_str:
                console.print(f"[red]❌[/red] Invalid component type: {component_type}")
                raise typer.Exit(1)

            from ginkgo.enums import FILE_TYPES
            file_type = getattr(FILE_TYPES, file_type_str)
            result = file_service.get_by_name(identifier, file_type)
            if result.success:
                component = result.data

        if not component:
            console.print(f"[red]❌[/red] Component not found: {identifier}")
            raise typer.Exit(1)

        # 获取组件代码
        content_result = file_service.get_content(component.uuid)
        content = content_result.data if content_result.is_success() else None
        if not content:
            console.print(f"[red]❌[/red] Failed to load component content")
            raise typer.Exit(1)

        code_str = content.decode('utf-8')

        console.print(f"[blue]🔍[/blue] Validating component: {component.name}")
        console.print(f"[blue]🏷️[/blue]  Type: {component.type.name}")

        # 语法检查
        try:
            compile(code_str, '<string>', 'exec')
            console.print("[green]✅[/green] Python syntax: Valid")
        except SyntaxError as e:
            console.print(f"[red]❌[/red] Python syntax error: {e}")
            console.print(f"[blue]📍[/blue] Line {e.lineno}: {e.text}")
            return

        # 结构检查
        if component.type.name == "STRATEGY":
            if "class " in code_str and "StrategyBase" in code_str:
                console.print("[green]✅[/green] Strategy structure: Valid")
            else:
                console.print("[yellow]⚠️[/yellow] Strategy structure: Should inherit from StrategyBase")

        elif component.type.name == "RISKMANAGER":
            if "class " in code_str and "BaseRiskManagement" in code_str:
                console.print("[green]✅[/green] RiskManager structure: Valid")
            else:
                console.print("[yellow]⚠️[/yellow] RiskManager structure: Should inherit from BaseRiskManagement")

        elif component.type.name == "SELECTOR":
            if "class " in code_str and "BaseSelector" in code_str:
                console.print("[green]✅[/green] Selector structure: Valid")
            else:
                console.print("[yellow]⚠️[/yellow] Selector structure: Should inherit from BaseSelector")

        elif component.type.name == "SIZER":
            if "class " in code_str and "BaseSizer" in code_str:
                console.print("[green]✅[/green] Sizer structure: Valid")
            else:
                console.print("[yellow]⚠️[/yellow] Sizer structure: Should inherit from BaseSizer")

        elif component.type.name == "ANALYZER":
            if "class " in code_str and "BaseAnalyzer" in code_str:
                console.print("[green]✅[/green] Analyzer structure: Valid")
            else:
                console.print("[yellow]⚠️[/yellow] Analyzer structure: Should inherit from BaseAnalyzer")

        # 检查__abstract__ = False
        if "__abstract__ = False" in code_str:
            console.print("[green]✅[/green] Abstract status: Correctly set to False")
        else:
            console.print("[yellow]⚠️[/yellow] Abstract status: Should include '__abstract__ = False'")

        console.print(f"[blue]📊[/blue] Code size: {len(code_str)} characters")
        console.print("[blue]🎉[/blue] Component validation completed!")

    except Exception as e:
        console.print(f"[red]❌[/red] Error validating component: {str(e)}")
        raise typer.Exit(1)


@app.command()
def show(
    identifier: str = typer.Argument(..., help="Component UUID or name"),
    component_type: Optional[str] = typer.Option(None, "--type", "-t", help="Component type (required if using name)"),
    lines: int = typer.Option(50, "--lines", "-l", help="Number of lines to show"),
):
    """[blue]📖[/blue] Show component code preview.

    Examples:
      ginkgo component show 123e4567-e89b-12d3-a456-426614174000    # Show by UUID
      ginkgo component show MyStrategy --type strategy --lines 100 # Show by name with custom lines
    """
    try:
        file_service = get_file_service()

        # 查找组件
        component = None
        if len(identifier.replace('-', '')) >= 30:  # UUID格式（至少30个字符）
            # 按UUID查询
            result = file_service.get_by_uuid(identifier)
            if result.success and result.data:
                # get_by_uuid返回格式: {"file": files[0], "exists": True}
                data = result.data
                if isinstance(data, dict):
                    component = data.get("file")
                else:
                    component = data
        else:
            # 按名称查询，需要指定类型
            if not component_type:
                console.print("[red]❌[/red] Component type required when using name")
                console.print("[yellow]💡[/yellow] Use: ginkgo component show NAME --type TYPE")
                raise typer.Exit(1)

            file_type_str = get_component_type_from_str(component_type)
            if not file_type_str:
                console.print(f"[red]❌[/red] Invalid component type: {component_type}")
                raise typer.Exit(1)

            from ginkgo.enums import FILE_TYPES
            file_type = getattr(FILE_TYPES, file_type_str)
            result = file_service.get_by_name(identifier, file_type)
            if result.success:
                component = result.data

        if not component:
            console.print(f"[red]❌[/red] Component not found: {identifier}")
            raise typer.Exit(1)

        # 获取组件代码
        content_result = file_service.get_content(component.uuid)
        content = content_result.data if content_result.is_success() else None
        if not content:
            console.print(f"[red]❌[/red] Failed to load component content")
            raise typer.Exit(1)

        code_str = content.decode('utf-8')

        console.print(f"[blue]📖[/blue] Component: {component.name}")
        console.print(f"[blue]🏷️[/blue]  Type: {component.type.name}")
        console.print(f"[blue]🆔[/blue] UUID: {component.uuid}")
        console.print(f"[yellow]📝[/yellow] Description: {component.description or 'No description'}")
        console.print(f"[blue]📊[/blue] Size: {len(code_str)} characters")
        console.print()

        # 显示代码行
        code_lines = code_str.split('\n')
        for i, line in enumerate(code_lines[:lines], 1):
            console.print(f"{i:4d}: {line}")

        if len(code_lines) > lines:
            console.print(f"... ({len(code_lines) - lines} more lines)")

    except Exception as e:
        console.print(f"[red]❌[/red] Error showing component: {str(e)}")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()