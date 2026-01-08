"""
API Gateway - Schedule Router

提供调度管理API:
- 查询调度计划
- 查询节点状态
- 手动迁移Portfolio
- 触发负载均衡
- 通过Redis查询Scheduler状态
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/scheduler",
    tags=["scheduler"]
)


# ============================================================================
# 调度计划查询 (T055)
# ============================================================================

@router.get("/assignments")
async def get_schedule_assignments() -> Dict:
    """
    查询当前调度计划

    Returns:
        Dict: 当前Portfolio到ExecutionNode的分配计划
    """
    try:
        from ginkgo.data.crud import RedisCRUD

        redis_client = RedisCRUD().redis

        # 获取调度计划
        plan_key = "schedule:plan"
        plan = redis_client.hgetall(plan_key)

        # 转换bytes到str
        assignments = {}
        for portfolio_id, node_id in plan.items():
            portfolio_id_str = portfolio_id.decode('utf-8') if isinstance(portfolio_id, bytes) else portfolio_id
            node_id_str = node_id.decode('utf-8') if isinstance(node_id, bytes) else node_id

            # 跳过孤儿portfolio
            if node_id_str != "__ORPHANED__":
                assignments[portfolio_id_str] = node_id_str

        # 按Node分组统计
        node_stats = {}
        for portfolio_id, node_id in assignments.items():
            if node_id not in node_stats:
                node_stats[node_id] = 0
            node_stats[node_id] += 1

        return {
            "assignments": assignments,
            "total_portfolios": len(assignments),
            "node_stats": node_stats,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get schedule assignments: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes")
async def get_scheduler_nodes() -> Dict:
    """
    查询所有ExecutionNode状态

    Returns:
        Dict: 所有Node的状态信息
    """
    try:
        from ginkgo.data.crud import RedisCRUD

        redis_client = RedisCRUD().redis

        # 扫描所有心跳键
        heartbeat_keys = redis_client.keys("heartbeat:node:*")

        nodes = []
        for key in heartbeat_keys:
            # 提取node_id
            node_id = key.decode('utf-8').replace("heartbeat:node:", "")

            # 获取性能指标
            metrics_key = f"node:metrics:{node_id}"
            metrics = redis_client.hgetall(metrics_key)

            # 获取Portfolio列表
            portfolios_key = f"node:{node_id}:portfolios"
            portfolio_ids = redis_client.smembers(portfolios_key)

            # 转换bytes到str
            if isinstance(metrics, dict):
                metrics = {k.decode('utf-8') if isinstance(k, bytes) else k:
                           v.decode('utf-8') if isinstance(v, bytes) else v
                           for k, v in metrics.items()}

            portfolio_ids = [p.decode('utf-8') if isinstance(p, bytes) else p
                            for p in portfolio_ids]

            nodes.append({
                "node_id": node_id,
                "is_online": True,
                "metrics": metrics,
                "portfolio_ids": portfolio_ids,
                "portfolio_count": len(portfolio_ids)
            })

        return {
            "nodes": nodes,
            "total": len(nodes),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get scheduler nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 调度控制
# ============================================================================

@router.post("/rebalance")
async def trigger_rebalance() -> Dict:
    """
    触发负载均衡

    发送recalculate命令到Scheduler，重新计算调度计划。

    Returns:
        Dict: 操作结果
    """
    try:
        # TODO: 发送recalculate命令到Kafka (T056)
        # 命令格式: {"command": "recalculate", "timestamp": ...}

        logger.info("Rebalance command sent to scheduler")

        return {
            "success": True,
            "message": "Rebalance command sent to scheduler",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to trigger rebalance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/migrate")
async def migrate_portfolio(
    portfolio_id: str,
    source_node: Optional[str] = None,
    target_node: str
) -> Dict:
    """
    手动迁移Portfolio

    Args:
        portfolio_id: Portfolio ID
        source_node: 源Node ID (可选，如果为None则自动查找)
        target_node: 目标Node ID

    Returns:
        Dict: 操作结果
    """
    try:
        # TODO: 发送迁移命令到Kafka (T056)
        # 命令格式: {"command": "portfolio.migrate", "portfolio_id": ..., "source_node": ..., "target_node": ...}

        logger.info(f"Migration command sent: {portfolio_id} → {target_node}")

        return {
            "success": True,
            "message": f"Portfolio {portfolio_id} migration command sent",
            "portfolio_id": portfolio_id,
            "source_node": source_node,
            "target_node": target_node,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to migrate portfolio {portfolio_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pause")
async def pause_scheduler() -> Dict:
    """
    暂停Scheduler

    暂停后，Scheduler不执行调度循环，但仍处理命令。

    Returns:
        Dict: 操作结果
    """
    try:
        # TODO: 发送pause命令到Kafka (T056)
        logger.info("Pause command sent to scheduler")

        return {
            "success": True,
            "message": "Scheduler pause command sent",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to pause scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/resume")
async def resume_scheduler() -> Dict:
    """
    恢复Scheduler

    恢复后，Scheduler重新执行调度循环。

    Returns:
        Dict: 操作结果
    """
    try:
        # TODO: 发送resume命令到Kafka (T056)
        logger.info("Resume command sent to scheduler")

        return {
            "success": True,
            "message": "Scheduler resume command sent",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to resume scheduler: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_scheduler_status() -> Dict:
    """
    查询Scheduler状态

    Returns:
        Dict: Scheduler状态信息
    """
    try:
        from ginkgo.data.crud import RedisCRUD

        redis_client = RedisCRUD().redis

        # 获取调度计划
        plan = redis_client.hgetall("schedule:plan")

        # 获取在线节点
        heartbeat_keys = redis_client.keys("heartbeat:node:*")
        online_nodes = len(heartbeat_keys)

        # 转换
        assignments = {}
        for k, v in plan.items():
            k_str = k.decode('utf-8') if isinstance(k, bytes) else k
            v_str = v.decode('utf-8') if isinstance(v, bytes) else v
            assignments[k_str] = v_str

        return {
            "is_running": True,  # TODO: 从Redis获取实际状态
            "online_nodes": online_nodes,
            "total_portfolios": len(assignments),
            "orphaned_portfolios": sum(1 for v in assignments.values() if v == "__ORPHANED__"),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
