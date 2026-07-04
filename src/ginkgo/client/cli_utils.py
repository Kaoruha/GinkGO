# Upstream: Data Layer
# Downstream: External APIs (Tushare, Yahoo, etc.)
# Role: 提供CLI通用工具函数包括获取参数/添加组件/显示树结构等辅助方法






import json
import os
import sys
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

import pandas as pd
import typer
from rich.console import Console
from rich.tree import Tree
from ginkgo.enums import FILE_TYPES

console = Console()

def _get_component_parameters(mapping_id: str, file_id: str, file_type: FILE_TYPES) -> dict:
    """获取组件的参数信息"""
    try:
        from ginkgo.data.containers import container
        
        # 从params表获取所有构造参数
        param_crud = container.cruds.param()
        params_df = param_crud.find(filters={"mapping_id": mapping_id}, order_by="index")
        params_dict = {}
        
        if params_df.shape[0] > 0:
            # 显示所有参数，使用索引作为键名
            for i, param_value in enumerate(params_df["value"].values):
                params_dict[f"param_{i}"] = param_value
        
        return params_dict
        
    except Exception as e:
        console.print(f"[red]Error getting parameters for {file_id}: {e}[/red]")
        return {}

def _add_portfolio_components(parent_node, portfolio_id: str, detail: bool, filter_type: Optional[FILE_TYPES]):
    """添加Portfolio的组件到树节点"""
    from ginkgo.data.containers import container
    
    # 获取portfolio的文件映射（#6136: 走 mapping_service._df 出口，data 即 DataFrame）
    mapping_service = container.mapping_service()
    mappings_result = mapping_service.get_portfolio_file_mappings_df(portfolio_uuid=portfolio_id)
    portfolio_files = mappings_result.data if mappings_result.success else pd.DataFrame()
    
    if portfolio_files.shape[0] == 0:
        parent_node.add("[dim]No components bound to this portfolio[/dim]")
        return
    
    # 按文件类型分组
    components = {
        "selectors": [],
        "sizers": [],
        "strategies": [],
        "risks": [],
        "analyzers": []
    }
    
    for _, mapping in portfolio_files.iterrows():
        file_type_value = mapping["type"]
        # 将数字转换为枚举
        file_type = FILE_TYPES(file_type_value)
        component_info = {
            "name": mapping["name"],
            "id": mapping["file_id"],
            "mapping_id": mapping["uuid"],
            "type": file_type
        }
        
        if file_type == FILE_TYPES.SELECTOR:
            components["selectors"].append(component_info)
        elif file_type == FILE_TYPES.SIZER:
            components["sizers"].append(component_info)
        elif file_type == FILE_TYPES.STRATEGY:
            components["strategies"].append(component_info)
        elif file_type == FILE_TYPES.RISKMANAGER:
            components["risks"].append(component_info)
        elif file_type == FILE_TYPES.ANALYZER:
            components["analyzers"].append(component_info)
    
    # 根据filter_type筛选要显示的组件类型
    component_sections = []
    if filter_type is None:
        component_sections = [
            ("selectors", ":dart: Selectors", "selector"),
            ("sizers", ":balance_scale: Sizers", "sizer"),
            ("strategies", ":chart_with_upwards_trend: Strategies", "strategy"),
            ("risks", ":shield: Risk Managements", "risk"),
            ("analyzers", ":bar_chart: Analyzers", "analyzer")
        ]
    else:
        type_mapping = {
            FILE_TYPES.SELECTOR: ("selectors", ":dart: Selectors", "selector"),
            FILE_TYPES.SIZER: ("sizers", ":balance_scale: Sizers", "sizer"),
            FILE_TYPES.STRATEGY: ("strategies", ":chart_with_upwards_trend: Strategies", "strategy"),
            FILE_TYPES.RISKMANAGER: ("risks", ":shield: Risk Managements", "risk"),
            FILE_TYPES.ANALYZER: ("analyzers", ":bar_chart: Analyzers", "analyzer")
        }
        if filter_type in type_mapping:
            component_sections = [type_mapping[filter_type]]
    
    # 显示各类组件
    for component_key, section_title, _ in component_sections:
        component_list = components[component_key]
        if component_list:
            section_node = parent_node.add(f"[bold]{section_title}[/bold]")
            for component in component_list:
                component_node = section_node.add(f"{component['name']} [dim]ID:{component['id']}[/dim]")
                
                if detail:
                    # 获取并显示组件参数详情
                    params = _get_component_parameters(component['mapping_id'], component['id'], component['type'])
                    if params:
                        for param_name, param_value in params.items():
                            component_node.add(f"[cyan]{param_name}[/cyan]: [green]{param_value}[/green]")
                    else:
                        component_node.add("[dim]No parameters found[/dim]")

