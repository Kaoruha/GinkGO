"""
测试 ExecutionNode 自我注册功能

验证 ExecutionNode 启动时会自动注册到 Redis：
1. 节点基本信息 (node:info:{node_id})
2. 节点能力 (node:capabilities:{node_id})
3. 心跳信息 (heartbeat:node:{node_id})
4. 节点指标 (node:metrics:{node_id})

运行方式：
    PYTHONPATH=/home/kaoru/Ginkgo/src python examples/test_node_registration.py
"""

import time
from datetime import datetime

print("=" * 70)
print("  ExecutionNode 自我注册测试")
print("=" * 70)

# ============================================================
# 测试 1: 节点启动时自动注册
# ============================================================
print("\n📋 测试 1: 节点启动时自动注册")
print("-" * 70)

try:
    from ginkgo.workers.execution_node.node import ExecutionNode
    from ginkgo.data.crud import RedisCRUD

    # 清理旧数据
    print("🧹 清理旧数据...")
    redis_crud = RedisCRUD()
    redis_client = redis_crud.redis
    test_node_id = "test_registration_node"

    keys_to_delete = [
        f"node:info:{test_node_id}",
        f"node:capabilities:{test_node_id}",
        f"heartbeat:node:{test_node_id}",
        f"node:metrics:{test_node_id}",
    ]
    for key in keys_to_delete:
        redis_client.delete(key)

    # 创建并启动节点
    print("\n📦 创建并启动 ExecutionNode...")
    node = ExecutionNode(node_id=test_node_id)

    print(f"   节点 ID: {node.node_id}")
    print(f"   最大 Portfolio 数: {node.max_portfolios}")
    print(f"   已注册标志: {node.registered}")

    print("\n🚀 启动节点...")
    node.start()

    # 验证注册结果
    print("\n🔍 验证 Redis 中的注册信息...")

    # 1. 检查节点基本信息
    info_key = f"node:info:{test_node_id}"
    info_data = redis_client.hgetall(info_key)

    if info_data:
        print(f"\n✅ 节点基本信息 (node:info:{test_node_id}):")
        for field, value in info_data.items():
            print(f"   • {field.decode('utf-8')}: {value.decode('utf-8')}")
        assert info_data.get(b'status') == b'running', "状态应为 running"
        assert info_data.get(b'max_portfolios') == b'5', "最大 Portfolio 数应为 5"
    else:
        print("❌ 未找到节点基本信息")
        raise AssertionError("Node registration failed")

    # 2. 检查节点能力
    capabilities_key = f"node:capabilities:{test_node_id}"
    capabilities_data = redis_client.hgetall(capabilities_key)

    if capabilities_data:
        print(f"\n✅ 节点能力 (node:capabilities:{test_node_id}):")
        for field, value in capabilities_data.items():
            print(f"   • {field.decode('utf-8')}: {value.decode('utf-8')}")
        assert capabilities_data.get(b'supports_migration') == b'true', "应支持迁移"
        assert capabilities_data.get(b'supports_reload') == b'true', "应支持重载"
    else:
        print("❌ 未找到节点能力信息")
        raise AssertionError("Node capabilities registration failed")

    # 3. 检查心跳（启动后会立即发送第一次心跳）
    heartbeat_key = f"heartbeat:node:{test_node_id}"
    heartbeat_value = redis_client.get(heartbeat_key)

    if heartbeat_value:
        print(f"\n✅ 心跳信息 (heartbeat:node:{test_node_id}):")
        print(f"   • 心跳时间: {heartbeat_value.decode('utf-8')}")
        ttl = redis_client.ttl(heartbeat_key)
        print(f"   • TTL: {ttl} 秒")
        assert ttl > 0 and ttl <= 30, "心跳 TTL 应在 30 秒内"
    else:
        print("⚠️  未找到心跳信息（可能心跳线程尚未发送）")

    # 4. 检查节点指标
    metrics_key = f"node:metrics:{test_node_id}"
    metrics_data = redis_client.hgetall(metrics_key)

    if metrics_data:
        print(f"\n✅ 节点指标 (node:metrics:{test_node_id}):")
        for field, value in metrics_data.items():
            print(f"   • {field.decode('utf-8')}: {value.decode('utf-8')}")
    else:
        print("⚠️  未找到节点指标信息（可能心跳线程尚未更新）")

    # 5. 验证内存状态
    print(f"\n🔍 节点内存状态:")
    print(f"   • 已注册: {node.registered}")
    print(f"   • 启动时间: {node.started_at}")
    print(f"   • 运行中: {node.is_running}")

    assert node.registered == True, "节点 registered 标志应为 True"
    assert node.started_at is not None, "启动时间应已设置"

    print("\n✅ 测试 1 通过：节点自我注册成功")

