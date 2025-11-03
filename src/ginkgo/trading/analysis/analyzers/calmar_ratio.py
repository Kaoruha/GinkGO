from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd
import numpy as np


class CalmarRatio(BaseAnalyzer):
    """卡尔马比率分析器 - 年化收益率与最大回撤的比值"""

    __abstract__ = False

    def __init__(self, name: str = "calmar_ratio", *args, **kwargs):
        super(CalmarRatio, self).__init__(name, *args, **kwargs)
        # 在每天结束时激活计算
        self.add_active_stage(RECORDSTAGE_TYPES.ENDDAY)
        # 在每天结束时记录到数据库
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)

        # 内部状态
        self._initial_worth = None
        self._max_worth = None
        self._current_worth = None
        self._max_drawdown = 0.0
        self._trading_days = 0

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """计算卡尔马比率"""
        current_worth = portfolio_info.get("worth", 0)

        # 初始化
        if self._initial_worth is None:
            self._initial_worth = current_worth
            self._max_worth = current_worth
            self._current_worth = current_worth
            calmar_ratio = 0.0
        else:
            self._current_worth = current_worth
            self._trading_days += 1

            # 更新最高净值
            if current_worth > self._max_worth:
                self._max_worth = current_worth

            # 计算当前回撤
            if self._max_worth > 0:
                current_drawdown = (self._max_worth - current_worth) / self._max_worth
                # 更新最大回撤
                if current_drawdown > self._max_drawdown:
                    self._max_drawdown = current_drawdown

            # 计算卡尔马比率
            if self._trading_days > 0 and self._initial_worth > 0:
                # 计算总收益率
                total_return = (current_worth - self._initial_worth) / self._initial_worth
                # 年化收益率 (假设252个交易日)
                annualized_return = (1 + total_return) ** (252 / self._trading_days) - 1

                # 卡尔马比率 = 年化收益率 / 最大回撤
                if self._max_drawdown > 0:
                    calmar_ratio = annualized_return / self._max_drawdown
                else:
                    # 没有回撤的情况，设为一个大的正值或收益率本身
                    calmar_ratio = annualized_return / 0.001 if annualized_return > 0 else 0
            else:
                calmar_ratio = 0.0

        self.add_data(calmar_ratio)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录卡尔马比率到数据库"""
        self.add_record()

    @property
    def current_calmar_ratio(self) -> float:
        """当前卡尔马比率（只读属性）"""
        return self.current_value

    @property
    def annualized_return(self) -> float:
        """年化收益率（只读属性）"""
        if self._trading_days > 0 and self._initial_worth > 0 and self._current_worth is not None:
            total_return = (self._current_worth - self._initial_worth) / self._initial_worth
            return float((1 + total_return) ** (252 / self._trading_days) - 1)
        return 0.0

    @property
    def max_drawdown_ratio(self) -> float:
        """最大回撤比例（只读属性）"""
        return float(self._max_drawdown)