def _show_portfolio_tree(portfolio_row, detail: bool, filter_type: Optional[FILE_TYPES]):
    """显示Portfolio树结构"""
    tree = Tree(f"[bold green]Portfolio:[/bold green] {portfolio_row['name']} ([yellow]{portfolio_row['uuid']}[/yellow])")
    _add_portfolio_components(tree, portfolio_row['uuid'], detail, filter_type)
    console.print(tree)

def _show_engine_tree(engine_row, detail: bool, filter_type: Optional[FILE_TYPES]):
    """显示Engine树结构"""
    from ginkgo.data.containers import container
    
    tree = Tree(f"[bold blue]Engine:[/bold blue] {engine_row['name']} ([cyan]{engine_row['uuid']}[/cyan])")
    
    # 获取engine关联的portfolios（#6136: 走 mapping_service._df 出口，data 即 DataFrame）
    mapping_service = container.mapping_service()
    mappings_result = mapping_service.get_engine_portfolio_mappings_df(engine_uuid=engine_row["uuid"])
    engine_portfolios = mappings_result.data if mappings_result.success else pd.DataFrame()
    
    if engine_portfolios.shape[0] == 0:
        tree.add("[dim]No portfolios bound to this engine[/dim]")
    else:
        for _, mapping in engine_portfolios.iterrows():
            portfolio_id = mapping["portfolio_id"]
            # 获取portfolio详情
            portfolio_service = container.portfolio_service()
            portfolio_df = portfolio_service.get_portfolio(portfolio_id)
            if portfolio_df.shape[0] > 0:
                portfolio_row = portfolio_df.iloc[0]
                portfolio_branch = tree.add(f"[bold green]Portfolio:[/bold green] {portfolio_row['name']} ([yellow]{portfolio_id}[/yellow])")
                _add_portfolio_components(portfolio_branch, portfolio_id, detail, filter_type)

    console.print(tree)


# ============================================================================
# ADR-021 E2 (#6577): CLI 输出层 helper
# 契约锚点: docs/adrs/ADR-021-cli-output-layer.md (10 维)
# ============================================================================


class CliConfirmError(Exception):
    """safe_confirm 在非 TTY 且未提供 --yes 时抛出。

    专用异常避免被通用 ``except Exception`` 吞（呼应
    ``arch_typer_exit_caught_by_except``）。调用方按具体类型捕获，
    不与 typer.Exit / 业务异常混淆。
    """


def is_interactive(explicit: Optional[bool] = None) -> bool:
    """判断当前是否交互模式（ADR-021 第 2 维）。

    - 默认 ``sys.stdin.isatty()``（人=交互，管道=非交互）
    - ``explicit=True/False`` 覆盖（docker ``-it`` 风格）
    - ``--format json`` 隐含非交互，由调用方判断后传 ``explicit=False``
    """
    if explicit is not None:
        return bool(explicit)
    return bool(sys.stdin.isatty())


def make_console(
    *,
    no_color: bool = False,
    isatty: Optional[bool] = None,
    stderr: bool = True,
) -> Console:
    """构造统一配置的 rich Console（ADR-021 第 7 维）。

    三层 NO_COLOR 优先级：
      Layer 1 自动检测（``isatty`` → emoji 开关；彩色由 rich 据 color_system+TTY 决定）
      Layer 2 ``NO_COLOR`` 环境变量（no-color.org 标准，存在即禁用彩色）
      Layer 3 ``--no-color`` flag 显式覆盖（优先级最高）

    保留 unicode emoji（``:x:`` → ``❌``）；**禁用** ``Console(emoji=False)``
    ——它会保留 ``:x:`` 原文，比无 emoji 更糟（ADR-021 实证）。
    """
    # Layer 3 优先；Layer 2 兜底（任一为真即禁彩色）
    use_color = not (no_color or ("NO_COLOR" in os.environ))
    if isatty is None:
        isatty = bool(sys.stdin.isatty() or sys.stdout.isatty())
    return Console(
        emoji=bool(isatty),
        color_system=None if not use_color else "auto",
        legacy_windows=False,
        stderr=stderr,
    )


