"""
竞技场相关API路由
"""

from fastapi import APIRouter

from core.response import ok

router = APIRouter()


@router.get("/portfolios")
async def get_arena_portfolios():
    """获取竞技场Portfolio列表"""
    # TODO: 实现实际的竞技场数据获取逻辑
    return ok(data={"items": []})


@router.post("/comparison")
async def get_arena_comparison():
    """获取Portfolio对比数据"""
    # TODO: 实现实际的对比数据获取逻辑
    return ok(data={"net_values": {}, "statistics": []})
