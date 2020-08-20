from .base_broker import BaseBroker


class SingleDailyBroker(BaseBroker):
    count = 0

    def general_handler(self):
        pass

    def market_handlers(self):
        pass

    def signal_handlers(self):
        self.count += 1
        print(self.count)

    def order_handlers(self):
        pass

    def fill_handlers(self):
        pass

    def daily_handlers(self):
        self.count += 2
        print(self.count)
