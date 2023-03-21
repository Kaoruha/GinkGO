import uuid
import datetime
from ginkgo.backtest.enums import Direction, OrderStatus, OrderType
from ginkgo.libs.ginkgo_pretty import pretty_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class Order(object):
    def __init__(
        self,
        timestamp: str or datetime.datetime,
        code: str,
        direction: Direction,
        order_type: OrderType,
        quantity: int,
        limit_price: float = 0.0,
    ):
        self.code = code
        self.timestamp = datetime_normalize(timestamp)
        self.__id = uuid.uuid3(
            uuid.NAMESPACE_DNS, str(datetime.datetime.now()) + Order.__name__
        )
        self.direction = Direction.LONG
        self.__order_type = order_type
        self.quantity = quantity
        self.limit_price = limit_price

        self.__status = OrderStatus.NEW

    @property
    def status(self):
        return self.__status

    @property
    def order_type(self):
        return self.__order_type

    @property
    def id(self):
        return self.__id

    def __repr__(self):
        mem = f"Mem    : {hex(id(self))}"
        event_id = f"ID     : {self.id}"
        date = f"Date   : {self.timestamp}"
        direction = f"Dir    : {self.direction}"
        order_type = f"Type   : {self.order_type}"
        amount = f"Quant  : {self.quantity}"
        status = f"Status : {self.status} : {self.status.value}"
        price = f"Price  : {self.limit_price}"
        msg = [mem, event_id, date, direction, order_type, amount, status]
        if self.order_type == OrderType.LIMITORDER:
            msg.append(price)
        return pretty_repr(Order.__name__, msg)

    def submit(self):
        self.__status = OrderStatus.SUBMITTED

    def fill(self):
        self.__status = OrderStatus.FILLED

    def cancel(self):
        self.__status = OrderStatus.CANCELED
