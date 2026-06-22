"""
#6181: LiquidityRisk / VolatilityRisk 报告方法 V5(ADR-010) Decimal 算术混算

Position.market_value 自 1803ce39 起为 Decimal（见 position.py:630）。
报告方法的 float 累加器（0.0）累加 Decimal market_value 会抛
TypeError: unsupported operand type(s) for +: 'float' and 'Decimal'.

注意区分：Decimal > float（比较）在 Py3.2+ 合法不抛，算术（+ * /）才抛。
故 #6180 ConcentrationRisk 的比较没崩，本处累加崩了。

对齐 #6180 修法：累加器改 Decimal(0) / float 量转换。
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from ginkgo.trading.risk_management.liquidity_risk import LiquidityRisk
from ginkgo.trading.risk_management.volatility_risk import VolatilityRisk


def _make_position(market_value):
    """market_value 取 Decimal 以模拟 ADR-010 后的真实 Position 类型。"""
    pos = MagicMock()
    pos.market_value = market_value
    return pos


def _make_portfolio_info(positions):
    return {"worth": 100000, "positions": positions, "uuid": "p1", "now": datetime.now()}


@pytest.mark.tdd
@pytest.mark.risk
@pytest.mark.financial
class TestRiskDecimalArithmetic:
    """#6181: 报告方法在 Decimal market_value 下不得抛 TypeError"""

    def test_get_liquidity_report_decimal_market_value_no_typeerror(self):
        """get_liquidity_report: Decimal market_value 累加不抛 TypeError（#6181）。"""
        r = LiquidityRisk()
        info = _make_portfolio_info({
            "000001.SZ": _make_position(Decimal("10000")),
            "600000.SH": _make_position(Decimal("8000")),
        })
        # 隔离外部数据依赖，聚焦报告方法的算术路径
        r.get_liquidity_score = MagicMock(return_value=80.0)
        report = r.get_liquidity_report(info)
        assert "portfolio_liquidity_score" in report
        assert report["total_positions"] == 2

    def test_get_portfolio_volatility_decimal_market_value_no_typeerror(self):
        """get_portfolio_volatility: Decimal market_value 加权不抛 TypeError（#6181）。"""
        r = VolatilityRisk()
        info = _make_portfolio_info({
            "000001.SZ": _make_position(Decimal("10000")),
            "600000.SH": _make_position(Decimal("8000")),
        })
        # 隔离外部数据依赖，聚焦加权算术路径
        r._get_stock_volatility = MagicMock(return_value=0.25)
        result = r.get_portfolio_volatility(info)
        # 签名声明 -> float；只要不抛 TypeError、返回非负数值即通过
        assert result >= 0
