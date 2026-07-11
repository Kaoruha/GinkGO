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
    - pydantic BaseModel → ``model_dump(mode="json")``（isinstance 判定 + 延迟 import，
      防 MagicMock duck-trap 无限递归；呼应 ``arch_module_level_validator_import_crash``）
    - SQLAlchemy DeclarativeBase → 列字典（isinstance 判定，非 ``hasattr(__table__)``）
    - 未识别类型 → ``raise TypeError``（响亮失败，json 标准契约；非 ``super().default()`` 兜底）
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
        # pydantic v2 BaseModel —— isinstance 替代 hasattr，防 MagicMock duck-trap 无限递归
        try:
            from pydantic import BaseModel
            if isinstance(obj, BaseModel):
                return obj.model_dump(mode="json")
        except ImportError:
            pass
        # SQLAlchemy ORM Model —— isinstance(DeclarativeBase) 替代 hasattr(__table__)
        try:
            from sqlalchemy.orm import DeclarativeBase
            if isinstance(obj, DeclarativeBase):
                return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
        except ImportError:
            pass
        # 未识别类型：显式 TypeError（json 标准契约，响亮失败而非无限递归 OOM）
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


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


def confirm_or_exit(message: str, *, yes_flag: bool = False) -> None:
    """safe_confirm 命令层封装（ADR-021 第 3 维，#6578）。

    危险操作命令的统一确认入口：
    - ``yes_flag=True``（命令的 ``--force``/``--yes``）：safe_confirm 短路返 True，放行
    - TTY + 用户确认（typer.confirm 返 True）：放行
    - TTY + 用户拒绝（typer.confirm 返 False）：``typer.Exit(0)`` —— 用户主动
      取消，正常退出（对齐 master 原契约 ``if not Confirm.ask(...): return/Exit(0)``）
    - 非 TTY + 无 yes_flag：safe_confirm 抛 ``CliConfirmError`` → stderr + ``typer.Exit(1)``。
      非零退出码让 CI/脚本能检测到"操作被拒绝"，而非静默 no-op 误以为成功。

    ``CliConfirmError`` 按具体类型 catch（不被通用 ``except Exception`` 吞，
    呼应其设计），错误走 stderr 保持 stdout（脚本数据通道）干净。

    .. note::
       ``typer.confirm`` 默认 ``abort=False``，拒绝返 False **不** raise，
       故必须显式检查 ``safe_confirm`` 返回值，不能依赖 typer 自己 Exit
       （#6578 review #1 的 regression：原实现忽略返回值，用户拒绝仍执行
       destructive op，把 master 守卫整个删了）。
    """
    try:
        confirmed = safe_confirm(message, yes_flag=yes_flag)
    except CliConfirmError as e:
        # 错误走 stderr：保持 stdout（脚本数据通道）干净
        Console(stderr=True).print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    if not confirmed:
        # TTY 用户主动拒绝（safe_confirm 走 typer.confirm 返 False）
        raise typer.Exit(0)


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
    """统一 ServiceResult → stdout JSON 输出 + exit code 映射（ADR-021 第 5/6/9 维）。

    三种输出结构：

    - 成功 list（``data`` 是 ``list``）：``{"success": true, "data": [...], "count": N, "metadata": {}}``
    - 成功 get（``data`` 非 list）：``{"success": true, "data": {...}}``
    - 失败：``{"success": false, "error": {"code": <result.code>, "message": <result.error>}, "data": null}``

    list vs get 区分：由 ``result.data`` 类型推断（``isinstance(data, list)`` → list 结构，
    含 ``count``/``metadata``）；其余（dict / 标量 / None）走 get 结构。对应 ADR-021 第 9 维
    「list/get 二分」。

    exit code 映射（ADR-021 第 6 维，失败路径 ``raise typer.Exit(code)``）：

    - 成功 → ``return``（exit 0，不显式 Exit；呼应 ADR「0 = 正常 return，不 Exit」）
    - ``code == "BAD_PARAMS"`` → exit 2（参数错误）
    - ``code == "TIMEOUT"`` → exit 124（超时，GNU timeout 惯例）
    - 其余失败（含 ``code is None``）→ exit 1（业务失败）

    向后兼容：用 ``getattr(result, "code", None)`` 读取 code，无 ``code`` 属性的旧
    ``ServiceResult`` 实例（全仓 436 处）按 ``code=None`` 处理，成功路径不受影响。

    ``format="text"`` 当前复用 JSON 输出（过渡）：rich 人读渲染（红框/table）留给
    E4/E5 接入时连同 ``make_console`` 一起落地；本 helper 保证 text 路径不崩、
    exit code 仍正确分流。

    Args:
        result: ``ServiceResult`` 实例（或 duck-typed 对象，需 ``success``/``error``/``data``）
        format: ``"json"`` 或 ``"text"``（来自 ``--format`` flag）
        command: 调用方命令名（如 ``"list"`` / ``"get"``），当前仅用于诊断/日志
    """
    success = bool(getattr(result, "success", False))
    # getattr 兜底：旧 ServiceResult 实例（无 code 字段）按 None 处理
    code = getattr(result, "code", None)

    if success:
        data = getattr(result, "data", None)
        if isinstance(data, list):
            # list 结构（ADR-021 第 9 维 list 类）：含 count + metadata
            payload = {
                "success": True,
                "data": data,
                "count": len(data),
                "metadata": getattr(result, "metadata", None) or {},
            }
        else:
            # get 结构（ADR-021 第 9 维 get 类）
            payload = {"success": True, "data": data}
        print(json.dumps(payload, cls=GinkgoJSONEncoder))
        # ADR-021 第 6 维：成功 = 正常 return（不显式 Exit），typer 自然 exit 0
        return

    # 失败路径（ADR-021 第 5 维 fail 结构）
    error_message = getattr(result, "error", None) or ""
    payload = {
        "success": False,
        "error": {"code": code, "message": error_message},
        "data": None,
    }
    print(json.dumps(payload, cls=GinkgoJSONEncoder))

    # exit code 映射（ADR-021 第 6 维）
    if code == "BAD_PARAMS":
        exit_code = 2
    elif code == "TIMEOUT":
        exit_code = 124
    else:
        exit_code = 1
    raise typer.Exit(code=exit_code)
