# Related: #5489
# _calculate_rsi 应使用 Wilder EMA 平滑（行业标准 alpha=1/period），非 SMA。
# tracer bullet: period=3, 6 根 bar 给出 5 个 changes（种子3 + 递推2），
# Wilder RSI≈54.17；旧 SMA（最近 3 个 changes）=60.0，区分明显。
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from unittest.mock import MagicMock

from ginkgo.trading.strategies.mean_reversion import MeanReversion


def _make_bar(close_price):
    bar = MagicMock()
    bar.close = close_price
    return bar


def _make_strategy(period=3):
    return MeanReversion(rsi_period=period, oversold=20, overbought=80)


class TestWilderRsi:

    def test_wilder_ema_recurrence_not_sma(self):
        """#5489: RSI 用 Wilder EMA 递推（alpha=1/period），非 SMA。
        period=3, closes=[100,103,102,104,105,103] → changes=[3,-1,2,1,-2]
        Wilder: 种子 avg_gain=5/3, avg_loss=1/3；递推后 RS=13/11 → RSI≈54.17
        旧 SMA(最近 3 个 [2,1,-2]): RS=1.5 → RSI=60.0，新旧可区分。"""
        strategy = _make_strategy(period=3)
        bars = [_make_bar(c) for c in [100, 103, 102, 104, 105, 103]]
        rsi = strategy._calculate_rsi(bars)
        assert rsi is not None
        assert abs(rsi - 54.17) < 0.5  # Wilder 值
        assert abs(rsi - 60.0) > 1.0   # 显著区别于旧 SMA

    def test_degenerates_to_sma_when_exactly_period_changes(self):
        """#5489: bars 恰为 period+1（changes 数 == period）时全做 SMA 种子、
        无递推，Wilder 退化为 SMA —— 保证现有信号测试行为兼容。"""
        strategy = _make_strategy(period=3)
        # changes=[2,-1,3]，全部做种子
        bars = [_make_bar(c) for c in [100, 102, 101, 104]]
        rsi = strategy._calculate_rsi(bars)
        # avg_gain=5/3, avg_loss=1/3 → RS=5 → RSI≈83.33
        assert rsi is not None
        assert abs(rsi - 83.33) < 0.5

    def test_all_gains_returns_100(self):
        """#5489: 持续上涨 avg_loss=0 → RSI=100"""
        strategy = _make_strategy(period=3)
        bars = [_make_bar(c) for c in [100, 101, 102, 103, 104, 105]]
        assert strategy._calculate_rsi(bars) == 100.0

    def test_all_losses_returns_0(self):
        """#5489: 持续下跌 avg_gain=0 → RS=0 → RSI=0"""
        strategy = _make_strategy(period=3)
        bars = [_make_bar(c) for c in [105, 104, 103, 102, 101, 100]]
        assert strategy._calculate_rsi(bars) == 0.0
