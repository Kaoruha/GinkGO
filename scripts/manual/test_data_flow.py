#!/usr/bin/env python3
"""
验证 LiveCore 数据流

测试场景：
1. 发送订阅更新到 Kafka
2. 验证 DataManager 接收并处理
3. 查看实时数据是否发布到 Kafka
"""

import time
import json
from datetime import datetime

def test_send_subscription():
    """发送订阅更新"""
    print("\n=== 测试 1: 发送订阅更新 ===")

    from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
    from ginkgo.interfaces.dtos import InterestUpdateDTO

    producer = GinkgoProducer()

    # 发送订阅更新
    dto = InterestUpdateDTO(
        portfolio_id="test_portfolio_001",
        node_id="test_node_001",
        symbols=["000001.SZ", "600000.SH"],
        timestamp=datetime.now()
    )

    result = producer.send(
        topic="ginkgo.live.interest.updates",
        msg=json.loads(dto.model_dump_json())
    )

    if result:
        print(f"✓ 订阅更新发送成功")
        print(f"  Portfolio: {dto.portfolio_id}")
        print(f"  Symbols: {dto.symbols}")
    else:
        print(f"✗ 订阅更新发送失败")

    return result

def test_consume_market_data():
    """消费市场数据"""
    print("\n=== 测试 2: 消费市场数据 ===")

    from ginkgo.data.drivers.ginkgo_kafka import GinkgoConsumer

    consumer = GinkgoConsumer(
        topic="ginkgo.live.market.data",
        group_id="test_consumer_group"
    )

    print("等待市场数据（10秒）...")
    print("如果 DataManager 正在运行，应该能看到数据")

    # 轮询 10 秒
    start_time = time.time()
    message_count = 0

    while time.time() - start_time < 10:
        try:
            # GinkgoConsumer 包装了 KafkaConsumer，可以直接迭代
            for message in consumer.consumer:
                message_count += 1
                try:
                    data = message.value
                    if isinstance(data, dict):
                        print(f"✓ 收到数据: {data.get('symbol', 'N/A')} @ {data.get('price', 'N/A')}")
                    else:
                        print(f"✓ 收到原始数据: {str(data)[:100]}")
                except Exception as e:
                    print(f"✓ 收到消息: {str(message.value)[:100]}")

                # 只处理一条就继续等待
                break
        except Exception as e:
            # 超时或没有消息，继续等待
            pass

    if message_count > 0:
        print(f"\n✓ 总共收到 {message_count} 条消息")
    else:
        print(f"\n⚠ 未收到市场数据")
        print("  可能原因：")
        print("  1. DataManager 未启动")
        print("  2. 没有活跃的数据订阅")
        print("  3. 数据源未连接")

    return message_count > 0

def test_control_commands():
    """测试控制命令"""
    print("\n=== 测试 3: 测试控制命令 ===")

    from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
    from ginkgo.interfaces.dtos import ControlCommandDTO

    producer = GinkgoProducer()

    # 发送 selector 更新命令
    cmd = ControlCommandDTO(
        command=ControlCommandDTO.Commands.UPDATE_SELECTOR
    )

    result = producer.send(
        topic="ginkgo.live.control.commands",
        msg=json.loads(cmd.model_dump_json())
    )

    if result:
        print(f"✓ 控制命令发送成功: {cmd.command}")
    else:
        print(f"✗ 控制命令发送失败")

    return result

def main():
    print("=" * 60)
    print("LiveCore 数据流验证")
    print("=" * 60)

    results = []

    # 测试 1: 发送订阅更新
    results.append(("发送订阅更新", test_send_subscription()))

    # 等待处理
    time.sleep(2)

    # 测试 2: 消费市场数据
    results.append(("消费市场数据", test_consume_market_data()))

    # 测试 3: 控制命令
    results.append(("控制命令", test_control_commands()))

    # 总结
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)

    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"{status} - {name}")

    passed = sum(1 for _, r in results if r)
    print(f"\n总计: {passed}/{len(results)} 通过")

    if passed == len(results):
        print("\n✅ LiveCore 数据模块运行正常！")
        return 0
    else:
        print("\n⚠ 部分功能可能需要检查")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
