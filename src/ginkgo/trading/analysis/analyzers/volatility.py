# Upstream: Portfolio (ENDDAY stage), BASIC_ANALYZERS
# Downstream: BaseAnalyzer, RECORDSTAGE_TYPES, worth_delta, get_worth, pandas, numpy
# Role: 波动率分析器 — 滚动窗口计算日收益率样本标准差并年化（sqrt(252)）






from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.trading.analysis.worth_delta import worth_delta
from ginkgo.trading.bases.portfolio_info_access import get_worth
from ginkgo.enums import RECORDSTAGE_TYPES
import numpy as np


class Volatility(BaseAnalyzer):
    """波动率分析器 - 计算策略收益率的标准差"""
    
    __abstract__ = False

    def __init__(self, name: str = "volatility", window: int = 20, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        # 在每天结束时激活计算
        self.add_active_stage(RECORDSTAGE_TYPES.ENDDAY)
        # 在每天结束时记录到数据库
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)
        
        # 配置参数
        self._window = window  # 滚动窗口大小
        
        # 内部状态
        self._returns = []
        self._last_worth = None

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """计算波动率"""
        current_worth = get_worth(portfolio_info)
        delta = worth_delta(current_worth, self._last_worth)

        if delta is None:
            volatility = 0.0
        else:
            if delta.return_ is not None:
                self._returns.append(delta.return_)

                # 保持窗口大小
                if len(self._returns) > self._window:
                    self._returns.pop(0)

                # 计算波动率 (需要至少2个数据点)
                if len(self._returns) >= 2:
                    returns_array = np.array(self._returns)
                    # 计算标准差
                    daily_volatility = np.std(returns_array, ddof=1)  # 样本标准差
                    # 年化波动率
                    volatility = daily_volatility * np.sqrt(252)
                else:
                    volatility = 0.0
            else:
                volatility = 0.0

        self._last_worth = current_worth
        self.add_data(volatility)

    @property
    def current_volatility(self) -> float:
        """当前年化波动率（只读属性）"""
        return self.current_value

    @property
    def daily_volatility(self) -> float:
        """当前日波动率（只读属性）"""
        if len(self._returns) >= 2:
            returns_array = np.array(self._returns)
            return float(np.std(returns_array, ddof=1))
        return 0.0

    @property
    def returns_count(self) -> int:
        """收益率数据点数量（只读属性）"""
        return len(self._returns)
