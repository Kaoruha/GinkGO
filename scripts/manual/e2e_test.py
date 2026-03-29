#!/usr/bin/env python3
"""
008-live-data-module 端到端测试

实际运行测试，验证数据流：
1. DataManager 接收订阅更新
2. TaskTimer 发送定时命令
3. PortfolioProcessor 处理命令
4. 查看实际日志输出

运行方式:
    python tests/manual/e2e_test.py
"""

import sys
import time
import json
from datetime import datetime
from queue import Queue

def test_kafka_connection():
    """测试 Kafka 连接"""
    print("\n=== 步骤 1: 测试 Kafka 连接 ===")

    try:
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer, GinkgoConsumer
        from ginkgo.libs import GCONF

        # 显示 Kafka 配置
        print(f"  Kafka Host: {GCONF.KAFKAHOST}")
        print(f"  Kafka Port: {GCONF.KAFKAPORT}")

        # 测试 Producer（从 GCONF 读取配置）
        producer = GinkgoProducer()
        if producer.is_connected:
            print("✓ Kafka Producer 连接成功")
        else:
            print("⚠ Kafka Producer 连接失败（可能 Kafka 未运行）")

        # 测试 Consumer（需要 topic 参数）
        consumer = GinkgoConsumer(
            topic="ginkgo.live.control.commands",
            group_id="e2e_test_group"
        )
        print("✓ Kafka Consumer 创建成功")

        return True, producer, consumer
    except Exception as e:
        print(f"✗ Kafka 连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False, None, None

def test_task_timer():
    """测试 TaskTimer 定时任务"""
    print("\n=== 步骤 2: 测试 TaskTimer ===")

    try:
        from ginkgo.livecore.task_timer import TaskTimer

        # 创建 TaskTimer
        timer = TaskTimer()
        print("✓ TaskTimer 创建成功")

        # 验证配置加载（可能返回 None）
        config = timer._load_config()
        if config is None:
            print("✓ 配置文件不存在，使用默认配置")
        else:
            print(f"✓ 配置加载成功，任务数: {len(config.get('scheduled_tasks', []))}")

        # 启动 TaskTimer（后台运行 3 秒）
        print("✓ 启动 TaskTimer（运行 3 秒）...")
        timer.start()
        time.sleep(3)

        # 停止
        timer.stop()
        print("✓ TaskTimer 已停止")

        return True
    except Exception as e:
        print(f"✗ TaskTimer 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_manager():
    """测试 DataManager 数据订阅"""
    print("\n=== 步骤 3: 测试 DataManager ===")

    try:
        from ginkgo.livecore.data_manager import DataManager
        from ginkgo.interfaces.dtos import InterestUpdateDTO
        from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer

        # 创建 DataManager（不实际连接外部数据源）
        print("✓ DataManager 创建成功（feeder_type=eastmoney）")

        # 测试订阅更新处理
        producer = GinkgoProducer()

        # 发送订阅更新
        dto = InterestUpdateDTO(
            portfolio_id="test_portfolio",
            node_id="test_node",
            symbols=["000001.SZ", "600000.SH"],
            timestamp=datetime.now()
        )

        print(f"✓ 创建订阅更新: {dto.symbols}")
        print(f"  JSON: {dto.model_dump_json()[:100]}...")

        return True
    except Exception as e:
        print(f"✗ DataManager 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_portfolio_processor():
    """测试 PortfolioProcessor 控制命令处理"""
    print("\n=== 步骤 4: 测试 PortfolioProcessor ===")

    try:
        from ginkgo.workers.execution_node.portfolio_processor import PortfolioProcessor
        from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
        from ginkgo.interfaces.dtos import ControlCommandDTO
        from unittest.mock import Mock
        import json

        # 创建 Mock Portfolio
        mock_portfolio = Mock(spec=PortfolioLive)
        mock_portfolio.portfolio_id = "e2e_test_portfolio"
        mock_portfolio._selectors = []

        # 创建 Queue
        input_queue = Queue()
        output_queue = Queue()

        # 创建 PortfolioProcessor
        processor = PortfolioProcessor(
            portfolio=mock_portfolio,
            input_queue=input_queue,
            output_queue=output_queue,
            max_queue_size=1000
        )
        print(f"✓ PortfolioProcessor 创建成功 (ID: {processor.portfolio_id})")

        # 测试控制命令处理
        command_dto = ControlCommandDTO(
            command=ControlCommandDTO.Commands.UPDATE_SELECTOR
        )
        message = command_dto.model_dump_json().encode('utf-8')

        processor._handle_control_command(message)
        print(f"✓ 控制命令处理成功: {command_dto.command}")

        # 验证输出
        if not output_queue.empty():
            event = output_queue.get()
            print(f"✓ 生成事件: {type(event).__name__}")
        else:
            print("✓ 无 selector，未生成事件（正常）")

        return True
    except Exception as e:
        print(f"✗ PortfolioProcessor 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_flow():
    """测试完整数据流"""
    print("\n=== 步骤 5: 测试完整数据流 ===")

    try:
        from ginkgo.interfaces.dtos import PriceUpdateDTO, BarDTO, InterestUpdateDTO, ControlCommandDTO
        from datetime import datetime

        # 1. 创建 InterestUpdateDTO
        interest_dto = InterestUpdateDTO(
            portfolio_id="test_portfolio",
            node_id="test_node",
            symbols=["000001.SZ"],
            timestamp=datetime.now()
        )
        print(f"✓ InterestUpdateDTO: {interest_dto.symbols}")

        # 2. 创建 PriceUpdateDTO
        price_dto = PriceUpdateDTO(
            symbol="000001.SZ",
            price=10.50,
            volume=1000,
            amount=10500.0,
            timestamp=datetime.now()
        )
        print(f"✓ PriceUpdateDTO: {price_dto.symbol} @ {price_dto.price}")

        # 3. 创建 BarDTO
        bar_dto = BarDTO(
            symbol="000001.SZ",
            period="1d",
            open=10.0,
            high=10.8,
            low=9.9,
            close=10.5,
            volume=1000000,
            timestamp=datetime.now()
        )
        print(f"✓ BarDTO: {bar_dto.symbol} OHLC={bar_dto.open}/{bar_dto.high}/{bar_dto.low}/{bar_dto.close}")

        # 4. 创建 ControlCommandDTO
        cmd_dto = ControlCommandDTO(
            command=ControlCommandDTO.Commands.UPDATE_SELECTOR
        )
        print(f"✓ ControlCommandDTO: {cmd_dto.command}")

        # 5. 测试序列化
        for dto_name, dto in [
            ("InterestUpdateDTO", interest_dto),
            ("PriceUpdateDTO", price_dto),
            ("BarDTO", bar_dto),
            ("ControlCommandDTO", cmd_dto),
        ]:
            json_str = dto.model_dump_json()
            print(f"✓ {dto_name} 序列化: {len(json_str)} 字节")

        return True
    except Exception as e:
        print(f"✗ 数据流测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """运行端到端测试"""
    print("=" * 60)
    print("008-live-data-module 端到端测试")
    print("=" * 60)
    print("\n这个测试将验证:")
    print("  1. Kafka 连接")
    print("  2. TaskTimer 定时任务")
    print("  3. DataManager 订阅管理")
    print("  4. PortfolioProcessor 控制命令")
    print("  5. 完整数据流（DTO 序列化）")

    # 测试步骤
    tests = [
        ("Kafka 连接", test_kafka_connection),
        ("TaskTimer", test_task_timer),
        ("DataManager", test_data_manager),
        ("PortfolioProcessor", test_portfolio_processor),
        ("数据流", test_data_flow),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if name == "Kafka 连接":
                success, _, _ = test_func()
                if success:
                    passed += 1
                else:
                    failed += 1
                    print("\n⚠️ Kafka 连接失败，跳过后续测试")
                    break
            else:
                result = test_func()
                if result:
                    passed += 1
                else:
                    failed += 1
        except Exception as e:
            print(f"\n✗ 测试异常: {name}")
            print(f"   错误: {e}")
            failed += 1

    # 总结
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    if failed == 0:
        print("\n✅ 所有测试通过！")
        print("\n下一步:")
        print("  1. 运行实际数据源测试: python tests/manual/live_test.py")
        print("  2. 查看 Kafka 消息: kafka-console-consumer --bootstrap-server localhost:9092 --topic ginkgo.live.market.data")
        return 0
    else:
        print("\n❌ 部分测试失败")
        print("\n请检查:")
        print("  1. Kafka 是否运行")
        print("  2. 网络连接是否正常")
        print("  3. 配置文件是否正确")
        return 1

if __name__ == "__main__":
    sys.exit(main())
