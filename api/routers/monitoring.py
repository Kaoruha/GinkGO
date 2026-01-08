# Upstream: Redis (ExecutionNode和Portfolio状态缓存)
# Downstream: 前端监控面板, 运维人员 (API调用)
# Role: 监控查询API路由，提供ExecutionNode和Portfolio的实时状态查询接口

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/metrics",
    tags=["monitoring"]
)


# ============================================================================
# 监控指标查询 (T070)
# ============================================================================

@router.get("/nodes")
async def get_all_nodes_metrics() -> Dict:
    """
    查询所有ExecutionNode的监控指标

    Returns:
        Dict: 所有Node的监控指标
    """
    try:
        from ginkgo.data.crud import RedisCRUD

        redis_client = RedisCRUD().redis

        # 扫描所有execution_node:*:info键
        node_keys = redis_client.keys("execution_node:*:info")

        nodes = []
        for key in node_keys:
            # 提取node_id
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            node_id = key_str.replace("execution_node:", "").replace(":info", "")

            # 读取节点状态
            info = redis_client.hgetall(key)

            # 转换bytes到str
            if isinstance(info, dict):
                info = {
                    k.decode('utf-8') if isinstance(k, bytes) else k:
                    v.decode('utf-8') if isinstance(v, bytes) else v
                    for k, v in info.items()
                }

            # 获取心跳状态
            heartbeat_key = f"heartbeat:node:{node_id}"
            is_online = redis_client.exists(heartbeat_key) > 0
            heartbeat_ttl = redis_client.ttl(heartbeat_key) if is_online else -1

            nodes.append({
                "node_id": node_id,
                "is_online": is_online,
                "heartbeat_ttl": heartbeat_ttl,
                "info": info
            })

        return {
            "nodes": nodes,
            "total": len(nodes),
            "online_count": sum(1 for n in nodes if n["is_online"]),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get nodes metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolios")
async def get_all_portfolios_metrics() -> Dict:
    """
    查询所有Portfolio的监控指标

    Returns:
        Dict: 所有Portfolio的监控指标
    """
    try:
        from ginkgo.data.crud import RedisCRUD

        redis_client = RedisCRUD().redis

        # 扫描所有portfolio:*:state键
        portfolio_keys = redis_client.keys("portfolio:*:state")

        portfolios = []
        for key in portfolio_keys:
            # 提取portfolio_id
            key_str = key.decode('utf-8') if isinstance(key, bytes) else key
            portfolio_id = key_str.replace("portfolio:", "").replace(":state", "")

            # 读取Portfolio状态
            state = redis_client.hgetall(key)

            # 转换bytes到str
            if isinstance(state, dict):
                state = {
                    k.decode('utf-8') if isinstance(k, bytes) else k:
                    v.decode('utf-8') if isinstance(v, bytes) else v
                    for k, v in state.items()
                }

            # 获取分配的Node
            assignment_key = "schedule:plan"
            assigned_node = redis_client.hget(assignment_key, portfolio_id)
            if assigned_node:
                assigned_node = assigned_node.decode('utf-8') if isinstance(assigned_node, bytes) else assigned_node

            portfolios.append({
                "portfolio_id": portfolio_id,
                "state": state,
                "assigned_node": assigned_node
            })

        # 按状态分组统计
        status_stats = {}
        for p in portfolios:
            status = p["state"].get("status", "UNKNOWN")
            status_stats[status] = status_stats.get(status, 0) + 1

        return {
            "portfolios": portfolios,
            "total": len(portfolios),
            "status_stats": status_stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get portfolios metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio/{portfolio_id}")
async def get_portfolio_metrics(portfolio_id: str) -> Dict:
    """
    查询单个Portfolio的详细监控指标

    Args:
        portfolio_id: Portfolio ID

    Returns:
        Dict: Portfolio详细指标
    """
    try:
        from ginkgo.data.crud import RedisCRUD

        redis_client = RedisCRUD().redis

        # 读取Portfolio状态
        state_key = f"portfolio:{portfolio_id}:state"
        state = redis_client.hgetall(state_key)

        if not state:
            raise HTTPException(
                status_code=404,
                detail=f"Portfolio {portfolio_id} not found or not running"
            )

        # 转换bytes到str
        if isinstance(state, dict):
            state = {
                k.decode('utf-8') if isinstance(k, bytes) else k:
                v.decode('utf-8') if isinstance(v, bytes) else v
                for k, v in state.items()
            }

        # 获取分配的Node
        assignment_key = "schedule:plan"
        assigned_node = redis_client.hget(assignment_key, portfolio_id)
        if assigned_node:
            assigned_node = assigned_node.decode('utf-8') if isinstance(assigned_node, bytes) else assigned_node

        # 获取Node心跳状态
        node_online = False
        if assigned_node and assigned_node != "__ORPHANED__":
            heartbeat_key = f"heartbeat:node:{assigned_node}"
            node_online = redis_client.exists(heartbeat_key) > 0

        return {
            "portfolio_id": portfolio_id,
            "state": state,
            "assigned_node": assigned_node,
            "node_online": node_online,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get portfolio metrics {portfolio_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def get_system_health() -> Dict:
    """
    查询系统整体健康状态

    Returns:
        Dict: 系统健康状态摘要
    """
    try:
        from ginkgo.data.crud import RedisCRUD

        redis_client = RedisCRUD().redis

        # 统计在线节点
        heartbeat_keys = redis_client.keys("heartbeat:node:*")
        online_nodes = len(heartbeat_keys)

        # 统计Portfolio状态
        portfolio_keys = redis_client.keys("portfolio:*:state")
        total_portfolios = len(portfolio_keys)

        # 统计各状态Portfolio数量
        status_stats = {}
        alerts = []

        for key in portfolio_keys:
            state = redis_client.hgetall(key)
            if state:
                status = state.get(b"status", b"UNKNOWN").decode('utf-8')
                status_stats[status] = status_stats.get(status, 0) + 1

                # 检查告警条件
                queue_size = int(state.get(b"queue_size", 0))
                buffer_size = int(state.get(b"buffer_size", 0))

                # Queue满告警
                if queue_size > 950:  # 接近1000上限
                    portfolio_id = key.decode('utf-8').replace("portfolio:", "").replace(":state", "")
                    alerts.append({
                        "type": "queue_full",
                        "severity": "critical",
                        "portfolio_id": portfolio_id,
                        "message": f"Portfolio {portfolio_id} queue nearly full: {queue_size}"
                    })

                # Buffer积压告警
                if buffer_size > 500:
                    portfolio_id = key.decode('utf-8').replace("portfolio:", "").replace(":state", "")
                    alerts.append({
                        "type": "buffer_accumulation",
                        "severity": "warning",
                        "portfolio_id": portfolio_id,
                        "message": f"Portfolio {portfolio_id} buffer accumulation: {buffer_size}"
                    })

        # 获取调度计划
        schedule_plan = redis_client.hgetall("schedule:plan")
        orphaned_count = sum(
            1 for v in schedule_plan.values()
            if v == b"__ORPHANED__" or v == "__ORPHANED__"
        )

        # 系统健康状态评估
        is_healthy = (
            online_nodes > 0 and
            orphaned_count == 0 and
            len([a for a in alerts if a["severity"] == "critical"]) == 0
        )

        return {
            "is_healthy": is_healthy,
            "summary": {
                "online_nodes": online_nodes,
                "total_portfolios": total_portfolios,
                "portfolio_status": status_stats,
                "orphaned_portfolios": orphaned_count,
                "active_alerts": len(alerts)
            },
            "alerts": alerts,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get system health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def get_metrics_overview() -> Dict:
    """
    获取监控指标概览

    Returns:
        Dict: 监控系统概览信息
    """
    return {
        "description": "Ginkgo Live Trading Monitoring API",
        "version": "1.0.0",
        "endpoints": {
            "nodes": "/api/metrics/nodes",
            "portfolios": "/api/metrics/portfolios",
            "portfolio_detail": "/api/metrics/portfolio/{portfolio_id}",
            "health": "/api/metrics/health"
        },
        "timestamp": datetime.now().isoformat()
    }
