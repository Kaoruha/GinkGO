# Upstream: CLI主入口(ginkgo component命令调用)
# Downstream: GCONF(WORKING_PATH配置)、FileService(组件文件注册)、subprocess(py_compile语法检查/EDITOR编辑器)、Path库(文件路径操作)、Rich库(表格/确认框/面板/语法高亮显示)
# Role: 文件系统组件管理CLI提供创建/编辑/删除/列表/验证等完整生命周期管理包含模板代码生成






"""
Ginkgo Component CLI - 组件创建、编辑和删除命令
支持策略、风控、选股器、仓位管理器等组件的完整生命周期管理
"""

import typer
from typing import Optional, List, Dict, Any
from pathlib import Path
import os
import subprocess
import datetime
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich.syntax import Syntax

app = typer.Typer(help="[blue]:wrench:[/blue] Component Management", rich_markup_mode="rich")
console = Console()

# 组件类型定义
COMPONENT_TYPES = {
    "strategy": {
        "directory": "strategies",
        "base_class": "BaseStrategy",
        "base_module": "ginkgo.trading.strategies.strategy_base",
        "file_types": ["basic", "ma", "rsi", "momentum", "bollinger", "volume"]
    },
    "riskmanager": {
        "directory": "risk_managements",
        "base_class": "BaseRiskManagement",
        "base_module": "ginkgo.backtest.strategy.risk_managements.base_risk_management",
        "file_types": ["basic", "stoploss", "position", "profitlimit", "losslimit"]
    },
    "selector": {
        "directory": "selectors",
        "base_class": "BaseSelector",
        "base_module": "ginkgo.backtest.strategy.selectors.base_selector",
        "file_types": ["basic", "fixed", "momentum", "fundamental"]
    },
    "sizer": {
        "directory": "sizers",
        "base_class": "BaseSizer",
        "base_module": "ginkgo.backtest.strategy.sizers.base_sizer",
        "file_types": ["basic", "fixed", "kelly", "atr", "riskparity"]
    },
    "analyzer": {
        "directory": "analyzers",
        "base_class": "BaseAnalyzer",
        "base_module": "ginkgo.backtest.analysis.analyzers.base_analyzer",
        "file_types": ["basic", "sharpe", "drawdown", "return", "risk"]
    }
}

# 用户组件目录（与库代码分离）
USER_COMPONENTS_DIR = Path.home() / ".ginkgo" / "components"

def get_user_component_dir(component_type: str) -> Path:
    """获取用户组件目录"""
    return USER_COMPONENTS_DIR / component_type

def get_library_component_dir(component_type: str) -> Path:
    """获取库组件目录"""
    from ginkgo.libs import GCONF
    ginkgo_root = GCONF.WORKING_PATH
    return Path(ginkgo_root) / "src" / "ginkgo" / "backtest" / "strategy" / COMPONENT_TYPES[component_type]["directory"]

