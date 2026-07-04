"""
Unit tests for Sizer lot_size 参数化（#6498）。

三个 Sizer（FixedSizer / RatioSizer / ATRSizer）原将 A 股 100 股/手硬编码在
开仓（LONG）路径。本组测试验证 lot_size 已参数化（复用 LotAlignableMixin，
默认 100 保持 A 股向后兼容），并锁定 lot_size=50 / lot_size=1（美股）行为。

SHORT/平仓路径本就全量下单（volume=pos.volume），不受 lot 对齐约束——
agent brief 已剔除 Claim #3，此处加守护测试防回归。
"""
import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pandas as pd
import pytest

from ginkgo.enums import DIRECTION_TYPES
from ginkgo.entities import Signal
from ginkgo.trading.sizers.fixed_sizer import FixedSizer
from ginkgo.trading.sizers.ratio_sizer import RatioSizer
from ginkgo.trading.sizers.atr_sizer import ATRSizer


# --------------------------------------------------------------------------- #
# 共用 fixture / helper
# --------------------------------------------------------------------------- #
def _time_provider():
    tp = MagicMock()
    tp.now.return_value = datetime.datetime(2026, 1, 15, 10, 0, 0)
    return tp


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG):
    s = Signal(code=code, direction=direction)
    s._portfolio_id = "test-portfolio"
    s._engine_id = "test-engine"
    return s


def _portfolio_info(cash=Decimal("500000"), positions=None):
    return {"cash": cash, "positions": positions or {}}


@pytest.mark.parametrize(
    "cls,kwargs",
    [
        (FixedSizer, {"volume": "100"}),
        (RatioSizer, {"ratio": "0.1"}),
        (ATRSizer, {"period": 14, "risk": 0.01, "risk_ratio": 2}),
    ],
)
class TestSizerLotSizeParam:
    """lot_size 构造器参数：默认 100（A 股向后兼容），可配。"""

    def test_default_lot_size_is_100(self, cls, kwargs):
        """未传 lot_size 时默认 100，保持 A 股现状。"""
        sizer = cls(name="T", **kwargs)
        assert sizer.lot_size == 100

    def test_lot_size_configurable(self, cls, kwargs):
        """lot_size 可通过构造器配置（复用 LotAlignableMixin.lot_size 属性）。"""
        sizer = cls(name="T", lot_size=50, **kwargs)
        assert sizer.lot_size == 50


class TestFixedSizerLotSize:
    """FixedSizer 开仓路径递减步长由 lot_size 决定（原硬编码 100）。"""

    def test_lot_size_1_us_stock_not_zeroed(self):
        """lot_size=1（美股 1 股/手）：资金紧张时步长 1 精确找到可买量，不被 100 步长跨过拒单。

        volume=100、price=$100、cash=$6000：100 股需 $10005 > $6000。
        默认 lot_size=100：100-=100 → 0，while size>0 结束 → (0,0) 拒单
            （即便 ~59 股实际买得起，100 步长直接跨过）；
        lot_size=1：100→99→...→59（$5905 ≤ $6000）→ 成交 59 股。
        """
        # 默认 lot_size=100：100 步长跨过可买区间 → 拒单
        sizer_default = FixedSizer(name="T", volume="100")
        size_default, _ = sizer_default.calculate_order_size(
            initial_size=100, last_price=Decimal("100"), cash=Decimal("6000")
        )
        assert size_default == 0  # A 股：资金不足 1 手 → 拒单

        # lot_size=1（美股）：步长 1 精确定位可买量
        sizer_us = FixedSizer(name="T", volume="100", lot_size=1)
        size_us, _ = sizer_us.calculate_order_size(
            initial_size=100, last_price=Decimal("100"), cash=Decimal("6000")
        )
        assert size_us == 59  # 美股：不被 100 步长跨过

    def test_lot_size_50_decrement_step(self):
        """lot_size=50：递减步长为 50，资金不足时按 50 股递减试探。

        volume=200、price=$100、cash 仅够 150 股（$15000+手续费）：
        默认 lot_size=100：200→100（步长 100），100 股资金够 → 返回 100；
        lot_size=50：200→150（步长 50），150 股资金够 → 返回 150。
        """
        sizer_default = FixedSizer(name="T", volume="200")
        size_default, _ = sizer_default.calculate_order_size(
            initial_size=200, last_price=Decimal("100"), cash=Decimal("15500")
        )
        assert size_default == 100  # 200 不够 → 减 100 → 100 够

        sizer_50 = FixedSizer(name="T", volume="200", lot_size=50)
        size_50, _ = sizer_50.calculate_order_size(
            initial_size=200, last_price=Decimal("100"), cash=Decimal("15500")
        )
        assert size_50 == 150  # 200 不够 → 减 50 → 150 够


