"""
公共查询接口测试示例

展示如何使用新的公共查询接口替代私有属性断言，
提高测试的稳定性和可维护性。
"""
import pytest
import sys
import datetime
from datetime import datetime as dt, timezone, timedelta
from pathlib import Path
import time
import threading
from unittest.mock import Mock

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.enums import EXECUTION_MODE, EVENT_TYPES, TIME_MODE
from ginkgo.trading.time.providers import LogicalTimeProvider, SystemTimeProvider
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.time_advance import EventTimeAdvance
from ginkgo.trading.core.status import EngineStatus, EventStats, QueueInfo, TimeInfo, ComponentSyncInfo


@pytest.mark.unit
class TestPublicQueryInterfaces:
    """公共查询接口测试示例"""

    def test_engine_status_query_interface(self):
        """测试引擎状态查询接口

        场景：验证引擎状态查询接口的完整功能
        预期：能够获取引擎的运行状态、执行模式、处理事件数等信息
        """
        # 创建回测引擎
        engine = TimeControlledEventEngine(
            name="StatusTestEngine",
            mode=EXECUTION_MODE.BACKTEST
        )

        # 使用公共接口获取引擎状态
        status = engine.get_engine_status()

        # 验证状态信息的完整性
        assert isinstance(status, EngineStatus), "应返回EngineStatus对象"
        assert status.is_running == False, "初始状态引擎不应运行"
        assert status.execution_mode == EXECUTION_MODE.BACKTEST, "执行模式应为BACKTEST"
        assert status.processed_events == 0, "初始处理事件数应为0"
        assert status.queue_size >= 0, "队列大小应非负"
        assert status.current_time is not None, "当前时间不应为空"

        print(f"✓ 引擎状态查询验证:")
        print(f"  - 运行状态: {status.is_running}")
        print(f"  - 执行模式: {status.execution_mode}")
        print(f"  - 处理事件数: {status.processed_events}")
        print(f"  - 队列大小: {status.queue_size}")
        print(f"  - 当前时间: {status.current_time}")

    def test_event_stats_query_interface(self):
        """测试事件统计查询接口

        场景：验证事件处理统计信息的获取
        预期：能够获取事件处理数量、处理器注册数量、处理速率等信息
        """
        # 创建引擎
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)

        # 注册一些测试处理器
        def test_handler(event):
            pass

        engine.register(EVENT_TYPES.PRICEUPDATE, test_handler)
        engine.register_general(test_handler)

        # 使用公共接口获取事件统计
        event_stats = engine.get_event_stats()

        # 验证统计信息的完整性
        assert isinstance(event_stats, EventStats), "应返回EventStats对象"
        assert event_stats.processed_events >= 0, "处理事件数应非负"
        assert event_stats.registered_handlers >= 2, "注册处理器数应至少为2"
        assert event_stats.queue_size >= 0, "队列大小应非负"
        assert event_stats.processing_rate >= 0.0, "处理速率应非负"

        # 获取详细的处理器分布信息
        distribution = engine.get_handler_distribution()
        assert 'type_specific' in distribution, "应包含专用处理器统计"
        assert 'general' in distribution, "应包含通用处理器统计"
        assert 'total' in distribution, "应包含总处理器统计"

        # 获取更详细的事件处理统计
        detailed_stats = engine.get_event_processing_stats()
        assert 'total_events' in detailed_stats, "应包含总事件数"
        assert 'success_rate' in detailed_stats, "应包含成功率"
        assert 'failure_rate' in detailed_stats, "应包含失败率"

        print(f"✓ 事件统计查询验证:")
        print(f"  - 处理事件数: {event_stats.processed_events}")
        print(f"  - 注册处理器数: {event_stats.registered_handlers}")
        print(f"  - 处理速率: {event_stats.processing_rate:.2f} 事件/秒")
        print(f"  - 处理器分布: {distribution}")

    def test_queue_info_query_interface(self):
        """测试队列信息查询接口

        场景：验证事件队列状态信息的获取
        预期：能够获取队列大小、最大容量、是否已满等信息
        """
        # 创建引擎
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)

        # 使用公共接口获取队列信息
        queue_info = engine.get_queue_info()

        # 验证队列信息的完整性
        assert isinstance(queue_info, QueueInfo), "应返回QueueInfo对象"
        assert queue_info.queue_size >= 0, "队列大小应非负"
        assert queue_info.max_size > 0, "最大容量应大于0"
        assert isinstance(queue_info.is_full, bool), "is_full应为布尔值"
        assert isinstance(queue_info.is_empty, bool), "is_empty应为布尔值"

        # 初始状态队列应为空
        assert queue_info.is_empty == True, "初始队列应为空"
        assert queue_info.is_full == False, "初始队列不应已满"

        print(f"✓ 队列信息查询验证:")
        print(f"  - 当前大小: {queue_info.queue_size}")
        print(f"  - 最大容量: {queue_info.max_size}")
        print(f"  - 是否已满: {queue_info.is_full}")
        print(f"  - 是否为空: {queue_info.is_empty}")

    def test_time_info_query_interface(self):
        """测试时间信息查询接口

        场景：验证时间相关信息的获取，包括回测和实盘模式
        预期：能够获取时间模式、提供者类型、逻辑时间等信息
        """
        # 测试回测模式的时间信息
        backtest_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)
        backtest_time_info = backtest_engine.get_time_info()

        # 验证回测时间信息
        assert isinstance(backtest_time_info, TimeInfo), "应返回TimeInfo对象"
        assert backtest_time_info.time_mode == TIME_MODE.LOGICAL, "回测模式时间模式应为LOGICAL"
        assert backtest_time_info.is_logical_time == True, "回测模式应使用逻辑时间"
        assert backtest_time_info.time_provider_type == "LogicalTimeProvider", "应为LogicalTimeProvider"
        assert backtest_time_info.current_time is not None, "当前时间不应为空"
        assert backtest_time_info.logical_start_time is not None, "逻辑开始时间不应为空"

        # 测试实盘模式的时间信息
        live_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE)
        live_time_info = live_engine.get_time_info()

        # 验证实盘时间信息
        assert live_time_info.time_mode == TIME_MODE.SYSTEM, "实盘模式时间模式应为SYSTEM"
        assert live_time_info.is_logical_time == False, "实盘模式不应使用逻辑时间"
        assert live_time_info.time_provider_type == "SystemTimeProvider", "应为SystemTimeProvider"
        assert live_time_info.current_time is not None, "当前时间不应为空"
        assert live_time_info.logical_start_time is None, "实盘模式逻辑开始时间应为空"

        print(f"✓ 时间信息查询验证:")
        print(f"  回测模式:")
        print(f"    - 时间模式: {backtest_time_info.time_mode}")
        print(f"    - 提供者类型: {backtest_time_info.time_provider_type}")
        print(f"    - 是否逻辑时间: {backtest_time_info.is_logical_time}")
        print(f"    - 逻辑开始时间: {backtest_time_info.logical_start_time}")
        print(f"  实盘模式:")
        print(f"    - 时间模式: {live_time_info.time_mode}")
        print(f"    - 提供者类型: {live_time_info.time_provider_type}")
        print(f"    - 是否逻辑时间: {live_time_info.is_logical_time}")

    def test_time_provider_info_interface(self):
        """测试时间提供者详细信息接口

        场景：验证时间提供者的详细配置信息
        预期：能够获取时间提供者的能力、模式、配置等详细信息
        """
        # 测试回测时间提供者信息
        backtest_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)
        backtest_provider_info = backtest_engine.get_time_provider_info()

        # 验证回测时间提供者信息
        assert backtest_provider_info['is_initialized'] == True, "时间提供者应已初始化"
        assert backtest_provider_info['supports_time_control'] == True, "回测模式应支持时间控制"
        assert backtest_provider_info['supports_listeners'] == True, "应支持时间监听器"
        assert backtest_provider_info['is_logical_time'] == True, "应为逻辑时间"
        assert backtest_provider_info['can_advance_time'] == True, "应支持时间推进"
        assert backtest_provider_info['mode'] == EXECUTION_MODE.BACKTEST.value, "模式应为BACKTEST"

        # 测试实盘时间提供者信息
        live_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE)
        live_provider_info = live_engine.get_time_provider_info()

        # 验证实盘时间提供者信息
        assert live_provider_info['is_initialized'] == True, "时间提供者应已初始化"
        assert live_provider_info['supports_time_control'] == True, "实盘模式也有advance_time_to方法（虽然会抛出异常）"
        assert live_provider_info['supports_listeners'] == True, "应支持时间监听器"
        assert live_provider_info['is_logical_time'] == False, "不应为逻辑时间"
        assert live_provider_info['can_advance_time'] == False, "不应支持时间推进"
        assert live_provider_info['mode'] == EXECUTION_MODE.LIVE.value, "模式应为LIVE"

        print(f"✓ 时间提供者详细信息验证:")
        print(f"  回测提供者:")
        print(f"    - 支持时间控制: {backtest_provider_info['supports_time_control']}")
        print(f"    - 支持时间推进: {backtest_provider_info['can_advance_time']}")
        print(f"  实盘提供者:")
        print(f"    - 支持时间控制: {live_provider_info['supports_time_control']} (方法存在但抛出异常)")
        print(f"    - 支持时间推进: {live_provider_info['can_advance_time']}")

    def test_component_sync_info_interface(self):
        """测试组件同步信息查询接口

        场景：验证组件同步状态的查询功能
        预期：能够获取单个组件和所有组件的同步状态信息
        """
        # 创建引擎
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)

        # 获取所有组件的同步状态
        all_sync_info = engine.get_all_components_sync_info()

        # 验证组件同步信息结构
        assert isinstance(all_sync_info, dict), "应返回字典类型"

        # 获取同步状态摘要
        sync_summary = engine.get_sync_summary()
        assert 'total_components' in sync_summary, "应包含总组件数"
        assert 'synced_components' in sync_summary, "应包含已同步组件数"
        assert 'sync_rate' in sync_summary, "应包含同步率"
        assert 'components_by_type' in sync_summary, "应包含组件类型分布"

        # 验证同步率的合理性
        assert 0.0 <= sync_summary['sync_rate'] <= 1.0, "同步率应在0-1之间"

        print(f"✓ 组件同步信息查询验证:")
        print(f"  - 总组件数: {sync_summary['total_components']}")
        print(f"  - 已同步组件数: {sync_summary['synced_components']}")
        print(f"  - 同步率: {sync_summary['sync_rate']:.2%}")
        print(f"  - 组件类型分布: {sync_summary['components_by_type']}")

    def test_comprehensive_interface_integration(self):
        """测试接口集成使用示例

        场景：综合展示所有查询接口的联合使用
        预期：验证接口之间的数据一致性和完整性
        """
        # 创建引擎
        engine = TimeControlledEventEngine(
            name="IntegrationTestEngine",
            mode=EXECUTION_MODE.BACKTEST
        )

        # 启动引擎
        engine.start()

        # 注册测试处理器
        def test_handler(event):
            pass
        engine.register(EVENT_TYPES.PRICEUPDATE, test_handler)

        # 投递测试事件
        test_event = EventPriceUpdate(
            code="000001.SZ",
            timestamp=engine.now,
            price=10.0
        )
        engine.put(test_event)

        # 等待事件处理
        time.sleep(0.1)

        # 使用所有查询接口获取状态
        engine_status = engine.get_engine_status()
        event_stats = engine.get_event_stats()
        queue_info = engine.get_queue_info()
        time_info = engine.get_time_info()
        provider_info = engine.get_time_provider_info()
        sync_summary = engine.get_sync_summary()

        # 验证数据一致性
        assert engine_status.queue_size == queue_info.queue_size, "队列大小应一致"
        assert engine_status.processed_events == event_stats.processed_events, "处理事件数应一致"
        assert time_info.current_time == provider_info['current_time'], "当前时间应一致"

        # 验证引擎运行状态
        assert engine_status.is_running == True, "启动后引擎应运行"
        assert engine_status.execution_mode == EXECUTION_MODE.BACKTEST, "执行模式应为BACKTEST"

        # 验证事件处理
        assert event_stats.registered_handlers >= 1, "应至少注册一个处理器"

        # 停止引擎
        engine.stop()

        # 验证停止后状态
        final_status = engine.get_engine_status()
        assert final_status.is_running == False, "停止后引擎不应运行"

        print(f"✓ 接口集成验证完成:")
        print(f"  引擎状态: 运行={engine_status.is_running}, 处理事件={engine_status.processed_events}")
        print(f"  事件统计: 注册处理器={event_stats.registered_handlers}, 处理速率={event_stats.processing_rate:.2f}")
        print(f"  队列状态: {queue_info.queue_size}/{queue_info.max_size}")
        print(f"  时间信息: 模式={time_info.time_mode}, 提供者={time_info.time_provider_type}")
        print(f"  组件同步: 总数={sync_summary['total_components']}, 同步率={sync_summary['sync_rate']:.2%}")

    def test_business_closed_loop_validation(self):
        """测试业务闭环验证示例

        场景：使用公共接口进行完整的业务流程验证
        预期：验证从事件投递到处理完成的完整链路
        """
        # 创建回测引擎
        engine = TimeControlledEventEngine(
            name="BusinessLoopTest",
            mode=EXECUTION_MODE.BACKTEST
        )

        # 记录初始状态
        initial_status = engine.get_engine_status()
        initial_event_stats = engine.get_event_stats()
        initial_time_info = engine.get_time_info()

        # 启动引擎
        engine.start()
        assert engine.get_engine_status().is_running == True, "引擎应启动"

        # 投递价格更新事件
        price_event = EventPriceUpdate(
            code="000001.SZ",
            timestamp=engine.now,
            price=10.0,
            volume=1000
        )
        engine.put(price_event)

        # 等待事件处理
        time.sleep(0.1)

        # 验证事件处理结果
        updated_status = engine.get_engine_status()
        updated_event_stats = engine.get_event_stats()
        updated_queue_info = engine.get_queue_info()

        # 业务闭环验证
        assert updated_status.is_running == True, "引擎应保持运行"
        assert updated_event_stats.processed_events > initial_event_stats.processed_events, "应有事件被处理"
        assert updated_event_stats.registered_handlers >= 0, "处理器注册状态正常"

        # 验证时间推进
        final_time_info = engine.get_time_info()
        assert final_time_info.current_time >= initial_time_info.current_time, "时间应推进"

        # 停止引擎并验证最终状态
        engine.stop()
        final_status = engine.get_engine_status()
        assert final_status.is_running == False, "引擎应停止"

        print(f"✓ 业务闭环验证完成:")
        print(f"  处理事件数变化: {initial_event_stats.processed_events} → {updated_event_stats.processed_events}")
        print(f"  时间推进: {initial_time_info.current_time} → {final_time_info.current_time}")
        print(f"  最终状态: 运行={final_status.is_running}, 队列={updated_queue_info.queue_size}")


