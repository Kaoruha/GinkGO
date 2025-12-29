# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: HoldPct持仓比例分析器继承BaseAnalyzer计算持仓比例和仓位占用评估资金使用效率支持交易系统功能和组件集成提供完整业务支持






from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES


class HoldPCT(BaseAnalyzer):
    """持仓比例分析器 - 记录投资组合的每日持仓占总资产的比例"""
    
    __abstract__ = False

    def __init__(self, name: str = "hold_pct", *args, **kwargs):
        super(HoldPCT, self).__init__(name, *args, **kwargs)
        # 在每天开始时激活持仓比例计算
        self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        # 在每天结束时记录到数据库
        self.set_record_stage(RECORDSTAGE_TYPES.NEWDAY)

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """激活持仓比例计算，更新当前持仓比例数据"""
        total_worth = portfolio_info.get("worth", 0)
        cash = portfolio_info.get("cash", 0)
        
        if total_worth > 0:
            # 持仓价值 = 总资产 - 现金
            position_value = total_worth - cash
            # 持仓比例 = 持仓价值 / 总资产
            hold_percentage = position_value / total_worth
        else:
            hold_percentage = 0.0
            
        self.add_data(hold_percentage)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录持仓比例数据到数据库"""
        self.add_record()

    @property
    def current_hold_percentage(self) -> float:
        """当前持仓比例（只读属性）"""
        return self.current_value
