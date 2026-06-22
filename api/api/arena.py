"""
竞技场相关API路由
"""

from typing import List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from core.response import ok

router = APIRouter()


class ArenaComparisonRequest(BaseModel):
    """Arena 对比请求体（#5400）

    task_ids 为回测任务ID列表，端点按此读取各任务的 net_value 分析器记录，
    聚合为净值曲线与基础统计。
    """

    task_ids: List[str] = Field(..., min_length=1, description="对比的回测任务ID列表")


def _compute_statistics(net_values: List[dict]) -> dict:
    """从净值序列计算基础统计（#5400）

    Args:
        net_values: [{"date": ..., "value": float}, ...]，按时间升序

    Returns:
        final_value: 末点净值
        total_return: 相对首点的累计回报率（%）
        max_drawdown: 峰值到谷底的最大回撤（%，非负）
    """
    if not net_values:
        return {"final_value": 0, "total_return": 0, "max_drawdown": 0}

    values = [float(nv["value"]) for nv in net_values]
    final_value = values[-1]
    initial = values[0]
    total_return = round((final_value / initial - 1) * 100, 4) if initial else 0

    # 最大回撤：running peak → (peak - v) / peak
    peak = values[0]
    max_dd = 0.0
    for v in values:
        if v > peak:
            peak = v
        if peak > 0:
            dd = (peak - v) / peak * 100
            if dd > max_dd:
                max_dd = dd

    return {
        "final_value": round(final_value, 4),
        "total_return": total_return,
        "max_drawdown": round(max_dd, 4),
    }


def _to_date_str(raw) -> Optional[str]:
    """将时间戳归一为字符串（datetime → isoformat，str 原样，None 透传）"""
    if raw is None:
        return None
    if hasattr(raw, "isoformat"):
        return raw.isoformat()
    return str(raw)


@router.get("/portfolios")
async def get_arena_portfolios():
    """获取竞技场Portfolio列表"""
    # TODO: 实现实际的竞技场数据获取逻辑
    return ok(data={"items": []})


@router.post("/comparison")
async def get_arena_comparison(request: ArenaComparisonRequest):
    """获取Portfolio对比数据（#5400）

    按请求的 task_ids 读取各回测任务的 net_value 分析器记录，
    聚合为净值曲线（按业务时间升序）与基础统计（最终值/总回报率/最大回撤）。
    无数据或查询失败的 task 跳过，不中断整体响应。
    """
    from ginkgo.data.containers import container

    analyzer_service = container.analyzer_service()

    net_values = {}
    statistics = []

    for task_id in request.task_ids:
        result = analyzer_service.get_by_task_id(
            task_id=task_id, analyzer_name="net_value", limit=10000
        )
        if not result.is_success() or not result.data:
            continue

        records = result.data
        curve = sorted(
            [
                {
                    "date": _to_date_str(
                        getattr(r, "business_timestamp", None)
                        or getattr(r, "timestamp", None)
                    ),
                    "value": float(getattr(r, "value", 0)),
                }
                for r in records
            ],
            key=lambda x: x["date"] or "",
        )
        net_values[task_id] = curve
        stats = _compute_statistics(curve)
        stats["task_id"] = task_id
        statistics.append(stats)

    return ok(data={"net_values": net_values, "statistics": statistics})
