"""
回测验证 API 路由

提供分段稳定性检验和蒙特卡洛模拟接口
"""

from fastapi import APIRouter
from typing import List, Optional
from pydantic import BaseModel, Field

from core.logging import logger
from core.response import ok
from core.exceptions import BusinessError


router = APIRouter()


class SegmentStabilityRequest(BaseModel):
    task_id: str = Field(..., description="回测任务 UUID")
    portfolio_id: str = Field(..., description="组合 UUID")
    n_segments: Optional[List[int]] = Field(default=[2, 4, 8], description="分段数列表")


class MonteCarloRequest(BaseModel):
    task_id: str = Field(..., description="回测任务 UUID")
    portfolio_id: str = Field(..., description="组合 UUID")
    n_simulations: int = Field(default=10000, ge=100, le=100000, description="模拟次数")
    confidence: float = Field(default=0.95, ge=0.8, le=0.99, description="置信水平")


def get_validation_service():
    from ginkgo.data.containers import container
    return container.validation_service()


@router.post("/segment-stability")
async def segment_stability(req: SegmentStabilityRequest):
    try:
        svc = get_validation_service()
        result = svc.segment_stability(
            task_id=req.task_id,
            portfolio_id=req.portfolio_id,
            n_segments_list=req.n_segments,
        )
        if not result.is_success():
            raise BusinessError(result.error)
        return ok(data=result.data)
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"分段稳定性接口异常: {e}")
        raise BusinessError(f"分段稳定性计算失败: {e}")


@router.post("/monte-carlo")
async def monte_carlo(req: MonteCarloRequest):
    try:
        svc = get_validation_service()
        result = svc.monte_carlo(
            task_id=req.task_id,
            portfolio_id=req.portfolio_id,
            n_simulations=req.n_simulations,
            confidence=req.confidence,
        )
        if not result.is_success():
            raise BusinessError(result.error)
        return ok(data=result.data)
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"蒙特卡洛接口异常: {e}")
        raise BusinessError(f"蒙特卡洛模拟失败: {e}")
