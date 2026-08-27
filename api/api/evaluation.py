# Upstream: 前端评估工作台 (EvaluationWorkbench), CLI (ginkgo eval)
# Downstream: EvaluationService (trading/services), gate_definitions (单一事实源)
# Role: 评估工作台 API — gate 清单/漏斗/一致性/数据预检四端点, 实时计算不落库

"""
评估 API 路由

完全基于服务层 (trading_container.evaluation_service)，不直接访问 CRUD。
报告实时计算 (零新建表、零落库，设计文档 §2.5)。
"""

from fastapi import APIRouter, Query
from typing import Optional

from core.response import ok
from core.exceptions import NotFoundError, ValidationError
from core.logging import logger

router = APIRouter()


def _get_evaluation_service():
    """获取 EvaluationService 实例 (trading_container 懒装配)"""
    from ginkgo.trading.containers import trading_container

    return trading_container.evaluation_service()


@router.get("/gates")
async def list_gate_definitions():
    """四级 gate 定义清单 (前端渲染阈值线/徽章用; 与求值同源)"""
    service = _get_evaluation_service()
    result = service.get_gate_definitions()
    if not result.success:
        raise NotFoundError("GateDefinitions", "all")
    return ok(data=result.data)


@router.get("/funnel")
async def get_funnel_report(
    portfolio_id: str = Query(..., description="Portfolio ID"),
    task_id: Optional[str] = Query(None, description="回测 task ID (缺省取最近完成)"),
    candidate_task_id: Optional[str] = Query(None, description="对比序列 ID (模拟盘)"),
    stability_window: int = Query(252, ge=20, le=756, description="滚动平稳度窗口"),
):
    """四级漏斗报告: G0 回测可信 → G1 回测有效 → G2 模拟一致 → G3 实盘就绪"""
    service = _get_evaluation_service()
    result = service.get_funnel_report(
        portfolio_id=portfolio_id,
        task_id=task_id,
        candidate_task_id=candidate_task_id,
        stability_window=stability_window,
    )
    if not result.success:
        raise NotFoundError("FunnelReport", portfolio_id)
    return ok(data=result.data)


@router.get("/parity")
async def get_parity_report(
    portfolio_id: str = Query(..., description="Portfolio ID"),
    baseline_task_id: str = Query(..., description="回测 task ID (基准)"),
    candidate_task_id: str = Query(..., description="模拟盘/对比 task ID"),
):
    """回测 vs 模拟盘同窗一致性 5 项指标 (G2)"""
    if baseline_task_id == candidate_task_id:
        raise ValidationError("基准与对比序列相同，无一致性意义", field="candidate_task_id")
    service = _get_evaluation_service()
    result = service.get_parity_report(
        portfolio_id=portfolio_id,
        baseline_task_id=baseline_task_id,
        candidate_task_id=candidate_task_id,
    )
    if not result.success:
        raise NotFoundError("ParityReport", f"{baseline_task_id}:{candidate_task_id}")
    return ok(data=result.data)


@router.post("/preflight")
async def run_preflight(
    portfolio_id: str = Query(..., description="Portfolio ID"),
    start: str = Query(..., description="窗口开始 YYYY-MM-DD"),
    end: str = Query(..., description="窗口结束 YYYY-MM-DD"),
    min_bars: int = Query(10, ge=1, le=10000, description="覆盖充足阈值"),
):
    """数据质量预检 (G0 质量项: 缺口/对齐/复权一致)"""
    if start > end:
        raise ValidationError("start 不得晚于 end", field="start")
    service = _get_evaluation_service()
    result = service.run_preflight(portfolio_id=portfolio_id, start=start, end=end, min_bars=min_bars)
    if not result.success:
        logger.warning(f"preflight failed: {result.error}")
        raise NotFoundError("PreflightReport", portfolio_id)
    # ok=False (存在 blocker) 是业务结论不是请求失败，仍 200 返回报告
    return ok(data=result.data)
