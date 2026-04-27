"""部署 API 路由"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel, Field
from core.response import ok
from core.exceptions import BusinessError
from core.logging import logger

router = APIRouter()


class DeployRequest(BaseModel):
    portfolio_id: str = Field(..., description="源组合 UUID")
    mode: str = Field(..., description="部署模式: paper / live")
    account_id: Optional[str] = Field(None, description="实盘账号 ID（live 模式必填）")
    name: Optional[str] = Field(None, description="新组合名称")


def _get_deployment_service():
    from ginkgo.data.containers import container
    return container.deployment_service()


@router.post("/")
async def deploy(req: DeployRequest):
    """一键部署（走 Saga 事务）"""
    from ginkgo.enums import PORTFOLIO_MODE_TYPES
    from services.saga_transaction import PortfolioSagaFactory

    mode_map = {
        "paper": PORTFOLIO_MODE_TYPES.PAPER.value,
        "live": PORTFOLIO_MODE_TYPES.LIVE.value,
    }
    mode = mode_map.get(req.mode.lower())
    if mode is None:
        raise BusinessError(f"无效部署模式: {req.mode}，支持: paper / live")

    if mode == PORTFOLIO_MODE_TYPES.LIVE.value and not req.account_id:
        raise BusinessError("实盘部署需要提供 account_id")

    saga = PortfolioSagaFactory.deploy_saga(
        portfolio_id=req.portfolio_id,
        mode=mode,
        account_id=req.account_id,
        name=req.name,
    )

    success = await saga.execute()
    if not success:
        raise BusinessError(f"部署失败: {saga.error}. 事务已回滚。")

    return ok(data=saga.steps[0].result, message="部署成功")


@router.get("/{portfolio_id}")
async def get_deployment_info(portfolio_id: str):
    """查询指定 Portfolio 的部署信息"""
    service = _get_deployment_service()
    result = service.get_deployment_info(portfolio_id)

    if not result.success:
        raise HTTPException(status_code=404, detail=result.error)

    return ok(data=result.data, message="查询成功")


@router.get("/")
async def list_deployments(portfolio_id: Optional[str] = Query(None, description="按源组合 ID 筛选")):
    """列出部署记录"""
    service = _get_deployment_service()
    result = service.list_deployments(portfolio_id=portfolio_id)

    if not result.success:
        raise BusinessError(result.error)

    return ok(data=result.data or [], message="查询成功")
