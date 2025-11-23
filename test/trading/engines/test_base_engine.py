"""
BaseEngine基础引擎TDD测试

通过TDD方式开发BaseEngine的核心逻辑测试套件
聚焦于引擎身份管理、状态控制和基础配置功能
"""
import sys
from pathlib import Path
from queue import Queue

import pytest

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.trading.core.identity import IdentityUtils
from ginkgo.trading.engines.base_engine import BaseEngine
from ginkgo.enums import EXECUTION_MODE


class DummyEngine(BaseEngine):
    """测试用的具体引擎实现，提供最小 run/handle_event 行为"""

    def __init__(self, *args, **kwargs):
        self.handled_events = []
        super().__init__(*args, **kwargs)

    def run(self):
        self._is_running = True
        return "running"

    def handle_event(self, event):
        self.handled_events.append(event)


class DummyPortfolio:
    def __init__(self, name: str):
        self.name = name


@pytest.mark.unit
class TestBaseEngineConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """验证默认构造参数会设置名称、模式"""
        engine = DummyEngine()

        assert engine.name == "BaseEngine"
        assert engine.mode is EXECUTION_MODE.BACKTEST

    def test_custom_name_constructor(self):
        """自定义名称应透传到实例"""
        engine = DummyEngine(name="AlphaEngine")

        assert engine.name == "AlphaEngine"

    def test_custom_engine_id_constructor(self):
        """显式传入 engine_id 时应直接使用该值"""
        engine = DummyEngine(engine_id="engine_manual_id")

        assert engine.engine_id == "engine_manual_id"

    def test_custom_mode_constructor(self):
        """自定义模式应覆盖默认 BACKTEST"""
        engine = DummyEngine(mode=EXECUTION_MODE.LIVE)

        assert engine.mode is EXECUTION_MODE.LIVE

    def test_backtest_base_inheritance(self):
        """BaseEngine 应继承 BacktestBase 并设置组件类型"""
        engine = DummyEngine()

        assert isinstance(engine, BacktestBase)
        from ginkgo.enums import COMPONENT_TYPES
        assert engine.component_type == COMPONENT_TYPES.ENGINE


@pytest.mark.unit
class TestBaseEngineProperties:
    """2. 属性访问测试"""

    def test_status_property(self):
        """Active 状态应在 start/stop 中切换"""
        engine = DummyEngine(engine_id="engine_seq_test")
        assert engine.status == "Idle"

        engine.start()
        assert engine.status == "Running"

        engine.stop()
        assert engine.status == "Stopped"

    def test_active_property(self):
        """is_active 与 pause 方法应保持一致"""
        engine = DummyEngine(engine_id="engine_active_test")
        assert engine.is_active is False

        engine.start()
        assert engine.is_active is True

        engine.pause()
        assert engine.is_active is False

    def test_run_sequence_property(self):
        """测试run_sequence和会话管理逻辑"""
        engine = DummyEngine(engine_id="engine_seq")
        assert engine.run_sequence == 0

        # 第一次启动：生成新会话
        start_success = engine.start()
        assert start_success is True
        assert engine.run_sequence == 1
        first_run = engine.run_id
        assert IdentityUtils.validate_run_id_format(first_run)

        # 暂停后重启：保持同一会话
        engine.pause()
        resume_success = engine.start()
        assert resume_success is True
        assert engine.run_sequence == 1  # 序列号不变
        resumed_run = engine.run_id
        assert resumed_run == first_run  # 同一个run_id

        # 停止后重启：生成新会话
        engine.stop()
        restart_success = engine.start()
        assert restart_success is True
        assert engine.run_sequence == 2  # 序列号递增
        second_run = engine.run_id
        assert IdentityUtils.validate_run_id_format(second_run)
        assert second_run != first_run  # 不同的run_id

    def test_config_property(self):
        """测试配置相关属性的可用性"""
        engine = DummyEngine()
        # BaseEngine没有config属性，但其他配置属性可用
        assert hasattr(engine, 'mode')
        assert hasattr(engine, 'event_timeout')
        assert hasattr(engine, 'portfolios')

    def test_mode_property(self):
        """mode setter 应接收 EXECUTION_MODE 枚举"""
        engine = DummyEngine()
        engine.mode = EXECUTION_MODE.SIMULATION
        assert engine.mode is EXECUTION_MODE.SIMULATION

    def test_is_running_property(self):
        """运行占位实现会将 _is_running 标记为 True"""
        engine = DummyEngine()
        assert engine._is_running is False

        engine.run()
        assert engine._is_running is True


