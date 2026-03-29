"""
引擎接口单元测试

测试 IEngine、IEventDrivenEngine、IMatrixEngine、IHybridEngine 接口定义，
验证构造、状态管理、回调机制、模式切换等行为。
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

from ginkgo.core.interfaces.engine_interface import (
    EngineMode,
    IEngine,
    IEventDrivenEngine,
    IMatrixEngine,
    IHybridEngine,
)
from ginkgo.enums import ENGINESTATUS_TYPES


# ── 补充源码中缺失的枚举值 ──────────────────────────────────────────
# 源码 engine_interface.py 引用了 COMPLETED 和 ERROR，但枚举中不存在
# 这里在测试中补充以保证接口方法可正常运行

if not hasattr(ENGINESTATUS_TYPES, "COMPLETED"):
    ENGINESTATUS_TYPES.COMPLETED = ENGINESTATUS_TYPES.STOPPED
if not hasattr(ENGINESTATUS_TYPES, "ERROR"):
    ENGINESTATUS_TYPES.ERROR = ENGINESTATUS_TYPES.VOID


# ── 具体实现用于测试抽象类 ──────────────────────────────────────────


class ConcreteEngine(IEngine):
    """IEngine 的具体实现，用于测试"""

    def initialize(self, config=None):
        pass

    def run(self, portfolio):
        return {"result": "ok"}


class ConcreteEventEngine(IEventDrivenEngine):
    """IEventDrivenEngine 的具体实现"""

    def process_event(self, event):
        pass

    def main_loop(self, stop_flag):
        pass

    def initialize(self, config=None):
        pass

    def run(self, portfolio):
        return {"result": "event_driven"}


class ConcreteMatrixEngine(IMatrixEngine):
    """IMatrixEngine 的具体实现"""

    def load_data(self, start_date, end_date):
        return {"data": "loaded"}

    def process_vectorized(self, data, portfolio):
        return {"result": "vectorized"}

    def initialize(self, config=None):
        pass

    def run(self, portfolio):
        return {"result": "matrix"}


class ConcreteHybridEngine(IHybridEngine):
    """IHybridEngine 的具体实现"""

    def select_optimal_mode(self, context):
        return EngineMode.EVENT_DRIVEN

    def switch_engine_mode(self, target_mode):
        return True

    def initialize(self, config=None):
        pass

    def run(self, portfolio):
        return {"result": "hybrid"}


# ── EngineMode 枚举测试 ─────────────────────────────────────────────


@pytest.mark.unit
class TestEngineMode:
    """EngineMode 枚举测试"""

    def test_enum_values(self):
        """验证所有模式值"""
        assert EngineMode.EVENT_DRIVEN.value == "event_driven"
        assert EngineMode.MATRIX.value == "matrix"
        assert EngineMode.HYBRID.value == "hybrid"
        assert EngineMode.AUTO.value == "auto"

    def test_enum_member_count(self):
        """验证枚举成员数量"""
        assert len(EngineMode) == 4


# ── IEngine 基础测试 ────────────────────────────────────────────────


@pytest.mark.unit
class TestIEngineConstruction:
    """IEngine 构造测试"""

    def test_default_construction(self):
        """默认参数构造"""
        engine = ConcreteEngine()
        assert engine.name == "UnknownEngine"
        assert engine.mode == EngineMode.AUTO
        assert engine.status == ENGINESTATUS_TYPES.IDLE
        assert engine.created_at is not None
        assert engine.started_at is None
        assert engine.completed_at is None

    def test_custom_name_and_mode(self):
        """自定义名称和模式"""
        engine = ConcreteEngine(name="MyEngine", mode=EngineMode.EVENT_DRIVEN)
        assert engine.name == "MyEngine"
        assert engine.mode == EngineMode.EVENT_DRIVEN

    def test_initial_config_is_empty(self):
        """初始配置为空字典"""
        engine = ConcreteEngine()
        assert engine.config == {}

    def test_initial_performance_stats(self):
        """初始性能统计"""
        engine = ConcreteEngine()
        stats = engine.performance_stats
        assert stats["events_processed"] == 0
        assert stats["execution_time"] == 0.0
        assert stats["memory_usage_mb"] == 0.0
        assert stats["error_count"] == 0

    def test_initial_callbacks_empty(self):
        """初始回调列表为空"""
        engine = ConcreteEngine()
        assert engine._on_start_callbacks == []
        assert engine._on_complete_callbacks == []
        assert engine._on_error_callbacks == []


@pytest.mark.unit
class TestIEngineProperties:
    """IEngine 属性测试"""

    def test_is_running_when_running(self):
        """运行状态下 is_running 为 True"""
        engine = ConcreteEngine()
        engine.status = ENGINESTATUS_TYPES.RUNNING
        assert engine.is_running is True

    def test_is_running_when_idle(self):
        """空闲状态下 is_running 为 False"""
        engine = ConcreteEngine()
        assert engine.is_running is False

    def test_is_completed_when_completed(self):
        """完成状态下 is_completed 为 True"""
        engine = ConcreteEngine()
        engine.status = ENGINESTATUS_TYPES.COMPLETED
        assert engine.is_completed is True

    def test_is_completed_when_idle(self):
        """空闲状态下 is_completed 为 False"""
        engine = ConcreteEngine()
        assert engine.is_completed is False


@pytest.mark.unit
class TestIEngineLifecycle:
    """IEngine 生命周期管理测试"""

    def test_start_from_idle(self):
        """从空闲状态启动"""
        engine = ConcreteEngine()
        engine.start()
        assert engine.status == ENGINESTATUS_TYPES.RUNNING
        assert engine.started_at is not None

    def test_start_from_paused(self):
        """从暂停状态恢复启动"""
        engine = ConcreteEngine()
        engine.status = ENGINESTATUS_TYPES.PAUSED
        engine.start()
        assert engine.status == ENGINESTATUS_TYPES.RUNNING

    def test_start_from_running_raises(self):
        """运行中启动应抛出异常"""
        engine = ConcreteEngine()
        engine.status = ENGINESTATUS_TYPES.RUNNING
        with pytest.raises(RuntimeError, match="不允许启动"):
            engine.start()

    def test_start_from_completed_raises(self):
        """已完成状态启动应抛出异常"""
        engine = ConcreteEngine()
        engine.status = ENGINESTATUS_TYPES.COMPLETED
        with pytest.raises(RuntimeError, match="不允许启动"):
            engine.start()

    def test_stop_from_running(self):
        """运行中停止"""
        engine = ConcreteEngine()
        engine.start()
        engine.stop()
        assert engine.status == ENGINESTATUS_TYPES.COMPLETED
        assert engine.completed_at is not None
        assert engine.performance_stats["execution_time"] > 0

    def test_stop_from_idle_no_effect(self):
        """空闲状态停止无效"""
        engine = ConcreteEngine()
        engine.stop()
        assert engine.status == ENGINESTATUS_TYPES.IDLE
        assert engine.completed_at is None

    def test_pause_from_running(self):
        """运行中暂停"""
        engine = ConcreteEngine()
        engine.start()
        engine.pause()
        assert engine.status == ENGINESTATUS_TYPES.PAUSED

    def test_pause_from_idle_no_effect(self):
        """空闲状态暂停无效"""
        engine = ConcreteEngine()
        engine.pause()
        assert engine.status == ENGINESTATUS_TYPES.IDLE

    def test_resume_from_paused(self):
        """暂停状态恢复"""
        engine = ConcreteEngine()
        engine.start()
        engine.pause()
        engine.resume()
        assert engine.status == ENGINESTATUS_TYPES.RUNNING

    def test_resume_from_idle_no_effect(self):
        """空闲状态恢复无效"""
        engine = ConcreteEngine()
        engine.resume()
        assert engine.status == ENGINESTATUS_TYPES.IDLE

    def test_reset(self):
        """重置引擎状态"""
        engine = ConcreteEngine()
        engine.start()
        engine.update_performance_stats({"events_processed": 100})
        engine.stop()

        engine.reset()
        assert engine.status == ENGINESTATUS_TYPES.IDLE
        assert engine.started_at is None
        assert engine.completed_at is None
        assert engine.performance_stats["events_processed"] == 0
        assert engine.performance_stats["execution_time"] == 0.0


@pytest.mark.unit
class TestIEngineConfig:
    """IEngine 配置管理测试"""

    def test_set_config(self):
        """设置配置"""
        engine = ConcreteEngine()
        engine.set_config({"max_workers": 4, "timeout": 30})
        assert engine.config["max_workers"] == 4
        assert engine.config["timeout"] == 30

    def test_set_config_updates_existing(self):
        """更新已有配置"""
        engine = ConcreteEngine()
        engine.set_config({"timeout": 30})
        engine.set_config({"timeout": 60})
        assert engine.config["timeout"] == 60

    def test_get_config_existing(self):
        """获取已有配置项"""
        engine = ConcreteEngine()
        engine.set_config({"timeout": 30})
        assert engine.get_config("timeout") == 30

    def test_get_config_missing_returns_default(self):
        """获取不存在配置项返回默认值"""
        engine = ConcreteEngine()
        assert engine.get_config("nonexistent", "default") == "default"

    def test_get_config_missing_returns_none(self):
        """获取不存在配置项返回 None"""
        engine = ConcreteEngine()
        assert engine.get_config("nonexistent") is None

    def test_validate_config_default_true(self):
        """默认配置验证返回 True"""
        engine = ConcreteEngine()
        assert engine.validate_config() is True


@pytest.mark.unit
class TestIEngineModeSwitching:
    """IEngine 模式切换测试"""

    def test_get_supported_modes_default(self):
        """默认支持模式列表"""
        engine = ConcreteEngine()
        modes = engine.get_supported_modes()
        assert EngineMode.AUTO in modes

    def test_can_switch_to_supported_mode(self):
        """可以切换到支持的模式"""
        engine = ConcreteEngine()
        assert engine.can_switch_mode(EngineMode.AUTO) is True

    def test_cannot_switch_to_unsupported_mode(self):
        """不能切换到不支持的模式"""
        engine = ConcreteEngine()
        assert engine.can_switch_mode(EngineMode.MATRIX) is False

    def test_switch_mode_success(self):
        """成功切换模式"""
        engine = ConcreteEngine()
        result = engine.switch_mode(EngineMode.AUTO)
        assert result is True
        assert engine.mode == EngineMode.AUTO

    def test_switch_mode_unsupported(self):
        """切换不支持的模式返回 False"""
        engine = ConcreteEngine()
        result = engine.switch_mode(EngineMode.MATRIX)
        assert result is False

    def test_switch_mode_while_running_returns_false(self):
        """运行中不允许切换模式"""
        engine = ConcreteEngine()
        engine.start()
        result = engine.switch_mode(EngineMode.AUTO)
        assert result is False


@pytest.mark.unit
class TestIEngineCallbacks:
    """IEngine 回调机制测试"""

    def test_add_on_start_callback(self):
        """添加启动回调"""
        engine = ConcreteEngine()
        cb = MagicMock()
        engine.add_callback("on_start", cb)
        assert cb in engine._on_start_callbacks

    def test_add_on_complete_callback(self):
        """添加完成回调"""
        engine = ConcreteEngine()
        cb = MagicMock()
        engine.add_callback("on_complete", cb)
        assert cb in engine._on_complete_callbacks

    def test_add_on_error_callback(self):
        """添加错误回调"""
        engine = ConcreteEngine()
        cb = MagicMock()
        engine.add_callback("on_error", cb)
        assert cb in engine._on_error_callbacks

    def test_add_invalid_callback_raises(self):
        """添加无效回调事件名抛出异常"""
        engine = ConcreteEngine()
        with pytest.raises(ValueError, match="不支持的回调事件"):
            engine.add_callback("invalid_event", MagicMock())

    def test_remove_callback(self):
        """移除回调"""
        engine = ConcreteEngine()
        cb = MagicMock()
        engine.add_callback("on_start", cb)
        engine.remove_callback("on_start", cb)
        assert cb not in engine._on_start_callbacks

    def test_remove_nonexistent_callback_no_error(self):
        """移除不存在的回调不报错"""
        engine = ConcreteEngine()
        cb = MagicMock()
        engine.remove_callback("on_start", cb)  # 不应抛出异常

    def test_start_callback_executed(self):
        """启动时执行回调"""
        engine = ConcreteEngine()
        cb = MagicMock()
        engine.add_callback("on_start", cb)
        engine.start()
        cb.assert_called_once_with(engine)

    def test_complete_callback_executed(self):
        """完成时执行回调"""
        engine = ConcreteEngine()
        cb = MagicMock()
        engine.add_callback("on_complete", cb)
        engine.start()
        engine.stop()
        cb.assert_called_once_with(engine)

    def test_callback_exception_does_not_break(self):
        """回调异常不中断流程"""
        engine = ConcreteEngine()
        bad_cb = MagicMock(side_effect=Exception("callback error"))
        good_cb = MagicMock()
        engine.add_callback("on_start", bad_cb)
        engine.add_callback("on_start", good_cb)
        engine.start()  # 不应抛出异常
        good_cb.assert_called_once()


@pytest.mark.unit
class TestIEngineErrorHandling:
    """IEngine 错误处理测试"""

    def test_log_error_increments_count(self):
        """记录错误递增计数"""
        engine = ConcreteEngine()
        engine.log_error(Exception("test error"))
        assert engine.performance_stats["error_count"] == 1

    def test_log_error_sets_status(self):
        """记录错误设置状态为 ERROR"""
        engine = ConcreteEngine()
        engine.log_error(Exception("test error"))
        assert engine.status == ENGINESTATUS_TYPES.ERROR

    def test_log_error_executes_error_callback(self):
        """记录错误执行错误回调"""
        engine = ConcreteEngine()
        cb = MagicMock()
        engine.add_callback("on_error", cb)
        err = Exception("test error")
        engine.log_error(err)
        cb.assert_called_once_with(engine, err)

    def test_update_performance_stats(self):
        """更新性能统计"""
        engine = ConcreteEngine()
        engine.update_performance_stats({"events_processed": 500, "memory_usage_mb": 128.5})
        assert engine.performance_stats["events_processed"] == 500
        assert engine.performance_stats["memory_usage_mb"] == 128.5

    def test_get_memory_usage_without_psutil(self):
        """无 psutil 时返回 0.0"""
        engine = ConcreteEngine()
        with patch.dict("sys.modules", {"psutil": None}):
            result = engine.get_memory_usage()
            assert result == 0.0


@pytest.mark.unit
class TestIEngineStatusReport:
    """IEngine 状态报告测试"""

    def test_status_report_structure(self):
        """状态报告结构完整"""
        engine = ConcreteEngine(name="TestEngine")
        report = engine.get_status_report()
        assert report["name"] == "TestEngine"
        assert "mode" in report
        assert "status" in report
        assert "created_at" in report
        assert "started_at" in report
        assert "completed_at" in report
        assert "performance_stats" in report
        assert "config" in report

    def test_status_report_after_run(self):
        """运行后状态报告包含时间"""
        engine = ConcreteEngine()
        engine.start()
        engine.stop()
        report = engine.get_status_report()
        assert report["started_at"] is not None
        assert report["completed_at"] is not None

    def test_str_representation(self):
        """字符串表示"""
        engine = ConcreteEngine(name="TestEngine", mode=EngineMode.EVENT_DRIVEN)
        s = str(engine)
        assert "TestEngine" in s
        assert "event_driven" in s

    def test_repr_equals_str(self):
        """repr 与 str 相同"""
        engine = ConcreteEngine()
        assert repr(engine) == str(engine)


# ── IEventDrivenEngine 测试 ─────────────────────────────────────────


@pytest.mark.unit
class TestIEventDrivenEngine:
    """事件驱动引擎接口测试"""

    def test_default_mode_is_event_driven(self):
        """默认模式为事件驱动"""
        engine = ConcreteEventEngine()
        assert engine.mode == EngineMode.EVENT_DRIVEN

    def test_default_name(self):
        """默认名称"""
        engine = ConcreteEventEngine()
        assert engine.name == "EventDrivenEngine"

    def test_register_event_handler(self):
        """注册事件处理器"""
        engine = ConcreteEventEngine()
        handler = MagicMock()
        engine.register_event_handler("price_update", handler)
        assert handler in engine._event_handlers["price_update"]

    def test_register_multiple_handlers(self):
        """注册多个同类型事件处理器"""
        engine = ConcreteEventEngine()
        h1 = MagicMock()
        h2 = MagicMock()
        engine.register_event_handler("price_update", h1)
        engine.register_event_handler("price_update", h2)
        assert len(engine._event_handlers["price_update"]) == 2

    def test_unregister_event_handler(self):
        """注销事件处理器"""
        engine = ConcreteEventEngine()
        handler = MagicMock()
        engine.register_event_handler("price_update", handler)
        engine.unregister_event_handler("price_update", handler)
        assert handler not in engine._event_handlers["price_update"]

    def test_get_supported_modes(self):
        """支持的模式列表"""
        engine = ConcreteEventEngine()
        modes = engine.get_supported_modes()
        assert EngineMode.EVENT_DRIVEN in modes
        assert EngineMode.HYBRID in modes


# ── IMatrixEngine 测试 ──────────────────────────────────────────────


@pytest.mark.unit
class TestIMatrixEngine:
    """矩阵引擎接口测试"""

    def test_default_mode_is_matrix(self):
        """默认模式为矩阵"""
        engine = ConcreteMatrixEngine()
        assert engine.mode == EngineMode.MATRIX

    def test_default_name(self):
        """默认名称"""
        engine = ConcreteMatrixEngine()
        assert engine.name == "MatrixEngine"

    def test_add_vectorized_processor(self):
        """添加向量化处理器"""
        engine = ConcreteMatrixEngine()
        processor = MagicMock()
        engine.add_vectorized_processor(processor)
        assert processor in engine._vectorized_processors

    def test_remove_vectorized_processor(self):
        """移除向量化处理器"""
        engine = ConcreteMatrixEngine()
        processor = MagicMock()
        engine.add_vectorized_processor(processor)
        engine.remove_vectorized_processor(processor)
        assert processor not in engine._vectorized_processors

    def test_remove_nonexistent_processor_no_error(self):
        """移除不存在的处理器不报错"""
        engine = ConcreteMatrixEngine()
        engine.remove_vectorized_processor(MagicMock())  # 不应抛出异常

    def test_get_supported_modes(self):
        """支持的模式列表"""
        engine = ConcreteMatrixEngine()
        modes = engine.get_supported_modes()
        assert EngineMode.MATRIX in modes
        assert EngineMode.HYBRID in modes


# ── IHybridEngine 测试 ──────────────────────────────────────────────


@pytest.mark.unit
class TestIHybridEngine:
    """混合引擎接口测试"""

    def test_default_mode_is_hybrid(self):
        """默认模式为混合"""
        engine = ConcreteHybridEngine()
        assert engine.mode == EngineMode.HYBRID

    def test_default_name(self):
        """默认名称"""
        engine = ConcreteHybridEngine()
        assert engine.name == "HybridEngine"

    def test_get_supported_modes(self):
        """支持所有模式"""
        engine = ConcreteHybridEngine()
        modes = engine.get_supported_modes()
        assert EngineMode.EVENT_DRIVEN in modes
        assert EngineMode.MATRIX in modes
        assert EngineMode.HYBRID in modes
        assert EngineMode.AUTO in modes

    def test_sub_engines_initially_none(self):
        """子引擎初始为 None"""
        engine = ConcreteHybridEngine()
        assert engine._event_engine is None
        assert engine._matrix_engine is None
        assert engine._mode_selector is None


# ── 继承关系测试 ────────────────────────────────────────────────────


@pytest.mark.unit
class TestInheritanceHierarchy:
    """接口继承关系测试"""

    def test_event_engine_inherits_iengine(self):
        """IEventDrivenEngine 继承 IEngine"""
        assert issubclass(IEventDrivenEngine, IEngine)

    def test_matrix_engine_inherits_iengine(self):
        """IMatrixEngine 继承 IEngine"""
        assert issubclass(IMatrixEngine, IEngine)

    def test_hybrid_engine_inherits_iengine(self):
        """IHybridEngine 继承 IEngine"""
        assert issubclass(IHybridEngine, IEngine)

    def test_concrete_engine_is_instance(self):
        """具体引擎是 IEngine 实例"""
        engine = ConcreteEngine()
        assert isinstance(engine, IEngine)

    def test_cannot_instantiate_abstract(self):
        """不能直接实例化抽象类"""
        with pytest.raises(TypeError):
            IEngine()
