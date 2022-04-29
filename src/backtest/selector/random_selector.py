"""
Author: Kaoru
Date: 2022-04-02 01:44:20
LastEditTime: 2022-04-02 01:44:21
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/src/backtest/selector/random_selector.py
What goes around comes around.
"""
from src.backtest.selector.base_selector import BaseSelector
from src.util.stock_filter import remove_index


class RandomSelector(BaseSelector):
    def __init__(self, name="随机选股", count=1, interval=0):
        super().__init__(name)
        self.count = count  # 选股数量
        self.interval = interval  # 重新选股间隔, 0为无限
        self.result = None
        self.timer = 0
        self.history = []

    def get_result(self, today: str) -> list:
        if self.result is None:
            self.result = remove_index().sample(self.count).code.tolist()
            self.record(date=today, result=self.result)

        if self.interval != 0:
            self.timer += 1
            if self.timer >= self.interval:
                self.result = remove_index().sample(self.count).code.tolist()
                self.record(date=today, result=self.result)
                self.timer = 0

        return self.result

    def record(self, date: str, result: list) -> None:
        self.history.append((date, result))
