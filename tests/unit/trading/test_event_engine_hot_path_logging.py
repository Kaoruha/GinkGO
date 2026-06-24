"""#3869 回测热路径日志降级行为测试。

热路径（put / _process / main loop）每事件产生 6-8 条 INFO 日志 + f-string
格式化，回测数百万事件 → 数千万次日志开销。owner 复核（2026-06-20）确认
仍存在。

行为契约（修复后）：
- put / _process 热路径不再产生 INFO 级噪音日志（降级为 DEBUG）
- 功能不变：事件正确入队、统计计数正确更新
"""
import logging
import threading
from queue import Queue
from unittest.mock import MagicMock, PropertyMock

import pytest

from ginkgo.libs import GLOG
from ginkgo.trading.engines.event_engine import EventEngine


def _make_lightweight_engine() -> EventEngine:
    """轻量装配 EventEngine（避开 BaseEngine 的 entities 延迟导入重依赖）。

    保留 _enhance_event / _get_next_sequence_number 等方法绑定，仅设 put() /
    _process() 依赖的数据属性。
    """
    engine = object.__new__(EventEngine)
    engine._engine_id = "test-engine-id"
    engine._task_id = "test-task-id"
    engine._sequence_number = 0
    engine._sequence_lock = threading.Lock()
    engine._event_queue = Queue(maxsize=100)
    engine._queue_lock = threading.Lock()
    engine._stats_lock = threading.Lock()
    engine._event_stats = {
        "total_events": 0,
        "completed_events": 0,
        "failed_events": 0,
        "processing_start_time": None,
    }
    engine._processed_events_count = 0
    engine._processing_start_time = None
    engine._handlers = {}
    engine._general_handlers = []
    engine.name = "test-engine"
    # now 是 EventEngine @property（返回 datetime.now()），无需装配
    return engine


def _make_event() -> MagicMock:
    """构造测试事件（event.order=None 使日志走 'NO_ORDER' 分支，无 MagicMock 切片）。"""
    event = MagicMock()
    event.event_type = "TEST_EVENT"
    event.order = None
    event.sequence_number = 0
    return event


class TestHotPathLoggingSilenced:
    """热路径 INFO 日志应降级为 DEBUG（默认 INFO 级别下静默）。"""

    def test_put_does_not_emit_info_on_hot_path(self, monkeypatch):
        """put() 入队路径不再产生 🔍 INFO 噪音，且事件正确入队。"""
        engine = _make_lightweight_engine()
        event = _make_event()
        info_calls = []
        monkeypatch.setattr(
            "ginkgo.trading.engines.event_engine.GLOG.INFO",
            lambda msg: info_calls.append(msg),
        )

        engine.put(event)

        hot_path_info = [m for m in info_calls if "EVENT ENGINE" in m]
        assert hot_path_info == [], f"put 热路径仍泄露 INFO: {hot_path_info}"
        # 功能不变：事件已入队
        assert not engine._event_queue.empty()
        assert engine._event_queue.qsize() == 1

    def test_process_does_not_emit_info_on_hot_path(self, monkeypatch):
        """_process() 处理路径不再产生 🔍 INFO 噪音，且 completed 统计正确。"""
        engine = _make_lightweight_engine()
        event = _make_event()
        info_calls = []
        monkeypatch.setattr(
            "ginkgo.trading.engines.event_engine.GLOG.INFO",
            lambda msg: info_calls.append(msg),
        )

        engine._process(event)

        hot_path_info = [m for m in info_calls if "EVENT ENGINE" in m]
        assert hot_path_info == [], f"_process 热路径仍泄露 INFO: {hot_path_info}"
        # 功能不变：completed 统计 +1
        assert engine._event_stats["completed_events"] == 1
        assert engine._processed_events_count == 1

    def test_put_still_logs_debug_for_diagnostics(self, monkeypatch):
        """回归锁：降级后 DEBUG 诊断日志仍在（put 成功入队仍可追踪，仅级别下调）。

        注：守卫语义下 DEBUG 仅在 DEBUG 启用时输出，故此处须显式 enable
        才符合「诊断仍可追踪」本意（与 TestHotPathDebugFStringLaziness 对齐）。
        """
        engine = _make_lightweight_engine()
        event = _make_event()
        debug_calls = []
        monkeypatch.setattr(
            "ginkgo.trading.engines.event_engine.GLOG.DEBUG",
            lambda msg: debug_calls.append(msg),
        )
        monkeypatch.setattr(GLOG.logger, "isEnabledFor", lambda lvl: True)

        engine.put(event)

        # put 成功后应有一条 DEBUG（Event queued ... seq=...）
        assert any("queued" in m for m in debug_calls), \
            f"put 应保留 DEBUG 诊断日志，实际 DEBUG: {debug_calls}"


