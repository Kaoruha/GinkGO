"""
BaseEngine基础引擎初始化测试

测试BaseEngine抽象基类的接口和基础功能，包括状态管理、事件队列、投资组合管理等。
采用TDD方法确保引擎基础架构的正确性。
"""

import pytest
from unittest.mock import Mock
from ginkgo.trading.engines.base_engine import BaseEngine
from ginkgo.enums import EXECUTION_MODE, ENGINESTATUS_TYPES


@pytest.mark.tdd
class TestBacktestEngineConstruction:
    """BaseEngine抽象基类接口测试"""

    def test_base_engine_is_abstract(self):
        """测试BaseEngine是抽象类，不能直接实例化"""
        # 验证BaseEngine是抽象类，不能直接实例化
        with pytest.raises(TypeError):
            BaseEngine()  # 应该抛出TypeError，因为是抽象类

    def test_base_engine_interface_compliance(self):
        """测试BaseEngine接口要求"""
        # 创建具体的引擎实现来测试接口
        class TestEngine(BaseEngine):
            def __init__(self, name="TestEngine", **kwargs):
                super().__init__(name=name, **kwargs)
                self.strategies = []
                self.risk_managers = []
                self.portfolio = Mock()
                self.data_feeder = Mock()
                self.broker = Mock()

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine()

        # 验证必需的属性存在
        assert hasattr(engine, 'name')
        assert hasattr(engine, 'uuid')
        assert hasattr(engine, 'status')
        assert hasattr(engine, 'engine_id')
        assert hasattr(engine, 'run_id')
        assert hasattr(engine, 'state')
        assert hasattr(engine, 'mode')

        # 验证继承的BacktestBase属性
        assert hasattr(engine, 'component_type')
        assert hasattr(engine, 'loggers')
        assert isinstance(engine.loggers, list)

        # 验证引擎特有属性
        assert hasattr(engine, 'portfolios')
        assert isinstance(engine.portfolios, list)
        assert hasattr(engine, '_event_queue')
        assert hasattr(engine, 'event_timeout')
        assert hasattr(engine, 'is_resizing_queue')

        # 验证基础值
        assert engine.name == "TestEngine"
        assert engine.engine_id is not None
        assert engine.run_id is None
        assert engine.status == "Idle"
        assert engine.state == ENGINESTATUS_TYPES.IDLE
        assert engine.is_active is False
        assert engine.run_sequence == 0

    def test_engine_initialization_with_parameters(self):
        """测试带参数的引擎初始化"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.strategies = []
                self.risk_managers = []
                self.portfolio = Mock()

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine(
            name="CustomEngine",
            mode=EXECUTION_MODE.BACKTEST,
            engine_id="test-engine-123"
        )

        assert engine.name == "CustomEngine"
        assert engine.mode == EXECUTION_MODE.BACKTEST
        assert engine.engine_id == "test-engine-123"

    def test_engine_component_initialization(self):
        """测试引擎组件初始化"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.strategies = []
                self.risk_managers = []
                self.portfolio = Mock()
                self.data_feeder = Mock()
                self.broker = Mock()

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine()

        # 验证核心组件已初始化
        assert hasattr(engine, 'portfolios')
        assert isinstance(engine.portfolios, list)
        assert hasattr(engine, '_event_queue')
        assert hasattr(engine, '_state')
        assert engine.state == ENGINESTATUS_TYPES.IDLE


@pytest.mark.tdd
class TestBacktestEngineStateManagement:
    """BaseEngine状态管理测试"""

    def test_initial_state(self):
        """测试初始状态"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine()

        # 验证引擎初始状态
        assert engine.status == "Idle"
        assert engine.state == ENGINESTATUS_TYPES.IDLE
        assert engine.is_active == False
        assert engine.run_sequence == 0
        assert engine.run_id is None

    def test_state_transitions(self):
        """测试状态转换"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine()

        # 测试启动状态转换
        result = engine.start()
        assert result is True
        assert engine.status == "Running"
        assert engine.state == ENGINESTATUS_TYPES.RUNNING
        assert engine.is_active == True
        assert engine.run_id is not None
        assert engine.run_sequence == 1

    def test_pause_and_resume(self):
        """测试暂停和恢复"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine()

        # 启动引擎
        engine.start()
        assert engine.status == "Running"

        # 暂停引擎
        result = engine.pause()
        assert result is True
        assert engine.status == "Paused"
        assert engine.state == ENGINESTATUS_TYPES.PAUSED
        assert engine.is_active == False

        # 恢复引擎
        result = engine.start()  # 从暂停状态恢复
        assert result is True
        assert engine.status == "Running"
        assert engine.is_active == True

    def test_stop_engine(self):
        """测试停止引擎"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine()

        # 启动引擎
        engine.start()
        assert engine.status == "Running"

        # 停止引擎
        result = engine.stop()
        assert result is True
        assert engine.status == "Stopped"
        assert engine.state == ENGINESTATUS_TYPES.STOPPED
        assert engine.is_active == False


