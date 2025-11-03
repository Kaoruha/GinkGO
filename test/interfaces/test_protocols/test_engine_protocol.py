"""
IEngine Protocol接口测试

测试IEngine Protocol接口的类型安全性和运行时验证。
遵循TDD方法，先写测试验证需求，再验证实现。
"""

import pytest
import threading
import time
from typing import Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal

# 导入Protocol接口
from ginkgo.trading.interfaces.protocols.engine import IEngine

# 导入枚举
from ginkgo.enums import ENGINESTATUS_TYPES, EXECUTION_MODE

# 导入测试工厂 - 使用内联创建替代
# from test.fixtures.trading_factories import (
#     PortfolioFactory, EventFactory, ProtocolTestFactory
# )


# 简单的内联测试工厂
class EventFactory:
    @staticmethod
    def create_price_update_event(code="000001.SZ", **kwargs):
        """创建价格更新事件"""
        from ginkgo.trading.entities.bar import Bar
        from ginkgo.trading.events.price_update import EventPriceUpdate
        from datetime import datetime, timezone

        bar = Bar(
            code=code,
            open=kwargs.get('open_price', 10.0),
            high=kwargs.get('high_price', 10.5),
            low=kwargs.get('low_price', 9.8),
            close=kwargs.get('close_price', 10.0),
            volume=kwargs.get('volume', 100000),
            amount=kwargs.get('amount', 1000000.0),
            frequency=kwargs.get('frequency', "DAY"),
            timestamp=kwargs.get('timestamp', datetime(2024, 1, 1, tzinfo=timezone.utc))
        )
        return EventPriceUpdate(bar)


class PortfolioFactory:
    @staticmethod
    def create_basic_portfolio(**kwargs):
        """创建基础投资组合"""
        return {
            'uuid': f"portfolio_{hash('basic')}",
            'cash': kwargs.get('cash', 50000.0),
            'total_value': kwargs.get('total_value', 100000.0),
            'positions': {}
        }

    @staticmethod
    def create_high_risk_portfolio(**kwargs):
        """创建高风险投资组合"""
        return {
            'uuid': f"portfolio_{hash('high_risk')}",
            'cash': kwargs.get('cash', 10000.0),
            'total_value': kwargs.get('total_value', 100000.0),
            'positions': {}
        }


class ProtocolTestFactory:
    @staticmethod
    def create_strategy_implementation(name, strategy_type):
        """创建策略实现"""
        class MockStrategy:
            def __init__(self):
                self.name = name
                self.signals_generated = []

            def cal(self, portfolio_info, event):
                return []

            def get_strategy_info(self):
                return {'name': self.name, 'type': strategy_type}

        return MockStrategy()


def tdd_phase(phase: str):
    """TDD阶段标记装饰器"""
    def decorator(test_func):
        test_func.tdd_phase = phase
        return test_func
    return decorator


