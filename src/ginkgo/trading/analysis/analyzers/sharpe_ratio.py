# Upstream: Portfolio (ENDDAY stage), BASIC_ANALYZERS
# Downstream: BaseAnalyzer, RECORDSTAGE_TYPES, to_decimal, numpy
# Role: 夏普比率分析器 — 日收益率标准方法，(mean_excess / std) * sqrt(252)


from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.libs.data.number import to_decimal
from ginkgo.enums import RECORDSTAGE_TYPES
import numpy as np

# 退化序列守卫（#5973）：策略日均收益 |mean_return| 至少为日无风险利率的多少倍，
# Sharpe 才视为可算。Sharpe = (mean - rf_daily) / std * sqrt(252)；当 mean 接近 0
# 而 rf_daily > 0 时，excess return 被 rf_daily 主导，叠加低换手/稀疏交易序列 std 趋零
# → 量级爆炸（实测 MA 单股 -13）。要求 |mean_return| >= rf_daily 确保 rf 不主导 excess。
# 注意：不能用 std 量级做守卫——线性增长 worth 的强正信号策略 std 也小，但 mean>>rf
# 属真信号（sharpe +405），std 阈值会误伤。区分关键在 mean vs rf，非 std 量级。
# rf=0 时该门槛退化为 |mean_return| >= 0 恒真，与原 std>0 守卫一致，不引入回归——
# 但 rf=0 下原 bug 形态（稀疏交易/等差增长，std 极小）仍会爆量（实测 +5.3 ~ +1.8e4），
# 故 rf=0 退化配置叠加 std 绝对下界兜底：std 这么小的序列 sharpe 估计统计不可信。
# rf>0 不卡 std 量级（保留线性增长真信号 mean>>rf 的正常计算）。
_MIN_MEAN_TO_RF_MULTIPLE = 1
_RF_ZERO_STD_FLOOR = 1e-5  # rf=0 退化配置下 std 绝对下界，防近常数序列爆量


class SharpeRatio(BaseAnalyzer):
    """夏普比率分析器 - 基于日收益率的标准计算方法"""

    __abstract__ = False

    def __init__(self, name: str = "sharpe_ratio", risk_free_rate: float = 0.03, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.add_active_stage(RECORDSTAGE_TYPES.ENDDAY)
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)

        self._risk_free_rate = risk_free_rate / 252  # 转换为日无风险收益率

        self._returns = []
        self._last_worth = None

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """计算夏普比率"""
        current_worth = float(to_decimal(portfolio_info.get("worth", 0)))

        if self._last_worth is None:
            self._last_worth = current_worth
            sharpe_ratio = 0.0
        else:
            if self._last_worth > 0:
                daily_return = (current_worth - self._last_worth) / self._last_worth
                self._returns.append(daily_return)

                if len(self._returns) >= 10:
                    returns_array = np.array(self._returns)
                    mean_return = np.mean(returns_array)
                    excess_returns = returns_array - self._risk_free_rate
                    mean_excess_return = np.mean(excess_returns)
                    std = np.std(returns_array, ddof=1)

                    # rf=0 退化配置：原守卫退化为 |mean|>=0 恒真，叠加 std 下界防爆量
                    if self._risk_free_rate == 0 and std < _RF_ZERO_STD_FLOOR:
                        sharpe_ratio = 0.0
                    elif std > 0 and abs(mean_return) >= _MIN_MEAN_TO_RF_MULTIPLE * self._risk_free_rate:
                        sharpe_ratio = mean_excess_return / std * np.sqrt(252)
                    else:
                        sharpe_ratio = 0.0
                else:
                    sharpe_ratio = 0.0
            else:
                sharpe_ratio = 0.0

            self._last_worth = current_worth

        self.add_data(sharpe_ratio)

    @property
    def current_sharpe_ratio(self) -> float:
        """当前夏普比率（只读属性）"""
        return self.current_value
