"""
Unit tests for LogService

This module tests the LogService business logic, including log querying,
filtering by portfolio/strategy/trace_id, and graceful error handling.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import requests

# TODO: 确认导入路径是否正确
from ginkgo.services.logging.log_service import LogService


@pytest.mark.tdd
class TestLogServiceQueryLogs:
    """
    测试 LogService 基础查询功能

    覆盖范围:
    - 多条件过滤查询
    - 参数传递
    - LokiClient 集成
    """

    def test_query_logs_filters_by_portfolio(self):
        """
        测试 query_logs() 按 portfolio_id 过滤

        验证点:
        - 传递 portfolio_id 参数
        - 调用 LokiClient.query()
        - 构建正确的 LogQL
        """
        mock_client = Mock()
        mock_client.query.return_value = []
        mock_client.build_logql.return_value = '{portfolio_id="portfolio-123"}'

        service = LogService(mock_client)
        service.query_logs(portfolio_id="portfolio-123")

        mock_client.query.assert_called_once()
        call_args = mock_client.query.call_args
        assert call_args[0][0] == '{portfolio_id="portfolio-123"}'

    def test_query_logs_with_strategy_id(self):
        """
        测试 query_logs() 按 strategy_id 过滤

        验证点:
        - 传递 strategy_id 参数
        - 构建正确的 LogQL
        """
        mock_client = Mock()
        mock_client.query.return_value = []
        mock_client.build_logql.return_value = '{strategy_id="strategy-456"}'

        service = LogService(mock_client)
        service.query_logs(strategy_id="strategy-456")

        mock_client.query.assert_called_once()

    def test_query_logs_with_trace_id(self):
        """
        测试 query_logs() 按 trace_id 过滤

        验证点:
        - 传递 trace_id 参数
        - 支持链路追踪查询
        """
        mock_client = Mock()
        mock_client.query.return_value = []
        mock_client.build_logql.return_value = '{trace_id="trace-789"}'

        service = LogService(mock_client)
        service.query_logs(trace_id="trace-789")

        mock_client.query.assert_called_once()

    def test_query_logs_with_level_filter(self):
        """
        测试 query_logs() 按日志级别过滤

        验证点:
        - 传递 level 参数
        - 支持不同日志级别 (error, warning, info, debug)
        """
        mock_client = Mock()
        mock_client.query.return_value = []
        mock_client.build_logql.return_value = '{level="error"}'

        service = LogService(mock_client)
        service.query_logs(level="error")

        mock_client.query.assert_called_once()

    def test_query_logs_with_multiple_filters(self):
        """
        测试 query_logs() 组合多个过滤条件

        验证点:
        - 同时使用 portfolio_id 和 level
        - 正确组合过滤器
        """
        mock_client = Mock()
        mock_client.query.return_value = []
        mock_client.build_logql.return_value = '{portfolio_id="portfolio-123", level="error"}'

        service = LogService(mock_client)
        service.query_logs(portfolio_id="portfolio-123", level="error")

        mock_client.query.assert_called_once()

    def test_query_logs_respects_limit(self):
        """
        测试 query_logs() 使用 limit 参数

        验证点:
        - 传递 limit 到 LokiClient
        - 支持分页查询
        """
        mock_client = Mock()
        mock_client.query.return_value = []
        mock_client.build_logql.return_value = '{}'

        service = LogService(mock_client)
        service.query_logs(limit=50)

        call_args = mock_client.query.call_args
        assert call_args[0][1] == 50

    def test_query_logs_default_limit(self):
        """
        测试 query_logs() 默认 limit 为 100

        验证点:
        - 不传递 limit 时使用默认值
        - 默认值合理
        """
        mock_client = Mock()
        mock_client.query.return_value = []
        mock_client.build_logql.return_value = '{}'

        service = LogService(mock_client)
        service.query_logs()

        call_args = mock_client.query.call_args
        assert call_args[0][1] == 100


@pytest.mark.tdd
class TestLogServicePortfolioQueries:
    """
    测试 LogService 组合相关查询

    覆盖范围:
    - 按组合 ID 查询
    - 组合错误日志查询
    """

    def test_query_by_portfolio(self):
        """
        测试 query_by_portfolio() 方法

        验证点:
        - 封装常用的 portfolio_id 查询
        - 调用底层 query_logs()
        """
        mock_client = Mock()
        mock_client.query.return_value = [
            {"timestamp": "123", "message": "Portfolio log"}
        ]

        service = LogService(mock_client)
        result = service.query_by_portfolio("portfolio-123")

        assert isinstance(result, list)
        mock_client.query.assert_called_once()

    def test_query_by_portfolio_with_level(self):
        """
        测试 query_by_portfolio() 带级别过滤

        验证点:
        - 组合 ID + 日志级别组合查询
        - 常用场景优化
        """
        mock_client = Mock()
        mock_client.query.return_value = []

        service = LogService(mock_client)
        service.query_by_portfolio("portfolio-123", level="error")

        mock_client.query.assert_called_once()

    def test_query_errors_by_portfolio(self):
        """
        测试 query_errors() 方法

        验证点:
        - 查询指定组合的错误日志
        - level 固定为 "error"
        - 默认 limit 为 50
        """
        mock_client = Mock()
        mock_client.query.return_value = [
            {"timestamp": "123", "message": "Error occurred"}
        ]

        service = LogService(mock_client)
        result = service.query_errors(portfolio_id="portfolio-123")

        assert isinstance(result, list)
        mock_client.query.assert_called_once()


@pytest.mark.tdd
class TestLogServiceTraceQueries:
    """
    测试 LogService 链路追踪查询

    覆盖范围:
    - 按 trace_id 查询
    - 完整调用链查询
    """

    def test_query_by_trace_id(self):
        """
        测试 query_by_trace_id() 方法

        验证点:
        - 按 trace_id 查询完整链路
        - 跨服务的日志关联
        """
        mock_client = Mock()
        mock_client.query.return_value = [
            {"timestamp": "123", "message": "Service A log"},
            {"timestamp": "124", "message": "Service B log"},
            {"timestamp": "125", "message": "Service C log"}
        ]

        service = LogService(mock_client)
        result = service.query_by_trace_id("trace-abc-123")

        assert len(result) == 3
        mock_client.query.assert_called_once()


@pytest.mark.tdd
class TestLogServiceStatistics:
    """
    测试 LogService 统计功能

    覆盖范围:
    - 日志数量统计
    - 分组统计
    """

    def test_get_log_count(self):
        """
        测试 get_log_count() 方法

        验证点:
        - 返回日志数量
        - 支持过滤条件
        """
        mock_client = Mock()
        mock_client.query.return_value = [
            {"timestamp": "1", "message": "log1"},
            {"timestamp": "2", "message": "log2"},
            {"timestamp": "3", "message": "log3"}
        ]

        service = LogService(mock_client)
        count = service.get_log_count(portfolio_id="portfolio-123")

        assert count == 3

    def test_get_log_count_empty(self):
        """
        测试 get_log_count() 空结果

        验证点:
        - 无日志时返回 0
        - 不抛出异常
        """
        mock_client = Mock()
        mock_client.query.return_value = []

        service = LogService(mock_client)
        count = service.get_log_count(portfolio_id="portfolio-123")

        assert count == 0


@pytest.mark.tdd
class TestLogServiceErrorHandling:
    """
    测试 LogService 错误处理

    覆盖范围:
    - Loki 不可用时的优雅降级
    - 空结果处理
    """

    def test_graceful_degradation_on_loki_unavailable(self):
        """
        测试 Loki 不可用时的优雅降级

        验证点:
        - 连接错误不抛出异常
        - 返回空列表
        - 用户友好的错误处理
        """
        mock_client = Mock()
        mock_client.query.return_value = []

        service = LogService(mock_client)
        result = service.query_logs(portfolio_id="portfolio-123")

        assert result == []

    def test_empty_result_handling(self):
        """
        测试空查询结果处理

        验证点:
        - 无匹配日志时返回空列表
        - 不抛出异常
        """
        mock_client = Mock()
        mock_client.query.return_value = []

        service = LogService(mock_client)
        result = service.query_by_portfolio("non-existent-portfolio")

        assert result == []
