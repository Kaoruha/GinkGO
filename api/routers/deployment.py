from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Dict
from pydantic import BaseModel

router = APIRouter(
    prefix="/api/v1/deploy",
    tags=["deploy"]
)


class DeployRequest(BaseModel):
    backtest_task_id: str
    mode: str  # "paper" or "live"
    account_id: Optional[str] = None
    name: Optional[str] = None


@router.post("")
async def deploy(request: DeployRequest) -> Dict:
    """一键部署：回测结果 → 纸上交易/实盘"""
    try:
        from ginkgo.data.containers import container
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        mode_map = {
            "paper": PORTFOLIO_MODE_TYPES.PAPER,
            "live": PORTFOLIO_MODE_TYPES.LIVE,
        }
        if request.mode not in mode_map:
            raise HTTPException(status_code=400, detail=f"无效的部署模式: {request.mode}")

        svc = container.deployment_service()
        result = svc.deploy(
            backtest_task_id=request.backtest_task_id,
            mode=mode_map[request.mode],
            account_id=request.account_id,
            name=request.name,
        )

        if result.success:
            return {"code": 0, "message": "部署成功", "data": result.data}
        else:
            raise HTTPException(status_code=400, detail=result.error)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{portfolio_id}")
async def get_deployment_info(portfolio_id: str) -> Dict:
    """获取部署详情"""
    try:
        from ginkgo.data.containers import container

        svc = container.deployment_service()
        result = svc.get_deployment_info(portfolio_id)

        if result.success:
            return {"code": 0, "message": "success", "data": result.data}
        else:
            raise HTTPException(status_code=404, detail=result.error)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
async def list_deployments(
    task_id: Optional[str] = Query(None, alias="task_id")
) -> Dict:
    """列出部署记录"""
    try:
        from ginkgo.data.containers import container

        svc = container.deployment_service()
        result = svc.list_deployments(source_task_id=task_id)

        return {"code": 0, "message": "success", "data": result.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
