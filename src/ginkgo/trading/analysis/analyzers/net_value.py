# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: NetValue净值分析器继承BaseAnalyzer计算净值曲线和累计收益率评估策略表现支持交易系统功能和组件集成提供完整业务支持






from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES


class NetValue(BaseAnalyzer):
    """净值分析器 - 记录投资组合的每日净值变化"""
    
    __abstract__ = False

    def __init__(self, name: str = "net_value", *args, **kwargs):
        super(NetValue, self).__init__(name, *args, **kwargs)
        # 在每天开始时和结束时都激活净值记录
        self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        self.add_active_stage(RECORDSTAGE_TYPES.ENDDAY)
        # 在每天结束时记录到数据库（记录收盘后净值）
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """激活净值计算，更新当前净值数据"""
        current_worth = portfolio_info.get("worth", 0)
        self.add_data(current_worth)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录净值数据到数据库"""
        self.add_record()

    @property
    def current_net_value(self) -> float:
        """当前净值（只读属性）"""
        return self.current_value
