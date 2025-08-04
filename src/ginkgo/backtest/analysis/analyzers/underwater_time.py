from ginkgo.backtest.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd
import numpy as np


class UnderwaterTime(BaseAnalyzer):
    """水下时间分析器 - 记录净值低于历史最高点的持续时间"""
    
    __abstract__ = False

    def __init__(self, name: str = "underwater_time", *args, **kwargs):
        super(UnderwaterTime, self).__init__(name, *args, **kwargs)
        # 在每天开始时激活水下时间计算
        self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        # 在每天结束时记录到数据库
        self.set_record_stage(RECORDSTAGE_TYPES.NEWDAY)
        
        # 内部状态
        self._max_worth = None
        self._underwater_days = 0
        self._max_underwater_days = 0
        self._total_underwater_days = 0
        self._underwater_periods = 0

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """计算水下时间"""
        current_worth = portfolio_info.get("worth", 0)
        
        if self._max_worth is None:
            # 初始化
            self._max_worth = current_worth
            underwater_time = 0
        else:
            if current_worth > self._max_worth:
                # 创新高，结束水下期
                if self._underwater_days > 0:
                    # 记录一个完整的水下期
                    self._underwater_periods += 1
                    if self._underwater_days > self._max_underwater_days:
                        self._max_underwater_days = self._underwater_days
                
                self._max_worth = current_worth
                self._underwater_days = 0
            else:
                # 仍在水下
                self._underwater_days += 1
                self._total_underwater_days += 1
        
        # 当前水下时间（天数）
        underwater_time = self._underwater_days
        self.add_data(underwater_time)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录水下时间数据到数据库"""
        self.add_record()

    @property
    def current_underwater_days(self) -> int:
        """当前连续水下天数（只读属性）"""
        return self._underwater_days

    @property
    def max_underwater_days(self) -> int:
        """历史最长水下天数（只读属性）"""
        # 考虑当前正在进行的水下期
        return max(self._max_underwater_days, self._underwater_days)

    @property
    def total_underwater_days(self) -> int:
        """总水下天数（只读属性）"""
        return self._total_underwater_days + self._underwater_days

    @property
    def underwater_periods_count(self) -> int:
        """水下期总次数（只读属性）"""
        # 如果当前在水下，需要加1
        current_periods = self._underwater_periods
        if self._underwater_days > 0:
            current_periods += 1
        return current_periods

    @property
    def average_underwater_period(self) -> float:
        """平均水下期长度（只读属性）"""
        completed_periods = self._underwater_periods
        total_completed_days = self._total_underwater_days
        
        # 如果当前在水下，加入计算
        if self._underwater_days > 0:
            completed_periods += 1
            total_completed_days += self._underwater_days
        
        if completed_periods > 0:
            return float(total_completed_days / completed_periods)
        return 0.0

    @property
    def is_currently_underwater(self) -> bool:
        """当前是否在水下（只读属性）"""
        return self._underwater_days > 0