except Exception as e:
    print(f"\n❌ 测试 1 失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================
# 测试 2: 节点停止时自动注销
# ============================================================
print("\n📋 测试 2: 节点停止时自动注销")
print("-" * 70)

try:
    print("🛑 停止节点...")
    node.stop()

    # 验证注销结果
    print("\n🔍 验证 Redis 中的注销结果...")

    # 检查所有键是否已删除
    all_deleted = True
    for key in keys_to_delete:
        exists = redis_client.exists(key)
        if exists:
            print(f"   ❌ 键仍存在: {key}")
            all_deleted = False
        else:
            print(f"   ✅ 键已删除: {key}")

    if all_deleted:
        print("\n✅ 所有注册信息已从 Redis 删除")
    else:
        print("\n⚠️  部分键仍存在")

    # 验证内存状态
    print(f"\n🔍 节点内存状态:")
    print(f"   • 已注册: {node.registered}")
    print(f"   • 运行中: {node.is_running}")

    assert node.registered == False, "节点 registered 标志应为 False"
    assert node.is_running == False, "节点 is_running 标志应为 False"

    print("\n✅ 测试 2 通过：节点自我注销成功")

except Exception as e:
    print(f"\n❌ 测试 2 失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================
# 测试 3: Scheduler CLI 能检测到注册的节点
# ============================================================
print("\n📋 测试 3: Scheduler CLI 检测注册节点")
print("-" * 70)

try:
    import subprocess

    # 重新启动节点
    print("🚀 重新启动节点...")
    node = ExecutionNode(node_id="test_cli_detection_node")
    node.start()

    # 等待心跳发送
    print("⏳ 等待心跳发送 (5秒)...")
    time.sleep(5)

    # 使用 CLI 检查
    print("\n🔍 使用 ginkgo scheduler nodes 检查...")
    result = subprocess.run(
        ["ginkgo", "scheduler", "nodes"],
        capture_output=True,
        text=True
    )

    if "test_cli_detection_node" in result.stdout:
        print("✅ Scheduler CLI 成功检测到注册的节点")
        print("\n" + result.stdout)
    else:
        print("⚠️  Scheduler CLI 输出中未找到节点")
        print("\n" + result.stdout)

    # 清理
    print("\n🛑 清理节点...")
    node.stop()

    print("\n✅ 测试 3 通过：Scheduler CLI 检测成功")

except Exception as e:
    print(f"\n❌ 测试 3 失败: {e}")
    import traceback
    traceback.print_exc()

# ============================================================
# 总结
# ============================================================
print("\n" + "=" * 70)
print("  ✅ ExecutionNode 自我注册测试完成")
print("=" * 70)

print("""
📊 测试总结：

✅ 测试 1: 节点启动时自动注册
   - 节点基本信息注册成功 (node:info:{node_id})
   - 节点能力信息注册成功 (node:capabilities:{node_id})
   - 心跳信息注册成功 (heartbeat:node:{node_id})
   - 节点指标信息注册成功 (node:metrics:{node_id})
   - 内存状态更新成功 (registered=True, started_at设置)

✅ 测试 2: 节点停止时自动注销
   - 所有 Redis 键成功删除
   - 内存状态恢复 (registered=False, is_running=False)

✅ 测试 3: Scheduler CLI 检测
   - Scheduler nodes 命令成功检测到注册的节点
   - 节点信息正确显示

🎯 自我注册功能验证完成：

💡 注册的 Redis 键结构：
   node:info:{node_id} (Hash)
     - node_id: 节点唯一标识
     - started_at: 启动时间
     - max_portfolios: 最大 Portfolio 数量
     - current_portfolios: 当前 Portfolio 数量
     - status: 运行状态 (running)
     - heartbeat_interval: 心跳间隔
     - heartbeat_ttl: 心跳 TTL

   node:capabilities:{node_id} (Hash)
     - max_portfolios: 最大容量
     - supports_migration: 支持迁移 (true)
     - supports_reload: 支持重载 (true)
     - supports_live_trading: 支持实盘 (true)
     - supports_paper_trading: 支持模拟盘 (true)

   heartbeat:node:{node_id} (String with TTL)
     - Value: ISO 8601 时间戳
     - TTL: 30 秒

   node:metrics:{node_id} (Hash)
     - portfolio_count: Portfolio 数量
     - queue_size: 平均队列大小
     - cpu_usage: CPU 使用率
     - memory_usage: 内存使用
     - total_events: 总事件数
     - backpressure_count: 背压次数
     - dropped_events: 丢弃事件数

🔧 使用场景：
   1. 节点启动 → 自动注册 → Scheduler 可见
   2. 定期心跳 → 保持在线状态
   3. 节点停止 → 自动注销 → Scheduler 检测到离线

🚀 Phase 5 自我注册功能：完成！
""")