@app.command()
def create(
    component_type: str = typer.Argument(..., help="Component type (strategy/riskmanager/selector/sizer/analyzer)"),
    name: str = typer.Option(..., "--name", "-n", help="Component name"),
    template: str = typer.Option("basic", "--template", "-t", help="Template type"),
    user_dir: bool = typer.Option(True, "--user-dir", "-u", help="Create in user directory"),
    open_editor: bool = typer.Option(False, "--edit", "-e", help="Open editor after creation"),
):
    """
    [green]➕[/green] Create a new component.

    Examples:
      ginkgo component create strategy MyStrategy --template ma
      ginkgo component create riskmanager StopLoss --template stoploss
      ginkgo component create selector MomentumSelector --template momentum
    """
    try:
        if component_type not in COMPONENT_TYPES:
            console.print(f"[red][red]:x:[/red][/red] Unknown component type: {component_type}")
            console.print(f"Available types: {', '.join(COMPONENT_TYPES.keys())}")
            raise typer.Exit(1)

        component_info = COMPONENT_TYPES[component_type]

        if template not in component_info["file_types"]:
            console.print(f"[red]:x:[/red] Unknown template: {template}")
            console.print(f"Available templates for {component_type}: {', '.join(component_info['file_types'])}")
            raise typer.Exit(1)

        # 选择目录
        if user_dir:
            component_dir = get_user_component_dir(component_type)
        else:
            component_dir = get_library_component_dir(component_type)

        # 确保目录存在
        component_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件路径
        class_name = f"{name}{component_type.title()}"
        file_name = f"{class_name.lower()}.py"
        file_path = component_dir / file_name

        # 检查文件是否已存在
        if file_path.exists():
            if not Confirm.ask(f"[yellow]:warning:[/yellow] File {file_path} already exists. Overwrite?"):
                console.print("[red]:x:[/red] Component creation cancelled")
                raise typer.Exit(0)

        # 生成组件代码
        content = _generate_component_code(component_type, template, name, class_name)

        # 写入文件
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        console.print(f"[green]:white_check_mark:[/green] Component created successfully!")
        console.print(f"[blue]:file_folder:[/blue] Location: {file_path}")
        console.print(f"[blue]:tag:[/blue]  Class: {class_name}")
        console.print(f"[blue]:art:[/blue] Template: {template}")

        # 注册组件
        if _register_component(component_type, file_path, name):
            console.print(f"[yellow]:memo:[/yellow] Component registered successfully")
        else:
            console.print(f"[yellow]:warning:[/yellow] Component created but registration failed")

        # 打开编辑器
        if open_editor:
            _open_editor(file_path)

    except Exception as e:
        console.print(f"[red]:x:[/red] Failed to create component: {e}")
        raise typer.Exit(1)

@app.command()
def edit(
    component_type: Optional[str] = typer.Argument(None, help="Filter by component type"),
    name_filter: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name"),
    list_only: bool = typer.Option(False, "--list", "-l", help="List components only"),
):
    """
    [yellow]:pencil:[/yellow] Edit components.

    Examples:
      ginkgo component edit --list                              # List all components
      ginkgo component edit strategy                               # Edit strategies
      ginkgo component edit strategy --name MyStrategy         # Edit specific strategy
    """
    try:
        if list_only:
            _list_components(component_type, name_filter)
            return

        # 获取组件列表
        components = _get_components(component_type, name_filter)

        if not components:
            console.print("[red]:x:[/red] No components found")
            raise typer.Exit(1)

        # 让用户选择组件
        if len(components) == 1:
            selected_component = components[0]
        else:
            console.print("[blue]:clipboard:[/blue] Available components:")
            table = Table()
            table.add_column("#", style="cyan", width=5)
            table.add_column("Type", style="green", width=12)
            table.add_column("Name", style="yellow", width=25)
            table.add_column("File", style="blue", width=40)

            for i, comp in enumerate(components, 1):
                table.add_row(str(i), comp["type"], comp["name"], str(comp["path"]))

            console.print(table)

            choice = Prompt.ask("Select component to edit (number)", choices=[str(i) for i in range(1, len(components)+1)])
            selected_component = components[int(choice) - 1]

        # 打开编辑器
        file_path = selected_component["path"]
        _open_editor(file_path)

        # 询问是否重新注册
        if Confirm.ask("[yellow]:memo:[/yellow] Re-register component after editing?"):
            if _register_component(selected_component["type"], file_path, selected_component["name"]):
                console.print("[green]:white_check_mark:[/green] Component re-registered successfully")
            else:
                console.print("[yellow]:warning:[/yellow] Component re-registration failed")

    except Exception as e:
        console.print(f"[red]:x:[/red] Failed to edit component: {e}")
        raise typer.Exit(1)

