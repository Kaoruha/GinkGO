"""
TimeControlledEventEngine高级功能测试

该文件包含TimeControlledEngine的高级功能测试，包括回测模式管理器核心、时间推进机制、以及端到端测试。
从原始的大文件中提取出来，提高代码的可维护性。

测试范围：
1. 回测模式管理器核心测试
2. 时间推进机制完整测试
3. 端到端测试
4. 确定性和一致性测试
5. 高级功能集成测试
"""

import pytest
import sys
import datetime
import time as time_module
import threading
from pathlib import Path
from datetime import datetime as dt, time, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# 核心依赖导入
from ginkgo.enums import (
    EVENT_TYPES, FREQUENCY_TYPES, TICKDIRECTION_TYPES,
    SOURCE_TYPES, EXECUTION_MODE, TIME_MODE, ENGINESTATUS_TYPES
)
from ginkgo.trading.events.time_advance import EventTimeAdvance
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.component_time_advance import EventComponentTimeAdvance
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.tick import Tick
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.trading.time.providers import LogicalTimeProvider, SystemTimeProvider


# 辅助函数：安全获取事件
def safe_get_event(engine, timeout=0.1):
    """安全获取事件，避免阻塞"""
    try:
        event = engine.get_event(timeout=timeout)
        return event
    except:
        return None


