#!/usr/bin/env python3
"""
测试 SSE 回测进度推送功能
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.redis_client import set_backtest_progress, get_backtest_progress


async def test_redis_progress():
    """测试 Redis 进度存储和读取"""
    task_uuid = "test-task-123"

    # 模拟进度更新
    print("测试 Redis 进度存储和读取...")

    for i in range(0, 101, 20):
        progress_data = {
            "progress": float(i),
            "state": "RUNNING" if i < 100 else "COMPLETED",
            "current_date": "2024-01-01",
            "updated_at": datetime.utcnow().isoformat()
        }

        # 写入 Redis
        await set_backtest_progress(task_uuid, progress_data, ttl=60)
        print(f"写入进度: {i}%")

        # 从 Redis 读取
        retrieved = await get_backtest_progress(task_uuid)
        if retrieved:
            print(f"读取进度: {retrieved['progress']}%, 状态: {retrieved['state']}")

        await asyncio.sleep(0.5)

    print("\n测试完成！")


if __name__ == "__main__":
    asyncio.run(test_redis_progress())