@app.command()
def delete(
    component_type: Optional[str] = typer.Argument(None, help="Filter by component type"),
    name_filter: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name"),
    list_only: bool = typer.Option(False, "--list", "-l", help="List components only"),
):
    """
    [red]:wastebasket:[/red] Delete components.

    Examples:
      ginkgo component delete --list                              # List all components
      ginkgo component delete strategy                               # Delete strategies
      ginkgo component delete strategy --name OldStrategy     # Delete specific strategy
    """
    try:
        if list_only:
            _list_components(component_type, name_filter)
            return

        # 获取组件列表
        components = _get_components(component_type, name_filter)

        if not components:
            console.print("[red]:x:[/red] No components found")
            raise typer.Exit(1)

        # 让用户选择组件
        if len(components) == 1:
            selected_component = components[0]
        else:
            console.print("[blue]:clipboard:[/blue] Available components:")
            table = Table()
            table.add_column("#", style="cyan", width=5)
            table.add_column("Type", style="green", width=12)
            table.add_column("Name", style="yellow", width=25)
            table.add_column("File", style="blue", width=40)

            for i, comp in enumerate(components, 1):
                table.add_row(str(i), comp["type"], comp["name"], str(comp["path"]))

            console.print(table)

            choice = Prompt.ask("Select component to delete (number)", choices=[str(i) for i in range(1, len(components)+1)])
            selected_component = components[int(choice) - 1]

        # 确认删除
        file_path = selected_component["path"]
        if not Confirm.ask(f"[yellow]:warning:[/yellow] Delete component '{selected_component['name']}' ({file_path})?"):
            console.print("[red]:x:[/red] Component deletion cancelled")
            raise typer.Exit(0)

        # 删除文件
        file_path.unlink()
        console.print(f"[green]:white_check_mark:[/green] Component file deleted: {file_path}")

        # 从注册中移除
        if _unregister_component(selected_component["type"], selected_component["name"]):
            console.print("[green]:white_check_mark:[/green] Component unregistered successfully")
        else:
            console.print("[yellow]:warning:[/yellow] Component file deleted but unregistration failed")

    except Exception as e:
        console.print(f"[red]:x:[/red] Failed to delete component: {e}")
        raise typer.Exit(1)

@app.command()
def list(
    component_type: Optional[str] = typer.Argument(None, help="Filter by component type"),
    name_filter: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name"),
    show_path: bool = typer.Option(False, "--path", "-p", help="Show file paths"),
):
    """
    [blue]:clipboard:[/blue] List components.

    Examples:
      ginkgo component list                                   # List all components
      ginkgo component list strategy                          # List strategies
      ginkgo component list strategy --name MyStrategy     # Filter by name
      ginkgo component list --path                         # Show file paths
    """
    _list_components(component_type, name_filter, show_path)

@app.command()
def validate(
    component_type: Optional[str] = typer.Argument(None, help="Filter by component type"),
    name_filter: Optional[str] = typer.Option(None, "--name", "-n", help="Filter by name"),
    fix_issues: bool = typer.Option(False, "--fix", "-f", help="Auto-fix issues"),
):
    """
    [blue]:mag:[/blue] Validate component syntax and structure.

    Examples:
      ginkgo component validate --list                         # List validation issues
      ginkgo component validate strategy --name MyStrategy     # Validate specific component
      ginkgo component validate --fix                          # Auto-fix issues
    """
    try:
        components = _get_components(component_type, name_filter)

        if not components:
            console.print("[red]:x:[/red] No components found")
            raise typer.Exit(1)

        total_issues = 0
        fixed_issues = 0

        for component in components:
            issues = _validate_component(component["path"])
            total_issues += len(issues)

            if issues:
                console.print(f"\n[blue]:mag:[/blue] {component['type']}/{component['name']}:")
                for issue in issues:
                    console.print(f"  [red]:x:[/red] {issue}")

                if fix_issues:
                    fixed = _fix_component_issues(component["path"], issues)
                    fixed_issues += len(fixed)
                    if fixed:
                        console.print(f"  [green]:white_check_mark:[/green] Fixed {len(fixed)} issues")
            else:
                console.print(f"[green]:white_check_mark:[/green] {component['type']}/{component['name']}: No issues found")

        console.print(f"\n[blue]:bar_chart:[/blue] Validation Summary:")
        console.print(f"  Total components checked: {len(components)}")
        console.print(f"  Total issues found: {total_issues}")
        if fix_issues:
            console.print(f"  Issues auto-fixed: {fixed_issues}")

    except Exception as e:
        console.print(f"[red]:x:[/red] Failed to validate components: {e}")
        raise typer.Exit(1)