@pytest.mark.tdd
class TestBacktestEngineEventQueue:
    """BaseEngine事件队列测试"""

    def test_event_queue_initialization(self):
        """测试事件队列初始化"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine()

        # 验证事件队列初始化
        assert hasattr(engine, '_event_queue')
        assert hasattr(engine, 'event_timeout')
        assert engine.event_timeout == 10.0
        assert hasattr(engine, 'is_resizing_queue')
        assert engine.is_resizing_queue == False

    def test_event_put_and_get(self):
        """测试事件放入和获取"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine()

        # 测试事件放入和获取
        test_event = Mock()
        engine.put_event(test_event)

        retrieved_event = engine.get_event(timeout=0.1)
        assert retrieved_event is test_event

    def test_event_queue_resize(self):
        """测试事件队列大小调整"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine()

        # 测试队列大小调整
        result = engine.set_event_queue_size(5000)
        assert result is True


@pytest.mark.tdd
class TestBacktestEnginePortfolioManagement:
    """BaseEngine投资组合管理测试"""

    def test_portfolio_list_initialization(self):
        """测试投资组合列表初始化"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine()

        # 验证投资组合列表初始化
        assert hasattr(engine, 'portfolios')
        assert isinstance(engine.portfolios, list)
        assert len(engine.portfolios) == 0

    def test_add_portfolio(self):
        """测试添加投资组合"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine()

        # 创建模拟投资组合
        mock_portfolio = Mock()
        mock_portfolio.name = "TestPortfolio"

        # 添加投资组合
        engine.add_portfolio(mock_portfolio)

        assert len(engine.portfolios) == 1
        assert mock_portfolio in engine.portfolios

    def test_remove_portfolio(self):
        """测试移除投资组合"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine()

        # 创建模拟投资组合
        mock_portfolio = Mock()
        mock_portfolio.name = "TestPortfolio"

        # 添加然后移除投资组合
        engine.add_portfolio(mock_portfolio)
        assert len(engine.portfolios) == 1

        engine.remove_portfolio(mock_portfolio)
        assert len(engine.portfolios) == 0
        assert mock_portfolio not in engine.portfolios

    def test_duplicate_portfolio_handling(self):
        """测试重复投资组合处理"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine()

        # 创建模拟投资组合
        mock_portfolio = Mock()
        mock_portfolio.name = "TestPortfolio"

        # 重复添加同一个投资组合
        engine.add_portfolio(mock_portfolio)
        engine.add_portfolio(mock_portfolio)  # 应该被忽略

        assert len(engine.portfolios) == 1  # 只有一个


@pytest.mark.tdd
class TestBacktestEngineSummary:
    """BaseEngine摘要信息测试"""

    def test_engine_summary_generation(self):
        """测试引擎摘要生成"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine(name="TestEngine", engine_id="test-123")

        # 生成引擎摘要
        summary = engine.get_engine_summary()

        # 验证摘要内容
        assert 'name' in summary
        assert 'engine_id' in summary
        assert 'run_id' in summary
        assert 'status' in summary
        assert 'is_active' in summary
        assert 'run_sequence' in summary
        assert 'component_type' in summary
        assert 'uuid' in summary
        assert 'mode' in summary
        assert 'portfolios_count' in summary

        assert summary['name'] == "TestEngine"
        assert summary['engine_id'] == "test-123"
        assert summary['status'] == "Idle"
        assert summary['is_active'] == False
        assert summary['run_sequence'] == 0
        assert summary['portfolios_count'] == 0

    def test_engine_string_representation(self):
        """测试引擎字符串表示"""
        class TestEngine(BaseEngine):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)

            def run(self):
                return {"status": "completed"}

            def handle_event(self, event):
                pass

        engine = TestEngine(name="TestEngine")

        # 测试字符串表示
        repr_str = repr(engine)
        assert isinstance(repr_str, str)
        assert "TestEngine" in repr_str


if __name__ == "__main__":
    # 运行测试确认失败（Red阶段）
    pytest.main([__file__, "-v"])