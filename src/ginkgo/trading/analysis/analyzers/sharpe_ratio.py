# Upstream: Portfolio (ENDDAY stage), BASIC_ANALYZERS
# Downstream: BaseAnalyzer, RECORDSTAGE_TYPES, to_decimal, numpy
# Role: 夏普比率分析器 — 日收益率标准方法，(mean_excess / std) * sqrt(252)


from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.libs.data.number import to_decimal
from ginkgo.enums import RECORDSTAGE_TYPES
import numpy as np


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
                    excess_returns = returns_array - self._risk_free_rate
                    mean_excess_return = np.mean(excess_returns)
                    std = np.std(returns_array, ddof=1)

                    if std > 0:
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
