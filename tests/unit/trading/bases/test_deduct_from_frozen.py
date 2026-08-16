"""
deduct_from_frozen 资金语义单测（2026-08-16 冻结资金 bug 修复锚定）。

三种行为：
1. 正常路径：cost ≤ frozen → 冻结扣减、剩余解冻回 cash；
2. 补扣兜底：cost > frozen 但现金充足（T+1 隔夜价差常态）→ 差额从现金补，
   不再整单拒绝（旧语义：差 $40 拒一单,系统性"只让次日跌的买入成交"）；
3. 真实超支：frozen + cash 都不够 → 仍然 ValueError（合法拒绝）。
"""
import os
import sys
from decimal import Decimal

import pytest

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.trading.bases.portfolio_base import PortfolioBase


class _Wallet:
    """绕过重量级 Portfolio __init__,只装资金三态——单测 deduct 纯逻辑"""

    deduct_from_frozen = PortfolioBase.deduct_from_frozen

    def __init__(self, cash, frozen):
        self._cash = Decimal(str(cash))
        self._frozen = Decimal(str(frozen))

    @property
    def frozen(self):
        return self._frozen


class TestDeductFromFrozen:

    def test_normal_path_deducts_and_unfreezes_remainder(self):
        w = _Wallet(cash=0, frozen=12075)
        w.deduct_from_frozen(12000)
        assert w._frozen == 0            # 剩余全部解冻
        assert w._cash == 75             # 回到现金

    def test_price_gap_covered_from_cash_not_rejected(self):
        """T+1 成本略超冻结(隔夜价差)且现金充足 → 补扣差额,不抛异常"""
        w = _Wallet(cash=950000, frozen=12075)
        w.deduct_from_frozen(12115)      # 差 $40
        assert w._frozen == 0
        assert w._cash == Decimal("950000") - (Decimal("12115") - Decimal("12075"))

    def test_true_insufficiency_still_raises(self):
        """frozen + cash 都不够 → 真实超支,保持 ValueError"""
        w = _Wallet(cash=10, frozen=12075)
        with pytest.raises(ValueError, match="Insufficient funds"):
            w.deduct_from_frozen(12115)
