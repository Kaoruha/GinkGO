import datetime
import random
from ginkgo.libs import datetime_normalize
from ginkgo.enums import EVENT_TYPES, ATTITUDE_TYPES
from ginkgo.backtest.event import EventPriceUpdate
from ginkgo.libs import GINKGOLOGGER as gl


class MatchMaking_Sim(object):
    def __init__(self):
        self._current = None
        self._price_info = {}
        self._attitude = ATTITUDE_TYPES.PESSMISTIC  # TODO maybe can be set by someway
        self._slip_base = 0.2
        pass

    @property
    def slippage(self) -> float:
        r = self._slip_base * (random.random() * 2 - 1 + 1)
        return r if r < 1 else 1

    @property
    def current_time(self) -> datetime.datetime:
        return self._current

    @property
    def price_info(self) -> dict:
        # The latest price info cache.
        return self._price_info

    @property
    def attitude(self) -> ATTITUDE_TYPES:
        return self._attitude

    def price_update(self, event: EventPriceUpdate):
        # TODO Check the source
        if self._current is None:
            self._current = event.timestamp
            gl.logger.debug(f"Sim MatchMaking start. {self.current_time}")

        # Update Current Time
        if event.timestamp < self._current:
            gl.logger.warn(
                f"Current Time is {self.current_time} the price come from past {event.timestamp}"
            )
            return

    def try_match(self, order_id: str):
        # Get the order from db
        # Get the price info from self.price_info
        # If there is no detail about the code, Try get the data from db again.The store the info into self.price_info.
        # According the price_info, try match the order.
        # 1. If limit price
        # 1.1 If the limit price is out of the bound of price_info, Cancel the order
        # 1.1.1 Change the order status => CANCELED
        # 1.1.2 Give it back to db
        # 1.2 If the limit price > low and < high
        # 1.2.1 Make it deal.
        # 1.2.2 Change the order status => FILLED
        # 1.2.3 Give it back to db
        # 2. If Maket price
        # 2.1 pessimistic
        # 2.1.1 If buy, the fill price should be open + (high - open) * self.slippage
        # 2.1.2 If sell, the fill price shoudl be open - (open - low) * self.slippage
        # 2.2 optimistic
        # 2.2.1 If buy, the fill price should be open - (open - low) * self.slippage
        # 2.2.2 If sell, the fill price shoudl be open + (high - low) * self.slippage
        pass
