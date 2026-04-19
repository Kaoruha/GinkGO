"""
Dashboard相关数据模型
"""

from pydantic import BaseModel
from typing import Literal, Optional


class SystemHealthItem(BaseModel):
    """系统健康检查项"""
    name: str
    status: Literal["ONLINE", "OFFLINE", "WARNING"]
    detail: Optional[str] = None


class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    total_asset: float
    today_pnl: float
    position_count: int
    running_strategies: int
    system_status: Literal["ONLINE", "OFFLINE", "WARNING"]
    portfolio_count: int = 0
    backtest_count: int = 0
    backtest_running: int = 0
    health_checks: list[SystemHealthItem] = []
