class Tick:
    def __init__(self):
        self.timestamp = None
        self.price = 0
        self.vol = 0
        self.turnover = 0
        self.code = "sh.600001"
        self.side = BUY
        self.dir = TickDirection.ZeroMinusTick
