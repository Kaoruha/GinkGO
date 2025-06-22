import datetime
import pandas as pd
import sys
import scipy.stats as stats
import random
from decimal import Decimal


from ginkgo.libs import datetime_normalize, to_decimal, Number
from ginkgo.data.models import MOrder
from ginkgo.enums import (
    EVENT_TYPES,
    ATTITUDE_TYPES,
    ORDERSTATUS_TYPES,
    ORDER_TYPES,
    DIRECTION_TYPES,
    SOURCE_TYPES,
)
from ginkgo.backtest.matchmakings.base_matchmaking import MatchMakingBase
from ginkgo.backtest.events import (
    EventPriceUpdate,
    EventOrderSubmitted,
    EventOrderFilled,
    EventOrderCanceled,
)
from ginkgo.backtest import Order


class MatchMakingSim(MatchMakingBase):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "SIMMATCH", *args, **kwargs):
        super(MatchMakingSim, self).__init__(name, *args, **kwargs)
        self._attitude = ATTITUDE_TYPES.PESSMISTIC  # PESSMISTIC, OPTIMISTIC effect the price mathced.
        self._slip_base = 0.2

    def set_attituede(self, attitude: ATTITUDE_TYPES, *args, **kwargs):
        """
        Change the match price
        Args:
            attitude(enum): PESSMISTIC, OPTIMISTIC, RANDOM
        Returns:
            current attitude
        """
        if not isinstance(attitude, ATTITUDE_TYPES):
            self.log("ERROR", "Attitude only support ATTITUDE_TYPES.")
            return
        self._attitude = attitude

    def on_price_received(self, event, *args, **kwargs):
        if event.timestamp > self.now:
            self.log("ERROR", f"The price {event.value} can not from the future.")
            import pdb

            pdb.set_trace()
            return
        df = event.value.to_dataframe()
        self._price_cache = pd.concat([self._price_cache, df], ignore_index=True)

    @property
    def attitude(self) -> ATTITUDE_TYPES:
        return self._attitude

    @property
    def slippage(self) -> float:
        r = self._slip_base * random.random()
        r = r if r < 1 else 1
        return r

    def cancel_order(self, order: Order, *args, **kwargs) -> None:
        """
        Cancel the order.
        Args:
            order_id(str): order id
        Returns:
            None
        """
        order.cancel()
        self.log("DEBUG", f"Return a CANCELED ORDER")
        self.put(EventOrderCanceled(order))

    def get_random_transaction_price(
        self, direction: DIRECTION_TYPES, low: Number, high: Number, attitude: ATTITUDE_TYPES, *args, **kwargs
    ) -> float:
        """
        Calculate the transaction price.
        Args:
            direction(enum): LONG or SHORT
            low(float): the lowest price
            high(float): the highest price
            attitude(enum): PESSMISTIC, OPTIMISTIC, RANDOM
        Returns:
            Transaction Price.
        """
        low = to_decimal(low)
        low = float(low)
        high = to_decimal(high)
        high = float(high)
        mean = (low + high) / 2
        mean = float(mean)
        std_dev = (high - low) / 6
        std_dev = float(std_dev)
        if attitude == ATTITUDE_TYPES.RANDOM:
            rs = stats.norm.rvs(loc=mean, scale=std_dev, size=1)
        else:
            skewness_right = mean
            skewness_left = -mean
            if attitude == ATTITUDE_TYPES.OPTIMISTIC:
                if direction == DIRECTION_TYPES.LONG:
                    rs = stats.skewnorm.rvs(skewness_right, loc=mean, scale=std_dev, size=1)
                else:
                    rs = stats.skewnorm.rvs(skewness_left, loc=mean, scale=std_dev, size=1)
            elif attitude == ATTITUDE_TYPES.PESSMISTIC:
                if direction == DIRECTION_TYPES.LONG:
                    rs = stats.skewnorm.rvs(skewness_left, loc=mean, scale=std_dev, size=1)
                else:
                    rs = stats.skewnorm.rvs(skewness_right, loc=mean, scale=std_dev, size=1)
            else:
                # TODO
                pass
        rs = rs[0]
        if rs > high:
            self.log("CRITICAL", f"Transaction price {rs} is over the high price {high}.")
            rs = high
        if rs < low:
            self.log("CRITICAL", f"Transaction price {rs} is under the low price {low}.")
            rs = low
        rs = round(rs, 2)
        return to_decimal(rs)

    def is_order_valid(self, order: Order, *args, **kwargs) -> bool:
        """
        Check if the order is valid.
        Args:
            order(Order): order
        Returns:
            True or False
        """
        if order is None:
            return False

        if order.timestamp < self.now:
            self.log("CRITICAL", "Will not handle the order {event.order_id} from past.")
            return False
        if order.timestamp > self.now:
            self.log("CRITICAL", "Will not handle the order {event.order_id} from future.")
            return False
        # Check Order Status
        if order.status == ORDERSTATUS_TYPES.NEW:
            order.submit()
            self.log("WARN", "Simmatch got a new order. Should not happen.")
        if order.status != ORDERSTATUS_TYPES.SUBMITTED:
            self.log("ERROR", f"Only accept SUBMITTED order. {order_id} is under {o.status}")
            self.cancel_order(order_id)
            return False
        return True

    def is_price_valid(self, code: str, price: pd.DataFrame, *args, **kwargs) -> bool:
        """
        Check if the price is valid.
        Args:
            price(pd.DataFrame): price
        Returns:
            True or False
        """
        if not isinstance(price, pd.DataFrame):
            self.log("WARN", f"Price is not a data frame. {type(price)}")
            return False
        # If there is no price info, try match next order
        if price.shape[0] == 0:
            self.log("ERROR", f"Have no Price info about {code} on {self.now}.")
            return False

        elif price.shape[0] > 1:
            self.log("CRITICAL", f"Price info {code} has more than 1 record. Something wrong in code.")
            return False

        # Try match
        p = price.iloc[0]
        if p["high"] <= 0:
            return False
        if p["open"] <= 0:
            return False
        if p["low"] <= 0:
            return False
        if p["close"] <= 0:
            return False
        return True

    def can_limit_order_be_filled(self, order: Order, price: pd.Series, *args, **kwargs) -> bool:
        # Cancle the order if the price is out of the bound, or the volume is over the bound.
        if order.limit_price < price["low"]:
            self.log("WARN", f"Order {order.uuid} limit price {order.limit_price} is under the valley: {price.low}.")
            return False
        if order.limit_price > price["high"]:
            self.log("WARN", f"Order {order.uuid} limit price {order.limit_price} is over the peak: {price.high}.")
            return False
        if order.volume > price["volume"]:
            self.log(
                "WARN",
                f"Order {order.uuid} limit price {order.limit_price} volume: {order.volume} is over the volume: {price.volume}.",
            )
            return False
        return True

    def can_market_order_be_filled(self, order: Order, price: pd.Series, *args, **kwargs) -> bool:
        return True

    def is_price_limit_up(self, price: pd.Series, *args, **kwargs) -> bool:
        if price["close"] / price["open"] >= 1.098:
            return True
        return False

    def is_price_limit_down(self, price: pd.Series, *args, **kwargs) -> bool:
        limit_price = price["open"] * Decimal("0.995")
        if price["close"] <= limit_price:
            return True
        return False

    def process_order_execution(self, order: Order, price: pd.Series, *args, **kwargs) -> Order:
        # Determine transaction price
        transaction_price = 0
        # 1. If limit price
        if order.order_type == ORDER_TYPES.LIMITORDER:
            transaction_price = order.limit_price
        # 2. If Maket price
        elif order.order_type == ORDER_TYPES.MARKETORDER:
            transaction_price = self.get_random_transaction_price(
                order.direction, price["low"], price["high"], self.attitude
            )

        volume = order.volume
        is_deal = False

        # Adjust Volume if direction is long, in case the frozen money can not afford the share.
        if order.direction == DIRECTION_TYPES.LONG:
            while volume >= 100:
                transaction_money = transaction_price * volume
                fee = self.cal_fee(transaction_money, True)
                cost = transaction_money + fee
                remain = order.frozen - cost
                if remain < 0:
                    volume -= 100
                else:
                    is_deal = True
                    break
            if not is_deal:
                self.cancel_order(order)
                return

        order.transaction_price = transaction_price
        order.transaction_volume = volume
        transaction_money = transaction_price * order.volume
        fee = self.cal_fee(transaction_money, order.direction == DIRECTION_TYPES.LONG)
        order.fee = to_decimal(fee)
        remain = 0
        if order.direction == DIRECTION_TYPES.LONG:
            cost = transaction_money + fee
            remain = order.frozen - cost
        else:
            remain = transaction_money - fee
        order.remain = to_decimal(remain)
        # 1.2.3 Give it back to db
        order.set_source(SOURCE_TYPES.SIMMATCH)
        order.fill()
        self.order_book[order.code].remove(order)
        return order

    def on_order_received(self, event: EventOrderSubmitted, *args, **kwargs) -> None:
        """
        Handlering the Order.
        Args:
            event(EventOrderSubmitted): event
        Returns:
            None
        """
        # Check if the id exsist
        order = event.value
        order_id = event.order_id
        self.log("DEBUG", f"{self.name} got an ORDER {event.code}_{order.direction}.")
        if not self.is_order_valid(order):
            return

        if order.code not in self.order_book.keys():
            self.order_book[order.code] = []
        self.order_book[order.code].append(order)
        self.log("DEBUG", f"{self.name} got an ORDER {event.code} >> {event.direction}.")
        self.try_match()

    def direct_match(self, order, *args, **kwargs) -> None:
        # Get the order from db
        print(1)
        if order.volume == 0:
            self.cancel_order(order)
            return
        code = order.code
        # Get the price info from self.price_info
        if self.price_cache.shape[0] == 0:
            self.log("WARN", f"There is no price about {order.code} on {self.now}. Return the order.")
            self.cancel_order(order)  # TODO Resubmmit?
            return

        print(2)
        try:
            price = self.price_cache[self.price_cache["code"] == order.code]
            if not self.is_price_valid(code, price):
                self.cancel_order(order)
                return
        except Exception as e:
            import pdb

            pdb.set_trace()
            print(e)

        print(3)
        if order.order_type == ORDER_TYPES.LIMITORDER:
            if not self.can_limit_order_be_filled(order, price.iloc[0]):
                self.cancel_order(order)
                return
        elif order.order_type == ORDER_TYPES.MARKETORDER:
            if not self.can_market_order_be_filled(order, price.iloc[0]):
                self.cancel_order(order)
                return

        print(4)
        if order.direction == DIRECTION_TYPES.LONG and self.is_price_limit_up(price.iloc[0]):
            self.cancel_order(order)
            return
        if order.direction == DIRECTION_TYPES.SHORT and self.is_price_limit_down(price.iloc[0]):
            self.cancel_order(order)
            return
        print(5)

        filled_order = self.process_order_execution(order, price.iloc[0])
        if filled_order:
            self.put(EventOrderFilled(filled_order))
        print(6)

    def try_match(self, *args, **kwargs) -> None:
        """
        Sim match. Iterrow the order book and try match.
        """
        self.log("DEBUG", "Try Match.")
        for code in self.order_book:
            for order in self.order_book[code]:
                try:
                    self.direct_match(order)
                except Exception as e:
                    import pdb

                    pdb.set_trace()
                    self.log("ERROR", e)
                finally:
                    pass
        self._order_book = {}
