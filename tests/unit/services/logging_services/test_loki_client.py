"""
Unit tests for Loki HTTP Client

This module tests the LokiClient HTTP API integration, including query building,
response parsing, error handling, and graceful degradation.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

# TODO: 确认导入路径是否正确
from ginkgo.services.logging.clients.loki_client import LokiClient


@pytest.mark.tdd
class TestLokiClient:
    """
    测试 Loki HTTP 客户端

    覆盖范围:
    - HTTP 请求构建
    - LogQL 查询字符串构建
    - 响应解析
    - 错误处理和优雅降级
    """

    def test_query_builds_http_request(self):
        """
        测试 query() 方法构建正确 HTTP 请求

        验证点:
        - 调用 Loki HTTP API
        - 传递正确的查询参数
        - 使用正确的端点 URL
        """
        client = LokiClient("http://localhost:3100")

        with patch("requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"data": {"result": []}}
            mock_get.return_value = mock_response

            client.query('{level="error"}')

            # 验证请求参数
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert "localhost:3100" in call_args[0][0]
            assert call_args[1]["params"]["query"] == '{level="error"}'

    @patch("requests.get")
    def test_parse_response(self, mock_get):
        """
        测试响应解析

        验证点:
        - 正确解析 Loki 响应格式
        - 提取日志条目
        - 处理空结果
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "result": [
                    {"stream": {"level": "error"}, "values": [["1234567890", "log message"]]}
                ]
            }
        }
        mock_get.return_value = mock_response

        client = LokiClient("http://localhost:3100")
        result = client.query('{level="error"}')

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["timestamp"] == "1234567890"
        assert result[0]["message"] == "log message"

    @patch("requests.get")
    def test_parse_empty_response(self, mock_get):
        """
        测试空响应解析

        验证点:
        - 处理没有结果的情况
        - 返回空列表
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"result": []}}
        mock_get.return_value = mock_response

        client = LokiClient("http://localhost:3100")
        result = client.query('{level="error"}')

        assert result == []

    @patch("requests.get")
    def test_connection_error_returns_empty_list(self, mock_get):
        """
        测试连接错误时返回空列表

        验证点:
        - Loki 不可用时优雅降级
        - 连接错误不抛出异常
        - 返回空列表而不是崩溃
        """
        mock_get.side_effect = requests.exceptions.ConnectionError()

        client = LokiClient("http://localhost:3100")
        result = client.query('{level="error"}')

        assert result == []

    @patch("requests.get")
    def test_timeout_returns_empty_list(self, mock_get):
        """
        测试超时时返回空列表

        验证点:
        - 请求超时时优雅降级
        - 超时错误不抛出异常
        - 返回空列表
        """
        mock_get.side_effect = requests.exceptions.Timeout()

        client = LokiClient("http://localhost:3100")
        result = client.query('{level="error"}')

        assert result == []

    def test_build_logql_with_portfolio_id(self):
        """
        测试构建带 portfolio_id 的 LogQL

        验证点:
        - 正确构建 portfolio_id 过滤器
        - 格式符合 LogQL 语法
        """
        client = LokiClient("http://localhost:3100")
        logql = client.build_logql(portfolio_id="portfolio-123")

        assert logql == '{portfolio_id="portfolio-123"}'

    def test_build_logql_with_multiple_filters(self):
        """
        测试构建带多个过滤器的 LogQL

        验证点:
        - 正确组合多个过滤器
        - 使用逗号分隔
        - 格式符合 LogQL 语法
        """
        client = LokiClient("http://localhost:3100")
        logql = client.build_logql(
            portfolio_id="portfolio-123",
            strategy_id="strategy-456",
            level="error"
        )

        assert 'portfolio_id="portfolio-123"' in logql
        assert 'strategy_id="strategy-456"' in logql
        assert 'level="error"' in logql

    def test_build_logql_with_trace_id(self):
        """
        测试构建带 trace_id 的 LogQL

        验证点:
        - 正确构建 trace_id 过滤器
        - 支持链路追踪查询
        """
        client = LokiClient("http://localhost:3100")
        logql = client.build_logql(trace_id="trace-789")

        assert logql == '{trace_id="trace-789"}'

    def test_build_logql_empty_filters(self):
        """
        测试无过滤器时的 LogQL 构建

        验证点:
        - 空过滤器返回空选择器
        - 不破坏 LogQL 语法
        """
        client = LokiClient("http://localhost:3100")
        logql = client.build_logql()

        assert logql == "{}"

    @patch("requests.get")
    def test_query_respects_limit_parameter(self, mock_get):
        """
        测试 query() 方法使用 limit 参数

        验证点:
        - 传递 limit 到 HTTP 请求
        - 默认 limit 为 100
        """
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"result": []}}
        mock_get.return_value = mock_response

        client = LokiClient("http://localhost:3100")
        client.query('{level="error"}', limit=50)

        call_args = mock_get.call_args
        assert call_args[1]["params"]["limit"] == 50

    @patch("requests.get")
    def test_http_error_returns_empty_list(self, mock_get):
        """
        测试 HTTP 错误时返回空列表

        验证点:
        - 4xx/5xx 错误优雅降级
        - 不抛出异常
        - 返回空列表
        """
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_get.return_value = mock_response

        client = LokiClient("http://localhost:3100")
        result = client.query('{level="error"}')

        assert result == []
