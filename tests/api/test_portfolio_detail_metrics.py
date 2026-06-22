# Issue: #5686 — Portfolio Detail 响应缺 performance metrics（annual_return 等），与 List schema 不一致
# Upstream: api.api.portfolio.list_portfolios (已有 metrics 计算 L209-224)
# Downstream: _compute_portfolio_metrics (新提取 helper，list/detail 共用) + get_portfolio detail 端点
# Role: 验证 (1) helper 在 backtest/非backtest 模式下正确计算 metrics；(2) detail 端点响应含 metrics 字段

"""
Portfolio Detail metrics schema 一致性测试

真实场景：list 端点返回 annual_return/sharpe_ratio/max_drawdown/win_rate/backtest_count/
last_backtest_date，但 detail 端点的 data dict 构造时漏了全部 metrics 字段，
前端 detail 页拿不到 performance metrics，无法与 list 统一数据模型。

修复：提取 _compute_portfolio_metrics(p, mode_int) 共享 helper（list 内联逻辑抽出），
list + detail 共用；detail data dict 补齐 metrics + related 字段。
"""

import pytest
from unittest.mock import patch, MagicMock


class TestComputePortfolioMetrics:
    """#5686 切片1: _compute_portfolio_metrics 在两种模式下正确计算 metrics"""

    def test_backtest_mode_uses_latest_backtest_metrics(self):
        """backtest 模式 → 走 _get_latest_backtest_metrics + _count_backtests"""
        from api.portfolio import _compute_portfolio_metrics
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        p = MagicMock()
        p.uuid = "p1"

        with patch("api.portfolio._get_latest_backtest_metrics",
                   return_value={"annual_return": 0.15, "sharpe_ratio": 1.2,
                                 "max_drawdown": -0.1, "win_rate": 0.6,
                                 "last_backtest_date": "2026-01-01"}), \
             patch("api.portfolio._count_backtests", return_value=3):
            result = _compute_portfolio_metrics(p, PORTFOLIO_MODE_TYPES.BACKTEST.value)

        assert result["annual_return"] == 0.15
        assert result["sharpe_ratio"] == 1.2
        assert result["max_drawdown"] == -0.1
        assert result["win_rate"] == 0.6
        assert result["backtest_count"] == 3
        assert result["last_backtest_date"] == "2026-01-01"

    def test_non_backtest_mode_uses_model_fields(self):
        """非 backtest 模式 → 从 portfolio 模型字段取，backtest_count=0"""
        from api.portfolio import _compute_portfolio_metrics
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        p = MagicMock()
        p.uuid = "p1"
        p.annual_return = 0.08
        p.sharpe_ratio = 0.9
        p.max_drawdown = -0.05
        p.win_rate = 0.55

        with patch("api.portfolio._get_latest_backtest_metrics") as mock_metrics:
            result = _compute_portfolio_metrics(p, PORTFOLIO_MODE_TYPES.LIVE.value)

        assert result["annual_return"] == 0.08
        assert result["sharpe_ratio"] == 0.9
        assert result["max_drawdown"] == -0.05
        assert result["win_rate"] == 0.55
        assert result["backtest_count"] == 0
        mock_metrics.assert_not_called()  # 非 backtest 不查回测指标

    def test_returns_all_six_fields(self):
        """返回 dict 必须含 6 个字段（schema 完整性，供 list/detail 共用）"""
        from api.portfolio import _compute_portfolio_metrics
        from ginkgo.enums import PORTFOLIO_MODE_TYPES

        p = MagicMock()
        p.uuid = "p1"
        p.annual_return = 0
        p.sharpe_ratio = 0
        p.max_drawdown = 0
        p.win_rate = 0

        result = _compute_portfolio_metrics(p, PORTFOLIO_MODE_TYPES.LIVE.value)

        required = {"annual_return", "sharpe_ratio", "max_drawdown",
                    "win_rate", "backtest_count", "last_backtest_date"}
        assert required.issubset(result.keys()), f"缺字段: {required - set(result.keys())}"


