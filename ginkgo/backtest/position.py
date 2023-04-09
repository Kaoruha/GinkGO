from ginkgo.backtest.base import Base


class Position(Base):
    def __init__(self):
        self.code = ""
        self.price = 0
        self.volume = 0
