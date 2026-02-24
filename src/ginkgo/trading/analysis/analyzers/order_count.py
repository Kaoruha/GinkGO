# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Order Count分析器继承BaseAnalyzer计算OrderCount订单统计性能指标




from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES


class OrderCount(BaseAnalyzer):
    """订单计数分析器 - 记录累计订单数量（取最新值即为总数）

    激活阶段: ORDERSEND - 订单发送时增加计数
    记录阶段: ENDDAY - 每天结束时写入当前累计值
    """

    __abstract__ = False

    def __init__(self, name: str = "order_count", *args, **kwargs):
        super(OrderCount, self).__init__(name, *args, **kwargs)
        # 激活阶段：订单发送时
        self.add_active_stage(RECORDSTAGE_TYPES.ORDERSEND)
        # 记录阶段：每天结束时
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)
        # 累计订单数
        self._total_count = 0

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """订单发送时增加累计计数"""
        self._total_count += 1
        self.add_data(self._total_count)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """每天结束时记录当前累计值到数据库"""
        current_time = self.get_current_time()
        if current_time is None:
            return

        # 直接写入数据库
        from ginkgo.data.containers import container as data_container
        analyzer_service = data_container.analyzer_service()
        analyzer_service.add_record(
            portfolio_id=self.portfolio_id,
            engine_id=self.engine_id,
            run_id=self.run_id,
            timestamp=current_time.strftime("%Y-%m-%d %H:%M:%S"),
            business_timestamp=current_time.strftime("%Y-%m-%d %H:%M:%S"),
            value=self._total_count,
            name=self.name,
            analyzer_id=self._analyzer_id,
        )

    @property
    def total_count(self) -> int:
        """累计订单数（只读属性）"""
        return self._total_count
