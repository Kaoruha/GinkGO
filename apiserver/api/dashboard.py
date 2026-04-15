"""
仪表盘相关API路由
"""

from fastapi import APIRouter, Request
from core.logging import logger
from models.dashboard import DashboardStats, SystemHealthItem
import sys
from pathlib import Path

# 添加 Ginkgo 源码路径
ginkgo_path = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(ginkgo_path))

router = APIRouter()


def _check_health() -> list[SystemHealthItem]:
    """检查各基础设施的健康状态"""
    health_items = []

    # MySQL 检查
    try:
        from ginkgo.data.containers import container
        ps = container.portfolio_service()
        result = ps.count()
        if result.is_success():
            health_items.append(SystemHealthItem(
                name="MySQL", status="ONLINE",
                detail=f"portfolio count: {result.data.get('count', 0)}"
            ))
        else:
            health_items.append(SystemHealthItem(
                name="MySQL", status="WARNING",
                detail=result.message or "query failed"
            ))
    except Exception as e:
        health_items.append(SystemHealthItem(
            name="MySQL", status="OFFLINE", detail=str(e)
        ))

    # Redis 检查
    try:
        from ginkgo.data.containers import container
        rs = container.redis_service()
        result = rs.count()
        if result.is_success():
            health_items.append(SystemHealthItem(
                name="Redis", status="ONLINE",
                detail=f"keys: {result.data.get('count', 0)}"
            ))
        else:
            health_items.append(SystemHealthItem(
                name="Redis", status="WARNING",
                detail=result.message or "ping failed"
            ))
    except Exception as e:
        health_items.append(SystemHealthItem(
            name="Redis", status="OFFLINE", detail=str(e)
        ))

    return health_items


@router.get("/")
async def get_dashboard_stats(request: Request):
    """获取仪表盘统计数据"""
    try:
        from ginkgo.data.containers import container

        # Portfolio 统计
        portfolio_count = 0
        total_asset = 0.0
        today_pnl = 0.0
        position_count = 0
        running_strategies = 0
        try:
            ps = container.portfolio_service()

            # Portfolio 总数
            count_result = ps.count()
            if count_result.is_success():
                portfolio_count = count_result.data.get("count", 0)

            # Portfolio 详情（用于计算资产等）
            result = ps.get(page=0, page_size=10000)
            if result.is_success() and result.data:
                portfolios = result.data
                total_asset = sum(
                    float(p.initial_capital or 0) for p in portfolios
                )
                for p in portfolios:
                    is_running = getattr(p, 'is_running', None)
                    if is_running == 1:
                        running_strategies += 1
        except Exception as e:
            logger.warning(f"Portfolio stats failed, using defaults: {e}")

        # Backtest 任务统计
        backtest_count = 0
        backtest_running = 0
        try:
            bts = container.backtest_task_service()
            bt_result = bts.list(page=0, page_size=1)
            if bt_result.is_success() and bt_result.data:
                backtest_count = bt_result.data.get("total", 0)
        except Exception as e:
            logger.warning(f"Backtest stats failed, using defaults: {e}")

        # 健康检查
        health_checks = _check_health()

        # 系统状态汇总
        statuses = [h.status for h in health_checks]
        if "OFFLINE" in statuses:
            system_status = "WARNING"
        elif "WARNING" in statuses:
            system_status = "WARNING"
        else:
            system_status = "ONLINE"

        stats = DashboardStats(
            total_asset=round(total_asset, 2),
            today_pnl=round(today_pnl, 2),
            position_count=position_count,
            running_strategies=running_strategies,
            system_status=system_status,
            portfolio_count=portfolio_count,
            backtest_count=backtest_count,
            backtest_running=backtest_running,
            health_checks=health_checks,
        )
        return {
            "success": True,
            "data": stats.model_dump(),
            "error": None,
            "message": "Dashboard stats retrieved successfully",
        }

    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        # 优雅降级：返回空默认值
        stats = DashboardStats(
            total_asset=0.0,
            today_pnl=0.0,
            position_count=0,
            running_strategies=0,
            system_status="WARNING",
            health_checks=[SystemHealthItem(
                name="System", status="WARNING", detail=str(e)
            )],
        )
        return {
            "success": True,
            "data": stats.model_dump(),
            "error": None,
            "message": "Dashboard stats retrieved with degraded data",
        }
