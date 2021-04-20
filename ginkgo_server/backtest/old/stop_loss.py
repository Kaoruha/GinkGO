"""
止损策略
"""
import pandas as pd
from .base_strategy import BaseStrategy
from ginkgo_server.backtest.postion import Position
from ginkgo_server.backtest.events import OrderEvent
from ginkgo_server.backtest.enums import DealType


class StopLoss(BaseStrategy):
    def __init__(self, loss: int = 5, target_reduce: int = 100):
        self.loss: float = loss / 100  # 设定止损点，默认5%
        self.target_reduce: float = self.cal_position(
            target_reduce
        )  # 设定目标减仓，默认为100%，直接空仓
        self.name = f"止损策略 {self.loss*100}%浮亏减仓{self.target_reduce*100}%"

    def cal_position(self, target_position: int):
        if target_position <= 0:
            return 0
        elif target_position >= 100:
            return 1
        else:
            return target_position / 100

    def data_transfer(self, data: pd.DataFrame, position: Position):
        # 数据传递至策略
        # 如果当天收盘价达到止损失点，则发出减持信号
        if position is None:
            return
        self.target_price = position.price * (1 - self.loss)
        self.current_price = data["close"]
        self.code = data["code"]
        self.date = data["date"]
        # 尝试产生信号
        if self.current_price <= self.target_price:
            volume = int(position.volume * self.target_reduce / 100) * 100
            self.exit_market(volume=volume)

    def enter_market(
        self,
    ):
        pass

    def exit_market(self, volume):
        order = OrderEvent(
            date=self.date,
            code=self.code,
            source=self.name,
            deal=DealType.SELL,
            target_volume=volume,
        )
        self._engine.put(order)