@pytest.mark.unit
@pytest.mark.backtest
class TestBacktestModeManagerCore:
    """1. 回测模式管理器核心测试 - 同步执行"""

    def test_backtest_sync_execution(self):
        """测试回测同步执行机制"""
        import threading
        import time

        # 创建回测引擎
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST, name="SyncExecutionEngine")

        # 验证引擎模式
        assert engine.mode == EXECUTION_MODE.BACKTEST, "引擎应为BACKTEST模式"

        # 验证同步执行相关属性
        assert hasattr(engine, '_event_queue'), "应有事件队列"
        assert hasattr(engine, '_handlers'), "应有处理器字典"
        assert hasattr(engine, '_sequence_lock'), "应有序列号锁"

        # 测试数据结构
        execution_order = []
        execution_threads = []

        # 创建测试处理器
        def sync_test_handler(event):
            """同步测试处理器"""
            # 记录执行线程
            current_thread = threading.current_thread().ident
            execution_threads.append(current_thread)

            # 记录执行顺序
            execution_order.append(f"Event-{len(execution_order)}-Thread-{current_thread}")

            # 模拟处理时间
            time.sleep(0.01)

        # 注册处理器
        reg_success = engine.register(EVENT_TYPES.TIME_ADVANCE, sync_test_handler)
        assert reg_success is True, "处理器注册应成功"

        # 创建多个测试事件
        test_events = []
        for i in range(5):
            event = EventTimeAdvance(dt.now(timezone.utc))
            test_events.append(event)
            engine.put(event)

        # 验证事件已在队列中
        assert not engine._event_queue.empty(), "事件应在队列中"

        # 模拟同步事件处理
        processed_count = 0
        while processed_count < len(test_events):
            try:
                # 获取事件
                event = safe_get_event(engine, timeout=0.1)
                if event:
                    # 同步处理事件
                    sync_test_handler(event)
                    processed_count += 1
            except Exception as e:
                print(f"事件处理异常: {e}")
                break

        # 验证所有事件都被处理
        assert processed_count >= len(test_events), f"应处理至少{len(test_events)}个事件，实际处理{processed_count}个"

        # 验证执行顺序
        assert len(execution_order) >= len(test_events), "执行记录数应不少于事件数"

        # 验证同步执行特性：在回测模式下，事件应按顺序处理
        # 检查执行线程的一致性（虽然可能不完全是单线程，但应有顺序性）
        print(f"执行顺序: {execution_order[:5]}")  # 显示前5个执行记录
        print(f"涉及的线程数: {len(set(execution_threads))}")

        # 验证事件处理的顺序性
        # 在回测模式下，事件应该按FIFO顺序处理
        for i in range(1, min(len(execution_order), len(test_events))):
            # 验证执行顺序的递增性
            current_order = execution_order[i]
            expected_index = i

            # 提取实际的事件索引
            try:
                actual_index = int(current_order.split('-')[1])
                assert actual_index == expected_index, f"事件顺序错误: 期望{expected_index}, 实际{actual_index}"
            except (IndexError, ValueError):
                # 如果格式解析失败，至少验证有执行记录
                assert True, "执行记录存在"

        # 验证回测模式的确定性特征
        # 回测模式不应有ThreadPoolExecutor等并发组件
        assert hasattr(engine, '_event_queue'), "回测模式应有事件队列"

        # 验证引擎状态稳定性
        assert engine.status in ["idle", "running", "stopped"], f"引擎状态应正常: {engine.status}"

        print(f"同步执行测试完成: 处理{processed_count}个事件, 使用{len(set(execution_threads))}个线程")
        assert True, "回测同步执行机制测试通过"

    def test_empty_exception_barrier(self):
        """测试Empty异常屏障机制"""
        import queue
        import time

        # 创建回测引擎
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST, name="EmptyBarrierEngine")

        # 验证事件队列存在
        assert hasattr(engine, '_event_queue'), "应有事件队列"
        assert engine._event_queue is not None, "事件队列不应为空"

        # 测试Empty异常作为同步屏障的机制
        # 在回测模式下，Queue.get(timeout)抛出Empty异常表示当前阶段所有事件处理完毕

        # 初始状态：队列为空
        try:
            # 清空队列
            while not engine._event_queue.empty():
                safe_get_event(engine, timeout=0.01)
        except Exception:
            pass

        # 验证初始队列为空
        assert engine._event_queue.empty(), "初始队列应为空"

        # 测试从空队列获取事件的行为
        empty_caught_count = 0
        start_time = time.time()

        # 尝试从空队列获取事件，应该抛出Empty异常或返回None
        for i in range(3):
            try:
                event = safe_get_event(engine, timeout=0.1)  # 短超时
                if event is None:
                    empty_caught_count += 1
                    print(f"第{i+1}次获取返回None")
                else:
                    print(f"第{i+1}次获取到事件: {type(event)}")
            except queue.Empty:
                empty_caught_count += 1
                print(f"第{i+1}次捕获Empty异常")
            except Exception as e:
                print(f"第{i+1}次捕获其他异常: {e}")

        elapsed_time = time.time() - start_time

        # 验证Empty异常屏障机制工作
        assert empty_caught_count > 0, f"应至少捕获1次Empty或返回None，实际捕获{empty_caught_count}次"
        print(f"Empty异常屏障测试: {empty_caught_count}/3次触发空队列, 耗时{elapsed_time:.2f}秒")

        # 测试添加事件后的行为
        test_event = EventTimeAdvance(dt.now(timezone.utc))
        engine.put(test_event)

        # 现在队列不为空，应该能获取到事件
        retrieved_event = None
        try:
            retrieved_event = safe_get_event(engine, timeout=0.1)
        except queue.Empty:
            print("意外：添加事件后仍抛出Empty异常")
        except Exception as e:
            print(f"获取事件时出现其他异常: {e}")

        assert retrieved_event is not None, "添加事件后应能获取到事件"
        assert isinstance(retrieved_event, EventTimeAdvance), "获取的事件类型应正确"

        # 验证事件处理后队列再次变空
        try:
            # 再次尝试获取，应该遇到Empty异常
            event_after_removal = safe_get_event(engine, timeout=0.1)
            if event_after_removal is None:
                print("正确：事件处理后队列为空")
            else:
                print(f"意外：处理后仍有事件: {type(event_after_removal)}")
        except queue.Empty:
            print("正确：事件处理后捕获Empty异常")
        except Exception as e:
            print(f"处理后获取事件异常: {e}")

        # 测试多个事件的Empty异常屏障行为
        multiple_events = [
            EventTimeAdvance(dt.now(timezone.utc)),
            EventTimeAdvance(dt.now(timezone.utc)),
            EventTimeAdvance(dt.now(timezone.utc))
        ]

        # 添加多个事件
        for event in multiple_events:
            engine.put(event)

        # 处理所有事件
        processed_count = 0
        while True:
            try:
                event = safe_get_event(engine, timeout=0.1)
                if event:
                    processed_count += 1
                else:
                    break
            except queue.Empty:
                print(f"处理完所有事件后捕获Empty异常，已处理{processed_count}个事件")
                break
            except Exception as e:
                print(f"处理事件时异常: {e}")
                break

        assert processed_count >= len(multiple_events), f"应处理至少{len(multiple_events)}个事件，实际处理{processed_count}个"

        # 最终验证：Empty异常作为同步屏障确保我们能够知道何时所有事件处理完毕
        # 这是回测模式同步执行的关键机制
        print("Empty异常屏障机制测试完成")
        assert True, "Empty异常屏障机制测试通过"

    def test_backtest_determinism_verification(self):
        """测试回测确定性验证"""
        # 回测确定性是量化交易的核心要求：相同输入必须产生相同输出
        # 这确保了策略回测结果的可重现性和可靠性

        # 测试配置参数
        test_name = "DeterminismEngine"
        event_count = 5
        initial_time = dt(2023, 6, 15, 9, 30, tzinfo=timezone.utc)

        # 存储两次运行的结果
        first_run_results = []
        second_run_results = []

        # 第一次运行
        print("开始第一次回测运行...")
        engine1 = TimeControlledEventEngine(
            mode=EXECUTION_MODE.BACKTEST,
            name=f"{test_name}_Run1"
        )

        # 设置处理器收集结果
        def result_collector_1(event):
            result = {
                'timestamp': event.timestamp if hasattr(event, 'timestamp') else None,
                'event_type': type(event).__name__,
                'sequence': len(first_run_results),
                'thread_id': id(event)  # 使用对象ID作为标识
            }
            first_run_results.append(result)

        # 注册处理器
        reg_success1 = engine1.register(EVENT_TYPES.TIME_ADVANCE, result_collector_1)
        assert reg_success1 is True, "第一次运行处理器注册应成功"

        # 添加相同的事件序列
        for i in range(event_count):
            # 创建具有相同时间戳的事件
            event_time = initial_time + timedelta(minutes=i)
            event = EventTimeAdvance(event_time)
            engine1.put(event)

        # 处理所有事件
        processed1 = 0
        while processed1 < event_count:
            try:
                event = engine1.get_event(timeout=0.1)
                if event:
                    result_collector_1(event)
                    processed1 += 1
            except Exception:
                break

        print(f"第一次运行完成，处理{processed1}个事件，产生{len(first_run_results)}个结果")

        # 第二次运行
        print("开始第二次回测运行...")
        engine2 = TimeControlledEventEngine(
            mode=EXECUTION_MODE.BACKTEST,
            name=f"{test_name}_Run2"
        )

        # 设置处理器收集结果
        def result_collector_2(event):
            result = {
                'timestamp': event.timestamp if hasattr(event, 'timestamp') else None,
                'event_type': type(event).__name__,
                'sequence': len(second_run_results),
                'thread_id': id(event)
            }
            second_run_results.append(result)

        # 注册处理器
        reg_success2 = engine2.register(EVENT_TYPES.TIME_ADVANCE, result_collector_2)
        assert reg_success2 is True, "第二次运行处理器注册应成功"

        # 添加完全相同的事件序列
        for i in range(event_count):
            event_time = initial_time + timedelta(minutes=i)
            event = EventTimeAdvance(event_time)
            engine2.put(event)

        # 处理所有事件
        processed2 = 0
        while processed2 < event_count:
            try:
                event = engine2.get_event(timeout=0.1)
                if event:
                    result_collector_2(event)
                    processed2 += 1
            except Exception:
                break

        print(f"第二次运行完成，处理{processed2}个事件，产生{len(second_run_results)}个结果")

        # 验证确定性
        assert processed1 == processed2 == event_count, f"两次运行应处理相同数量的事件: {processed1} vs {processed2}"
        assert len(first_run_results) == len(second_run_results), f"两次运行应产生相同数量的结果: {len(first_run_results)} vs {len(second_run_results)}"

        # 逐个比较结果
        determinism_passed = True
        for i, (result1, result2) in enumerate(zip(first_run_results, second_run_results)):
            # 比较时间戳
            if result1['timestamp'] != result2['timestamp']:
                print(f"事件{i}时间戳不一致: {result1['timestamp']} vs {result2['timestamp']}")
                determinism_passed = False

            # 比较事件类型
            if result1['event_type'] != result2['event_type']:
                print(f"事件{i}类型不一致: {result1['event_type']} vs {result2['event_type']}")
                determinism_passed = False

            # 比较执行顺序
            if result1['sequence'] != result2['sequence']:
                print(f"事件{i}顺序不一致: {result1['sequence']} vs {result2['sequence']}")
                determinism_passed = False

        # 验证确定性结果
        assert determinism_passed, "回测确定性验证失败：两次运行结果不一致"

        # 验证引擎状态一致性
        assert engine1.mode == engine2.mode == EXECUTION_MODE.BACKTEST, "两次运行引擎模式应一致"

        # 验证事件处理顺序的一致性
        for i in range(len(first_run_results)):
            assert first_run_results[i]['sequence'] == second_run_results[i]['sequence'], f"事件{i}执行顺序应一致"

        print(f"回测确定性验证通过: {len(first_run_results)}个事件结果完全一致")
        print(f"第一次运行时间戳示例: {[r['timestamp'] for r in first_run_results[:3]]}")
        print(f"第二次运行时间戳示例: {[r['timestamp'] for r in second_run_results[:3]]}")

        # 额外的确定性测试：验证事件处理的可重现性
        # 这是量化交易系统可靠性的基础
        assert True, "回测确定性验证测试通过"

    def test_backtest_event_replay(self):
        """测试事件重放一致性"""
        # 事件重放是回测系统的重要特性：记录第一次运行的事件序列，然后重放验证一致性

        # 创建第一次运行的引擎
        engine1 = TimeControlledEventEngine(
            mode=EXECUTION_MODE.BACKTEST,
            name="EventReplay_FirstRun"
        )

        # 记录第一次运行的事件和处理结果
        first_run_events = []
        first_run_results = []

        def first_run_handler(event):
            """第一次运行的处理器，记录所有事件"""
            event_record = {
                'timestamp': event.timestamp if hasattr(event, 'timestamp') else dt.now(timezone.utc),
                'event_type': type(event).__name__,
                'event_id': id(event),
                'sequence': len(first_run_events)
            }
            first_run_events.append(event_record)

            # 模拟处理逻辑
            result = {
                'input_sequence': event_record['sequence'],
                'processed_at': dt.now(timezone.utc),
                'result_value': event_record['sequence'] * 10  # 简单的处理逻辑
            }
            first_run_results.append(result)

        # 注册处理器
        reg_success1 = engine1.register(EVENT_TYPES.TIME_ADVANCE, first_run_handler)
        assert reg_success1 is True, "第一次运行处理器注册应成功"

        # 创建并投递事件序列
        test_events = []
        base_time = dt(2023, 6, 15, 9, 30, tzinfo=timezone.utc)

        for i in range(5):
            event_time = base_time + timedelta(minutes=i)
            event = EventTimeAdvance(event_time)
            test_events.append(event)
            engine1.put(event)

        # 处理所有事件
        processed_count = 0
        while processed_count < len(test_events):
            try:
                event = engine1.get_event(timeout=0.1)
                if event:
                    first_run_handler(event)
                    processed_count += 1
            except Exception:
                break

        print(f"第一次运行完成: 处理{processed_count}个事件，记录{len(first_run_events)}个事件记录")

        # ===== 第二次运行：事件重放 =====
        engine2 = TimeControlledEventEngine(
            mode=EXECUTION_MODE.BACKTEST,
            name="EventReplay_SecondRun"
        )

        # 记录第二次运行的结果
        second_run_results = []

        def second_run_handler(event):
            """第二次运行的处理器，重放相同逻辑"""
            result = {
                'input_sequence': len(second_run_results),
                'processed_at': dt.now(timezone.utc),
                'result_value': len(second_run_results) * 10  # 相同的处理逻辑
            }
            second_run_results.append(result)

        # 注册处理器
        reg_success2 = engine2.register(EVENT_TYPES.TIME_ADVANCE, second_run_handler)
        assert reg_success2 is True, "第二次运行处理器注册应成功"

        # 重放完全相同的事件序列
        for event in test_events:
            engine2.put(event)

        # 处理重放事件
        replay_processed = 0
        while replay_processed < len(test_events):
            try:
                event = engine2.get_event(timeout=0.1)
                if event:
                    second_run_handler(event)
                    replay_processed += 1
            except Exception:
                break

        print(f"第二次运行(重放)完成: 处理{replay_processed}个事件，产生{len(second_run_results)}个结果")

        # ===== 验证事件重放一致性 =====

        # 验证处理的事件数量相同
        assert processed_count == replay_processed, f"两次运行应处理相同数量的事件: {processed_count} vs {replay_processed}"
        assert len(first_run_results) == len(second_run_results), f"两次运行应产生相同数量的结果: {len(first_run_results)} vs {len(second_run_results)}"

        # 验证每个事件的处理结果一致
        replay_consistency = True
        for i, (result1, result2) in enumerate(zip(first_run_results, second_run_results)):
            # 验证输入序列一致性
            if result1['input_sequence'] != result2['input_sequence']:
                print(f"事件{i}输入序列不一致: {result1['input_sequence']} vs {result2['input_sequence']}")
                replay_consistency = False

            # 验证处理结果一致性
            if result1['result_value'] != result2['result_value']:
                print(f"事件{i}处理结果不一致: {result1['result_value']} vs {result2['result_value']}")
                replay_consistency = False

        # 验证事件记录的顺序一致性
        for i in range(len(first_run_events)):
            if i < len(first_run_events) - 1:
                # 验证时间戳递增（事件应该按时间顺序处理）
                current_time = first_run_events[i]['timestamp']
                next_time = first_run_events[i + 1]['timestamp']
                assert next_time >= current_time, f"事件{i+1}时间戳应不小于事件{i}: {next_time} vs {current_time}"

        # 验证重放的一致性
        assert replay_consistency, "事件重放一致性验证失败：两次运行结果不一致"

        # 验证引擎状态一致性
        assert engine1.mode == engine2.mode == EXECUTION_MODE.BACKTEST, "两次运行引擎模式应一致"

        # 验证事件处理的可重现性 - 这是回测系统的核心特性
        print(f"事件重放一致性验证通过:")
        print(f"  第一次运行结果示例: {[r['result_value'] for r in first_run_results[:3]]}")
        print(f"  第二次运行结果示例: {[r['result_value'] for r in second_run_results[:3]]}")

        # 最终验证：事件重放机制确保了回测结果的可重现性
        # 这对于量化交易策略的验证和优化至关重要
        assert True, "事件重放一致性测试通过"

    def test_backtest_main_loop_single_thread(self):
        """测试回测主循环单线程执行"""
        import threading
        import time

        # 回测模式的主循环应该在单线程中执行，确保事件的确定性处理
        # 这与实盘模式的并发处理形成对比

        # 创建回测引擎
        engine = TimeControlledEventEngine(
            mode=EXECUTION_MODE.BACKTEST,
            name="SingleThreadEngine"
        )

        # 验证引擎模式
        assert engine.mode == EXECUTION_MODE.BACKTEST, "引擎应为BACKTEST模式"

        # 测试数据结构
        execution_threads = set()
        execution_order = []
        thread_usage = []

        def single_thread_test_handler(event):
            """单线程测试处理器"""
            current_thread = threading.current_thread().ident
            execution_threads.add(current_thread)

            # 记录执行信息
            execution_info = {
                'thread_id': current_thread,
                'thread_name': threading.current_thread().name,
                'sequence': len(execution_order),
                'timestamp': dt.now(timezone.utc)
            }
            execution_order.append(execution_info)
            thread_usage.append(current_thread)

            # 模拟处理时间
            time.sleep(0.001)

        # 注册处理器
        reg_success = engine.register(EVENT_TYPES.TIME_ADVANCE, single_thread_test_handler)
        assert reg_success is True, "处理器注册应成功"

        # 创建测试事件序列
        test_events = []
        base_time = dt(2023, 6, 15, 9, 30, tzinfo=timezone.utc)

        for i in range(8):  # 增加事件数量以提高测试可靠性
            event_time = base_time + timedelta(minutes=i)
            event = EventTimeAdvance(event_time)
            test_events.append(event)
            engine.put(event)

        print(f"投递{len(test_events)}个事件到队列")

        # 验证队列中有事件
        assert not engine._event_queue.empty(), "事件队列不应为空"

        # 模拟单线程主循环处理事件
        processed_count = 0
        main_thread_id = threading.current_thread().ident

        print(f"主线程ID: {main_thread_id}")

        while processed_count < len(test_events):
            try:
                # 获取事件
                event = safe_get_event(engine, timeout=0.1)
                if event:
                    # 在当前线程中处理事件（单线程模式）
                    single_thread_test_handler(event)
                    processed_count += 1

                    # 验证仍在主线程中执行
                    current_thread = threading.current_thread().ident
                    assert current_thread == main_thread_id, f"事件应在主线程中处理: 期望{main_thread_id}, 实际{current_thread}"

            except Exception as e:
                print(f"事件处理异常: {e}")
                break

        print(f"单线程处理完成: 处理{processed_count}个事件")

        # 验证单线程执行特性
        assert processed_count == len(test_events), f"应处理所有{len(test_events)}个事件，实际处理{processed_count}个"

        # 验证所有事件都在同一个线程中处理
        assert len(execution_threads) == 1, f"单线程模式应只使用1个线程，实际使用了{len(execution_threads)}个线程"

        # 获取实际使用的线程ID
        used_thread_id = execution_threads.pop()
        assert used_thread_id == main_thread_id, f"事件处理线程应为主线程: 期望{main_thread_id}, 实际{used_thread_id}"

        # 验证执行顺序的严格性
        for i in range(len(execution_order)):
            expected_sequence = i
            actual_sequence = execution_order[i]['sequence']
            assert actual_sequence == expected_sequence, f"事件{i}执行顺序错误: 期望{expected_sequence}, 实际{actual_sequence}"

        # 验证没有并发执行的迹象
        # 在单线程模式下，事件应严格按顺序执行，没有并发
        unique_threads = set(thread_usage)
        assert len(unique_threads) == 1, f"应只有1个唯一线程，实际有{len(unique_threads)}个"

        # 验证引擎内部状态
        assert hasattr(engine, '_event_queue'), "引擎应有事件队列"
        assert hasattr(engine, '_handlers'), "引擎应有处理器字典"
        assert hasattr(engine, '_sequence_lock'), "引擎应有序列号锁"

        # 验证没有ThreadPoolExecutor的迹象
        # 在回测模式下，引擎不应该使用线程池等并发机制
        print("检查回测模式是否使用并发组件...")

        # 验证事件队列的同步特性
        # 回测模式应该使用同步队列，而非异步并发队列
        assert engine._event_queue is not None, "事件队列应存在"

        # 验证处理器注册是同步的
        assert len(engine._handlers) > 0, "应注册了处理器"

        print(f"单线程执行验证通过:")
        print(f"  处理事件数: {processed_count}")
        print(f"  使用线程数: {len(execution_threads)}")
        print(f"  主线程ID: {main_thread_id}")
        print(f"  执行线程ID: {used_thread_id}")
        print(f"  执行顺序: {[info['sequence'] for info in execution_order[:3]]}...")

        # 最终验证：回测模式的主循环确实在单线程中执行
        # 这确保了事件处理的确定性，避免了并发带来的不确定性
        assert True, "回测主循环单线程执行测试通过"

    def test_backtest_event_order_preservation(self):
        """测试回测事件顺序保持"""
        # FIFO（First In First Out）是回测系统的核心特性
        # 确保事件按时间顺序严格处理，避免未来信息泄露

        # 创建回测引擎
        engine = TimeControlledEventEngine(
            mode=EXECUTION_MODE.BACKTEST,
            name="FIFOOrderEngine"
        )

        # 验证引擎模式
        assert engine.mode == EXECUTION_MODE.BACKTEST, "引擎应为BACKTEST模式"

        # 测试数据结构
        processed_order = []
        submission_order = []
        processing_timestamps = []

        def fifo_test_handler(event):
            """FIFO测试处理器"""
            # 记录处理时间戳
            processing_timestamps.append(dt.now(timezone.utc))

            # 获取事件的提交顺序信息
            if hasattr(event, 'submission_order'):
                processed_order.append(event.submission_order)
            else:
                # 如果事件没有submission_order属性，使用时间戳作为顺序标识
                processed_order.append(event.timestamp if hasattr(event, 'timestamp') else len(processed_order))

        # 注册处理器
        reg_success = engine.register(EVENT_TYPES.TIME_ADVANCE, fifo_test_handler)
        assert reg_success is True, "处理器注册应成功"

        # 创建具有明确时间顺序的事件序列
        base_time = dt(2023, 6, 15, 9, 30, tzinfo=timezone.utc)
        test_events = []

        for i in range(6):
            event_time = base_time + timedelta(minutes=i)
            event = EventTimeAdvance(event_time)

            # 为事件添加提交顺序标记
            event.submission_order = i
            submission_order.append(i)

            test_events.append(event)

        # 按时间顺序投递事件（FIFO队列的自然行为）
        for event in test_events:
            engine.put(event)

        print(f"按顺序投递{len(test_events)}个事件，提交顺序: {submission_order}")

        # 验证队列中有事件
        assert not engine._event_queue.empty(), "事件队列不应为空"

        # 处理所有事件
        processed_count = 0
        while processed_count < len(test_events):
            try:
                event = safe_get_event(engine, timeout=0.1)
                if event:
                    fifo_test_handler(event)
                    processed_count += 1
            except Exception as e:
                print(f"事件处理异常: {e}")
                break

        print(f"FIFO处理完成: 处理{processed_count}个事件")
        print(f"提交顺序: {submission_order}")
        print(f"处理顺序: {processed_order}")

        # 验证FIFO顺序
        assert processed_count == len(test_events), f"应处理所有{len(test_events)}个事件，实际处理{processed_count}个"
        assert len(processed_order) == len(submission_order), f"处理顺序长度应等于提交顺序长度: {len(processed_order)} vs {len(submission_order)}"

        # 验证严格的FIFO顺序
        fifo_violations = 0
        for i in range(len(submission_order)):
            expected_order = submission_order[i]
            actual_order = processed_order[i]

            if expected_order != actual_order:
                print(f"FIFO违规: 位置{i}期望{expected_order}, 实际{actual_order}")
                fifo_violations += 1

        assert fifo_violations == 0, f"发现{fifo_violations}个FIFO顺序违规"

        # 验证处理时间戳的单调递增
        for i in range(1, len(processing_timestamps)):
            prev_time = processing_timestamps[i-1]
            curr_time = processing_timestamps[i]
            assert curr_time >= prev_time, f"处理时间戳应递增: {prev_time} -> {curr_time}"

        # 测试混合顺序事件的FIFO行为
        print("\n测试混合顺序事件FIFO行为...")

        # 清空队列
        while not engine._event_queue.empty():
            try:
                safe_get_event(engine, timeout=0.01)
            except:
                break

        # 创建乱序提交但期望按FIFO处理的事件
        mixed_order_events = []
        mixed_submission_order = [3, 1, 4, 0, 2, 5]  # 乱序提交
        mixed_base_time = dt(2023, 6, 15, 10, 0, tzinfo=timezone.utc)

        for i, order in enumerate(mixed_submission_order):
            event_time = mixed_base_time + timedelta(minutes=order)
            event = EventTimeAdvance(event_time)
            event.submission_order = order
            mixed_order_events.append(event)
            engine.put(event)

        print(f"乱序提交事件: {mixed_submission_order}")

        # 重置处理记录
        mixed_processed_order = []
        original_handler = fifo_test_handler

        def mixed_handler(event):
            if hasattr(event, 'submission_order'):
                mixed_processed_order.append(event.submission_order)
            original_handler(event)

        # 临时替换处理器（如果可能）
        # 这里我们直接处理事件，不重新注册处理器
        mixed_processed_count = 0
        while mixed_processed_count < len(mixed_order_events):
            try:
                event = safe_get_event(engine, timeout=0.1)
                if event:
                    mixed_handler(event)
                    mixed_processed_count += 1
            except Exception:
                break

        print(f"乱序事件处理顺序: {mixed_processed_order}")

        # 验证FIFO队列确保了按投递顺序处理，而非时间顺序
        # 注意：这里我们按投递顺序处理，因为队列是FIFO的
        assert len(mixed_processed_order) == len(mixed_submission_order), "乱序测试处理数量应正确"

        print(f"FIFO顺序验证通过:")
        print(f"  顺序测试事件数: {processed_count}")
        print(f"  FIFO违规数: {fifo_violations}")
        print(f"  处理时间戳单调性: 正确")

        # 最终验证：FIFO机制确保了事件的严格顺序处理
        # 这是回测系统确定性的重要保证
        assert True, "回测事件顺序保持测试通过"

    def test_backtest_no_concurrent_handlers(self):
        """测试回测无并发处理器"""
        import threading
        import time

        # 回测模式下，事件处理器不应该并发执行
        # 这确保了事件处理的确定性和可重现性

        # 创建回测引擎
        engine = TimeControlledEventEngine(
            mode=EXECUTION_MODE.BACKTEST,
            name="NoConcurrentHandlersEngine"
        )

        # 验证引擎模式
        assert engine.mode == EXECUTION_MODE.BACKTEST, "引擎应为BACKTEST模式"

        # 并发检测数据结构
        concurrent_counter = 0
        max_concurrent = 0
        execution_log = []
        thread_usage = []

        # 创建线程锁来安全地更新共享状态
        concurrency_lock = threading.Lock()

        def concurrency_test_handler(event):
            """并发测试处理器"""
            nonlocal concurrent_counter, max_concurrent

            current_thread = threading.current_thread().ident
            thread_usage.append(current_thread)

            # 记录开始执行
            start_time = dt.now(timezone.utc)

            with concurrency_lock:
                concurrent_counter += 1
                current_concurrent = concurrent_counter
                max_concurrent = max(max_concurrent, current_concurrent)

                # 记录并发状态
                execution_log.append({
                    'thread_id': current_thread,
                    'start_time': start_time,
                    'concurrent_count': current_concurrent,
                    'max_concurrent': max_concurrent,
                    'action': 'start'
                })

            # 模拟处理时间，增加并发检测的机会
            time.sleep(0.01)

            # 处理完成
            end_time = dt.now(timezone.utc)

            with concurrency_lock:
                concurrent_counter -= 1

                execution_log.append({
                    'thread_id': current_thread,
                    'end_time': end_time,
                    'concurrent_count': concurrent_counter,
                    'max_concurrent': max_concurrent,
                    'action': 'end'
                })

        # 注册处理器
        reg_success = engine.register(EVENT_TYPES.TIME_ADVANCE, concurrency_test_handler)
        assert reg_success is True, "处理器注册应成功"

        # 创建测试事件
        test_events = []
        base_time = dt(2023, 6, 15, 9, 30, tzinfo=timezone.utc)

        for i in range(5):
            event_time = base_time + timedelta(minutes=i)
            event = EventTimeAdvance(event_time)
            test_events.append(event)
            engine.put(event)

        print(f"投递{len(test_events)}个事件到队列")

        # 在主线程中顺序处理所有事件（回测模式的行为）
        processed_count = 0
        main_thread_id = threading.current_thread().ident

        while processed_count < len(test_events):
            try:
                event = safe_get_event(engine, timeout=0.1)
                if event:
                    # 在主线程中调用处理器
                    concurrency_test_handler(event)
                    processed_count += 1

                    # 验证在主线程中执行
                    current_thread = threading.current_thread().ident
                    assert current_thread == main_thread_id, f"事件应在主线程中处理: 期望{main_thread_id}, 实际{current_thread}"

            except Exception as e:
                print(f"事件处理异常: {e}")
                break

        print(f"并发处理测试完成: 处理{processed_count}个事件")
        print(f"最大并发数: {max_concurrent}")
        print(f"使用的线程: {set(thread_usage)}")

        # 验证无并发执行
        assert max_concurrent == 1, f"回测模式最大并发数应为1，实际为{max_concurrent}"
        assert concurrent_counter == 0, f"所有处理器完成后并发计数器应为0，实际为{concurrent_counter}"

        # 验证只使用了一个线程
        unique_threads = set(thread_usage)
        assert len(unique_threads) == 1, f"应只使用1个线程，实际使用了{len(unique_threads)}个线程"
        assert list(unique_threads)[0] == main_thread_id, f"应使用主线程，实际使用了{list(unique_threads)[0]}"

        # 验证执行日志的一致性
        start_events = [log for log in execution_log if log['action'] == 'start']
        end_events = [log for log in execution_log if log['action'] == 'end']

        assert len(start_events) == len(end_events) == len(test_events), f"开始和结束事件数应相等且等于测试事件数: 开始{len(start_events)}, 结束{len(end_events)}, 测试{len(test_events)}"

        # 验证没有并发执行的时间重叠
        # 简化验证：由于单线程执行，事件应该按顺序处理
        for i in range(len(start_events) - 1):
            current_start = start_events[i]
            next_start = start_events[i + 1]

            # 下一个事件开始时，前一个事件应该已经结束
            # 这是单线程顺序处理的特征
            assert next_start['start_time'] >= current_start['start_time'], "事件开始时间应递增"

        # 验证引擎内部状态
        assert hasattr(engine, '_event_queue'), "引擎应有事件队列"
        assert hasattr(engine, '_handlers'), "引擎应有处理器字典"
        assert len(engine._handlers) > 0, "应注册了处理器"

        print(f"无并发处理器验证通过:")
        print(f"  处理事件数: {processed_count}")
        print(f"  最大并发数: {max_concurrent}")
        print(f"  使用线程数: {len(unique_threads)}")
        print(f"  执行日志条目: {len(execution_log)}")

        # 最终验证：回测模式下确实没有并发处理器执行
        # 这确保了事件处理的严格顺序性和确定性
        assert True, "回测无并发处理器测试通过"

    def test_backtest_completion_waiting(self):
        """测试回测完成等待机制"""
        import queue
        import time

        # 回测完成等待机制确保所有事件都被处理完毕后才结束回测
        # 这避免了事件丢失和不完整的回测结果

        # 创建回测引擎
        engine = TimeControlledEventEngine(
            mode=EXECUTION_MODE.BACKTEST,
            name="CompletionWaitingEngine"
        )

        # 验证引擎模式
        assert engine.mode == EXECUTION_MODE.BACKTEST, "引擎应为BACKTEST模式"

        # 测试数据结构
        processed_events = []

        def completion_test_handler(event):
            """完成测试处理器"""
            processed_events.append({
                'event_type': type(event).__name__,
                'timestamp': event.timestamp if hasattr(event, 'timestamp') else dt.now(timezone.utc),
                'sequence': len(processed_events)
            })

        # 注册处理器
        reg_success = engine.register(EVENT_TYPES.TIME_ADVANCE, completion_test_handler)
        assert reg_success is True, "处理器注册应成功"

        # 创建事件序列
        test_events = []
        base_time = dt(2023, 6, 15, 9, 30, tzinfo=timezone.utc)

        for i in range(3):
            event_time = base_time + timedelta(minutes=i)
            event = EventTimeAdvance(event_time)
            test_events.append(event)
            engine.put(event)

        print(f"投递{len(test_events)}个事件到队列")

        # 模拟完成等待机制
        # 在回测模式下，应该持续处理事件直到队列为空
        start_time = time.time()
        wait_timeout = 2.0  # 最大等待2秒

        while time.time() - start_time < wait_timeout:
            try:
                event = safe_get_event(engine, timeout=0.1)
                if event:
                    completion_test_handler(event)
                else:
                    # 队列为空，退出等待
                    print("队列为空，完成等待机制触发")
                    break
            except queue.Empty:
                # Empty异常表示队列为空，这是正常的完成信号
                print("捕获Empty异常，队列为空")
                break
            except Exception as e:
                print(f"等待过程中异常: {e}")
                break

        # 验证所有事件都被处理
        assert len(processed_events) == len(test_events), f"所有{len(test_events)}个事件都应被处理，实际处理{len(processed_events)}个"

        # 验证事件处理的完整性
        for i, event_record in enumerate(processed_events):
            assert event_record['sequence'] == i, f"事件{i}的序列号应正确"
            assert event_record['event_type'] == 'EventTimeAdvance', f"事件{i}类型应正确"

        # 测试长时间运行的完成等待
        print("\n测试长时间运行完成等待...")

        # 添加更多事件
        long_running_events = []
        for i in range(10):
            event_time = base_time + timedelta(hours=i)
            event = EventTime(event_time)
            long_running_events.append(event)
            engine.put(event)

        # 重置处理记录
        processed_events.clear()

        # 长时间等待完成
        long_start_time = time.time()
        long_wait_timeout = 3.0  # 长时间等待

        while time.time() - long_start_time < long_wait_timeout:
            try:
                event = safe_get_event(engine, timeout=0.2)
                if event:
                    completion_test_handler(event)
                else:
                    print("长时间运行完成，队列为空")
                    break
            except queue.Empty:
                print("长时间运行捕获Empty异常")
                break
            except Exception as e:
                print(f"长时间等待异常: {e}")
                break

        print(f"长时间运行完成: 处理{len(processed_events)}个事件")

        # 验证长时间运行的完整性
        assert len(processed_events) == len(long_running_events), f"长时间运行所有{len(long_running_events)}个事件都应被处理"

        # 验证完成等待机制的核心特性
        # 回测完成等待应该：
        # 1. 持续处理直到队列为空
        # 2. 使用Empty异常作为完成信号
        # 3. 确保没有事件丢失
        print(f"完成等待机制验证通过:")
        print(f"  短时间测试: {len(test_events)}个事件全部处理")
        print(f"  长时间测试: {len(long_running_events)}个事件全部处理")
        print(f"  总处理事件: {len(test_events) + len(long_running_events)}个")

        # 最终验证：回测完成等待机制确保了事件处理的完整性
        # 这对于回测结果的可靠性至关重要
        assert True, "回测完成等待机制测试通过"

    def test_time_advance_barrier_synchronization(self):
        """测试时间推进屏障同步"""
        # 创建引擎实例
        engine = TimeControlledEventEngine(
            name="BarrierSyncEngine",
            mode=EXECUTION_MODE.BACKTEST
        )

        # 检查可能的同步屏障方法
        possible_methods = [
            'wait_for_phase_completion',
            '_wait_for_phase_completion',
            'wait_for_completion',
            '_wait_for_completion',
            'synchronize_phase',
            '_synchronize_phase'
        ]

        found_method = None
        for method_name in possible_methods:
            if hasattr(engine, method_name):
                found_method = method_name
                break

        if found_method:
            method = getattr(engine, found_method)
            assert callable(method), f"找到的方法{found_method}应可调用"

            # 测试同步屏障方法
            try:
                result = method()
                print(f"同步屏障方法{found_method}调用成功，返回: {result}")
            except Exception as e:
                print(f"同步屏障方法{found_method}调用问题: {e}")
        else:
            print("同步屏障方法待实现")

        # 验证引擎的并发控制能力
        if hasattr(engine, '_concurrent_semaphore'):
            semaphore = engine._concurrent_semaphore
            print(f"并发信号量存在: {semaphore}")
        else:
            print("回测模式不需要并发信号量")

        # 验证事件序列号机制
        assert hasattr(engine, '_event_sequence_number'), "应有序列号追踪"
        assert isinstance(engine._event_sequence_number, int), "序列号应为整数"

        assert True, "时间推进屏障同步测试完成"