class GinkgoJSONEncoder(json.JSONEncoder):
    """Ginkgo 统一 JSON 编码器（ADR-021 第 10 维）。

    - datetime/date → ISO8601（``T`` 分隔，非空格）
    - Decimal → str（金融精度，float 会丢；与 ADR-005 序列化对称同精神）
    - UUID → 带横线（用户面向，与库内 hex 存储 ``arch_uuid_storage_no_dashes`` 分层）
    - pydantic BaseModel → ``model_dump(mode="json")``（duck-typing，避免顶部
      import pydantic 拖慢 CLI 启动，呼应 ``arch_module_level_validator_import_crash``）
    - SQLAlchemy Model → 列字典
    - DataFrame → ``to_dict('records')``（每行一对象，jq 友好）
    """

    def default(self, obj):
        # datetime 必须先于 date 判断（datetime 是 date 子类）
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict("records")
        # pydantic v2 BaseModel（duck-typing on model_dump）
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="json")
        # SQLAlchemy ORM Model
        if hasattr(obj, "__table__"):
            return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        return super().default(obj)


def safe_confirm(
    message: str,
    *,
    default: bool = False,
    require_tty: bool = True,
    yes_flag: bool = False,
) -> bool:
    """TTY 守卫的危险操作确认（ADR-021 第 3 维）。

    - ``yes_flag=True``（``--yes``）：返 True，显式跳过（最高优先级）
    - TTY：正常 ``typer.confirm``
    - 非 TTY + ``require_tty=True``：抛 ``CliConfirmError``（拒绝静默走 default）
    - 非 TTY + ``require_tty=False``：返 ``default``（向后兼容场景）
    """
    if yes_flag:
        return True
    if sys.stdin.isatty():
        return bool(typer.confirm(message, default=default))
    if require_tty:
        raise CliConfirmError(
            f"需要交互确认但当前非 TTY：{message!r}（用 --yes 显式跳过）"
        )
    return bool(default)


def make_progress(*, format: str, isatty: bool) -> Optional["Progress"]:
    """构造 rich Progress（ADR-021 第 8 维）。

    - JSON 模式或非 TTY：返 ``None``（禁用 rich 渲染，避免污染 JSON 输出/日志）
    - TTY + text 模式：返 ``Progress(transient=True)``，console 走 stderr
      （契约：进度永远 stderr，结果永远 stdout，二者不混）

    Progress 延迟 import（仅 TTY+text 路径用到，保持模块顶部轻量）。
    """
    if format == "json" or not isatty:
        return None
    from rich.progress import Progress

    return Progress(
        console=Console(stderr=True),
        transient=True,
    )


def format_result(result, *, format: str, command: str) -> None:
    """统一 ServiceResult → 输出（ADR-021 第 5 维）。

    .. warning::
        **Step 2，阻塞 #6576**。依赖 ``ServiceResult.code`` 字段（``Optional[str]``），
        由 E1 (#6576) 落地决策，当前 master 未合并。本 helper 现为占位，
        待 #6576 合并后实现：

        - 成功 list：``{"success": true, "data": [...], "count": N, "metadata": {}}``
        - 成功 get：``{"success": true, "data": {...}}``
        - 失败：``{"success": false, "error": {"code": ..., "message": ...}, "data": null}``
        - exit code 映射：``BAD_PARAMS``→2 / ``TIMEOUT``→124 / 其余→1

        按归因纪律（CLAUDE.md）：raise 而非 stub 兜底——宁可响亮报错，
        也不静默返回错误结构误导调用方。
    """
    raise NotImplementedError(
        "format_result 待 #6576 (E1 ServiceResult.code) 合并后实现："
        f"当前 command={command!r} format={format!r} 暂不支持。"
    )
