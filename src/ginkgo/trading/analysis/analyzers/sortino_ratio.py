# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Sortino Ratio分析器继承BaseAnalyzer计算SortinoRatio索提诺比率性能指标






from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.libs.data.number import to_decimal
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd
import numpy as np


class SortinoRatio(BaseAnalyzer):
    """索提诺比率分析器 - 只考虑下行风险的风险调整收益率指标"""
    
    __abstract__ = False

    def __init__(self, name: str = "sortino_ratio", risk_free_rate: float = 0.03, *args, **kwargs):
        super(SortinoRatio, self).__init__(name, *args, **kwargs)
        # 在每天结束时激活计算
        self.add_active_stage(RECORDSTAGE_TYPES.ENDDAY)
        # 在每天结束时记录到数据库
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)
        
        # 配置参数
        self._risk_free_rate = risk_free_rate / 252  # 转换为日无风险收益率
        
        # 内部状态
        self._returns = []
        self._last_worth = None

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """计算索提诺比率"""
        current_worth = float(to_decimal(portfolio_info.get("worth", 0)))

        if self._last_worth is None:
            self._last_worth = current_worth
            sortino_ratio = 0.0
        else:
            # 计算日收益率
            if self._last_worth > 0:
                daily_return = (current_worth - self._last_worth) / self._last_worth
                self._returns.append(daily_return)
                
                # 计算索提诺比率 (需要至少10个数据点)
                if len(self._returns) >= 10:
                    returns_array = np.array(self._returns)
                    
                    # 计算平均超额收益
                    excess_returns = returns_array - self._risk_free_rate
                    mean_excess_return = np.mean(excess_returns)
                    
                    # 计算下行标准差 (只考虑负超额收益)
                    negative_excess_returns = excess_returns[excess_returns < 0]
                    if len(negative_excess_returns) > 0:
                        downside_deviation = np.sqrt(np.mean(negative_excess_returns ** 2))
                        sortino_ratio = mean_excess_return / downside_deviation if downside_deviation > 0 else 0
                    else:
                        # 没有负收益，设为一个大的正值
                        sortino_ratio = mean_excess_return / 0.0001 if mean_excess_return > 0 else 0
                    
                    # 年化索提诺比率
                    sortino_ratio = sortino_ratio * np.sqrt(252)
                else:
                    sortino_ratio = 0.0
            else:
                sortino_ratio = 0.0
            
            self._last_worth = current_worth
        
        self.add_data(sortino_ratio)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录索提诺比率到数据库"""
        self.add_record()

    @property
    def current_sortino_ratio(self) -> float:
        """当前索提诺比率（只读属性）"""
        return self.current_value

    @property
    def downside_volatility(self) -> float:
        """下行波动率（只读属性）"""
        if len(self._returns) >= 2:
            returns_array = np.array(self._returns)
            excess_returns = returns_array - self._risk_free_rate
            negative_excess_returns = excess_returns[excess_returns < 0]
            if len(negative_excess_returns) > 0:
                return float(np.sqrt(np.mean(negative_excess_returns ** 2)) * np.sqrt(252))
        return 0.0