"""#5567: node_graph 端点 500 响应不泄露 str(e) 内部细节。

接续 PR #6421（components.py 切片），同根因同修复模式：
`raise HTTPException(500, detail=f"...{str(e)}")` → `detail="..."`，
异常详情已在紧邻的 `logger.error(f"...: {str(e)}")` 记录，诊断不丢。

参考 [[arch_global_error_handler_trace_id]]：FastAPI 默认 HTTPException handler
精确匹配优先于全局 Exception handler，global_error_handler 的
isinstance(HTTPException) 分支是死代码，端点须自行脱敏。

覆盖 7 个 service-backed 可达端点。delete/duplicate/create_from_backtest
的 `except Exception` 不可达（try 体只 raise HTTPException 被
`except HTTPException: raise` 重抛），脱敏是防御性，不测死代码。
validate/compile 为纯逻辑/内部 import，service mock 不触发其 except。
"""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

# node_graph.py 行39 `from ._file_type import` 是相对导入，需保持包上下文。
# 自行 insert /repo/api/ 使 `api` 包可导入，node_graph 作为 api.node_graph，
# 相对导入 from ._file_type → api._file_type 正确解析（对齐
# [[arch_api_test_import_collapse]] 折叠约定；components 切片用 from components
# 顶层导入是因为 components.py 无相对导入，node_graph 不同）。
_api_dir = str(Path(__file__).parent.parent.parent / "api")
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

# config.py 全局 Settings() 需合法 SECRET_KEY
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-security-tests")

from api.node_graph import (  # noqa: E402
    add_file_to_portfolio,
    create_node_graph,
    get_node_graph,
    get_portfolio_mappings,
    list_node_graphs,
    remove_file_from_portfolio,
    update_node_graph,
)

# 模拟内部异常细节（SQL/表名/连接串/IP）——这些绝不应出现在 500 响应里
SENSITIVE = "SQL: SELECT * FROM secret_internal_table; conn=postgres://u:p@10.0.0.1/db"


def _raise_sensitive(*_a, **_kw):
    raise RuntimeError(SENSITIVE)


def _assert_sanitized(exc, expected_detail):
    """断言 500 响应不含敏感细节，detail 为 generic。"""
    assert exc.value.status_code == 500
    assert "SQL" not in exc.value.detail
    assert "secret_internal_table" not in exc.value.detail
    assert "postgres" not in exc.value.detail
    assert "10.0.0.1" not in exc.value.detail
    assert exc.value.detail == expected_detail


class TestListNodeGraphsSanitization:
    """list_node_graphs 500 响应 detail 不含异常内部细节。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.get_portfolio_graph.side_effect = _raise_sensitive
        with patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                # 传 portfolio_uuid 才会走 service.get_portfolio_graph 调用
                asyncio.run(list_node_graphs(portfolio_uuid="some-uuid"))

        _assert_sanitized(exc, "Error listing node graphs")


class TestGetNodeGraphSanitization:
    """get_node_graph 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.get_portfolio_graph.side_effect = _raise_sensitive
        with patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_node_graph("some-uuid"))

        _assert_sanitized(exc, "Error getting node graph")


class TestCreateNodeGraphSanitization:
    """create_node_graph 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.create_from_graph_editor.side_effect = _raise_sensitive
        with patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(create_node_graph(data=MagicMock()))

        _assert_sanitized(exc, "Error creating node graph")


class TestUpdateNodeGraphSanitization:
    """update_node_graph 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.update_from_graph_editor.side_effect = _raise_sensitive
        with patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(update_node_graph("some-uuid", data=MagicMock()))

        _assert_sanitized(exc, "Error updating node graph")


class TestGetPortfolioMappingsSanitization:
    """get_portfolio_mappings 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.get_portfolio_mappings.side_effect = _raise_sensitive
        with patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_portfolio_mappings("some-uuid"))

        _assert_sanitized(exc, "Error getting portfolio mappings")


class TestAddFileToPortfolioSanitization:
    """add_file_to_portfolio 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.add_file.side_effect = _raise_sensitive
        with patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                # file_type="strategy" 合法，_resolve_file_type 不抛，进 service.add_file
                asyncio.run(add_file_to_portfolio("some-uuid", "file-id", "strategy"))

        _assert_sanitized(exc, "Error adding file")


class TestRemoveFileFromPortfolioSanitization:
    """remove_file_from_portfolio 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.remove_file.side_effect = _raise_sensitive
        with patch("api.node_graph.get_portfolio_mapping_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(remove_file_from_portfolio("some-uuid", "file-id"))

        _assert_sanitized(exc, "Error removing file")
