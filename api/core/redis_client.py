"""
Redis client utilities for API Server
"""

import json
from typing import Optional, Any
import asyncio
import redis.asyncio as aioredis

from core.logging import logger


# 数据库/Redis 配置从 GCONF 读取（与 get_db_config() 保持一致）
def _get_redis_config():
    from ginkgo.libs import GCONF
    return {"host": GCONF.REDISHOST, "port": GCONF.REDISPORT}


# 全局 Redis 连接池
_redis_pool: Optional[aioredis.ConnectionPool] = None


async def get_redis_pool() -> aioredis.ConnectionPool:
    """获取 Redis 连接池（单例）"""
    global _redis_pool
    if _redis_pool is None:
        # #5447: Redis 配置从 GCONF 读取，与 get_db_config() 模式一致
        redis_cfg = _get_redis_config()
        _redis_pool = aioredis.ConnectionPool(
            host=redis_cfg["host"],
            port=int(redis_cfg["port"]),
            db=0,
            decode_responses=True,
        )
        logger.info(f"Redis pool created: {redis_cfg['host']}:{redis_cfg['port']}")
    return _redis_pool


async def get_redis() -> aioredis.Redis:
    """获取 Redis 客户端"""
    pool = await get_redis_pool()
    return aioredis.Redis(connection_pool=pool)


async def close_redis_pool():
    """关闭 Redis 连接池"""
    global _redis_pool
    if _redis_pool:
        await _redis_pool.aclose()  # type: ignore
        _redis_pool = None
        logger.info("Redis pool closed")


async def set_backtest_progress(task_uuid: str, progress_data: dict, ttl: int = 60):
    """
    设置回测进度到 Redis

    Args:
        task_uuid: 任务 UUID
        progress_data: 进度数据字典
        ttl: 过期时间（秒）
    """
    try:
        redis = await get_redis()
        key = f"backtest:progress:{task_uuid}"
        value = json.dumps(progress_data, ensure_ascii=False)
        await redis.setex(key, ttl, value)
        logger.debug(f"Set progress for {task_uuid[:8]}: {progress_data.get('progress', 0):.1f}%")
    except Exception as e:
        logger.error(f"Failed to set progress in Redis: {e}")


async def get_backtest_progress(task_uuid: str) -> Optional[dict]:
    """
    从 Redis 获取回测进度

    Args:
        task_uuid: 任务 UUID

    Returns:
        进度数据字典，不存在时返回 None
    """
    try:
        redis = await get_redis()
        key = f"backtest:progress:{task_uuid}"
        value = await redis.get(key)
        if value:
            return json.loads(value)
        return None
    except Exception as e:
        logger.error(f"Failed to get progress from Redis: {e}")
        return None


async def delete_backtest_progress(task_uuid: str):
    """
    删除回测进度数据

    Args:
        task_uuid: 任务 UUID
    """
    try:
        redis = await get_redis()
        key = f"backtest:progress:{task_uuid}"
        await redis.delete(key)
    except Exception as e:
        logger.error(f"Failed to delete progress from Redis: {e}")
