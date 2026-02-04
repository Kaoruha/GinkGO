"""
Dashboard相关数据模型
"""

from pydantic import BaseModel
from typing import Literal


class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    total_asset: float
    today_pnl: float
    position_count: int
    running_strategies: int
    system_status: Literal["ONLINE", "OFFLINE", "WARNING"]
