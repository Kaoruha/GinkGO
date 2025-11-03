from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES


class SignalCount(BaseAnalyzer):
    """优化的信号计数分析器 - 记录每天的信号生成数量"""

    __abstract__ = False

    def __init__(self, name: str = "signal_count", *args, **kwargs):
        super(SignalCount, self).__init__(name, *args, **kwargs)
        # 在信号生成时激活计数
        self.add_active_stage(RECORDSTAGE_TYPES.SIGNALGENERATION)
        # 在每天结束时记录到数据库
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)
        # 简单的日计数器
        self._daily_count = 0

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """每次信号生成时增加计数并更新数据点"""
        self._daily_count += 1
        # 关键：每次都调用add_data，框架会自动处理时间戳覆盖
        self.add_data(self._daily_count)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录当天最终计数到数据库并重置计数器"""
        # 记录到数据库
        self.add_record()

        # 重置计数器为下一天准备
        self._daily_count = 0

    @property
    def current_daily_count(self) -> int:
        """当前日信号计数（只读属性）"""
        return self._daily_count
