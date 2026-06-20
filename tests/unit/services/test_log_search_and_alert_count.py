"""TDD tests for #5553: alert_service._count_error_pattern -> search_logs
签名不匹配 TypeError 杀死整个告警管线。

根因: search_logs(keyword, log_type, limit, offset) 不接受 level/time_start/time_end,
而 _count_error_pattern 传了这些 kwargs -> TypeError。
修复: search_logs 增加可选 level/time_start/time_end 过滤（向后兼容）。
"""
import inspect
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


class TestSearchLogsAcceptsLevelAndTimeFilters:
    """#5553: search_logs 必须接受 level/time_start/time_end。"""

    def test_search_logs_signature_has_optional_filters(self):
        from ginkgo.services.logging.log_service import LogService
        sig = inspect.signature(LogService.search_logs)
        params = sig.parameters
        assert "level" in params, "search_logs 应支持 level 过滤（#5553）"
        assert "time_start" in params, "search_logs 应支持 time_start 过滤（#5553）"
        assert "time_end" in params, "search_logs 应支持 time_end 过滤（#5553）"
        # 向后兼容：新增参数须有默认值
        assert params["level"].default is None
        assert params["time_start"].default is None
        assert params["time_end"].default is None

    def test_search_logs_call_with_filters_does_not_raise(self):
        """带 level/time 过滤调用不应 TypeError（mock engine 返回空）。"""
        from ginkgo.services.logging.log_service import LogService

        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []
        engine = MagicMock()
        engine.get_session.return_value.__enter__ = MagicMock(return_value=session)
        engine.get_session.return_value.__exit__ = MagicMock(return_value=False)

        svc = LogService(engine=engine)
        # 修复前: TypeError（unexpected keyword 'level'）
        # 修复后: 返回 []（空结果）
        result = svc.search_logs(
            keyword="timeout",
            level="ERROR",
            time_start=datetime.now() - timedelta(minutes=5),
            time_end=datetime.now(),
            limit=100,
        )
        assert isinstance(result, list)


class TestCountErrorPatternReturnsInt:
    """#5553: _count_error_pattern 不应 TypeError，应返回 int。"""

    def _make_svc(self):
        session = MagicMock()
        session.execute.return_value.scalars.return_value.all.return_value = []
        db_engine = MagicMock()
        db_engine.get_session.return_value.__enter__ = MagicMock(return_value=session)
        db_engine.get_session.return_value.__exit__ = MagicMock(return_value=False)
        with patch("ginkgo.services.logging.alert_service.GCONF"):
            from ginkgo.services.logging.alert_service import AlertService
            svc = AlertService(redis_client=MagicMock(), db_engine=db_engine)
        return svc

    def test_count_error_pattern_returns_int(self):
        svc = self._make_svc()
        # 修复前: TypeError（search_logs 不接受 level/time_start/time_end）
        # 修复后: 返回 int（0，因为 mock 返回空）
        result = svc._count_error_pattern(pattern="ERROR.*timeout", window_minutes=5, level="ERROR")
        assert isinstance(result, int)
        assert result == 0
