"""#6640: Portfolio 装配回测引擎所需的必需组件清单（单点维护）。

创建回测预检（backtest_task_service.create）与装配层（component_loader /
engine_assembly_service）共用此清单，替代散落在多处 `# Add ... (required)` 检查。

Upstream: ginkgo.enums (FILE_TYPES)
Downstream: backtest_task_service (创建预检), component_loader (装配检查),
            engine_assembly_service (错误透传)
Role: 必需组件清单 + 缺失检测/格式化辅助（纯逻辑，无 data 层依赖，避免循环 import）
"""
from typing import Dict, Iterable, List, Tuple

from ginkgo.enums import FILE_TYPES

# 必需组件清单：(FILE_TYPES, 可读标签, bind-component 的 --type 值)
# 顺序与装配阶段一致（strategy → selector → sizer），错误信息按此顺序呈现。
# 当前覆盖 component_loader.perform_component_binding 的全部 required 检查点；
# 未来新增必需组件只需在此追加元组（issue #6640「单点维护」目标）。
REQUIRED_PORTFOLIO_COMPONENT_TYPES: Tuple[Tuple[FILE_TYPES, str, str], ...] = (
    (FILE_TYPES.STRATEGY, "Strategy", "strategy"),
    (FILE_TYPES.SELECTOR, "Selector", "selector"),
    (FILE_TYPES.SIZER, "Sizer", "sizer"),
)


def find_missing_required_components(
    bound_component_types: Iterable,
) -> List[Tuple[str, str]]:
    """对比已绑定组件类型与必需清单，返回缺失项。

    Args:
        bound_component_types: 已绑定组件的类型集合（可迭代）。元素可为：
            - FILE_TYPES 枚举成员
            - 成员名字符串（如 "STRATEGY"，PortfolioService.get_components 返回此格式）
            - 成员 value（int）

    Returns:
        缺失的必需组件 [(label, bind_type), ...]，按 REQUIRED_PORTFOLIO_COMPONENT_TYPES 顺序。
        已全部满足时返回空 list。
    """
    bound_normalized = set()
    for t in bound_component_types:
        if isinstance(t, FILE_TYPES):
            bound_normalized.add(t)
        elif isinstance(t, str):
            # 兼容两种字符串形态（与 engine_assembly_service._resolve_component_type 同语义）：
            #   - 数字串（"6"）：生产 get_components 的真实返回格式。mapping.type 经
            #     FILE_TYPES.validate_input 转 int 存储，get_components 用
            #     `mapping.type.name if hasattr(...) else str(mapping.type)`，int 无 .name
            #     → 返回 str(int)，即数字串。#6643 P0：原分支仅 FILE_TYPES[t] 会抛 KeyError
            #     被静默吞，致全部已绑组件归一化为空集、预检误判全缺。
            #   - 成员名（"STRATEGY"）：忽略未知字符串（非必需类型的合法组件可传入）。
            try:
                bound_normalized.add(FILE_TYPES(int(t)) if t.isdigit() else FILE_TYPES[t])
            except (KeyError, ValueError):
                continue
        elif isinstance(t, int):
            try:
                bound_normalized.add(FILE_TYPES(t))
            except ValueError:
                continue

    return [
        (label, bind_type)
        for ftype, label, bind_type in REQUIRED_PORTFOLIO_COMPONENT_TYPES
        if ftype not in bound_normalized
    ]


def format_missing_components_message(
    portfolio_id: str, missing: List[Tuple[str, str]]
) -> str:
    """生成统一的缺失组件错误信息（含绑定命令提示）。

    Args:
        portfolio_id: portfolio UUID
        missing: find_missing_required_components 的返回值

    Returns:
        形如:
            Portfolio <pid> missing required component: Sizer is required.
              Bind via: ginkgo portfolio bind-component <pid> <sizer_file_id> --type sizer

        missing 为空时返回空串（调用方应先判空）。
    """
    if not missing:
        return ""
    labels = " and ".join(label for label, _ in missing)
    hints = "\n".join(
        f"  Bind via: ginkgo portfolio bind-component {portfolio_id} <{bt}_file_id> --type {bt}"
        for _, bt in missing
    )
    return (
        f"Portfolio {portfolio_id} missing required component: "
        f"{labels} is required.\n{hints}"
    )


# 分桶名 → FILE_TYPES 映射（与 component_loader/task_helpers 的分桶一致）
_BUCKET_TO_FILE_TYPE = {
    "strategies": FILE_TYPES.STRATEGY,
    "selectors": FILE_TYPES.SELECTOR,
    "sizers": FILE_TYPES.SIZER,
}


def find_missing_required_from_bucketed(
    components: Dict[str, List],
) -> List[Tuple[str, str]]:
    """从分桶后的 components dict 检查缺失的必需组件（装配层用）。

    Args:
        components: 分桶 dict，键为桶名（"strategies"/"selectors"/"sizers"），
            值为组件列表。空 list / 缺键 均视为该组件未绑定。

    Returns:
        缺失的必需组件 [(label, bind_type), ...]，按 REQUIRED_PORTFOLIO_COMPONENT_TYPES 顺序。
    """
    if not components:
        bound_types: set = set()
    else:
        bound_types = {
            ftype
            for bucket, ftype in _BUCKET_TO_FILE_TYPE.items()
            if components.get(bucket)  # 非空 list 才算已绑定
        }
    return find_missing_required_components(bound_types)
