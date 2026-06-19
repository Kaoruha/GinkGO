"""#5553: alert_service._count_error_pattern 调 search_logs 时传了 level/time_start/time_end，
但 LogService.search_logs 签名无这些参数 → TypeError 被 except 静默吞 → count 恒 0 → 告警永不触发。

方案 A：扩展 LogService.search_logs 支持 level/time_start/time_end 过滤。

测试从「可观察症状」切入：告警计数不再因 TypeError 归零。
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

try:
    from ginkgo.services.logging.log_service import LogService
    from ginkgo.services.logging.alert_service import AlertService

    HAS = True
except ImportError:
    HAS = False


@pytest.mark.skipif(not HAS, reason="logging services not importable")
class TestAlertCountPattern5553:
    """#5553: 告警计数不再因 search_logs 签名缺失而 TypeError 归零"""

    def _make_log_svc(self):
        """构造 LogService + mock engine/session（不连真 ClickHouse）"""
        engine = MagicMock()
        session = MagicMock()
        engine.get_session.return_value.__enter__ = MagicMock(return_value=session)
        engine.get_session.return_value.__exit__ = MagicMock(return_value=False)
        return LogService(engine=engine), engine, session

    def _make_alert_svc(self):
        with patch("ginkgo.services.logging.alert_service.GCONF"):
            return AlertService(redis_client=MagicMock(), db_engine=MagicMock())

    @pytest.mark.unit
    def test_search_logs_accepts_level_and_time_filters(self):
        """tracer bullet: LogService.search_logs 须接受 level/time_start/time_end 参数

        alert_service._count_error_pattern 依赖这三个参数；当前签名缺失 → TypeError。
        只 mock 最底层 engine/session，让真实 search_logs 代码路径触发签名错误。
        修复前: TypeError: unexpected keyword argument 'level' (红)
        修复后: 接受参数返回 list (绿)
        """
        svc, _, session = self._make_log_svc()
        session.execute.return_value.scalars.return_value.all.return_value = []
        result = svc.search_logs(
            keyword="error",
            level="ERROR",
            time_start=datetime(2026, 1, 1),
            time_end=datetime(2026, 1, 2),
        )
        assert isinstance(result, list)

    @pytest.mark.unit
    def test_search_logs_filters_by_level(self):
        """#5553: level 参数应真正作为过滤条件（而非仅接受不用）"""
        svc, _, session = self._make_log_svc()
        session.execute.return_value.scalars.return_value.all.return_value = []
        svc.search_logs(keyword="error", level="ERROR")
        compiled = str(
            session.execute.call_args[0][0].compile(compile_kwargs={"literal_binds": True})
        )
        assert "ERROR" in compiled, "查询应含 level=ERROR 过滤"
        assert "level" in compiled.lower()

    @pytest.mark.unit
    def test_search_logs_filters_by_time_range(self):
        """#5553: time_start/time_end 应作为时间窗口过滤"""
        svc, _, session = self._make_log_svc()
        session.execute.return_value.scalars.return_value.all.return_value = []
        svc.search_logs(
            keyword="error",
            time_start=datetime(2026, 1, 1),
            time_end=datetime(2026, 1, 2),
        )
        compiled = str(
            session.execute.call_args[0][0].compile(compile_kwargs={"literal_binds": True})
        )
        assert "timestamp" in compiled.lower(), "查询应含 timestamp 时间窗口过滤"
        assert "2026-01-01" in compiled and "2026-01-02" in compiled

    @pytest.mark.unit
    def test_count_error_pattern_returns_real_count(self):
        """#5553 端到端: _count_error_pattern 返回 search_logs 真实计数（不再 TypeError 归 0）

        用真实 LogService（不 patch）+ mock 底层 engine/session，让真实 search_logs 走通。
        修复前: search_logs(level=...) TypeError → except 吞 → return 0 (红)
        修复后: 签名匹配 → execute → 5 条 → count == 5 (绿)
        """
        svc = self._make_alert_svc()
        session = svc._db_engine.get_session.return_value.__enter__.return_value

        class _FakeLog:
            """模拟日志行：_model_to_dict 遍历 __table__.columns（空）→ 返回 {}"""
            class _Table:
                columns = []

            __table__ = _Table()

        fake_logs = [_FakeLog() for _ in range(5)]
        session.execute.return_value.scalars.return_value.all.return_value = fake_logs

        count = svc._count_error_pattern("ERROR.*timeout", window_minutes=10, level="ERROR")
        assert count == 5, f"告警计数应为 5（search_logs 返回 5 条），实际 {count}（疑似异常被吞归零）"
