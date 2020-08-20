from .base_strategy import BaseStrategy


class MovingAverageStrategy(BaseStrategy):
    def __init__(self, *, short: int, long: int):
        self.short = short
        self.long = long
    def enter_market(self):
        pass

    def exiting_market(self):
        pass