# review #6317 打回点：INFO→DEBUG 降级缺 isEnabledFor 守卫。
# GLOG.DEBUG(msg: str) 接收预构造 str（logger.py:747），f-string 在调用处传参时已求值；
# DEBUG 内部 isEnabledFor 守卫（logger.py:749）只跳过 _emit I/O，不省格式化（arch_glog_debug_fstring_eager）。
# #3869 AC1 要求「GLOG.DEBUG + if GLOG.isEnabledFor(DEBUG) guard」——本组测试钉死该契约。
def _make_counting_event():
    """event_type 用 PropertyMock 计数——验证 DEBUG f-string 是否被守卫跳过。

    put 路径 event_type 仅出现在日志 f-string（无业务读），故访问次数==0 等价于
    「f-string 未 eager 求值」。order=None 走 'NO_ORDER' 分支避开 MagicMock 切片。
    """
    event = MagicMock()
    event.order = None
    event.sequence_number = 0
    counter = {"n": 0}

    def _count_event_type():
        counter["n"] += 1
        return "COUNTED"

    type(event).event_type = PropertyMock(side_effect=_count_event_type)
    return event, counter


class TestHotPathDebugFStringLaziness:
    """#3869 AC1：默认 INFO 级，热路径 DEBUG f-string 不得 eager 求值。"""

    def test_put_does_not_eagerly_format_debug_fstring_when_debug_disabled(self, monkeypatch):
        """put() 入队路径 4 处 DEBUG f-string（_enhance_event L628 + put L419/421/423）在
        DEBUG 禁用时不得 eager 求值——event_type 访问次数==0。"""
        engine = _make_lightweight_engine()
        event, counter = _make_counting_event()
        # 默认 INFO 级：DEBUG 关闭（模拟生产回测常态）
        monkeypatch.setattr(GLOG.logger, "isEnabledFor", lambda lvl: lvl >= logging.INFO)

        engine.put(event)

        assert counter["n"] == 0, (
            f"put() DEBUG f-string 仍 eager 求值 event_type {counter['n']} 次"
            "（缺 isEnabledFor 守卫，arch_glog_debug_fstring_eager）"
        )

    def test_process_skips_debug_calls_when_debug_disabled(self, monkeypatch):
        """_process() 业务逻辑（L434 event_type in handlers）必须执行，无法断 event_type==0；
        改断 GLOG.DEBUG 调用次数==0 验证守卫跳过诊断日志（L429/430 等）。"""
        engine = _make_lightweight_engine()
        event = _make_event()  # _handlers={} → 走 else 分支
        debug_calls = []
        monkeypatch.setattr(
            "ginkgo.trading.engines.event_engine.GLOG.DEBUG",
            lambda msg: debug_calls.append(msg),
        )
        monkeypatch.setattr(GLOG.logger, "isEnabledFor", lambda lvl: lvl >= logging.INFO)

        engine._process(event)

        assert debug_calls == [], (
            f"DEBUG 禁用时 _process 仍调 GLOG.DEBUG {len(debug_calls)} 次: {debug_calls}"
        )

    def test_put_still_emits_debug_when_enabled(self, monkeypatch):
        """回归锁：守卫不破坏 DEBUG 启用时的诊断日志（put 仍记录 'Event queued'）。"""
        engine = _make_lightweight_engine()
        event = _make_event()
        debug_calls = []
        monkeypatch.setattr(
            "ginkgo.trading.engines.event_engine.GLOG.DEBUG",
            lambda msg: debug_calls.append(msg),
        )
        monkeypatch.setattr(GLOG.logger, "isEnabledFor", lambda lvl: True)  # DEBUG 启用

        engine.put(event)

        assert any("queued" in m for m in debug_calls), (
            f"DEBUG 启用时 put 应记录诊断日志，实际: {debug_calls}"
        )
