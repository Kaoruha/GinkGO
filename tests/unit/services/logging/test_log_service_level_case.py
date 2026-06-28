# Upstream: src/ginkgo/services/logging/log_service.py
# Context: [[arch_log_level_lowercase_storage]] — ClickHouse level 列混大小写存储，
#          `==` 大小写敏感。search_logs 已用 func.lower() 双向归一修复（#6232），
#          但 query_backtest_logs / query_component_logs 仍用单边 level.upper()，
#          传 "ERROR" 匹配不到小写 "error" → CLI/portfolio_service 按级别过滤漏数据。
from unittest.mock import MagicMock

from ginkgo.services.logging.log_service import LogService


def _make_service_with_capturing_session():
    """装配 LogService（object.__new__ 避开 __init__ 的 get_db_connection 重依赖），
    mock session 捕获 execute 收到的 query，供断言 where clause 的 level 归一。"""
    svc = object.__new__(LogService)
    svc._logger = MagicMock()
    # _log_operation_start/end 继承自 BaseService，mock 成 no-op
    svc._log_operation_start = lambda *a, **kw: None
    svc._log_operation_end = lambda *a, **kw: None

    captured = {"query": None}

    mock_session = MagicMock()

    def _execute(q):
        captured["query"] = q
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        return result

    mock_session.execute.side_effect = _execute
    mock_engine = MagicMock()
    mock_engine.get_session.return_value.__enter__.return_value = mock_session
    mock_engine.get_session.return_value.__exit__.return_value = False
    svc._engine = mock_engine
    return svc, captured


def _compiled_sql(query) -> str:
    """编译 query 为含字面量的 SQL（保留原始大小写）。

    保留大小写是关键：bug 代码参数='ERROR'（大写），修复后='error'（小写），
    若整体 .lower() 会掩盖该差异致假绿。
    """
    return str(query.compile(compile_kwargs={"literal_binds": True}))


class TestQueryLogLevelCaseInsensitive:
    """[[arch_log_level_lowercase_storage]] — query_*_logs level 过滤须双向 lower 归一。"""

    def test_query_backtest_logs_uses_double_lower_for_level(self):
        """query_backtest_logs level 过滤应双向 lower（列 + 参数），对齐 search_logs。

        三断言共同区分 bug（单边 .upper()）与修复（双向 func.lower）：
        - lower( 函数名存在（列侧归一）
        - 参数小写 'error'（参数侧归一）
        - 参数非大写 'ERROR'（反向锁，单边 .upper() 会留大写）
        """
        svc, captured = _make_service_with_capturing_session()
        svc.query_backtest_logs(level="ErRoR")

        assert captured["query"] is not None, "query 未被 session.execute 捕获"
        sql = _compiled_sql(captured["query"])
        assert "lower(" in sql.lower(), (
            f"列侧未用 func.lower 归一（单边 .upper() 漏小写存储）: {sql}"
        )
        assert "'error'" in sql, f"参数未归一小写（应为 'error'）: {sql}"
        assert "'ERROR'" not in sql, (
            f"参数仍为大写 'ERROR'（单边 .upper() 未双向归一）: {sql}"
        )

    def test_query_component_logs_uses_double_lower_for_level(self):
        """query_component_logs 同源 bug，同样须双向 lower。"""
        svc, captured = _make_service_with_capturing_session()
        svc.query_component_logs(level="WARNING")

        assert captured["query"] is not None, "query 未被 session.execute 捕获"
        sql = _compiled_sql(captured["query"])
        assert "lower(" in sql.lower(), f"列侧未用 func.lower 归一: {sql}"
        assert "'warning'" in sql, f"参数未归一小写: {sql}"
        assert "'WARNING'" not in sql, (
            f"参数仍为大写 'WARNING'（单边 .upper() 未双向归一）: {sql}"
        )

    def test_query_backtest_logs_no_level_does_not_filter(self):
        """回归锁：level=None（默认）时不加 level 条件（if level 守卫）。"""
        svc, captured = _make_service_with_capturing_session()
        svc.query_backtest_logs()  # 无 level

        assert captured["query"] is not None
        sql = _compiled_sql(captured["query"])
        assert "'error'" not in sql and "'ERROR'" not in sql, (
            f"level=None 时不应注入级别过滤: {sql}"
        )