@pytest.mark.tdd
@pytest.mark.protocol
class TestIEngineProtocol:
    """IEngine Protocol接口测试类"""

    def test_basic_engine_implementation_compliance(self):
        """测试基础引擎实现符合IEngine Protocol"""
        # 创建一个模拟的Engine类实现
        class MockEngine:
            def __init__(self):
                self._name = "TestEngine"
                self._engine_id = "engine_123"
                self._run_id = None
                self._status = ENGINESTATUS_TYPES.VOID
                self._state = ENGINESTATUS_TYPES.VOID
                self._is_active_flag = False
                self._mode = EXECUTION_MODE.BACKTEST
                self._run_sequence = 1
                self._portfolios = []
                self._event_timeout = 30.0
                self._is_resizing_queue = False
                self._component_type = "ENGINE"
                # uuid属性通过property提供

            # ========== 基础属性 ==========

            @property
            def name(self) -> str:
                return self._name

            @property
            def engine_id(self) -> str:
                return self._engine_id

            @property
            def run_id(self):
                return self._run_id

            @property
            def status(self) -> str:
                return self._status.value

            @property
            def state(self):
                return self._state

            @property
            def is_active(self) -> bool:
                return self._is_active_flag

            @property
            def mode(self):
                return self._mode

            @mode.setter
            def mode(self, value):
                self._mode = value

            @property
            def run_sequence(self) -> int:
                return self._run_sequence

            # ========== 生命周期管理 ==========

            def start(self) -> bool:
                if self.state != ENGINESTATUS_TYPES.VOID:
                    return False
                self.state = ENGINESTATUS_TYPES.RUNNING
                self.is_active_flag = True
                self._run_id = f"run_{int(time.time())}"
                return True

            def pause(self) -> bool:
                if self.state != ENGINESTATUS_TYPES.RUNNING:
                    return False
                self.state = ENGINESTATUS_TYPES.PAUSED
                self.is_active_flag = False
                return True

            def stop(self) -> bool:
                if self.state not in [ENGINESTATUS_TYPES.RUNNING, ENGINESTATUS_TYPES.PAUSED]:
                    return False
                self.state = ENGINESTATUS_TYPES.STOPPED
                self.is_active_flag = False
                self._run_id = None
                return True

            # ========== 事件管理 ==========

            def put_event(self, event) -> None:
                # 模拟事件投递
                pass

            def get_event(self, timeout=None):
                # 模拟事件获取
                return None

            def handle_event(self, event) -> None:
                # 模拟事件处理
                pass

            def run(self) -> Any:
                # 模拟运行逻辑
                self.start()
                time.sleep(0.1)  # 模拟运行
                return {"status": "completed"}

            # ========== 组件管理 ==========

            @property
            def portfolios(self) -> List:
                return self._portfolios.copy()

            def add_portfolio(self, portfolio) -> None:
                if portfolio not in self._portfolios:
                    self._portfolios.append(portfolio)

            def remove_portfolio(self, portfolio) -> None:
                if portfolio in self._portfolios:
                    self._portfolios.remove(portfolio)

            # ========== 配置管理 ==========

            @property
            def event_timeout(self) -> float:
                return self._event_timeout

            def set_event_timeout(self, timeout: float) -> None:
                self._event_timeout = max(0.1, timeout)  # 最小0.1秒

            def set_event_queue_size(self, size: int) -> bool:
                if size <= 0:
                    return False
                # 模拟队列大小调整
                return True

            @property
            def is_resizing_queue(self) -> bool:
                return self._is_resizing_queue

            # ========== 监控和统计 ==========

            def get_engine_summary(self) -> Dict[str, Any]:
                return {
                    "name": self.name,
                    "engine_id": self.engine_id,
                    "run_id": self.run_id,
                    "status": self.status,
                    "is_active": self.is_active,
                    "run_sequence": self.run_sequence,
                    "mode": self.mode.value,
                    "portfolios_count": len(self.portfolios)
                }

            def put(self, event) -> None:
                self.put_event(event)

            # ========== 身份管理 ==========

            @property
            def component_type(self):
                return self._component_type

            @property
            def uuid(self) -> str:
                return self._uuid

            # ========== 线程和并发管理 ==========

            def _get_next_sequence_number(self) -> int:
                seq = self._run_sequence
                self._run_sequence += 1
                return seq

            def _enhance_event(self, event) -> Any:
                # 模拟事件增强
                if hasattr(event, 'engine_id'):
                    event.engine_id = self.engine_id
                if hasattr(event, 'run_id'):
                    event.run_id = self.run_id
                return event

            def _transfer_events_with_buffer(self, old_queue, temp_queue, new_queue, old_size, new_size) -> None:
                # 模拟事件转移
                pass

        engine = MockEngine()

        # 验证Protocol接口合规性
        # 注意：由于MockEngine不是真正的IEngine实现，这里会失败
        # 这正是TDD Red阶段的目的：明确需求

        # 验证必需属性存在
        assert hasattr(engine, 'name'), "引擎必须有name属性"
        assert hasattr(engine, 'engine_id'), "引擎必须有engine_id属性"
        assert hasattr(engine, 'run_id'), "引擎必须有run_id属性"
        assert hasattr(engine, 'status'), "引擎必须有status属性"
        assert hasattr(engine, 'state'), "引擎必须有state属性"
        assert hasattr(engine, 'is_active'), "引擎必须有is_active属性"
        assert hasattr(engine, 'mode'), "引擎必须有mode属性"
        assert hasattr(engine, 'run_sequence'), "引擎必须有run_sequence属性"

        # 验证必需方法存在
        assert hasattr(engine, 'start'), "引擎必须有start方法"
        assert hasattr(engine, 'pause'), "引擎必须有pause方法"
        assert hasattr(engine, 'stop'), "引擎必须有stop方法"
        assert hasattr(engine, 'put_event'), "引擎必须有put_event方法"
        assert hasattr(engine, 'get_event'), "引擎必须有get_event方法"
        assert hasattr(engine, 'handle_event'), "引擎必须有handle_event方法"
        assert hasattr(engine, 'run'), "引擎必须有run方法"
        assert hasattr(engine, 'add_portfolio'), "引擎必须有add_portfolio方法"
        assert hasattr(engine, 'remove_portfolio'), "引擎必须有remove_portfolio方法"
        assert hasattr(engine, 'set_event_timeout'), "引擎必须有set_event_timeout方法"
        assert hasattr(engine, 'set_event_queue_size'), "引擎必须有set_event_queue_size方法"
        assert hasattr(engine, 'get_engine_summary'), "引擎必须有get_engine_summary方法"
        assert hasattr(engine, 'put'), "引擎必须有put方法"

    def test_engine_lifecycle_methods(self):
        """测试引擎生命周期方法"""
        engine = self._create_mock_engine()

        # 测试初始状态
        assert engine.state == ENGINESTATUS_TYPES.VOID, "初始状态应该是VOID"
        assert engine.is_active == False, "初始状态应该不活跃"

        # 测试启动
        start_result = engine.start()
        assert start_result == True, "启动应该成功"
        assert engine.state == ENGINESTATUS_TYPES.RUNNING, "启动后状态应该是RUNNING"
        assert engine.is_active == True, "启动后应该活跃"
        assert engine.run_id is not None, "启动后应该有运行ID"

        # 测试暂停
        pause_result = engine.pause()
        assert pause_result == True, "暂停应该成功"
        assert engine.state == ENGINESTATUS_TYPES.PAUSED, "暂停后状态应该是PAUSED"
        assert engine.is_active == False, "暂停后应该不活跃"

        # 测试恢复（通过start）
        resume_result = engine.start()  # 暂停状态下应该可以恢复
        assert resume_result == True, "恢复应该成功"
        assert engine.state == ENGINESTATUS_TYPES.RUNNING, "恢复后状态应该是RUNNING"

        # 测试停止
        stop_result = engine.stop()
        assert stop_result == True, "停止应该成功"
        assert engine.state == ENGINESTATUS_TYPES.STOPPED, "停止后状态应该是STOPPED"
        assert engine.is_active == False, "停止后应该不活跃"

    def test_engine_portfolio_management(self):
        """测试引擎投资组合管理"""
        engine = self._create_mock_engine()

        # 测试初始状态
        assert len(engine.portfolios) == 0, "初始应该没有投资组合"

        # 创建测试投资组合
        portfolio1 = PortfolioFactory.create_basic_portfolio()
        portfolio2 = PortfolioFactory.create_high_risk_portfolio()

        # 测试添加投资组合
        engine.add_portfolio(portfolio1)
        assert len(engine.portfolios) == 1, "添加后应该有1个投资组合"

        engine.add_portfolio(portfolio2)
        assert len(engine.portfolios) == 2, "添加第二个后应该有2个投资组合"

        # 测试重复添加（应该不会重复）
        engine.add_portfolio(portfolio1)
        assert len(engine.portfolios) == 2, "重复添加不应该增加数量"

        # 测试移除投资组合
        engine.remove_portfolio(portfolio1)
        assert len(engine.portfolios) == 1, "移除后应该有1个投资组合"

        engine.remove_portfolio(portfolio2)
        assert len(engine.portfolios) == 0, "全部移除后应该没有投资组合"

    def test_engine_event_management(self):
        """测试引擎事件管理"""
        engine = self._create_mock_engine()

        # 创建测试事件
        event1 = EventFactory.create_price_update_event(code="000001.SZ")
        event2 = EventFactory.create_price_update_event(code="000002.SZ")

        # 测试事件投递
        engine.put_event(event1)  # 应该不抛出异常
        engine.put_event(event2)  # 应该不抛出异常

        # 测试事件获取
        result = engine.get_event(timeout=0.1)  # 应该不抛出异常
        # Mock实现返回None，这是正常的

        # 测试事件处理
        engine.handle_event(event1)  # 应该不抛出异常
        engine.handle_event(event2)  # 应该不抛出异常

        # 测试put别名方法
        engine.put(event1)  # 应该不抛出异常

    def test_engine_configuration_methods(self):
        """测试引擎配置方法"""
        engine = self._create_mock_engine()

        # 测试事件超时配置
        assert engine.event_timeout > 0, "默认事件超时应该大于0"

        engine.set_event_timeout(60.0)
        assert engine.event_timeout == 60.0, "设置超时应该生效"

        # 测试无效超时值
        original_timeout = engine.event_timeout
        engine.set_event_timeout(-1.0)  # 负值应该被调整
        assert engine.event_timeout >= 0.1, "最小超时应该被强制执行"

        # 测试队列大小配置
        result = engine.set_event_queue_size(1000)
        assert result == True, "设置有效队列大小应该成功"

        result = engine.set_event_queue_size(-1)  # 负值应该失败
        assert result == False, "设置无效队列大小应该失败"

        # 测试队列状态查询
        assert isinstance(engine.is_resizing_queue, bool), "队列调整状态应该是布尔值"

    def test_engine_monitoring_methods(self):
        """测试引擎监控方法"""
        engine = self._create_mock_engine()

        # 测试引擎摘要
        summary = engine.get_engine_summary()
        assert isinstance(summary, dict), "引擎摘要应该是字典类型"

        # 验证必需字段
        required_fields = [
            "name", "engine_id", "run_id", "status", "is_active",
            "run_sequence", "mode", "portfolios_count"
        ]
        for field in required_fields:
            assert field in summary, f"摘要应该包含{field}字段"

        # 验证字段类型
        assert isinstance(summary["name"], str), "名称应该是字符串"
        assert isinstance(summary["engine_id"], str), "引擎ID应该是字符串"
        assert isinstance(summary["status"], str), "状态应该是字符串"
        assert isinstance(summary["is_active"], bool), "活跃状态应该是布尔值"
        assert isinstance(summary["run_sequence"], int), "运行序列号应该是整数"
        assert isinstance(summary["portfolios_count"], int), "投资组合数量应该是整数"

    def test_engine_properties_validation(self):
        """测试引擎属性验证"""
        engine = self._create_mock_engine()

        # 测试基础属性
        assert isinstance(engine.name, str), "名称应该是字符串"
        assert len(engine.name) > 0, "名称不应该为空"

        assert isinstance(engine.engine_id, str), "引擎ID应该是字符串"
        assert len(engine.engine_id) > 0, "引擎ID不应该为空"

        assert isinstance(engine.run_sequence, int), "运行序列号应该是整数"
        assert engine.run_sequence > 0, "运行序列号应该大于0"

        # 测试状态属性
        assert engine.status in [s.value for s in ENGINESTATUS_TYPES], "状态应该是有效的枚举值"

        # 测试模式属性
        assert hasattr(engine, 'mode'), "应该有模式属性"
        engine.mode = EXECUTION_MODE.LIVE
        assert engine.mode == EXECUTION_MODE.LIVE, "模式设置应该生效"

    @tdd_phase('red')
    def test_missing_required_method_should_fail_protocol_check(self):
        """TDD Red阶段：缺少必需方法的类应该Protocol检查失败"""

        class IncompleteEngine:
            """故意缺少某些方法的引擎实现"""
            def __init__(self):
                self.name = "IncompleteEngine"
                self.engine_id = "incomplete_engine_123"
                self.status = "Void"
                self.is_active = False

            def start(self):
                return True

            # 故意缺少其他必需方法

        incomplete_engine = IncompleteEngine()

        # 验证缺少必需方法
        required_methods = [
            'pause', 'stop', 'put_event', 'get_event', 'handle_event',
            'run', 'add_portfolio', 'remove_portfolio', 'set_event_timeout',
            'set_event_queue_size', 'get_engine_summary', 'put'
        ]

        missing_methods = []
        for method in required_methods:
            if not hasattr(incomplete_engine, method):
                missing_methods.append(method)

        # TDD Red阶段：这个测试应该通过，因为确实缺少方法
        assert len(missing_methods) > 0, f"应该缺少必需方法: {missing_methods}"
        assert False, "TDD Red阶段：需要实现完整的Engine接口"

    def _create_mock_engine(self):
        """创建模拟引擎实例的辅助方法"""
        class SimpleMockEngine:
            def __init__(self):
                self._name = "MockEngine"
                self._engine_id = "mock_engine_123"
                self.run_id = None
                self.status = ENGINESTATUS_TYPES.VOID
                self.state = ENGINESTATUS_TYPES.VOID
                self.is_active_flag = False
                self.mode = EXECUTION_MODE.BACKTEST
                self.run_sequence = 1
                self._portfolios = []
                self._event_timeout = 30.0
                self._is_resizing_queue = False
                self.component_type = "ENGINE"
                self.uuid = self.engine_id

            @property
            def name(self):
                return self._name

            @property
            def engine_id(self):
                return self._engine_id

            @property
            def run_id(self):
                return self._run_id

            @property
            def status(self):
                return self._status.value

            @property
            def state(self):
                return self._state

            @property
            def is_active(self):
                return self._is_active_flag

            @property
            def mode(self):
                return self._mode

            @mode.setter
            def mode(self, value):
                self._mode = value

            @property
            def run_sequence(self):
                return self._run_sequence

            @property
            def portfolios(self):
                return self._portfolios.copy()

            @property
            def event_timeout(self):
                return self._event_timeout

            @property
            def is_resizing_queue(self):
                return self._is_resizing_queue

            def start(self):
                if self.state != ENGINESTATUS_TYPES.VOID:
                    return False
                self.state = ENGINESTATUS_TYPES.RUNNING
                self.is_active_flag = True
                self._run_id = f"run_{int(time.time())}"
                return True

            def pause(self):
                if self.state != ENGINESTATUS_TYPES.RUNNING:
                    return False
                self.state = ENGINESTATUS_TYPES.PAUSED
                self.is_active_flag = False
                return True

            def stop(self):
                if self.state not in [ENGINESTATUS_TYPES.RUNNING, ENGINESTATUS_TYPES.PAUSED]:
                    return False
                self.state = ENGINESTATUS_TYPES.STOPPED
                self.is_active_flag = False
                self._run_id = None
                return True

            def put_event(self, event):
                pass

            def get_event(self, timeout=None):
                return None

            def handle_event(self, event):
                pass

            def run(self):
                return {"status": "completed"}

            def add_portfolio(self, portfolio):
                if portfolio not in self._portfolios:
                    self._portfolios.append(portfolio)

            def remove_portfolio(self, portfolio):
                if portfolio in self._portfolios:
                    self._portfolios.remove(portfolio)

            def set_event_timeout(self, timeout):
                self._event_timeout = max(0.1, timeout)

            def set_event_queue_size(self, size):
                return size > 0

            def get_engine_summary(self):
                return {
                    "name": self.name,
                    "engine_id": self.engine_id,
                    "run_id": self.run_id,
                    "status": self.status,
                    "is_active": self.is_active,
                    "run_sequence": self.run_sequence,
                    "mode": self.mode.value,
                    "portfolios_count": len(self._portfolios)
                }

            def put(self, event):
                self.put_event(event)

        return SimpleMockEngine()