def _make_portfolio_model(uuid="p1", mode=0):
    """构造 detail 端点用的 portfolio 模型 mock"""
    pm = MagicMock()
    pm.uuid = uuid
    pm.name = "test"
    pm.mode = mode
    pm.state = 0
    pm.initial_capital = 100000.0
    pm.cash = 95000.0
    pm.create_at = None
    return pm


def _make_result(data, success=True):
    r = MagicMock()
    r.is_success = MagicMock(return_value=success)
    r.data = data
    return r


class TestDetailResponseIncludesMetrics:
    """#5686 切片2: get_portfolio (detail) 响应含 performance metrics + related（与 list 统一）"""

    @pytest.mark.asyncio
    async def test_detail_includes_all_metrics_fields(self):
        """detail data 必须含 list 的全部 metrics 字段 + related（schema 统一）"""
        from api.portfolio import get_portfolio

        pm = _make_portfolio_model(mode=0)  # BACKTEST

        ps = MagicMock()
        ps.get.return_value = _make_result(pm)
        ps.is_portfolio_frozen.return_value = False

        ms = MagicMock()
        ms.get_portfolio_mappings.return_value = _make_result([], success=False)

        with patch("api.portfolio.get_portfolio_service", return_value=ps), \
             patch("api.portfolio.get_mapping_service", return_value=ms), \
             patch("api.portfolio.get_file_service", return_value=MagicMock()), \
             patch("api.portfolio._get_latest_backtest_metrics",
                   return_value={"annual_return": 0.12, "sharpe_ratio": 1.1,
                                 "max_drawdown": -0.08, "win_rate": 0.55,
                                 "last_backtest_date": "2026-06-01"}), \
             patch("api.portfolio._count_backtests", return_value=2), \
             patch("api.portfolio._get_related_portfolios", return_value=[]):
            result = await get_portfolio("p1")

        data = result["data"]
        # 与 list 共享的全部字段
        for field in ("annual_return", "sharpe_ratio", "max_drawdown",
                      "win_rate", "backtest_count", "last_backtest_date", "related"):
            assert field in data, f"detail 响应缺字段 {field}"
        assert data["annual_return"] == 0.12
        assert data["backtest_count"] == 2
        assert data["last_backtest_date"] == "2026-06-01"
        assert data["related"] == []


class TestListMetricsRegression:
    """#5686 切片3: list 端点改调 _compute_portfolio_metrics 后 metrics 不变（特征化基线）"""

    @pytest.mark.asyncio
    async def test_list_metrics_fields_preserved(self):
        """list 响应 metrics 字段在 helper 重构后保持不变"""
        from api.portfolio import list_portfolios

        p = _make_portfolio_model(mode=0)  # BACKTEST
        ps = MagicMock()
        ps.list_paginated.return_value = MagicMock(
            success=True, data={"items": [p], "total": 1})
        ps.is_portfolio_frozen.return_value = False

        with patch("api.portfolio.get_portfolio_service", return_value=ps), \
             patch("api.portfolio._get_latest_backtest_metrics",
                   return_value={"annual_return": 0.2, "sharpe_ratio": 1.5,
                                 "max_drawdown": -0.12, "win_rate": 0.6,
                                 "last_backtest_date": "2026-05-01"}), \
             patch("api.portfolio._count_backtests", return_value=4), \
             patch("api.portfolio._get_related_portfolios", return_value=[]):
            result = await list_portfolios(mode=None, page=0, page_size=20, keyword=None)

        item = result["data"][0]
        assert item["annual_return"] == 0.2
        assert item["sharpe_ratio"] == 1.5
        assert item["max_drawdown"] == -0.12
        assert item["win_rate"] == 0.6
        assert item["backtest_count"] == 4
        assert item["last_backtest_date"] == "2026-05-01"
