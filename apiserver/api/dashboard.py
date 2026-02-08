"""
仪表盘相关API路由
"""

from fastapi import APIRouter, Request

from models.dashboard import DashboardStats

router = APIRouter()


@router.get("/", response_model=DashboardStats)
async def get_dashboard_stats(request: Request):
    """获取仪表盘统计数据"""
    # TODO: 从Ginkgo核心服务获取实际统计数据
    # 暂时返回模拟数据
    return DashboardStats(
        total_asset=128500.00,
        today_pnl=1250.00,
        position_count=8,
        running_strategies=5,
        system_status="ONLINE"
    )
