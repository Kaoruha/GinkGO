import datetime
import sys
import random
from time import sleep
import random
from ginkgo.libs import datetime_normalize
from ginkgo.enums import (
    EVENT_TYPES,
    ATTITUDE_TYPES,
    ORDERSTATUS_TYPES,
    ORDER_TYPES,
    DIRECTION_TYPES,
)
from ginkgo.backtest.events import (
    EventPriceUpdate,
    EventOrderSubmitted,
    EventOrderFilled,
    EventOrderCanceled,
)
from ginkgo import GLOG
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MOrder
from ginkgo.backtest.matchmakings.base_matchmaking import MatchMakingBase


class MatchMakingSim(MatchMakingBase):
    def __init__(self, name: str = "SIMMATCH", *args, **kwargs):
        super(MatchMakingSim, self).__init__(name, *args, **kwargs)
        self._attitude = ATTITUDE_TYPES.PESSMISTIC  # TODO maybe can be set by someway
        self._slip_base = 0.2

    def set_attituede(self, attitude: ATTITUDE_TYPES):
        """
        Change the match price
        PESSMISTIC
        OPTIMISTIC
        RANDOM
        """
        self._attitude = attitude

    @property
    def slippage(self) -> float:
        r = self._slip_base * (random.random() * 2 - 1 + 1)
        return r if r < 1 else 1

    @property
    def attitude(self) -> ATTITUDE_TYPES:
        return self._attitude

    def return_order(self, order):
        order.status = ORDERSTATUS_TYPES.CANCELED
        GDATA.commit()
        canceld_order = EventOrderCanceled(order.uuid)
        GLOG.WARN(f"Return a CANCELED ORDER")
        self.engine.put(canceld_order)

    def on_stock_order(self, event: EventOrderSubmitted):
        # Check if the id exsist
        GLOG.INFO(f"{self.name} got an ORDER {event.order_id}.")
        order_id = event.order_id
        o = self.query_order(order_id)
        if o is None:
            return
        if o.timestamp < self.now:
            GLOG.CRITICAL("Will not handle the order {event.order_id} from past")
            self.return_order(o)
            return
        if o.timestamp > self.now:
            GLOG.CRITICAL("Will not handle the order {event.order_id} from future")
            self.return_order(o)
            return

        # Check Order Status
        if o.status == ORDERSTATUS_TYPES.NEW:
            o.status = ORDERSTATUS_TYPES.SUBMITTED
            GDATA.commit()
        if o.status != ORDERSTATUS_TYPES.SUBMITTED:
            GLOG.ERROR(f"Only accept SUBMITTED order. {order_id} is under {o.status}")
            o.status = ORDERSTATUS_TYPES.CANCELED
            GDATA.commit()
            canceld_order = EventOrderCanceled(o.uuid)
            self.engine.put(canceld_order)
            return
        if order_id in self.order_book:
            GLOG.WARN(f"Order {order_id} is cached in queue, do not resubmit.")
            self.return_order(o)
        else:
            self.order_book.append(order_id)

        GLOG.INFO(f"{self.now} OrderBooks: {len(self.order_book)}")
        self.try_match()

    def query_order(self, order_id: str) -> MOrder:
        """
        query order from database
        """
        if not isinstance(order_id, str):
            GLOG.WARN("Order id only support string.")
            return
        o = GDATA.get_order(order_id)
        if o is None:
            GLOG.WARN(f"Order {order_id} not exsist.")
        return o

    def try_match(self):
        GLOG.INFO("Try Match.")
        for order_id in self.order_book:
            # Get the order from db
            o = self.query_order(order_id)
            oid = o.uuid
            # Get the price info from self.price_info
            p = self.price
            if p.shape[0] == 0:
                GLOG.CRITICAL("There is no price data. Need to check the code.")
                self.return_order(o)
                continue

            p = p[p.code == o.code]

            # If there is no price info, try match next order
            if p.shape[0] == 0:
                GLOG.ERROR(f"Have no Price info about {o.code} on {self.now}.")
                self.return_order(o)
                continue
            elif p.shape[0] > 1:
                GLOG.CRITICAL(
                    f"Price info {o.code} has more than 1 record. Something wrong in code."
                )
                self.return_order(o)
                continue

            # # Try match
            p = p.iloc[0, :]
            transaction_price = 0
            high = p.high
            low = p.low
            open = p.open
            if o.direction == DIRECTION_TYPES.SHORT:
                if o.volume == 0:
                    self.return_order(o)
                    continue
                GLOG.WARN(f"Start Matching SHORT ORDER")
                print(o)
            # 1. If limit price
            if o.type == ORDER_TYPES.LIMITORDER:
                # 1.1 If the limit price is out of the bound of price_info, Cancel the order
                if o.limit_price < p.low:
                    GLOG.INFO(
                        f"Order {o.uuid} limit price {o.limit_price} is under the valley: {p.low}."
                    )
                    self.return_order(o)
                    continue

                if o.limit_price > p.high:
                    GLOG.INFO(
                        f"Order {o.uuid} limit price {o.limit_price} is over the peak: {p.high}."
                    )
                    self.return_order(o)
                    continue

                # 1.2 If the limit price > low and < high
                # 1.2.1 Make the deal.
                if o.volume > p.volume:
                    GLOG.ERROR(
                        f"Order {o.uuid} limit price {o.limit_price} volume: {o.volume} is over the volume: {p.volume}."
                    )
                    self.return_order(o)
                    continue
                transaction_price = o.limit_price

            # 2. If Maket price
            elif o.type == ORDER_TYPES.MARKETORDER:
                # 2.1 pessimistic
                if self.attitude == ATTITUDE_TYPES.PESSMISTIC:
                    # 2.1.1 If buy, the fill price should be open + (high - open) * self.slippage
                    if o.direction == DIRECTION_TYPES.LONG:
                        transaction_price = (
                            p.open + abs(p.high - p.open) * self.slippage
                        )
                        transaction_price = round(transaction_price, 4)
                    # 2.1.2 If sell, the fill price shoudl be open - (open - low) * self.slippage
                    elif o.direction == DIRECTION_TYPES.SHORT:
                        transaction_price = p.open - abs(p.open - p.low) * self.slippage
                # 2.2 optimistic
                elif self.attitude == ATTITUDE_TYPES.OPTIMISTIC:
                    # 2.2.1 If buy, the fill price should be open - (open - low) * self.slippage
                    if o.direction == DIRECTION_TYPES.LONG:
                        transaction_price = p.open - abs(p.open - p.low) * self.slippage
                    # 2.2.2 If sell, the fill price shoudl be open + (high - open) * self.slippage
                    elif o.direction == DIRECTION_TYPES.SHORT:
                        transaction_price = (
                            p.open + abs(p.high - p.open) * self.slippage
                        )
                elif self.attitude == ATTITUDE_TYPES.RANDOM:
                    transaction_price = p.low + abs(p.high - p.low) * random.random()

            o.status = ORDERSTATUS_TYPES.FILLED
            o.transaction_price = round(transaction_price, 4)
            volume = float(transaction_price * o.volume)
            volume = round(volume, 4)
            is_long = o.direction == DIRECTION_TYPES.LONG
            fee = self.cal_fee(volume, is_long)
            o.fee = round(fee, 4)
            remain = 0
            if is_long:
                remain = float(o.frozen) - volume - fee
            else:
                remain = volume - fee
            o.remain = round(remain, 4)
            if o.direction == DIRECTION_TYPES.SHORT:
                GLOG.WARN(f"Complete Matching SHORT ORDER")
                print(o)
            # 1.2.3 Give it back to db
            GDATA.commit()
            self.order_book.remove(o.uuid)
            filled_order = EventOrderFilled(o.uuid)
            self.engine.put(filled_order)
        GLOG.INFO("Done Match.")
        self._order_book = []
        # # If there is no detail about the code, Try get the data from db again.The store the info into self.price_info.
        # # According the price_info, try match the order.
