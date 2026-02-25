# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: WinRate胜率分析器继承BaseAnalyzer计算交易胜率和盈亏比评估策略表现和盈利能力支持交易系统功能和组件集成提供完整业务支持






from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.libs.data.number import to_decimal
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd
import numpy as np


class WinRate(BaseAnalyzer):
    """胜率分析器 - 统计盈利交易的比例和盈亏比"""
    
    __abstract__ = False

    def __init__(self, name: str = "win_rate", *args, **kwargs):
        super(WinRate, self).__init__(name, *args, **kwargs)
        # 在每天结束时激活计算
        self.add_active_stage(RECORDSTAGE_TYPES.ENDDAY)
        # 在每天结束时记录到数据库
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)
        
        # 内部状态
        self._returns = []
        self._last_worth = None
        self._win_count = 0
        self._loss_count = 0
        self._total_profit = 0.0
        self._total_loss = 0.0

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """计算胜率"""
        current_worth = float(to_decimal(portfolio_info.get("worth", 0)))

        if self._last_worth is None:
            self._last_worth = current_worth
            win_rate = 0.0
        else:
            # 计算日收益
            if self._last_worth > 0:
                daily_pnl = current_worth - self._last_worth
                daily_return = daily_pnl / self._last_worth
                self._returns.append(daily_return)

                # 统计盈亏
                if daily_pnl > 0:
                    self._win_count += 1
                    self._total_profit += daily_pnl
                elif daily_pnl < 0:
                    self._loss_count += 1
                    self._total_loss += abs(daily_pnl)
                
                # 计算胜率
                total_trades = self._win_count + self._loss_count
                if total_trades > 0:
                    win_rate = self._win_count / total_trades
                else:
                    win_rate = 0.0
            else:
                win_rate = 0.0
            
            self._last_worth = current_worth
        
        self.add_data(win_rate)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录胜率到数据库"""
        self.add_record()

    @property
    def current_win_rate(self) -> float:
        """当前胜率（只读属性）"""
        return self.current_value

    @property
    def profit_loss_ratio(self) -> float:
        """盈亏比 - 平均盈利/平均亏损（只读属性）"""
        if self._loss_count > 0 and self._win_count > 0:
            avg_profit = self._total_profit / self._win_count
            avg_loss = self._total_loss / self._loss_count
            return float(avg_profit / avg_loss)
        return 0.0

    @property
    def total_trades(self) -> int:
        """总交易次数（只读属性）"""
        return self._win_count + self._loss_count

    @property
    def win_count(self) -> int:
        """盈利交易次数（只读属性）"""
        return self._win_count

    @property
    def loss_count(self) -> int:
        """亏损交易次数（只读属性）"""
        return self._loss_count