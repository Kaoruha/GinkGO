# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: VaRCVaR风险价值分析器继承BaseAnalyzer计算VaR和CVaR评估最大潜在损失风险支持交易系统功能和组件集成提供完整业务支持






from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd
import numpy as np


class VarCVar(BaseAnalyzer):
    """VaR/CVaR风险度量分析器 - 计算风险价值和条件风险价值"""
    
    __abstract__ = False

    def __init__(self, name: str = "var_cvar", confidence_level: float = 0.95, window: int = 252, *args, **kwargs):
        super(VarCVar, self).__init__(name, *args, **kwargs)
        # 在每天结束时激活计算
        self.add_active_stage(RECORDSTAGE_TYPES.ENDDAY)
        # 在每天结束时记录到数据库
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)
        
        # 配置参数
        self._confidence_level = confidence_level  # 置信度 (0.95 = 95%)
        self._window = window  # 滚动窗口大小
        
        # 内部状态
        self._returns = []
        self._last_worth = None

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """计算VaR值（存储为负值表示风险）"""
        current_worth = portfolio_info.get("worth", 0)
        
        if self._last_worth is None:
            self._last_worth = current_worth
            var_value = 0.0
        else:
            # 计算日收益率
            if self._last_worth > 0:
                daily_return = (current_worth - self._last_worth) / self._last_worth
                self._returns.append(daily_return)
                
                # 保持窗口大小
                if len(self._returns) > self._window:
                    self._returns.pop(0)
                
                # 计算VaR (需要至少20个数据点)
                if len(self._returns) >= 20:
                    returns_array = np.array(self._returns)
                    
                    # 计算VaR (历史模拟法)
                    var_percentile = (1 - self._confidence_level) * 100
                    var_value = np.percentile(returns_array, var_percentile)
                    
                    # 年化VaR (存储为负值表示风险)
                    var_value = var_value * np.sqrt(252)
                else:
                    var_value = 0.0
            else:
                var_value = 0.0
            
            self._last_worth = current_worth
        
        self.add_data(var_value)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录VaR到数据库"""
        self.add_record()

    @property
    def current_var(self) -> float:
        """当前VaR值（只读属性）"""
        return self.current_value

    @property
    def current_cvar(self) -> float:
        """当前CVaR值（条件风险价值）（只读属性）"""
        if len(self._returns) >= 20:
            returns_array = np.array(self._returns)
            var_percentile = (1 - self._confidence_level) * 100
            var_threshold = np.percentile(returns_array, var_percentile)
            
            # CVaR = 超过VaR损失的平均值
            tail_losses = returns_array[returns_array <= var_threshold]
            if len(tail_losses) > 0:
                cvar_value = np.mean(tail_losses)
                # 年化CVaR
                return float(cvar_value * np.sqrt(252))
        return 0.0

    @property
    def confidence_level(self) -> float:
        """置信度水平（只读属性）"""
        return self._confidence_level

    @property
    def tail_risk_ratio(self) -> float:
        """尾部风险比例 - CVaR/VaR（只读属性）"""
        var = self.current_var
        cvar = self.current_cvar
        if var != 0:
            return float(cvar / var)
        return 0.0

    @property
    def returns_count(self) -> int:
        """收益率数据点数量（只读属性）"""
        return len(self._returns)