@pytest.mark.unit
class TestInterfaceErrorHandling:
    """公共查询接口错误处理测试"""

    def test_invalid_component_sync_query(self):
        """测试无效组件ID的同步查询

        场景：查询不存在的组件ID
        预期：应返回None而不是抛出异常
        """
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)

        # 查询不存在的组件
        sync_info = engine.get_component_sync_info("non_existent_component")
        assert sync_info is None, "不存在的组件应返回None"

        # 检查组件同步状态
        is_synced = engine.is_component_synced("non_existent_component")
        assert is_synced == False, "不存在的组件应返回未同步"

        print("✓ 无效组件查询处理验证: 正确返回None或False")

    def test_interface_thread_safety(self):
        """测试接口的线程安全性

        场景：在多线程环境下调用查询接口
        预期：接口调用应安全，不产生竞态条件
        """
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)
        results = []

        def query_worker():
            try:
                for _ in range(10):
                    status = engine.get_engine_status()
                    event_stats = engine.get_event_stats()
                    queue_info = engine.get_queue_info()
                    time_info = engine.get_time_info()
                    results.append((status, event_stats, queue_info, time_info))
                    time.sleep(0.001)  # 短暂休眠
            except Exception as e:
                results.append(f"Error: {e}")

        # 启动多个查询线程
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=query_worker)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证结果
        assert len(results) == 50, "应获得50个查询结果"
        error_count = sum(1 for r in results if isinstance(r, str) and r.startswith("Error:"))
        assert error_count == 0, f"不应有错误: {error_count}个错误"

        print(f"✓ 线程安全验证完成: {len(results)}个查询全部成功，无错误")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])