# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Max Drawdown分析器继承BaseAnalyzer计算MaxDrawdown最大回撤性能指标






from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES


class MaxDrawdown(BaseAnalyzer):
    """最大回撤分析器 - 记录投资组合的最大回撤比例"""
    
    __abstract__ = False

    def __init__(self, name: str = "max_drawdown", *args, **kwargs):
        super(MaxDrawdown, self).__init__(name, *args, **kwargs)
        # 在每天开始时激活回撤计算
        self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        # 在每天结束时记录到数据库
        self.set_record_stage(RECORDSTAGE_TYPES.NEWDAY)
        # 记录历史最高净值
        self._max_worth = None

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """激活最大回撤计算，更新当前回撤数据"""
        current_worth = portfolio_info.get("worth", 0)
        
        if self._max_worth is None:
            # 初始化，第一天无回撤
            self._max_worth = current_worth
            drawdown = 0.0
        else:
            if current_worth > self._max_worth:
                # 创新高，更新最高净值，回撤为0
                self._max_worth = current_worth
                drawdown = 0.0
            else:
                # 计算回撤比例：(当前净值 - 最高净值) / 最高净值
                # 回撤为负值，表示损失百分比
                drawdown = (current_worth - self._max_worth) / self._max_worth if self._max_worth > 0 else 0.0
                
        self.add_data(drawdown)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录最大回撤数据到数据库"""
        self.add_record()

    @property
    def current_drawdown(self) -> float:
        """当前回撤比例（只读属性）"""
        return self.current_value

    @property
    def peak_worth(self) -> float:
        """历史最高净值（只读属性）"""
        return self._max_worth if self._max_worth is not None else 0.0
