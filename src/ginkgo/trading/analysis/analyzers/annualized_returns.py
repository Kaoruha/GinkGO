# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Annualized Returns分析器继承BaseAnalyzer计算AnnualizedReturns年化收益率性能指标




from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.libs.data.number import to_decimal
from ginkgo.enums import RECORDSTAGE_TYPES
import math


class AnnualizedReturn(BaseAnalyzer):
    """年化收益率分析器 - 计算投资组合的年化收益率"""

    __abstract__ = False

    def __init__(self, name: str = "annualized_return", *args, **kwargs):
        super(AnnualizedReturn, self).__init__(name, *args, **kwargs)
        # 在每天开始时激活计算
        self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        # 在每天结束时记录到数据库
        self.set_record_stage(RECORDSTAGE_TYPES.NEWDAY)

        # 内部状态
        self._initial_worth = None  # 初始资产
        self._days = 0  # 经过天数

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """计算年化收益率"""
        current_worth = float(to_decimal(portfolio_info.get("worth", 0)))

        if self._initial_worth is None:
            # 第一天，初始化
            self._initial_worth = current_worth
            annualized_return = 0.0
        else:
            self._days += 1

            # 计算年化收益率
            # 公式: (当前资产 / 初始资产) ^ (252 / 天数) - 1
            if self._days > 0 and self._initial_worth > 0:
                total_return = current_worth / self._initial_worth
                # 使用252个交易日作为一年
                annualized_return = math.pow(total_return, 252.0 / self._days) - 1

                # 限制极端值
                if annualized_return > 10.0:  # 1000%
                    annualized_return = 10.0
                elif annualized_return < -1.0:  # -100%
                    annualized_return = -1.0
            else:
                annualized_return = 0.0

        self.add_data(annualized_return)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录年化收益率到数据库"""
        self.add_record()

    @property
    def current_annualized_return(self) -> float:
        """当前年化收益率（只读属性）"""
        return self.current_value

    @property
    def total_days(self) -> int:
        """经过的总天数（只读属性）"""
        return self._days

    @property
    def initial_worth(self) -> float:
        """初始资产（只读属性）"""
        return self._initial_worth if self._initial_worth is not None else 0.0