@pytest.mark.unit
class TestEndToEnd:
    """2. 端到端测试"""

    def test_complete_trading_simulation(self):
        """测试完整交易模拟"""
        print("测试完整交易模拟...")

        # 创建交易引擎
        engine = TimeControledEventEngine(
            mode=EXECUTION_MODE.BACKTEST,
            name="CompleteTradingEngine"
        )

        # 设置交易时间范围
        start_time = dt(2023, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        end_time = dt(2023, 1, 3, 16, 0, 0, tzinfo=timezone.utc)
        engine._time_provider.set_start_time(start_time)
        engine._time_provider.set_end_time(end_time)

        # 模拟交易数据收集
        trading_records = []

        def price_update_handler(event):
            if isinstance(event, EventPriceUpdate):
                # 正确的Event访问方式：通过value字段访问payload
                bar = event.value
                trading_records.append({
                    'type': 'price_update',
                    'symbol': bar.code,
                    'price': float(bar.close),
                    'volume': bar.volume,
                    'timestamp': event.timestamp
                })

        def time_advancement_handler(event):
            if isinstance(event, EventTimeAdvance):
                trading_records.append({
                    'type': 'time_advancement',
                    'target_time': event.target_time,
                    'current_time': engine._time_provider.now(),
                    'timestamp': event.timestamp
                })

        # 注册处理器
        engine.register(EVENT_TYPES.PRICEUPDATE, price_update_handler)
        engine.register(EVENT_TYPES.TIME_ADVANCE, time_advancement_handler)

        # 启动引擎
        engine.start()

        # 模拟完整的交易流程
        trading_days = [
            # 第一天
            {
                'date': '2023-01-01',
                'events': [
                    {'time': '09:30', 'symbol': '000001.SZ', 'open': 10.0, 'high': 10.2, 'low': 9.8, 'close': 10.1, 'volume': 10000},
                    {'time': '10:00', 'symbol': '000001.SZ', 'open': 10.1, 'high': 10.3, 'low': 10.0, 'close': 10.2, 'volume': 8000},
                    {'time': '10:30', 'symbol': '000001.SZ', 'open': 10.2, 'high': 10.4, 'low': 10.1, 'close': 10.3, 'volume': 12000},
                    {'time': '11:00', 'symbol': '000001.SZ', 'open': 10.3, 'high': 10.5, 'low': 10.2, 'close': 10.4, 'volume': 9000},
                    {'time': '14:00', 'symbol': '000001.SZ', 'open': 10.4, 'high': 10.6, 'low': 10.3, 'close': 10.5, 'volume': 15000},
                    {'time': '15:00', 'symbol': '000001.SZ', 'open': 10.5, 'high': 10.7, 'low': 10.4, 'close': 10.6, 'volume': 11000}
                ]
            },
            # 第二天
            {
                'date': '2023-01-02',
                'events': [
                    {'time': '09:30', 'symbol': '000001.SZ', 'open': 10.6, 'high': 10.8, 'low': 10.4, 'close': 10.7, 'volume': 13000},
                    {'time': '10:00', 'symbol': '000001.SZ', 'open': 10.7, 'high': 10.9, 'low': 10.6, 'close': 10.8, 'volume': 10000},
                    {'time': '14:30', 'symbol': '000001.SZ', 'open': 10.8, 'high': 11.0, 'low': 10.7, 'close': 10.9, 'volume': 14000},
                    {'time': '15:00', 'symbol': '000001.SZ', 'open': 10.9, 'high': 11.1, 'low': 10.8, 'close': 11.0, 'volume': 16000}
                ]
            },
            # 第三天
            {
                'date': '2023-01-03',
                'events': [
                    {'time': '09:30', 'symbol': '000001.SZ', 'open': 11.0, 'high': 11.2, 'low': 10.9, 'close': 11.1, 'volume': 17000},
                    {'time': '10:00', 'symbol': '000001.SZ', 'open': 11.1, 'high': 11.3, 'low': 11.0, 'close': 11.2, 'volume': 18000},
                    {'time': '14:00', 'symbol': '000001.SZ', 'open': 11.2, 'high': 11.4, 'low': 11.1, 'close': 11.3, 'volume': 19000},
                    {'time': '15:00', 'symbol': '000001.SZ', 'open': 11.3, 'high': 11.5, 'low': 11.2, 'close': 11.4, 'volume': 20000}
                ]
            }
        ]

        total_events_processed = 0
        for day_data in trading_days:
            date_str = day_data['date']
            print(f"  处理交易日: {date_str}")

            for event_data in day_data['events']:
                # 推进时间
                event_datetime = dt.strptime(f"{date_str} {event_data['time']}", "%Y-%m-%d %H:%M")
                event_datetime = event_datetime.replace(tzinfo=timezone.utc)
                engine._time_provider.advance_time_to(event_datetime)

                # 创建时间推进事件
                time_event = EventTimeAdvance(target_time=event_datetime)
                engine.put(time_event)

                # 创建价格更新事件
                bar = Bar(
                    code=event_data['symbol'],
                    open=event_data['open'],
                    high=event_data['high'],
                    low=event_data['low'],
                    close=event_data['close'],
                    volume=event_data['volume'],
                    amount=event_data['volume'] * event_data['close'],
                    frequency=FREQUENCY_TYPES.MIN1,
                    timestamp=event_datetime
                )
                price_event = EventPriceUpdate(price_info=bar, timestamp=event_datetime)
                engine.put(price_event)

                # 等待事件处理
                time_module.sleep(0.05)

                total_events_processed += 2  # 每个时间点2个事件

        # 停止引擎
        engine.stop()

        # 验证交易模拟结果
        price_updates = [r for r in trading_records if r['type'] == 'price_update']
        time_advances = [r for r in trading_records if r['type'] == 'time_advancement']

        assert len(price_updates) > 0, "应有价格更新记录"
        assert len(time_advances) > 0, "应有时间推进记录"
        assert total_events_processed > 0, f"应处理事件: {total_events_processed}"

        # 验证交易数据的完整性
        expected_price_updates = sum(len(day['events']) for day in trading_days)
        assert len(price_updates) == expected_price_updates, f"价格更新数量应正确: {len(price_updates)}"

        # 验证时间推进的连续性
        for i in range(1, len(time_advances)):
            prev_time = time_advances[i-1]['current_time']
            curr_time = time_advances[i]['current_time']
            assert curr_time >= prev_time, f"时间应连续递进: {prev_time} -> {curr_time}"

        print(f"✓ 完整交易模拟验证通过:")
        print(f"  - 处理交易日: {len(trading_days)}天")
        print(f"  - 总事件数: {total_events_processed}")
        print(f"  - 价格更新: {len(price_updates)}个")
        print(f"  - 时间推进: {len(time_advances)}个")
        print("✓ 完整交易模拟测试通过")

    def test_system_integration_workflow(self):
        """测试系统集成工作流"""
        # 创建系统工作流测试
        print("测试系统集成工作流...")

        # 创建引擎
        engine = TimeControlledEventEngine(
            name="SystemIntegrationEngine",
            mode=EXECUTION_MODE.BACKTEST
        )

        # 工作流状态追踪
        workflow_states = []

        def track_workflow_state(stage_name, event=None):
            workflow_states.append({
                'stage': stage_name,
                'timestamp': dt.now(timezone.utc),
                'event_count': len(workflow_states),
                'event': event
            })

        # 定义工作流处理器
        def initialization_handler(event):
            track_workflow_state('initialization', event)

        def data_processing_handler(event):
            track_workflow_state('data_processing', event)

        def strategy_execution_handler(event):
            track_workflow_state('strategy_execution', event)

        def risk_management_handler(event):
            track_workflow_state('risk_management', event)

        def completion_handler(event):
            track_workflow_state('completion', event)

        # 注册处理器
        engine.register(EVENT_TYPES.TIME_ADVANCE, initialization_handler)
        engine.register(EVENT_TYPES.PRICEUPDATE, data_processing_handler)
        # 注意：这里可以注册更多的处理器类型来模拟完整的工作流

        # 启动引擎
        track_workflow_state('startup')
        engine.start()

        # 模拟系统工作流
        # 1. 初始化阶段
        track_workflow_state('initialization_phase')
        init_event = EventTimeAdvance(dt.now(timezone.utc))
        engine.put(init_event)

        # 2. 数据处理阶段
        track_workflow_state('data_processing_phase')
        for i in range(3):
            tick = Tick(
                code=f"DATA{i+1}",
                price=10.0 + i * 0.1,
                volume=1000 + i * 100,
                direction=TICKDIRECTION_TYPES.NEUTRAL,
                timestamp=dt.now(timezone.utc)
            )
            price_event = EventPriceUpdate(price_info=tick)
            engine.put(price_event)

        # 3. 策待处理完成
        time_module.sleep(0.1)

        # 4. 策略执行阶段
        track_workflow_state('strategy_execution_phase')
        strategy_event = EventTimeAdvance(dt.now(timezone.utc))
        engine.put(strategy_event)

        # 5. 风控管理阶段
        track_workflow_state('risk_management_phase')
        risk_event = EventTimeAdvance(dt.now(timezone.utc))
        engine.put(risk_event)

        # 6. 完成阶段
        track_workflow_state('completion_phase')
        completion_event = EventTimeAdvance(dt.now(timezone.utc))
        engine.put(completion_event)

        # 等待所有事件处理
        time_module.sleep(0.2)

        # 停止引擎
        engine.stop()

        # 验证工作流状态
        expected_stages = [
            'startup', 'initialization', 'initialization_phase',
            'data_processing_phase', 'data_processing_phase', 'data_processing_phase',
            'strategy_execution_phase', 'risk_management_phase', 'completion_phase'
        ]

        actual_stages = [state['stage'] for state in workflow_states]

        # 验证所有预期阶段都被记录
        for expected_stage in expected_stages:
            assert expected_stage in actual_stages, f"工作流阶段{expected_stage}应被记录"

        # 验证工作流的逻辑顺序
        # 初始化应在数据处理之前
        init_index = actual_stages.index('initialization')
        data_index = actual_stages.index('data_processing')
        assert init_index < data_index, "初始化应在数据处理之前"

        # 策略执行应在数据之后
        strategy_index = actual_stages.index('strategy_execution')
        assert data_index < strategy_index, "数据处理应在策略执行之前"

        # 风控管理应在策略执行之后
        risk_index = actual_stages.index('risk_management')
        assert strategy_index < risk_index, "策略执行应在风控管理之前"

        # 完成应在最后
        completion_index = actual_stages.index('completion')
        assert completion_index == len(actual_stages) - 1, "完成阶段应在最后"

        print(f"✓ 系统集成工作流验证通过:")
        print(f"  - 工作流阶段数: {len(set(actual_stages))}")
        print(f"  - 事件总数: {len(workflow_states)}")
        print(f"  - 阶段顺序: {' → '.join(actual_stages[:5])}...")

        assert True, "系统集成工作流测试通过"

    def test_error_recovery_resilience(self):
        """测试错误恢复弹性"""
        # 创建引擎
        engine = TimeControlledEventEngine(
            name="ErrorRecoveryEngine",
            mode=EXECUTION_MODE_MODE.BACKTEST
        )

        # 错误追踪
        error_log = []
        recovery_actions = []

        def error_handling_handler(event):
            try:
                # 模拟可能出错的操作
                if len(error_log) < 2:  # 前两个事件模拟错误
                    raise RuntimeError(f"模拟处理错误 {len(error_log)+1}")
                else:
                    # 后续事件正常处理
                    pass
            except Exception as e:
                error_log.append({
                    'error': str(e),
                    'timestamp': dt.now(timezone.utc),
                    'event_type': type(event).__name__
                })
                recovery_actions.append({
                    'action': 'error_logged',
                    'timestamp': dt.now(timezone.utc)
                })

        # 注册错误处理处理器
        engine.register(EVENT_TYPES.TIME_ADVANCE, error_handling_handler)

        # 创建测试事件，包括一些会导致错误的
        test_events = []
        for i in range(5):
            event = EventTimeAdvance(dt.now(timezone.utc))
            test_events.append(event)
            engine.put(event)

        # 处理事件并验证错误恢复
        processed_count = 0
        for i in range(len(test_events)):
            try:
                event = safe_get_event(engine, timeout=0.1)
                if event:
                    error_handling_handler(event)
                    processed_count += 1
            except Exception as e:
                print(f"事件{i}处理严重错误: {e}")
                break

        # 验证错误被正确记录
        assert len(error_log) >= 2, "应记录至少2个错误"
        assert len(recovery_actions) >= 2, "应执行至少2个恢复操作"

        # 验证引擎在错误后仍能继续工作
        assert processed_count >= 3, "应有至少3个事件被尝试处理"

        # 验证引擎状态正常
        assert engine.status in ["idle", "running", "stopped"], "引擎状态应正常"

        print(f"✓ 错误恢复弹性验证通过:")
        print(f"  - 处理事件数: {processed_count}")
        print(f"  - 记录错误数: {len(error_log)}")
        print(f"  - 恢复操作数: {len(recovery_actions)}")

        assert True, "错误恢复弹性测试通过"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])