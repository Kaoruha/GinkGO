"""
演示 ExecutionNode 心跳上报的具体信息

展示心跳和指标在 Redis 中的实际存储内容。

运行方式：
    PYTHONPATH=/home/kaoru/Ginkgo/src python examples/show_heartbeat_info.py
"""

import time
from datetime import datetime

print("=" * 70)
print("  ExecutionNode 心跳上报信息演示")
print("=" * 70)

try:
    from ginkgo.workers.execution_node.node import ExecutionNode
    from ginkgo.data.crud import RedisCRUD

    redis_crud = RedisCRUD()
    redis_client = redis_crud.redis
    test_node_id = "demo_heartbeat_node"

    # ============================================================
    # 第一部分：查看心跳信息
    # ============================================================
    print("\n📋 第一部分：心跳信息 (heartbeat:node:{node_id})")
    print("-" * 70)

    # 启动节点
    print("\n🚀 启动 ExecutionNode...")
    node = ExecutionNode(node_id=test_node_id)
    node.start()

    # 立即查看心跳
    print("\n🔍 查看心跳信息...")
    heartbeat_key = f"heartbeat:node:{test_node_id}"

    heartbeat_value = redis_client.get(heartbeat_key)
    if heartbeat_value:
        print(f"\n✅ 心跳键: {heartbeat_key}")
        print(f"   类型: String")
        print(f"   值: {heartbeat_value.decode('utf-8')}")
        print(f"   说明: ISO 8601 格式的时间戳")

        ttl = redis_client.ttl(heartbeat_key)
        print(f"   TTL: {ttl}秒 (30秒后自动过期)")
    else:
        print("❌ 未找到心跳信息")

    # 等待几秒，再次查看
    print("\n⏳ 等待 5 秒...")
    time.sleep(5)

    print("\n🔍 再次查看心跳信息...")
    heartbeat_value = redis_client.get(heartbeat_key)
    ttl = redis_client.ttl(heartbeat_key)

    if heartbeat_value:
        new_value = heartbeat_value.decode('utf-8')
        print(f"   心跳值: {new_value}")
        print(f"   TTL: {ttl}秒")
        print(f"   💡 心跳已更新（时间戳变化）")

    # ============================================================
    # 第二部分：查看性能指标
    # ============================================================
    print("\n\n📋 第二部分：性能指标 (node:metrics:{node_id})")
    print("-" * 70)

    print("\n🔍 查看性能指标...")
    metrics_key = f"node:metrics:{test_node_id}"

    metrics = redis_client.hgetall(metrics_key)

    if metrics:
        print(f"\n✅ 指标键: {metrics_key}")
        print(f"   类型: Hash")
        print(f"   字段数: {len(metrics)}")

        print(f"\n📊 详细指标:")
        print(f"{'字段':<25} {'值':<15} {'说明'}")
        print("-" * 70)

        field_descriptions = {
            b'portfolio_count': '当前运行的 Portfolio 数量',
            b'queue_size': '所有 Portfolio 的平均队列大小',
            b'cpu_usage': 'CPU 使用率（预留，未实现）',
            b'memory_usage': '内存使用（预留，未实现）',
            b'total_events': '累计处理事件总数',
            b'backpressure_count': '背压发生次数',
            b'dropped_events': '丢弃事件数'
        }

        for field, value in metrics.items():
            field_str = field.decode('utf-8')
            value_str = value.decode('utf-8')
            desc = field_descriptions.get(field, '未知字段')

            # 标记预留字段
            if field_str in ['cpu_usage', 'memory_usage']:
                status = "⏳ 预留"
            else:
                status = "✅"

            print(f"{status} {field_str:<25} {value_str:<15} {desc}")
    else:
        print("⚠️  未找到指标信息（可能心跳线程尚未更新）")

    # 等待指标更新
    print("\n⏳ 等待 3 秒，让指标更新...")
    time.sleep(3)

    print("\n🔍 再次查看性能指标...")
    metrics = redis_client.hgetall(metrics_key)

    if metrics:
        print(f"\n✅ 指标已更新:")
        for field, value in metrics.items():
            field_str = field.decode('utf-8')
            value_str = value.decode('utf-8')
            print(f"   • {field_str}: {value_str}")

    # ============================================================
    # 第三部分：模拟负载变化
    # ============================================================
    print("\n\n📋 第三部分：模拟负载变化")
    print("-" * 70)

    # 模拟指标变化
    print("\n📈 模拟指标变化...")
    node.total_event_count = 1000
    node.backpressure_count = 5
    node.dropped_event_count = 2

    # 手动触发更新
    print("\n🔄 手动触发指标更新...")
    node._update_node_metrics()

    print("\n🔍 查看更新后的指标...")
    metrics = redis_client.hgetall(metrics_key)

    if metrics:
        print(f"\n✅ 更新后的指标:")
        for field, value in metrics.items():
            field_str = field.decode('utf-8')
            value_str = value.decode('utf-8')
            print(f"   • {field_str}: {value_str}")

        # 验证变化
        if metrics.get(b'total_events') == b'1000':
            print("\n✅ 指标已正确更新")

    # ============================================================
    # 第四部分：Redis CLI 命令演示
    # ============================================================
    print("\n\n📋 第四部分：Redis CLI 命令演示")
    print("-" * 70)

    print("\n💡 你可以使用以下 Redis CLI 命令查看心跳信息：\n")

    print("1️⃣  查看心跳时间：")
    print(f"   redis-cli GET heartbeat:node:{test_node_id}")

    print("\n2️⃣  查看心跳 TTL：")
    print(f"   redis-cli TTL heartbeat:node:{test_node_id}")

    print("\n3️⃣  查看所有指标：")
    print(f"   redis-cli HGETALL node:metrics:{test_node_id}")

    print("\n4️⃣  查看特定指标：")
    print(f"   redis-cli HGET node:metrics:{test_node_id} portfolio_count")

    print("\n5️⃣  查看所有在线节点：")
    print("   redis-cli KEYS heartbeat:node:*")

    print("\n6️⃣  查看所有节点指标：")
    print("   redis-cli KEYS node:metrics:*")

    # ============================================================
    # 清理
    # ============================================================
    print("\n\n📋 清理资源")
    print("-" * 70)

    print("\n🛑 停止节点...")
    node.stop()

    print("\n⏳ 等待 3 秒，验证心跳过期...")
    time.sleep(3)

    print("\n🔍 验证心跳是否已删除...")
    heartbeat_exists = redis_client.exists(heartbeat_key)

    if heartbeat_exists:
        print(f"   ⚠️  心跳仍存在（TTL={redis_client.ttl(heartbeat_key)}秒）")
        print("   💡 再等待几秒，TTL 会自动过期")
    else:
        print("   ✅ 心跳已删除（TTL 自动过期）")
        print("   💡 Scheduler 将检测到节点离线")

    print("\n🧹 清理测试数据...")
    redis_client.delete(metrics_key)
    print("   ✅ 测试数据已清理")

    # ============================================================
    # 总结
    # ============================================================
    print("\n" + "=" * 70)
    print("  ✅ 心跳上报信息演示完成")
    print("=" * 70)

    print("""
📊 心跳上报的信息总结：

【心跳信息】heartbeat:node:{node_id}
   类型: String + TTL (30秒)
   值: ISO 8601 时间戳
   用途: 存活证明，离线检测

【性能指标】node:metrics:{node_id}
   类型: Hash (7个字段)

   ✅ 已实现的指标：
   • portfolio_count: Portfolio 数量
   • queue_size: 平均队列大小
   • total_events: 累计事件数
   • backpressure_count: 背压次数
   • dropped_events: 丢弃事件数

   ⏳ 预留的指标（未来实现）：
   • cpu_usage: CPU 使用率
   • memory_usage: 内存使用

💡 关键特点：
   - 每 10 秒自动上报一次
   - 启动时立即发送第 1 次心跳
   - 停止后 TTL 自动过期（30秒）
   - 简单、可靠、高效

🔧 监控命令：
   # 查看所有节点
   redis-cli KEYS "heartbeat:node:*"

   # 查看节点指标
   redis-cli HGETALL "node:metrics:node_id"

   # 查看节点心跳时间
   redis-cli GET "heartbeat:node:node_id"

   # 使用 CLI
   ginkgo scheduler nodes
""")

except Exception as e:
    print(f"\n❌ 演示失败: {e}")
    import traceback
    traceback.print_exc()
