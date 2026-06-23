"""
竞技场相关API路由

fix(#5861): Arena 竞技场功能尚未实现，端点返 501 而非假装成功的空数据，
避免前端/用户误判「竞技场无数据」为「功能可用但空」。
"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/portfolios")
async def get_arena_portfolios():
    """获取竞技场Portfolio列表（尚未实现）"""
    raise HTTPException(status_code=501, detail="Arena 竞技场功能尚未实现")


@router.post("/comparison")
async def get_arena_comparison():
    """获取Portfolio对比数据（尚未实现）"""
    raise HTTPException(status_code=501, detail="Arena 对比功能尚未实现")