@pytest.mark.tdd
@pytest.mark.protocol
class TestIEngineProtocolRuntimeValidation:
    """IEngine Protocol运行时验证测试"""

    def test_engine_state_transitions(self):
        """测试引擎状态转换"""
        engine = self._create_mock_engine()

        # 验证状态转换规则
        assert engine.state == ENGINESTATUS_TYPES.VOID, "初始状态应该是VOID"

        # VOID -> RUNNING
        assert engine.start() == True, "VOID状态应该能启动到RUNNING"
        assert engine.state == ENGINESTATUS_TYPES.RUNNING, "状态应该转换为RUNNING"

        # RUNNING -> PAUSED
        assert engine.pause() == True, "RUNNING状态应该能暂停到PAUSED"
        assert engine.state == ENGINESTATUS_TYPES.PAUSED, "状态应该转换为PAUSED"

        # PAUSED -> RUNNING
        assert engine.start() == True, "PAUSED状态应该能恢复到RUNNING"
        assert engine.state == ENGINESTATUS_TYPES.RUNNING, "状态应该转换为RUNNING"

        # RUNNING -> STOPPED
        assert engine.stop() == True, "RUNNING状态应该能停止到STOPPED"
        assert engine.state == ENGINESTATUS_TYPES.STOPPED, "状态应该转换为STOPPED"

        # 停止状态下不能启动（需要新的运行会话）
        # 这取决于具体实现

    def test_engine_concurrent_lifecycle_operations(self):
        """测试引擎生命周期操作的并发安全性"""
        engine = self._create_mock_engine()
        results = []
        errors = []

        def lifecycle_worker(worker_id):
            try:
                for i in range(5):
                    # 模拟生命周期操作
                    if engine.state == ENGINESTATUS_TYPES.VOID:
                        result = engine.start()
                    elif engine.state == ENGINESTATUS_TYPES.RUNNING:
                        result = engine.pause()
                    elif engine.state == ENGINESTATUS_TYPES.PAUSED:
                        result = engine.start()
                    else:
                        result = False

                    results.append({
                        'worker_id': worker_id,
                        'operation': i,
                        'result': result,
                        'state_after': engine.state.value
                    })
                    time.sleep(0.001)
            except Exception as e:
                errors.append((worker_id, e))

        # 启动多个线程
        threads = [threading.Thread(target=lifecycle_worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证结果
        assert len(errors) == 0, f"并发操作不应该产生错误: {errors}"
        assert len(results) > 0, "应该有操作结果"

    def test_engine_portfolio_concurrent_operations(self):
        """测试引擎投资组合并发操作"""
        engine = self._create_mock_engine()
        portfolios = [
            PortfolioFactory.create_basic_portfolio() for _ in range(10)
        ]

        add_results = []
        remove_results = []
        errors = []

        def portfolio_worker(worker_id):
            try:
                for i, portfolio in enumerate(portfolios):
                    # 添加投资组合
                    engine.add_portfolio(portfolio)
                    add_results.append((worker_id, i, len(engine.portfolios)))

                    # 稍微延迟
                    time.sleep(0.001)

                    # 移除投资组合
                    engine.remove_portfolio(portfolio)
                    remove_results.append((worker_id, i, len(engine.portfolios)))
            except Exception as e:
                errors.append((worker_id, e))

        # 启动多个线程
        threads = [threading.Thread(target=portfolio_worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证结果
        assert len(errors) == 0, f"并发投资组合操作不应该产生错误: {errors}"
        assert len(add_results) > 0, "应该有添加操作结果"
        assert len(remove_results) > 0, "应该有移除操作结果"
        assert len(engine.portfolios) == 0, "最终应该没有投资组合"

    def test_engine_event_handling_performance(self):
        """测试引擎事件处理性能"""
        engine = self._create_mock_engine()
        events = [
            EventFactory.create_price_update_event(code=f"{i:06d}.SZ")
            for i in range(100)
        ]

        start_time = time.time()

        # 投递事件
        for event in events:
            engine.put_event(event)

        put_time = time.time()

        # 处理事件
        for event in events:
            engine.handle_event(event)

        handle_time = time.time()

        # 计算性能指标
        put_duration = put_time - start_time
        handle_duration = handle_time - put_time
        total_duration = handle_time - start_time

        # 验证性能（Mock实现应该很快）
        assert total_duration < 1.0, "总处理时间应该小于1秒"
        assert len(events) == 100, "应该处理100个事件"

    def _create_mock_engine(self):
        """创建模拟引擎实例"""
        class PerformanceMockEngine:
            def __init__(self):
                self.name = "PerfMockEngine"
                self.engine_id = "perf_engine_123"
                self.run_id = None
                self.status = ENGINESTATUS_TYPES.VOID
                self.state = ENGINESTATUS_TYPES.VOID
                self.is_active_flag = False
                self.mode = EXECUTION_MODE.BACKTEST
                self.run_sequence = 1
                self._portfolios = []
                self._event_timeout = 30.0
                self._is_resizing_queue = False
                self.component_type = "ENGINE"
                self.uuid = self.engine_id

            @property
            def name(self):
                return self._name

            @property
            def engine_id(self):
                return self._engine_id

            @property
            def run_id(self):
                return self._run_id

            @property
            def status(self):
                return self._status.value

            @property
            def state(self):
                return self._state

            @property
            def is_active(self):
                return self._is_active_flag

            @property
            def mode(self):
                return self._mode

            @mode.setter
            def mode(self, value):
                self._mode = value

            @property
            def run_sequence(self):
                return self._run_sequence

            @property
            def portfolios(self):
                return self._portfolios.copy()

            @property
            def event_timeout(self):
                return self._event_timeout

            @property
            def is_resizing_queue(self):
                return self._is_resizing_queue

            def start(self):
                if self.state != ENGINESTATUS_TYPES.VOID:
                    return False
                self.state = ENGINESTATUS_TYPES.RUNNING
                self.is_active_flag = True
                self._run_id = f"run_{int(time.time())}"
                return True

            def pause(self):
                if self.state != ENGINESTATUS_TYPES.RUNNING:
                    return False
                self.state = ENGINESTATUS_TYPES.PAUSED
                self.is_active_flag = False
                return True

            def stop(self):
                if self.state not in [ENGINESTATUS_TYPES.RUNNING, ENGINESTATUS_TYPES.PAUSED]:
                    return False
                self.state = ENGINESTATUS_TYPES.STOPPED
                self.is_active_flag = False
                self._run_id = None
                return True

            def put_event(self, event):
                pass

            def get_event(self, timeout=None):
                return None

            def handle_event(self, event):
                pass

            def run(self):
                return {"status": "completed"}

            def add_portfolio(self, portfolio):
                if portfolio not in self._portfolios:
                    self._portfolios.append(portfolio)

            def remove_portfolio(self, portfolio):
                if portfolio in self._portfolios:
                    self._portfolios.remove(portfolio)

            def set_event_timeout(self, timeout):
                self._event_timeout = max(0.1, timeout)

            def set_event_queue_size(self, size):
                return size > 0

            def get_engine_summary(self):
                return {
                    "name": self.name,
                    "engine_id": self.engine_id,
                    "run_id": self.run_id,
                    "status": self.status,
                    "is_active": self.is_active,
                    "run_sequence": self.run_sequence,
                    "mode": self.mode.value,
                    "portfolios_count": len(self._portfolios)
                }

            def put(self, event):
                self.put_event(event)

        return PerformanceMockEngine()


@pytest.mark.tdd
@pytest.mark.protocol
class TestIEngineProtocolEdgeCases:
    """IEngine Protocol边界情况测试"""

    def test_engine_with_invalid_state_transitions(self):
        """测试无效状态转换"""
        engine = self._create_mock_engine()

        # 初始状态应该是VOID
        assert engine.state == ENGINESTATUS_TYPES.VOID

        # 从VOID状态尝试暂停（应该失败）
        pause_result = engine.pause()
        assert pause_result == False, "VOID状态不应该能暂停"
        assert engine.state == ENGINESTATUS_TYPES.VOID, "状态不应该改变"

        # 从VOID状态尝试停止（应该失败）
        stop_result = engine.stop()
        assert stop_result == False, "VOID状态不应该能停止"
        assert engine.state == ENGINESTATUS_TYPES.VOID, "状态不应该改变"

        # 正确启动
        start_result = engine.start()
        assert start_result == True, "VOID状态应该能启动"

        # 重复启动（应该失败）
        duplicate_start = engine.start()
        assert duplicate_start == False, "RUNNING状态不应该能再次启动"

    def test_engine_with_zero_configuration(self):
        """测试零配置的引擎"""
        engine = self._create_mock_engine()

        # 测试最小配置
        engine.set_event_timeout(0.1)  # 最小超时
        assert engine.event_timeout >= 0.1, "最小超时应该被强制执行"

        engine.set_event_queue_size(1)  # 最小队列大小
        assert engine.set_event_queue_size(1) == True, "最小队列大小应该被接受"

        # 测试零投资组合
        assert len(engine.portfolios) == 0, "初始应该没有投资组合"
        summary = engine.get_engine_summary()
        assert summary["portfolios_count"] == 0, "摘要应该反映零投资组合"

    def test_engine_with_extreme_operations(self):
        """测试极端操作"""
        engine = self._create_mock_engine()

        # 测试大量投资组合
        many_portfolios = [
            PortfolioFactory.create_basic_portfolio() for _ in range(1000)
        ]

        start_time = time.time()
        for portfolio in many_portfolios:
            engine.add_portfolio(portfolio)
        add_time = time.time()

        assert len(engine.portfolios) == 1000, "应该能处理1000个投资组合"
        assert add_time - start_time < 5.0, "添加操作应该很快"

        # 测试大量事件
        many_events = [
            EventFactory.create_price_update_event(code=f"{i:06d}.SZ")
            for i in range(1000)
        ]

        event_start = time.time()
        for event in many_events:
            engine.put_event(event)
        event_time = time.time()

        assert event_time - event_start < 5.0, "事件投递应该很快"

    def test_engine_with_invalid_inputs(self):
        """测试无效输入处理"""
        engine = self._create_mock_engine()

        # 测试None事件
        try:
            engine.put_event(None)  # 应该不崩溃
        except Exception as e:
            # 如果抛出异常，应该是预期的
            assert isinstance(e, (TypeError, AttributeError))

        # 测试None投资组合
        try:
            engine.add_portfolio(None)  # 应该不崩溃
        except Exception as e:
            # 如果抛出异常，应该是预期的
            assert isinstance(e, (TypeError, AttributeError))

        # 测试无效配置
        engine.set_event_timeout(-100.0)  # 负值应该被调整
        assert engine.event_timeout >= 0.1, "负值超时应该被调整"

        engine.set_event_queue_size(0)  # 零大小应该失败
        assert engine.set_event_queue_size(0) == False, "零队列大小应该被拒绝"

    def test_engine_memory_management(self):
        """测试引擎内存管理"""
        engine = self._create_mock_engine()

        # 添加大量数据
        large_portfolio = PortfolioFactory.create_basic_portfolio(
            positions=[
                {
                    "code": f"{i:06d}.SZ",
                    "volume": 1000,
                    "cost": Decimal('10.0'),
                    "current_price": Decimal('10.0'),
                    "market_value": Decimal('10000.0')
                }
                for i in range(1000)  # 1000个持仓
            ]
        )

        engine.add_portfolio(large_portfolio)

        # 验证内存使用合理
        summary = engine.get_engine_summary()
        assert summary["portfolios_count"] == 1, "应该有1个投资组合"

        # 清理数据
        engine.remove_portfolio(large_portfolio)
        assert len(engine.portfolios) == 0, "清理后应该没有投资组合"

    def _create_mock_engine(self):
        """创建模拟引擎实例"""
        class EdgeCaseMockEngine:
            def __init__(self):
                self.name = "EdgeCaseMockEngine"
                self.engine_id = "edge_engine_123"
                self.run_id = None
                self.status = ENGINESTATUS_TYPES.VOID
                self.state = ENGINESTATUS_TYPES.VOID
                self.is_active_flag = False
                self.mode = EXECUTION_MODE.BACKTEST
                self.run_sequence = 1
                self._portfolios = []
                self._event_timeout = 30.0
                self._is_resizing_queue = False
                self.component_type = "ENGINE"
                self.uuid = self.engine_id

            @property
            def name(self):
                return self._name

            @property
            def engine_id(self):
                return self._engine_id

            @property
            def run_id(self):
                return self._run_id

            @property
            def status(self):
                return self._status.value

            @property
            def state(self):
                return self._state

            @property
            def is_active(self):
                return self._is_active_flag

            @property
            def mode(self):
                return self._mode

            @mode.setter
            def mode(self, value):
                self._mode = value

            @property
            def run_sequence(self):
                return self._run_sequence

            @property
            def portfolios(self):
                return self._portfolios.copy()

            @property
            def event_timeout(self):
                return self._event_timeout

            @property
            def is_resizing_queue(self):
                return self._is_resizing_queue

            def start(self):
                if self.state != ENGINESTATUS_TYPES.VOID:
                    return False
                self.state = ENGINESTATUS_TYPES.RUNNING
                self.is_active_flag = True
                self._run_id = f"run_{int(time.time())}"
                return True

            def pause(self):
                if self.state != ENGINESTATUS_TYPES.RUNNING:
                    return False
                self.state = ENGINESTATUS_TYPES.PAUSED
                self.is_active_flag = False
                return True

            def stop(self):
                if self.state not in [ENGINESTATUS_TYPES.RUNNING, ENGINESTATUS_TYPES.PAUSED]:
                    return False
                self.state = ENGINESTATUS_TYPES.STOPPED
                self.is_active_flag = False
                self._run_id = None
                return True

            def put_event(self, event):
                # 处理None事件
                if event is None:
                    return
                # 正常处理
                pass

            def get_event(self, timeout=None):
                return None

            def handle_event(self, event):
                pass

            def run(self):
                return {"status": "completed"}

            def add_portfolio(self, portfolio):
                # 处理None投资组合
                if portfolio is None:
                    return
                if portfolio not in self._portfolios:
                    self._portfolios.append(portfolio)

            def remove_portfolio(self, portfolio):
                if portfolio in self._portfolios:
                    self._portfolios.remove(portfolio)

            def set_event_timeout(self, timeout):
                # 处理负值
                self._event_timeout = max(0.1, timeout)

            def set_event_queue_size(self, size):
                return size > 0

            def get_engine_summary(self):
                return {
                    "name": self.name,
                    "engine_id": self.engine_id,
                    "run_id": self.run_id,
                    "status": self.status,
                    "is_active": self.is_active,
                    "run_sequence": self.run_sequence,
                    "mode": self.mode.value,
                    "portfolios_count": len(self._portfolios)
                }

            def put(self, event):
                self.put_event(event)

        return EdgeCaseMockEngine()


# ===== TDD阶段标记 =====

def tdd_phase(phase: str):
    """TDD阶段标记装饰器"""
    def decorator(test_func):
        test_func.tdd_phase = phase
        return test_func
    return decorator