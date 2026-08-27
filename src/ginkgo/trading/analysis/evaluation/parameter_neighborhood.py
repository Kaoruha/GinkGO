# Upstream: optimize 模块 (四优化器, 接线后供邻域回测数据)
# Downstream: FunnelEvaluator (g1_param_neighborhood gate)
# Role: G1 参数邻域衰减 — 纯计算无 DB 依赖; optimize 未接线时上游无法供数, gate 如实 BLOCKED


"""
ParameterNeighborhood — 参数邻域衰减计算器 (G1)

过拟合策略的特征之一: 参数尖峰 — 中心参数绩效很好, 邻域 (±扰动) 绩效暴跌。
本模块衡量邻域衰减: (center - worst) / center, 衰减越小策略对参数越不敏感。

数据来源 (外部依赖): optimize 接线后, 调用方用优化器跑邻域网格回测,
把中心点与各邻域点的绩效指标 (Sharpe 为主) 传入本计算器。
未接线前 funnel 侧 gate 返回 BLOCKED(依赖未就绪), 不假装通过 — 见 ADR §5。
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class NeighborhoodResult:
    """邻域衰减求值结果"""

    center: float
    neighbors: List[float] = field(default_factory=list)
    worst: Optional[float] = None
    median: Optional[float] = None
    # (center - worst) / center; center <= 0 时衰减无意义, 置 None (上游报样本不足)
    decay: Optional[float] = None

    @property
    def computable(self) -> bool:
        return self.decay is not None


def evaluate_neighborhood(center: float, neighbors: List[float]) -> NeighborhoodResult:
    """求邻域衰减

    Args:
        center: 中心参数点的绩效指标 (如 Sharpe)
        neighbors: 各邻域点的同口径指标

    Returns:
        NeighborhoodResult; decay 为 None 表示不可算 (邻域空/含 NaN/center<=0)
    """
    result = NeighborhoodResult(center=center, neighbors=list(neighbors))

    valid = [float(n) for n in neighbors if n is not None and not math.isnan(float(n))]
    if not valid:
        return result

    result.worst = min(valid)
    sorted_vals = sorted(valid)
    n = len(sorted_vals)
    result.median = (
        sorted_vals[n // 2]
        if n % 2 == 1
        else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
    )

    if center is None or math.isnan(float(center)) or center <= 0:
        # 中心绩效非正: 衰减分母无意义 (策略本身已在 G1 其他 gate 被拦)
        return result

    result.decay = (center - result.worst) / center
    return result


def gate_status(
    result: NeighborhoodResult, threshold: float
) -> tuple:
    """按 gate 语义求值

    Returns:
        (status, value, detail): status ∈ PASS / FAIL / INSUFFICIENT_DATA
        BLOCKED (依赖未就绪) 由上游 funnel 判定 — 本函数只管数据到手后的求值
    """
    if not result.computable:
        return (
            "INSUFFICIENT_DATA",
            None,
            f"邻域不可算: center={result.center}, 邻域点 {len(result.neighbors)} 个",
        )
    passed = result.decay <= threshold
    detail = (
        f"center={result.center:.3f}, worst={result.worst:.3f}, "
        f"median={result.median:.3f}, 邻域 {len(result.neighbors)} 点"
    )
    return ("PASS" if passed else "FAIL", result.decay, detail)
