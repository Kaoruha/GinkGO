"""
回测验证 API 路由

提供分段稳定性检验和蒙特卡洛模拟接口
"""

from fastapi import APIRouter, Query
from typing import List, Optional
from pydantic import BaseModel, Field

from core.logging import logger
from core.response import ok, paginated
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


@router.get("/results")
async def list_results(
    portfolio_id: Optional[str] = Query(None, description="按组合筛选"),
    method: Optional[str] = Query(None, description="按验证方法筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取验证结果列表"""
    try:
        import json
        svc = get_validation_service()
        crud = svc._result_crud
        if not crud:
            return paginated(items=[], total=0, page=page, page_size=page_size)

        filters = {}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if method:
            filters["method"] = method

        records = crud.find(filters=filters) if filters else crud.find()
        items = []
        for r in records:
            items.append({
                "uuid": r.uuid,
                "task_id": r.task_id,
                "portfolio_id": r.portfolio_id,
                "method": r.method,
                "config": json.loads(r.config) if r.config else {},
                "result": json.loads(r.result) if r.result else None,
                "score": r.score,
                "status": r.status,
                "create_at": r.create_at.isoformat() if hasattr(r.create_at, 'isoformat') else str(r.create_at),
            })

        total = len(items)
        start = (page - 1) * page_size
        end = start + page_size
        return paginated(items=items[start:end], total=total, page=page, page_size=page_size)
    except Exception as e:
        logger.error(f"验证结果列表异常: {e}")
        raise BusinessError(f"获取验证结果失败: {e}")


@router.get("/results/{result_id}")
async def get_result(result_id: str):
    """获取验证结果详情"""
    try:
        import json
        svc = get_validation_service()
        crud = svc._result_crud
        if not crud:
            raise BusinessError("验证结果存储不可用")

        record = crud.get(result_id)
        if not record:
            raise BusinessError("验证结果不存在")

        return ok(data={
            "uuid": record.uuid,
            "task_id": record.task_id,
            "portfolio_id": record.portfolio_id,
            "method": record.method,
            "config": json.loads(record.config) if record.config else {},
            "result": json.loads(record.result) if record.result else None,
            "score": record.score,
            "status": record.status,
            "create_at": record.create_at.isoformat() if hasattr(record.create_at, 'isoformat') else str(record.create_at),
        })
    except BusinessError:
        raise
    except Exception as e:
        logger.error(f"验证结果详情异常: {e}")
        raise BusinessError(f"获取验证结果失败: {e}")