@pytest.mark.unit
class TestBaseEngineIdentityManagement:
    """3. 身份管理测试"""

    def test_engine_id_generation_default(self, monkeypatch):
        """无显式 engine_id 时应使用 generate_component_uuid"""
        calls = []

        def fake_generate(prefix=""):
            index = len(calls)
            value = f"{prefix}_fake_{index}"
            calls.append(value)
            return value

        monkeypatch.setattr(
            "ginkgo.trading.core.identity.IdentityUtils.generate_component_uuid",
            fake_generate,
        )

        engine = DummyEngine()

        assert "engine_fake_0" in engine.engine_id
        assert "engine_fake_1" in engine.uuid

    def test_engine_id_custom_setting(self):
        """engine_id 参数优先级最高"""
        engine = DummyEngine(engine_id="engine_explicit")
        assert engine.engine_id == "engine_explicit"

    def test_component_type_setting(self):
        """component_type 应保持为 engine"""
        engine = DummyEngine()
        summary = engine.get_engine_summary()

        from ginkgo.enums import COMPONENT_TYPES
        assert engine.component_type == COMPONENT_TYPES.ENGINE
        assert summary["component_type"] == COMPONENT_TYPES.ENGINE  # summary中的component_type是枚举

    def test_identity_utils_integration(self, monkeypatch):
        """start 时生成的 run_id 应符合 IdentityUtils 校验"""
        def fake_run_id(engine_id, sequence):
            return f"{engine_id}_run_20240101_120000_{sequence:03d}"

        monkeypatch.setattr(
            "ginkgo.trading.core.identity.IdentityUtils.generate_run_id", fake_run_id
        )

        engine = DummyEngine(engine_id="engine_identity")
        start_success = engine.start()
        assert start_success is True

        run_id = engine.run_id
        assert run_id.startswith("engine_identity_run_20240101_120000_")
        assert IdentityUtils.validate_run_id_format(run_id) is True


@pytest.mark.unit
class TestBaseEngineComponentManagement:
    """4. 组件管理测试"""

    def test_portfolios_initialization(self):
        """默认情况下投资组合列表为空"""
        engine = DummyEngine()
        assert engine.portfolios == []

    def test_event_queue_initialization(self):
        """事件队列应初始化为 Queue 并可收发事件"""
        engine = DummyEngine()
        assert isinstance(engine._event_queue, Queue)

        sentinel = object()
        engine.put(sentinel)
        assert engine._event_queue.get_nowait() is sentinel

    def test_component_container_structure(self):
        """get_engine_summary 返回的摘要应包含关键字段"""
        engine = DummyEngine()
        summary = engine.get_engine_summary()

        expected_keys = {
            "name",
            "engine_id",
            "run_id",
            "status",
            "is_active",
            "run_sequence",
            "component_type",
            "uuid",
            "mode",
            "portfolios_count",
        }
        assert expected_keys.issubset(summary.keys())

    def test_add_and_remove_portfolio(self):
        """add/remove 应维护 portfolios 列表且避免重复"""
        engine = DummyEngine()
        portfolio = DummyPortfolio("TestPortfolio")

        engine.add_portfolio(portfolio)
        engine.add_portfolio(portfolio)

        assert engine.portfolios == [portfolio]

        engine.remove_portfolio(portfolio)
        assert engine.portfolios == []


@pytest.mark.unit
class TestEngineMode:
    """5. 引擎模式测试"""

    def test_engine_mode_enum_values(self):
        """枚举值应与字符串常量保持一致"""
        # EXECUTION_MODE枚举值是数字，不是字符串
        assert EXECUTION_MODE.BACKTEST.value == 0
        assert EXECUTION_MODE.LIVE.value == 1
        assert EXECUTION_MODE.SIMULATION.value == 2

    def test_backtest_mode_setting(self):
        """默认构造即为 BACKTEST 模式"""
        engine = DummyEngine()
        assert engine.mode is EXECUTION_MODE.BACKTEST

    def test_live_mode_setting(self):
        """可切换到 LIVE 模式"""
        engine = DummyEngine(mode=EXECUTION_MODE.LIVE)
        assert engine.mode is EXECUTION_MODE.LIVE

    def test_simulation_mode_setting(self):
        """可切换到 SIMULATION 模式"""
        engine = DummyEngine(mode=EXECUTION_MODE.SIMULATION)
        assert engine.mode is EXECUTION_MODE.SIMULATION


@pytest.mark.unit
class TestBaseEngineValidation:
    """6. 基础引擎验证测试"""

    def test_abstract_base_class_behavior(self):
        """BaseEngine 作为抽象类直接实例化应报错"""
        with pytest.raises(TypeError):
            BaseEngine()

    def test_run_method_abstract(self):
        """缺少 run 实现的子类无法实例化"""

        class MissingRun(BaseEngine):
            def handle_event(self, event):
                pass

        with pytest.raises(TypeError):
            MissingRun()

    def test_handle_event_method_abstract(self):
        """缺少 handle_event 实现的子类无法实例化"""

        class MissingHandle(BaseEngine):
            def run(self):
                pass

        with pytest.raises(TypeError):
            MissingHandle()

    def test_initialization_parameter_validation(self):
        """BaseEngine 基本参数验证"""
        engine = DummyEngine()
        assert engine.name == "BaseEngine"
        assert engine.mode is EXECUTION_MODE.BACKTEST
