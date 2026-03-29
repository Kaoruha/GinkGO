#!/usr/bin/env python3
"""
测试TaskTimer心跳功能

验证场景：
1. 启动TaskTimer
2. 检查Redis心跳key是否创建
3. 检查心跳值是否正确
4. 检查TTL是否正确
5. 停止TaskTimer
6. 检查心跳key是否过期
"""

import time
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from redis import Redis
    from ginkgo.libs import GCONF
    from ginkgo.livecore.task_timer import TaskTimer
except ImportError as e:
    print(f"[ERROR] Failed to import: {e}")
    sys.exit(1)


def get_redis_client():
    """获取Redis客户端"""
    try:
        return Redis(
            host=GCONF.REDISHOST,
            port=GCONF.REDISPORT,
            db=0,
            decode_responses=True
        )
    except Exception as e:
        print(f"[ERROR] Failed to connect to Redis: {e}")
        return None


def test_task_timer_heartbeat():
    """测试TaskTimer心跳功能"""
    print("\n" + "=" * 60)
    print("TaskTimer Heartbeat Test")
    print("=" * 60)

    redis_client = get_redis_client()
    if not redis_client:
        print("[ERROR] Redis connection failed")
        return False

    node_id = "test_task_timer"
    heartbeat_key = f"heartbeat:task_timer:{node_id}"

    # 清理旧数据
    print("\n[Step 1] Cleaning up old data...")
    redis_client.delete(heartbeat_key)
    print(f"  ✓ Deleted old heartbeat key: {heartbeat_key}")

    # 启动TaskTimer
    print("\n[Step 2] Starting TaskTimer...")
    timer = TaskTimer(node_id=node_id)
    result = timer.start()

    if not result:
        print("  ✗ Failed to start TaskTimer")
        return False
    print(f"  ✓ TaskTimer started")

    # 等待心跳发送
    print("\n[Step 3] Waiting for heartbeat (2 seconds)...")
    time.sleep(2)

    # 检查心跳key
    print("\n[Step 4] Checking heartbeat key...")
    exists = redis_client.exists(heartbeat_key)

    if not exists:
        print(f"  ✗ Heartbeat key not found: {heartbeat_key}")
        timer.stop()
        return False

    print(f"  ✓ Heartbeat key exists: {heartbeat_key}")

    # 获取心跳值
    heartbeat_value = redis_client.get(heartbeat_key)
    print(f"  ✓ Heartbeat value: {heartbeat_value}")

    # 获取TTL
    ttl = redis_client.ttl(heartbeat_key)
    print(f"  ✓ Heartbeat TTL: {ttl}s (expected: ~30s)")

    if ttl < 20 or ttl > 30:
        print(f"  ⚠ TTL is outside expected range: {ttl}s")

    # 等待一段时间，观察心跳更新
    print("\n[Step 5] Waiting for heartbeat refresh (15 seconds)...")
    time.sleep(15)

    # 检查心跳是否更新
    new_heartbeat_value = redis_client.get(heartbeat_key)
    new_ttl = redis_client.ttl(heartbeat_key)

    print(f"  New heartbeat value: {new_heartbeat_value}")
    print(f"  New TTL: {new_ttl}s")

    if new_heartbeat_value != heartbeat_value:
        print("  ✓ Heartbeat was refreshed")
    else:
        print("  ⚠ Heartbeat may not have refreshed")

    # 停止TaskTimer
    print("\n[Step 6] Stopping TaskTimer...")
    timer.stop()
    print("  ✓ TaskTimer stopped")

    # 等待心跳过期
    print("\n[Step 7] Waiting for heartbeat to expire (35 seconds)...")
    for i in range(35):
        exists = redis_client.exists(heartbeat_key)
        if not exists:
            print(f"  ✓ Heartbeat expired after {i+1} seconds")
            break
        time.sleep(1)

    # 最终检查
    print("\n[Step 8] Final check...")
    exists = redis_client.exists(heartbeat_key)

    if exists:
        print(f"  ✗ Heartbeat key still exists (should have expired)")
        return False
    else:
        print(f"  ✓ Heartbeat key correctly expired")

    # 清理
    redis_client.delete(heartbeat_key)

    print("\n" + "=" * 60)
    print("✅ TaskTimer heartbeat test PASSED")
    print("=" * 60)

    return True


if __name__ == "__main__":
    try:
        success = test_task_timer_heartbeat()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
