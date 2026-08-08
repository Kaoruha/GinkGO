"""worth_delta 单测:8 个分析器重复差分逻辑的收敛点。"""
from decimal import Decimal

import pytest

from ginkgo.trading.analysis.worth_delta import WorthDelta, worth_delta


class TestWorthDelta:
    def test_first_call_returns_none(self):
        """首次(last=None)无差分,调用方据此 init _last_worth。"""
        assert worth_delta(10000, None) is None

    def test_normal_positive_delta(self):
        """正常上涨:pnl 绝对 + return 相对。"""
        d = worth_delta(11000, 10000)
        assert d.pnl == pytest.approx(1000.0)
        assert d.return_ == pytest.approx(0.1)

    def test_negative_delta(self):
        """下跌:负 pnl + 负 return。"""
        d = worth_delta(9000, 10000)
        assert d.pnl == pytest.approx(-1000.0)
        assert d.return_ == pytest.approx(-0.1)

    def test_zero_change(self):
        """worth 不变:pnl=0,return=0。"""
        d = worth_delta(10000, 10000)
        assert d.pnl == 0.0
        assert d.return_ == 0.0

    def test_zero_last_return_none(self):
        """last=0 除零守卫:return_ None,pnl 仍算(与原 `if _last_worth>0` 一致)。"""
        d = worth_delta(1000, 0)
        assert d.pnl == pytest.approx(1000.0)
        assert d.return_ is None

    def test_negative_last_return_none(self):
        """last<0(异常状态)同样守卫,不爆。"""
        d = worth_delta(1000, -100)
        assert d.pnl == pytest.approx(1100.0)
        assert d.return_ is None

    def test_decimal_inputs_float_normalized(self):
        """Decimal 入参(经 get_worth)内部 float 化,返回 float(analyzer 喂 numpy)。"""
        d = worth_delta(Decimal("11000"), Decimal("10000"))
        assert isinstance(d.pnl, float)
        assert d.pnl == pytest.approx(1000.0)
        assert d.return_ == pytest.approx(0.1)

    def test_int_inputs(self):
        """int 入参同样工作,返回 float。"""
        d = worth_delta(11000, 10000)
        assert d.pnl == 1000.0
        assert isinstance(d.pnl, float)
