# Issue #6048: trading API position_value/total_asset 从持仓市值计算（接力 #6363 的下一切片）
# Upstream: api.api.trading._compute_position_value (new helper)
# Downstream: api.api.trading.list_paper_accounts / get_paper_account
# Role: 验证 position_value = Σ market_value，total_asset = cash + position_value。

"""
#6048 子集测试：trading 端点 position_value/total_asset 硬编码零值。

``list_paper_accounts`` (trading.py:184) 和 ``get_paper_account`` (trading.py:274) 的
``position_value`` 字段是 TODO 桩（固定 0），``total_asset`` 只含现金（不含持仓市值）。
``_query_positions`` 已返回含 ``market_value`` 的 dict（trading.py:560），但端点未求和。

本测试验证 ``_compute_position_value`` helper 与端点接线：
- ``position_value`` = Σ positions[i].market_value
- ``total_asset`` = cash + position_value

与 #6363（``_query_positions``/``_query_orders`` 填 name）不同 hunk，零重叠。
``today_pnl``/``total_pnl`` 留后续 slice（需 result_service 聚合，涉
[[arch_analyzer_read_page_size]] limit 截断陷阱）。
"""
import asyncio
from types import SimpleNamespace

import pytest
from unittest.mock import patch, MagicMock

from ginkgo.libs import GCONF


@pytest.fixture(autouse=True)
def _ensure_debug():
    GCONF.set_debug(True)


def run_async(coro):
    return asyncio.run(coro)


class TestComputePositionValue:
    """_compute_position_value 从 positions 的 market_value 求和（#6048）。"""

    def test_empty_positions_returns_zero(self):
        """空持仓 position_value = 0。"""
        from api.trading import _compute_position_value

        assert _compute_position_value([]) == 0

    def test_single_position_sums_market_value(self):
        """单持仓 position_value = market_value。"""
        from api.trading import _compute_position_value

        positions = [{"code": "000001", "market_value": 1500.0}]
        assert _compute_position_value(positions) == 1500.0

    def test_multiple_positions_sum_all(self):
        """多持仓 position_value = Σ market_value。"""
        from api.trading import _compute_position_value

        positions = [
            {"code": "000001", "market_value": 1500.0},
            {"code": "600000", "market_value": 2300.5},
            {"code": "000002", "market_value": 800.0},
        ]
        assert _compute_position_value(positions) == 4600.5

    def test_missing_market_value_key_treated_as_zero(self):
        """缺 market_value 键的 position 按 0 计（容错，不崩）。"""
        from api.trading import _compute_position_value

        positions = [
            {"code": "000001", "market_value": 1000.0},
            {"code": "600000"},  # 缺 market_value
        ]
        assert _compute_position_value(positions) == 1000.0


class TestGetPaperAccountPositionValue:
    """get_paper_account position_value/total_asset 从持仓市值计算（#6048）。"""

    def test_position_value_sums_positions_market_value(self):
        """position_value = Σ market_value, total_asset = cash + position_value。"""
        from api.trading import get_paper_account

        portfolio = SimpleNamespace(
            uuid="acc-1", name="test", initial_capital=100000,
            cash=80000, create_at=None,
        )
        positions = [
            {"code": "000001", "market_value": 1500.0},
            {"code": "600000", "market_value": 2300.0},
        ]

        with patch("api.trading._require_portfolio", return_value=[portfolio]), \
             patch("api.trading._query_positions", return_value=positions), \
             patch("api.trading._query_orders", return_value=[]):
            result = run_async(get_paper_account("acc-1"))

        data = result["data"]
        assert data["position_value"] == 3800.0
        assert data["total_asset"] == 83800.0  # 80000 cash + 3800

    def test_empty_positions_position_value_zero_total_asset_is_cash(self):
        """空持仓 position_value=0, total_asset=cash（不再丢持仓市值以外的逻辑）。"""
        from api.trading import get_paper_account

        portfolio = SimpleNamespace(
            uuid="acc-1", name="test", initial_capital=100000,
            cash=50000, create_at=None,
        )

        with patch("api.trading._require_portfolio", return_value=[portfolio]), \
             patch("api.trading._query_positions", return_value=[]), \
             patch("api.trading._query_orders", return_value=[]):
            result = run_async(get_paper_account("acc-1"))

        data = result["data"]
        assert data["position_value"] == 0
        assert data["total_asset"] == 50000.0


class TestListPaperAccountsPositionValue:
    """list_paper_accounts 每个账户 position_value 从其持仓计算（#6048）。"""

    def test_each_account_position_value_from_its_positions(self):
        """多账户各自 position_value 独立计算, total_asset = cash + position_value。"""
        from api.trading import list_paper_accounts
        from ginkgo.data.services.base_service import ServiceResult

        p1 = SimpleNamespace(uuid="acc-1", name="a", initial_capital=100000,
                             cash=90000, create_at=None)
        p2 = SimpleNamespace(uuid="acc-2", name="b", initial_capital=200000,
                             cash=150000, create_at=None)

        positions_map = {
            "acc-1": [{"code": "000001", "market_value": 1000.0}],
            "acc-2": [{"code": "600000", "market_value": 2000.0},
                      {"code": "000002", "market_value": 500.0}],
        }

        mock_service = MagicMock()
        mock_service.get.return_value = ServiceResult.success(data=[p1, p2])

        with patch("api.trading._get_portfolio_service", return_value=mock_service), \
             patch("api.trading._query_positions",
                   side_effect=lambda aid: positions_map.get(aid, [])):
            result = run_async(list_paper_accounts())

        accounts = result["data"]
        assert accounts[0]["position_value"] == 1000.0
        assert accounts[0]["total_asset"] == 91000.0  # 90000 + 1000
        assert accounts[1]["position_value"] == 2500.0
        assert accounts[1]["total_asset"] == 152500.0  # 150000 + 2500