# 辅助函数
def _generate_component_code(component_type: str, template: str, name: str, class_name: str) -> str:
    """生成组件代码"""
    templates = {
        ("strategy", "basic"): _get_basic_strategy_template,
        ("strategy", "ma"): _get_ma_strategy_template,
        ("strategy", "rsi"): _get_rsi_strategy_template,
        ("strategy", "momentum"): _get_momentum_strategy_template,
        ("riskmanager", "basic"): _get_basic_risk_template,
        ("riskmanager", "stoploss"): _get_stoploss_risk_template,
        ("selector", "basic"): _get_basic_selector_template,
        ("sizer", "basic"): _get_basic_sizer_template,
        ("analyzer", "basic"): _get_basic_analyzer_template,
    }

    template_key = (component_type, template)
    if template_key not in templates:
        template_key = (component_type, "basic")

    template_func = templates[template_key]
    return template_func(name, class_name)

# === 以下为模板函数，已迁移至 component_templates.py ===
from .component_templates import *  # noqa: F401,F403 导入所有模板函数
def _get_components(component_type: Optional[str], name_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """获取组件列表"""
    components = []

    # 如果没有指定类型，扫描所有类型
    if component_type:
        component_types = [component_type]
    else:
        component_types = COMPONENT_TYPES

    # 扫描每种类型的组件
    for comp_type in component_types:
        # 扫描用户目录
        user_dir = get_user_component_dir(comp_type)
        if user_dir.exists():
            for file_path in user_dir.glob("*.py"):
                if file_path.stem.startswith("__"):
                    continue

                # 简单的类名推断
                class_name = None
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        for line in content.split('\n'):
                            if line.strip().startswith('class ') and '(' in line:
                                class_name = line.split('(')[0].split()[1]
                                break
                except Exception as e:
                    GLOG.ERROR(f"Failed to read class name from file '{file_path}': {e}")

                component_name = file_path.stem
                if name_filter and name_filter.lower() not in component_name.lower():
                    continue

                components.append({
                    "type": comp_type,
                    "name": component_name,
                    "class_name": class_name or component_name.title(),
                    "path": file_path,
                    "user_dir": True
                })

        # 扫描库目录（只读模板）
        library_dir = get_library_component_dir(comp_type)
        if library_dir.exists():
            for file_path in library_dir.glob("*.py"):
                if file_path.stem.startswith("__") or file_path.stem.startswith("base_"):
                    continue

                component_name = file_path.stem
                if name_filter and name_filter.lower() not in component_name.lower():
                    continue

                components.append({
                    "type": comp_type,
                "name": component_name,
                "class_name": component_name.title(),
                "path": file_path,
                "user_dir": False
            })

    return components

def _list_components(component_type: Optional[str], name_filter: Optional[str] = None, show_path: bool = False):
    """列出组件"""
    components = _get_components(component_type, name_filter)

    if not components:
        console.print("[blue]📭[/blue] No components found")
        return

    table = Table()
    table.add_column("Type", style="cyan", width=12)
    table.add_column("Name", style="green", width=20)
    if show_path:
        table.add_column("Path", style="blue", width=50)
    table.add_column("Location", style="yellow", width=10)

    for comp in components:
        location = "User" if comp["user_dir"] else "Library"
        row = [comp["type"], comp["name"]]
        if show_path:
            row.append(str(comp["path"]))
        row.append(location)
        table.add_row(row)

    console.print(table)
    console.print(f"\n[blue]:bar_chart:[/blue] Total: {len(components)} components")

def _register_component(component_type: str, file_path: Path, name: str) -> bool:
    """注册组件到系统"""
    try:
        from ginkgo.data.containers import container
        from ginkgo.data.services.file_service import FILE_TYPES

        file_service = container.file_service()

        # 读取文件内容
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 添加文件到系统
        result = file_service.add(name=f"user_{name.lower()}",
                                   file_type=_get_file_type(component_type),
                                   data=content.encode('utf-8'))

        return result.success

    except Exception as e:
        console.print(f"[yellow]:warning:[/yellow] Registration warning: {e}")
        return False

def _unregister_component(component_type: str, name: str) -> bool:
    """从系统注销组件"""
    try:
        from ginkgo.data.containers import container
        from ginkgo.data.services.file_service import FILE_TYPES

        file_service = container.file_service()

        # 查找文件
        result = file_service.get(name=f"user_{name.lower()}",
                                   file_type=_get_file_type(component_type))

        if result.success and result.data.get("files"):
            file_id = result.data["files"][0].uuid
            delete_result = file_service.delete(file_id)
            return delete_result.success

    except Exception as e:
        console.print(f"[yellow]:warning:[/yellow] Unregistration warning: {e}")
        return False

def _get_file_type(component_type: str):
    """获取文件类型映射"""
    mapping = {
        "strategy": FILE_TYPES.STRATEGY,
        "riskmanager": FILE_TYPES.RISKMANAGER,
        "selector": FILE_TYPES.SELECTOR,
        "sizer": FILE_TYPES.SIZER,
        "analyzer": FILE_TYPES.ANALYZER
    }
    return mapping.get(component_type, FILE_TYPES.STRATEGY)

def _validate_component(file_path: Path) -> List[str]:
    """验证组件语法和结构"""
    issues = []

    try:
        # Python语法检查
        import subprocess
        result = subprocess.run(['python', '-m', 'py_compile', str(file_path)],
                                capture_output=True, text=True)
        if result.returncode != 0:
            issues.append("Syntax error")

        # 基本结构检查
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查必要的关键词
        required_keywords = ['__abstract__ = False', 'def cal(', 'def reset_state(']
        for keyword in required_keywords:
            if keyword not in content:
                issues.append(f"Missing: {keyword}")

        # 检查基类导入
        if 'from ' not in content and 'import ' not in content:
            issues.append("Missing base class import")

    except Exception as e:
        issues.append(f"Validation error: {e}")

    return issues

def _fix_component_issues(file_path: Path, issues: List[str]) -> List[str]:
    """自动修复组件问题"""
    fixed = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        for issue in issues:
            if "Missing: __abstract__ = False" in issue:
                if '__abstract__' in content:
                    content = content.replace('__abstract__ = True', '__abstract__ = False')
                    fixed.append("Fixed __abstract__ flag")
                else:
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'class ' in line:
                            lines[i] = line + '\n    __abstract__ = False  # Required for registration'
                            break
                    content = '\n'.join(lines)
                    fixed.append("Added __abstract__ flag")

            # 可以添加更多自动修复逻辑...

        if fixed:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

    except Exception as e:
        console.print(f"Auto-fix error: {e}")

    return fixed

def _open_editor(file_path: Path):
    """打开编辑器"""
    editor = os.environ.get('EDITOR', 'vim')
    try:
        subprocess.run([editor, str(file_path)])
    except FileNotFoundError:
        console.print(f"[red]:x:[/red] Editor '{editor}' not found. Please set EDITOR environment variable.")
        console.print("  Examples: export EDITOR=nano, export EDITOR=code")
        console.print("  Or install your preferred editor.")


if __name__ == "__main__":
    app()