class TestRatioSizerLotSize:
    """RatioSizer 开仓路径 lot 对齐由 lot_size 决定（原硬编码 100）。"""

    def test_lot_size_50_aligns_via_cal(self):
        """lot_size=50 经 cal() 端到端：开仓量对齐 50 而非 100。

        ratio=0.1、cash=550000 → budget=55000；price=40 → raw=int(55000/40)=1375。
        默认 lot_size=100：(1375//100)*100=1300，资金够 → 成交 1300；
        lot_size=50：align_to_lot(1375)=1350，资金够 → 成交 1350。
        """
        df = pd.DataFrame({"close": [40.0, 40.0, 40.0]})

        # 默认 lot_size=100
        sizer_default = RatioSizer(name="T", ratio="0.1")
        sizer_default._time_provider = _time_provider()
        feeder_default = MagicMock()
        feeder_default.get_historical_data.return_value = df
        sizer_default._data_feeder = feeder_default
        order_default = sizer_default.cal(
            _portfolio_info(cash=Decimal("550000")), _make_signal()
        )
        assert order_default.volume == 1300

        # lot_size=50
        sizer_50 = RatioSizer(name="T", ratio="0.1", lot_size=50)
        sizer_50._time_provider = _time_provider()
        feeder_50 = MagicMock()
        feeder_50.get_historical_data.return_value = df
        sizer_50._data_feeder = feeder_50
        order_50 = sizer_50.cal(
            _portfolio_info(cash=Decimal("550000")), _make_signal()
        )
        assert order_50.volume == 1350


class TestATRSizerLotSize:
    """ATRSizer 开仓路径 lot 对齐由 lot_size 决定（原硬编码 100 内联）。

    ATRSizer LONG 取数经注入的 _data_feeder.get_historical_data()（#4706），
    模拟注入方式同 RatioSizer 测试（feeder.get_historical_data 返回 bar DF）。
    """

    @staticmethod
    def _bar_df(n, high, low, close):
        return pd.DataFrame({"high": [high] * n, "low": [low] * n, "close": [close] * n})

    def test_lot_size_50_aligns_via_cal(self):
        """lot_size=50 经 cal() 端到端：开仓量对齐 50 而非 100。

        TR=1.5（high=11.5/low=10/close=10）、period=14、risk_ratio=2 → atr=3；
        cash=500000 * risk=0.01 → max_money=5000；raw=int(5000/3)=1666。
        默认 lot_size=100：int(1666/100)*100=1600；
        lot_size=50：align_to_lot(1666)=1650。
        """
        df = self._bar_df(15, high=11.5, low=10.0, close=10.0)
        signal = _make_signal()
        info = {"cash": 500000.0, "positions": {}}  # float：atr_sizer 不做 Decimal 强转

        # 默认 lot_size=100
        sizer_default = ATRSizer(name="T", period=14, risk=0.01, risk_ratio=2)
        sizer_default.now = datetime.datetime(2026, 1, 15, 10, 0, 0)
        feeder_default = MagicMock()
        feeder_default.get_historical_data.return_value = df
        sizer_default._data_feeder = feeder_default
        order_default = sizer_default.cal(info, signal)
        assert order_default.volume == 1600

        # lot_size=50
        sizer_50 = ATRSizer(name="T", period=14, risk=0.01, risk_ratio=2, lot_size=50)
        sizer_50.now = datetime.datetime(2026, 1, 15, 10, 0, 0)
        feeder_50 = MagicMock()
        feeder_50.get_historical_data.return_value = df
        sizer_50._data_feeder = feeder_50
        order_50 = sizer_50.cal(info, signal)
        assert order_50.volume == 1650


class TestShortCloseFullVolume:
    """平仓(SHORT)路径全量下单守护（agent brief 已剔除 Claim #3）。

    三个 Sizer 的 SHORT 分支均直接 volume=pos.volume 全量下单，不受 lot 对齐
    约束——零股持仓（送股/拆股/历史遗留）平仓不受影响。加守护防回归。
    """

    @staticmethod
    def _position(volume):
        pos = MagicMock()
        pos.volume = volume
        return pos

    def test_fixed_sizer_short_uses_full_odd_lot_volume(self):
        """FixedSizer SHORT：含零股(17 股)持仓全量平仓，不被 lot 对齐截断。"""
        sizer = FixedSizer(name="T", volume="100", lot_size=100)
        sizer._time_provider = _time_provider()
        signal = _make_signal(direction=DIRECTION_TYPES.SHORT)
        info = _portfolio_info(positions={"000001.SZ": self._position(17)})
        order = sizer.cal(info, signal)
        assert order is not None
        assert order.volume == 17  # 零股全量平仓

    def test_ratio_sizer_short_uses_full_odd_lot_volume(self):
        """RatioSizer SHORT：含零股(17 股)持仓全量平仓。"""
        sizer = RatioSizer(name="T", ratio="0.1", lot_size=100)
        sizer._time_provider = _time_provider()
        signal = _make_signal(direction=DIRECTION_TYPES.SHORT)
        info = _portfolio_info(positions={"000001.SZ": self._position(17)})
        order = sizer.cal(info, signal)
        assert order is not None
        assert order.volume == 17
