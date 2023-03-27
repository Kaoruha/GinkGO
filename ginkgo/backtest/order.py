import uuid
import datetime
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize


class Order(object):
    def __init__(
        self,
        timestamp: str or datetime.datetime,
        code: str,
        direction: DIRECTION_TYPES,
        order_type: ORDER_TYPES,
        volume: int,
        limit_price: float = 0.0,
    ):
        self.code = code
        self.timestamp = datetime_normalize(timestamp)
        self.__id = uuid.uuid4().hex
        self.direction = DIRECTION_TYPES.LONG
        self.__order_type = order_type
        self.volume = volume
        self.limit_price = limit_price

        self.__status = ORDERSTATUS_TYPES.NEW

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
        return base_repr(self, Order.__name__, 12, 60)

    def submit(self):
        self.__status = ORDERSTATUS_TYPES.SUBMITTED

    def fill(self):
        self.__status = ORDERSTATUS_TYPES.FILLED

    def cancel(self):
        self.__status = ORDERSTATUS_TYPES.CANCELED
