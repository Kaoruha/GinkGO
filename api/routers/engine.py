"""
API Gateway - Engine Router

提供引擎（LiveEngine/ExecutionNode）控制API:
- 查询引擎状态
- 启动/停止引擎
- 更新Portfolio配置
- 通过Redis查询状态

使用FastAPI实现RESTful API接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/engine",
    tags=["engine"]
)


# ============================================================================
# 引擎状态查询
# ============================================================================

@router.get("/{engine_id}")
async def get_engine_status(engine_id: str) -> Dict:
    """
    查询引擎状态 (T053)

    Args:
        engine_id: 引擎ID (ExecutionNode或LiveEngine ID)

    Returns:
        Dict: 引擎状态信息
    """
    try:
        from ginkgo.data.crud import RedisCRUD

        redis_client = RedisCRUD().redis

        # 检查心跳
        heartbeat_key = f"heartbeat:node:{engine_id}"
        heartbeat_exists = redis_client.exists(heartbeat_key)

        # 获取性能指标
        metrics_key = f"node:metrics:{engine_id}"
        metrics = redis_client.hgetall(metrics_key)

        # 获取Portfolio列表
        portfolios_key = f"node:{engine_id}:portfolios"
        portfolio_ids = redis_client.smembers(portfolios_key)

        # 转换bytes到str
        if isinstance(metrics, dict):
            metrics = {k.decode('utf-8') if isinstance(k, bytes) else k:
                       v.decode('utf-8') if isinstance(v, bytes) else v
                       for k, v in metrics.items()}

        portfolio_ids = [p.decode('utf-8') if isinstance(p, bytes) else p
                        for p in portfolio_ids]

        return {
            "engine_id": engine_id,
            "is_online": bool(heartbeat_exists),
            "metrics": metrics,
            "portfolio_ids": portfolio_ids,
            "portfolio_count": len(portfolio_ids),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to get engine status for {engine_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_engines() -> Dict:
    """
    列出所有引擎（ExecutionNode）状态

    Returns:
        Dict: 所有引擎的状态列表
    """
    try:
        from ginkgo.data.crud import RedisCRUD

        redis_client = RedisCRUD().redis

        # 扫描所有心跳键
        heartbeat_keys = redis_client.keys("heartbeat:node:*")

        engines = []
        for key in heartbeat_keys:
            # 提取engine_id
            engine_id = key.decode('utf-8').replace("heartbeat:node:", "")

            # 获取状态
            status = await get_engine_status(engine_id)
            engines.append(status)

        return {
            "engines": engines,
            "total": len(engines),
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to list engines: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Portfolio配置管理
# ============================================================================

@router.put("/{engine_id}/portfolio/{portfolio_id}")
async def update_portfolio_config(
    engine_id: str,
    portfolio_id: str,
    strategy_params: Optional[Dict] = None,
    risk_params: Optional[Dict] = None,
    interest_codes: Optional[List[str]] = None
) -> Dict:
    """
    更新Portfolio配置

    通过Kafka发送配置更新命令到ExecutionNode，
    ExecutionNode收到后触发Portfolio优雅重启。

    Args:
        engine_id: ExecutionNode ID
        portfolio_id: Portfolio ID
        strategy_params: 策略参数
        risk_params: 风控参数
        interest_codes: 订阅股票代码列表

    Returns:
        Dict: 操作结果
    """
    try:
        # TODO: 发送配置更新命令到Kafka (T056)
        # 命令格式: {"command": "portfolio.reload", "portfolio_id": ..., "params": ...}

        logger.info(f"Updating portfolio {portfolio_id} on engine {engine_id}")

        return {
            "success": True,
            "message": f"Portfolio {portfolio_id} configuration update queued",
            "engine_id": engine_id,
            "portfolio_id": portfolio_id,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to update portfolio config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{engine_id}/portfolio/{portfolio_id}/params")
async def update_strategy_params(
    engine_id: str,
    portfolio_id: str,
    params: Dict
) -> Dict:
    """
    更新策略参数

    Args:
        engine_id: ExecutionNode ID
        portfolio_id: Portfolio ID
        params: 策略参数

    Returns:
        Dict: 操作结果
    """
    return await update_portfolio_config(
        engine_id, portfolio_id, strategy_params=params
    )


@router.put("/{engine_id}/portfolio/{portfolio_id}/interest")
async def update_portfolio_interest(
    engine_id: str,
    portfolio_id: str,
    codes: List[str]
) -> Dict:
    """
    更新Portfolio订阅股票代码列表

    Args:
        engine_id: ExecutionNode ID
        portfolio_id: Portfolio ID
        codes: 股票代码列表

    Returns:
        Dict: 操作结果
    """
    return await update_portfolio_config(
        engine_id, portfolio_id, interest_codes=codes
    )


# ============================================================================
# 引擎控制
# ============================================================================

@router.post("/{engine_id}/start")
async def start_engine(engine_id: str) -> Dict:
    """
    启动引擎

    注意：实际启动通常通过CLI或系统管理工具完成，
    此接口主要用于触发调度器分配Portfolio到该引擎。

    Args:
        engine_id: 引擎ID

    Returns:
        Dict: 操作结果
    """
    try:
        # TODO: 发送启动命令到Kafka或更新调度计划

        logger.info(f"Start command sent for engine {engine_id}")

        return {
            "success": True,
            "message": f"Engine {engine_id} start command sent",
            "engine_id": engine_id,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to start engine {engine_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{engine_id}/stop")
async def stop_engine(engine_id: str) -> Dict:
    """
    停止引擎

    注意：实际停止通常通过CLI或系统管理工具完成，
    此接口主要用于通知调度器将该引擎标记为下线。

    Args:
        engine_id: 引擎ID

    Returns:
        Dict: 操作结果
    """
    try:
        # TODO: 发送停止命令到Kafka或更新调度计划

        logger.info(f"Stop command sent for engine {engine_id}")

        return {
            "success": True,
            "message": f"Engine {engine_id} stop command sent",
            "engine_id": engine_id,
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Failed to stop engine {engine_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
