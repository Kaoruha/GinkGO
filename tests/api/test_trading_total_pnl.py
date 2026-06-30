# Issue #6048: trading API total_pnl 从净资产计算（接力 PR#6420 的下一切片）
# Upstream: api.api.trading._compute_total_pnl (new helper)
# Downstream: api.api.trading.list_paper_accounts / get_paper_account
# Role: 验证 total_pnl = total_asset - initial_capital（含已实现+未实现盈亏）。

"""
#6048 子集测试：trading 端点 total_pnl 硬编码零值。

``list_paper_accounts`` (trading.py:188) 和 ``get_paper_account`` (trading.py:280) 的
``total_pnl`` 字段是 TODO 桩（固定 0）。PR#6420 已接线 ``position_value`` /
``total_asset``，``initial_capital`` 已现成 —— ``total_pnl = total_asset -
initial_capital`` 数据全具备，无需 result_service/analyzer，规避模拟盘（PAPER
portfolio）无回测 task_id 的陷阱。

本测试验证 ``_compute_total_pnl`` helper 与端点接线：
- ``total_pnl`` = total_asset - initial_capital（盈利为正、亏损为负、持平为 0）

``today_pnl`` 留后续 slice（需历史 position_record 按日对比，独立数据源）。
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


class TestComputeTotalPnl:
    """_compute_total_pnl = total_asset - initial_capital（#6048）。"""

    def test_profit_when_total_asset_exceeds_initial(self):
        """净资产 > 初始资金 → 正盈亏。"""
        from api.trading import _compute_total_pnl

        assert _compute_total_pnl(110000.0, 100000.0) == 10000.0

    def test_loss_when_total_asset_below_initial(self):
        """净资产 < 初始资金 → 负盈亏（亏损为负）。"""
        from api.trading import _compute_total_pnl

        assert _compute_total_pnl(95000.0, 100000.0) == -5000.0

    def test_zero_when_equal(self):
        """净资产 == 初始资金 → 0（持平）。"""
        from api.trading import _compute_total_pnl

        assert _compute_total_pnl(100000.0, 100000.0) == 0.0

    def test_non_numeric_safe_zero(self):
        """非数值入参安全降级为 0.0（容错，不崩）。"""
        from api.trading import _compute_total_pnl

        assert _compute_total_pnl("abc", 100000.0) == 0.0
        assert _compute_total_pnl(100000.0, None) == 0.0


class TestGetPaperAccountTotalPnl:
    """get_paper_account total_pnl = total_asset - initial_capital（#6048）。"""

    def test_total_pnl_is_total_asset_minus_initial_capital(self):
        """total_pnl = (cash + position_value) - initial_capital。"""
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
        # total_asset = 80000 + 3800 = 83800; total_pnl = 83800 - 100000 = -16200
        assert data["total_asset"] == 83800.0
        assert data["total_pnl"] == -16200.0


class TestListPaperAccountsTotalPnl:
    """list_paper_accounts 每个账户 total_pnl 独立计算（#6048）。"""

    def test_each_account_total_pnl_from_its_net_asset(self):
        """多账户各自 total_pnl = (cash + position_value) - initial_capital。"""
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
        # acc-1: total_asset = 90000 + 1000 = 91000; total_pnl = 91000 - 100000 = -9000
        assert accounts[0]["total_pnl"] == -9000.0
        # acc-2: total_asset = 150000 + 2500 = 152500; total_pnl = 152500 - 200000 = -47500
        assert accounts[1]["total_pnl"] == -47500.0
