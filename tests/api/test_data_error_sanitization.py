"""#5567: data.py 端点 500 响应不泄露 str(e) 内部细节。

接续 PR #6421（components.py）/ #6422（node_graph.py）切片，同根因同修复模式：
- HTTPException(500, detail=f"...{str(e)}") → detail="..."，异常详情已在紧邻的
  logger.error 记录，诊断不丢。
- helper get_tick_data_summary 的降级 dict 移除 "error": str(e) 字段（200 body 泄露）。

参考 [[arch_global_error_handler_trace_id]]：FastAPI 默认 HTTPException handler 精确匹配
优先于全局 Exception handler，global_error_handler 的 isinstance(HTTPException) 分支是
死代码，端点须自行脱敏。

覆盖 8 个可测泄露点。get_data_sources（792）try 体纯静态 dict 无 service 调用，
except 不可达，脱敏是防御性，不测死代码。
"""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

# data.py 无相对导入（grep ^from \. 为空），用顶层 from data import。
# 自行 insert /repo/api/ 使 `data` 顶层模块可导入（_API_DIR = api/，core 作为 api/core）。
# 对齐 components 切片（PR #6421）顶层导入约定。
_api_dir = str(Path(__file__).parent.parent.parent / "api")
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

# config.py 全局 Settings() 需合法 SECRET_KEY
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-security-tests")

from api.data import (  # noqa: E402
    DataUpdateRequest,
    get_adjust_factors,
    get_bars,
    get_data_stats,
    get_stockinfo,
    get_sync_history,
    get_tick_data_summary,
    get_ticks,
    sync_data,
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


class TestGetDataStatsSanitization:
    """get_data_stats 500 响应 detail 不含异常内部细节。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.count.side_effect = _raise_sensitive
        with patch("api.data.get_stockinfo_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_data_stats())

        _assert_sanitized(exc, "Failed to get data stats")


class TestGetTickDataSummarySanitization:
    """get_tick_data_summary helper 降级 dict 不含 error 字段（200 body 泄露）。"""

    def test_fallback_dict_excludes_error_field(self):
        # helper 接收 service 参数（不经 getter），stockinfo_service.get 抛 → except → 降级 dict
        mock_stockinfo = MagicMock()
        mock_stockinfo.get.side_effect = _raise_sensitive
        mock_tick = MagicMock()

        result = asyncio.run(get_tick_data_summary(mock_stockinfo, mock_tick, sample_size=10))

        # 降级 dict 仍含统计字段（零值），但绝不泄露异常文本
        assert "error" not in result
        assert "SQL" not in str(result)
        assert "secret_internal_table" not in str(result)
        assert "postgres" not in str(result)
        assert "10.0.0.1" not in str(result)
        assert result["stocks_with_tick_data"] == 0


class TestGetStockinfoSanitization:
    """get_stockinfo 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.search.side_effect = _raise_sensitive
        with patch("api.data.get_stockinfo_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                # search 触发 service.search 调用路径
                asyncio.run(get_stockinfo(search="600"))

        _assert_sanitized(exc, "Failed to get stock info")


class TestGetBarsSanitization:
    """get_bars 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.get.side_effect = _raise_sensitive
        with patch("api.data.get_bar_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_bars())

        _assert_sanitized(exc, "Failed to get bars")


class TestGetTicksSanitization:
    """get_ticks 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        # get_tick_service() 抛在 try 首行（code 校验之前），不传 code 即可触发
        with patch("api.data.get_tick_service", side_effect=_raise_sensitive):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_ticks())

        _assert_sanitized(exc, "Failed to get ticks")


class TestGetAdjustFactorsSanitization:
    """get_adjust_factors 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.get.side_effect = _raise_sensitive
        with patch("api.data.get_adjustfactor_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_adjust_factors())

        _assert_sanitized(exc, "Failed to get adjust factors")


class TestSyncDataSanitization:
    """sync_data 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        # record_start 在内层 try 之前（行 614），抛异常直达外层 except → 724 泄露点
        mock_svc = MagicMock()
        mock_svc.record_start.side_effect = _raise_sensitive
        with patch("api.data.get_sync_record_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(sync_data(DataUpdateRequest(type="stockinfo")))

        _assert_sanitized(exc, "Failed to update data")


class TestGetSyncHistorySanitization:
    """get_sync_history 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.get_history.side_effect = _raise_sensitive
        with patch("api.data.get_sync_record_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(get_sync_history())

        _assert_sanitized(exc, "Failed to get sync history")
