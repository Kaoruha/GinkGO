from ginkgo.backtest.base import Base


class Position(Base):
    def __init__(self, *args, **kwargs):
        super(Position, self).__init__(*args, **kwargs)
        self.code = ""
        self.price = 0
        self.volume = 0
