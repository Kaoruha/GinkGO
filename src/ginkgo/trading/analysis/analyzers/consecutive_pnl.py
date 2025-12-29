# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Consecutive Pnl分析器继承BaseAnalyzer计算ConsecutivePnl连续盈亏性能指标






from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd
import numpy as np


class ConsecutivePnL(BaseAnalyzer):
    """连续盈亏分析器 - 记录最大连续盈利和亏损情况"""

    __abstract__ = False

    def __init__(self, name: str = "consecutive_pnl", *args, **kwargs):
        super(ConsecutivePnL, self).__init__(name, *args, **kwargs)
        # 在每天结束时激活计算
        self.add_active_stage(RECORDSTAGE_TYPES.ENDDAY)
        # 在每天结束时记录到数据库
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)

        # 内部状态
        self._last_worth = None

        # 连续盈利统计
        self._current_win_streak = 0
        self._max_win_streak = 0
        self._current_win_amount = 0.0
        self._max_win_amount = 0.0

        # 连续亏损统计
        self._current_loss_streak = 0
        self._max_loss_streak = 0
        self._current_loss_amount = 0.0
        self._max_loss_amount = 0.0

        # 当前状态
        self._current_streak_type = None  # 'win', 'loss', or None

    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """计算连续盈亏统计，存储当前连续亏损天数"""
        current_worth = portfolio_info.get("worth", 0)

        if self._last_worth is None:
            self._last_worth = current_worth
            consecutive_losses = 0
        else:
            # 计算日盈亏
            daily_pnl = current_worth - self._last_worth

            if daily_pnl > 0:
                # 盈利日
                if self._current_streak_type == "win":
                    # 继续盈利
                    self._current_win_streak += 1
                    self._current_win_amount += daily_pnl
                else:
                    # 结束亏损，开始盈利
                    if self._current_streak_type == "loss":
                        # 更新最大亏损记录
                        if self._current_loss_streak > self._max_loss_streak:
                            self._max_loss_streak = self._current_loss_streak
                        if self._current_loss_amount > self._max_loss_amount:
                            self._max_loss_amount = self._current_loss_amount

                    # 开始新的盈利序列
                    self._current_win_streak = 1
                    self._current_win_amount = daily_pnl
                    self._current_loss_streak = 0
                    self._current_loss_amount = 0.0
                    self._current_streak_type = "win"

            elif daily_pnl < 0:
                # 亏损日
                if self._current_streak_type == "loss":
                    # 继续亏损
                    self._current_loss_streak += 1
                    self._current_loss_amount += abs(daily_pnl)
                else:
                    # 结束盈利，开始亏损
                    if self._current_streak_type == "win":
                        # 更新最大盈利记录
                        if self._current_win_streak > self._max_win_streak:
                            self._max_win_streak = self._current_win_streak
                        if self._current_win_amount > self._max_win_amount:
                            self._max_win_amount = self._current_win_amount

                    # 开始新的亏损序列
                    self._current_loss_streak = 1
                    self._current_loss_amount = abs(daily_pnl)
                    self._current_win_streak = 0
                    self._current_win_amount = 0.0
                    self._current_streak_type = "loss"

            # 存储当前连续亏损天数（主要指标）
            consecutive_losses = self._current_loss_streak
            self._last_worth = current_worth

        self.add_data(consecutive_losses)

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """记录连续亏损数据到数据库"""
        self.add_record()

    @property
    def current_consecutive_losses(self) -> int:
        """当前连续亏损天数（只读属性）"""
        return self._current_loss_streak

    @property
    def max_consecutive_losses(self) -> int:
        """历史最大连续亏损天数（只读属性）"""
        return max(self._max_loss_streak, self._current_loss_streak)

    @property
    def current_consecutive_wins(self) -> int:
        """当前连续盈利天数（只读属性）"""
        return self._current_win_streak

    @property
    def max_consecutive_wins(self) -> int:
        """历史最大连续盈利天数（只读属性）"""
        return max(self._max_win_streak, self._current_win_streak)

    @property
    def current_loss_amount(self) -> float:
        """当前连续亏损金额（只读属性）"""
        return self._current_loss_amount

    @property
    def max_loss_amount(self) -> float:
        """历史最大连续亏损金额（只读属性）"""
        return max(self._max_loss_amount, self._current_loss_amount)

    @property
    def current_win_amount(self) -> float:
        """当前连续盈利金额（只读属性）"""
        return self._current_win_amount

    @property
    def max_win_amount(self) -> float:
        """历史最大连续盈利金额（只读属性）"""
        return max(self._max_win_amount, self._current_win_amount)

    @property
    def current_streak_type(self) -> str:
        """当前连续状态类型（只读属性）"""
        if self._current_streak_type is None:
            return "无"
        elif self._current_streak_type == "win":
            return "连续盈利"
        else:
            return "连续亏损"

    @property
    def streak_ratio(self) -> float:
        """连续盈利/亏损比率（只读属性）"""
        max_wins = self.max_consecutive_wins
        max_losses = self.max_consecutive_losses
        if max_losses > 0:
            return float(max_wins / max_losses)
        return float(max_wins) if max_wins > 0 else 0.0
