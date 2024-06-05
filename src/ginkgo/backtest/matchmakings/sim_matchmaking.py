import datetime
import sys
import scipy.stats as stats
import random


from ginkgo.libs import datetime_normalize
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MOrder
from ginkgo.enums import (
    EVENT_TYPES,
    ATTITUDE_TYPES,
    ORDERSTATUS_TYPES,
    ORDER_TYPES,
    DIRECTION_TYPES,
)
from ginkgo.backtest.matchmakings.base_matchmaking import MatchMakingBase
from ginkgo.backtest.events import (
    EventPriceUpdate,
    EventOrderSubmitted,
    EventOrderFilled,
    EventOrderCanceled,
)


class MatchMakingSim(MatchMakingBase):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "SIMMATCH", *args, **kwargs):
        super(MatchMakingSim, self).__init__(name, *args, **kwargs)
        self._attitude = ATTITUDE_TYPES.PESSMISTIC
        self._slip_base = 0.2

    def set_attituede(self, attitude: ATTITUDE_TYPES) -> ATTITUDE_TYPES:
        """
        Change the match price
        Args:
            attitude(enum): PESSMISTIC, OPTIMISTIC, RANDOM
        Returns:
            current attitude
        """
        self._attitude = attitude
        return self.attitude

    @property
    def attitude(self) -> ATTITUDE_TYPES:
        return self._attitude

    @property
    def slippage(self) -> float:
        r = self._slip_base * random.random()
        r = r if r < 1 else 1
        return r

    def return_order(self, order_id: str) -> None:
        """
        Cancel the order.
        Args:
            order_id(str): order id
        Returns:
            None
        """
        order = GDATA.get_order(order_id=order_id)
        order.status = ORDERSTATUS_TYPES.CANCELED
        GDATA.get_driver(MOrder).session.merge(order)
        GDATA.get_driver(MOrder).session.commit()
        GDATA.get_driver(MOrder).session.close()
        canceld_order = EventOrderCanceled(order_id)
        GLOG.WARN(f"Return a CANCELED ORDER")
        self.engine.put(canceld_order)

    def get_random_transaction_price(
        self,
        direction: DIRECTION_TYPES,
        low: float,
        high: float,
        attitude: ATTITUDE_TYPES,
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
        mean = (low + high) / 2
        std_dev = (high - low) / 6
        if attitude == ATTITUDE_TYPES.RANDOM:
            rs = stats.norm.rvs(loc=mean, scale=std_dev, size=1)
        else:
            skewness_right = mean
            skewness_left = -mean
            if attitude == ATTITUDE_TYPES.OPTIMISTIC:
                if direction == DIRECTION_TYPES.LONG:
                    rs = stats.skewnorm.rvs(
                        skewness_right, loc=mean, scale=std_dev, size=1
                    )
                else:
                    rs = stats.skewnorm.rvs(
                        skewness_left, loc=mean, scale=std_dev, size=1
                    )
            elif attitude == ATTITUDE_TYPES.PESSMISTIC:
                if direction == DIRECTION_TYPES.LONG:
                    rs = stats.skewnorm.rvs(
                        skewness_left, loc=mean, scale=std_dev, size=1
                    )
                else:
                    rs = stats.skewnorm.rvs(
                        skewness_right, loc=mean, scale=std_dev, size=1
                    )
            else:
                # TODO
                pass
        rs = rs[0]
        if rs > high:
            GLOG.CRITICAL(f"Transaction price {rs} is over the high price {high}.")
            rs = high
        if rs < low:
            GLOG.CRITICAL(f"Transaction price {rs} is under the low price {low}.")
            rs = low
        return rs

    def on_stock_order(self, event: EventOrderSubmitted):
        """
        Handlering the Order.
        Args:
            event(EventOrderSubmitted): event
        Returns:
            None
        """
        # Check if the id exsist
        GLOG.DEBUG(f"{self.name} got an ORDER {event.order_id}.")
        print(f"{self.name} got an ORDER {event.order_id}.")
        order_id = event.order_id
        o = self.query_order(order_id)
        if o is None:
            return
        if o.timestamp < self.now:
            GLOG.CRITICAL("Will not handle the order {event.order_id} from past.")
            self.return_order(order_id)
            return
        if o.timestamp > self.now:
            GLOG.CRITICAL("Will not handle the order {event.order_id} from future.")
            self.return_order(order_id)
            return

        # Check Order Status
        if o.status == ORDERSTATUS_TYPES.NEW:
            o.status = ORDERSTATUS_TYPES.SUBMITTED
            GDATA.get_driver(MOrder).session.merge(o)
            GDATA.get_driver(MOrder).session.commit()
            GDATA.get_driver(MOrder).session.close()

        if o.status != ORDERSTATUS_TYPES.SUBMITTED:
            GLOG.ERROR(f"Only accept SUBMITTED order. {order_id} is under {o.status}")
            self.return_order(order_id)
            return

        if order_id in self.order_book:
            GLOG.WARN(f"Order {order_id} is cached in queue, do not resubmit.")
            self.return_order(order_id)
        else:
            self.order_book.append(order_id)

        GLOG.INFO(f"{self.now} OrderBooks: {len(self.order_book)}")
        self.try_match()

    def query_order(self, order_id: str) -> MOrder:
        """
        Query order from database.
        Args:
            order_id(str): order id
        Returns:
            Model of Order.
        """
        if not isinstance(order_id, str):
            GLOG.WARN("Order id only support string.")
            return
        o = GDATA.get_order(order_id)
        if o is None:
            GLOG.WARN(f"Order {order_id} not exsist.")
        return o

    def try_match(self):
        """
        Sim match. Iterrow the order book and try match.
        Args:
            None
        Returns:
            None
        """
        GLOG.DEBUG("Try Match.")
        for order_id in self.order_book:
            # Get the order from db
            o = self.query_order(order_id)
            if o.volume == 0:
                self.return_order(order_id)
                continue
            oid = o.uuid
            # Get the price info from self.price_info
            p = self.price
            if p.shape[0] == 0:
                GLOG.WARN("There is no price data. Need to check the code.")
                import pdb

                pdb.set_trace()
                self.return_order(order_id)  # TODO Resubmmit the event.
                continue

            p = p[p.code == o.code]

            # If there is no price info, try match next order
            if p.shape[0] == 0:
                GLOG.ERROR(f"Have no Price info about {o.code} on {self.now}.")
                import pdb

                pdb.set_trace()
                self.return_order(order_id)
                continue
            elif p.shape[0] > 1:
                GLOG.CRITICAL(
                    f"Price info {o.code} has more than 1 record. Something wrong in code."
                )
                import pdb

                pdb.set_trace()
                self.return_order(order_id)
                continue

            # Try match
            p = p.iloc[0, :]
            transaction_price = 0
            high = p.high
            low = p.low
            open = p.open
            close = p.close
            if high <= 0:
                return
            if low <= 0:
                return
            if low <= 0:
                return
            if close <= 0:
                return

            # Cancle the order if the price is out of the bound, or the volume is over the bound.
            # Cancel the order when price go to limit.
            if o.type == ORDER_TYPES.LIMITORDER:
                if o.limit_price < low:
                    GLOG.WARN(
                        f"Order {o.uuid} limit price {o.limit_price} is under the valley: {p.low}."
                    )
                    self.return_order(order_id)
                    continue
                if o.limit_price > high:
                    GLOG.WARN(
                        f"Order {o.uuid} limit price {o.limit_price} is over the peak: {p.high}."
                    )
                    self.return_order(order_id)
                    continue
                if o.volume > p.volume:
                    GLOG.WARN(
                        f"Order {o.uuid} limit price {o.limit_price} volume: {o.volume} is over the volume: {p.volume}."
                    )
                    self.return_order(order_id)
                    continue
            if o.direction == DIRECTION_TYPES.LONG:
                if close / open >= 1.098:
                    GLOG.WARN(f"Order {o.uuid} is over the limit price.")
                    self.return_order(order_id)
                    continue
            elif o.direction == DIRECTION_TYPES.SHORT:
                if (open - close) / open >= 0.095:
                    GLOG.WARN(f"Order {o.uuid} is over the limit price.")
                    self.return_order(order_id)
                    continue

            # Determine transaction price
            transaction_price = 0
            # 1. If limit price
            if o.type == ORDER_TYPES.LIMITORDER:
                transaction_price = o.limit_price
            # 2. If Maket price
            elif o.type == ORDER_TYPES.MARKETORDER:
                transaction_price = self.get_random_transaction_price(
                    o.direction, low, high, self.attitude
                )

            transaction_price = round(transaction_price, 4)
            o.status = ORDERSTATUS_TYPES.FILLED
            o.transaction_price = transaction_price
            transaction_money = float(transaction_price * o.volume)
            transaction_money = round(transaction_money, 4)
            is_long = o.direction == DIRECTION_TYPES.LONG
            fee = self.cal_fee(transaction_price, is_long)
            o.fee = round(fee, 4)
            remain = 0
            if is_long:
                cost = transaction_money + fee
                remain = float(o.frozen) - cost
                if remain < 0:
                    GLOG.WARN(
                        f"Order {o.uuid} has not enough money. Should freeze more."
                    )
                    print(o)
                    self.return_order(order_id)
                    continue
            else:
                remain = transaction_money - fee
            o.remain = round(remain, 4)
            # 1.2.3 Give it back to db
            GDATA.get_driver(MOrder).session.merge(o)
            GDATA.get_driver(MOrder).session.commit()
            GDATA.get_driver(MOrder).session.close()
            self.order_book.remove(o.uuid)
            filled_order = EventOrderFilled(o.uuid)
            self.engine.put(filled_order)
        GLOG.INFO("Done Match.")
        self._order_book = []
        # If there is no detail about the code, Try get the data from db again.The store the info into self.price_info.
        # According the price_info, try match the order.
