import datetime
import random
from ginkgo.libs import datetime_normalize
from ginkgo.enums import EVENT_TYPES, ATTITUDE_TYPES, ORDERSTATUS_TYPES
from ginkgo.backtest.events import EventPriceUpdate
from ginkgo import GLOG
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.data.models import MOrder
from ginkgo.backtest.matchmakings.base_matchmaking import MatchMakingBase


class MatchMakingSim(MatchMakingBase):
    def __init__(self):
        super(MatchMakingSim, self).__init__(*args, **kwargs)
        self._attitude = ATTITUDE_TYPES.PESSMISTIC  # TODO maybe can be set by someway
        self._slip_base = 0.2

    @property
    def slippage(self) -> float:
        r = self._slip_base * (random.random() * 2 - 1 + 1)
        return r if r < 1 else 1

    @property
    def attitude(self) -> ATTITUDE_TYPES:
        return self._attitude

    def on_stock_order(self, order_id: str):
        # TODO Check if the id exsist
        o = self.query_order(order_id)
        if o is None:
            return
        if o.status == ORDERSTATUS_TYPES.NEW:
            o.status = ORDERSTATUS_TYPES.SUBMITTED
            GDATA.commit()
        if o.status != ORDERSTATUS_TYPES.SUBMITTED:
            GLOG.ERROR(f"Only accept SUBMITTED order. {order_id} is under {o.status}")
            return
        if order_id in self._order:
            GLOG.WARN(f"Order {order_id} is cached in queue, do not resubmit.")
        else:
            self._order.append(order_id)

        self.try_match()

    def query_order(self, order_id: str) -> MOrder:
        if not isinstance(order_id, str):
            GLOG.WARN("Order id only support string.")
            return
        o = GDATA.get_order(order_id)
        if o is None:
            GLOG.WARN(f"Order {order_id} not exsist.")
        return o

    def try_match(self):
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
