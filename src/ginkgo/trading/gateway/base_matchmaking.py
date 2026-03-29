# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: BaseMatchmaking基础撮合定义订单撮合抽象接口支持交易系统功能支持交易系统功能支持交易系统功能和组件集成提供完整业务支持






from typing import TYPE_CHECKING, Dict, List


import datetime
import time
import pandas as pd

from decimal import Decimal


from ginkgo.libs import datetime_normalize, to_decimal, Number, GLOG
from ginkgo.trading.events import EventPriceUpdate
from ginkgo.enums import PRICEINFO_TYPES, DIRECTION_TYPES
from ginkgo.entities.base import Base
from ginkgo.entities.mixins import TimeMixin
from ginkgo.entities.mixins import NamedMixin
from ginkgo.trading.engines.base_engine import BaseEngine


class MatchMakingBase(TimeMixin, NamedMixin, Base):
    def __init__(self, name: str = "MatchMaking", timestamp=None, *args, **kwargs):
        super().__init__(name=name, *args, **kwargs)
        if timestamp is not None:
            self.set_business_timestamp(timestamp)
        self._price_cache = pd.DataFrame()
        self._order_book: Dict[str, List] = {}
        self._commission_rate = Decimal("0.0003")
        self._commission_min = 5
        self._data_feeder = None
        
    def set_event_publisher(self, publisher) -> None:
        """
        Inject an event publisher (typically engine.put) for pushing events back to engine.
        """
        self._engine_put = publisher

    def bind_data_feeder(self, feeder, *args, **kwargs):
        self._data_feeder = feeder

    def put(self, event) -> None:
        """
        Put event to eventengine.
        """
        if self._engine_put is None:
            GLOG.ERROR(f"Engine put not bind. Events can not put back to the engine.")
            return
        self._engine_put(event)

    @property
    def price_cache(self) -> pd.DataFrame:
        return self._price_cache

    @property
    def commission_rate(self) -> float:
        """
        Rate of commision.
        """
        return self._commission_rate

    @property
    def commission_min(self) -> float:
        """
        The minimal of commission.
        """
        return self._commission_min

    @property
    def order_book(self) -> Dict[str, List]:
        """
        List of order, waiting for match.
        """
        return self._order_book

    def on_order_received(self, *args, **kwargs):
        # If sim, run try_match
        # If live, send the order to broker
        raise NotImplementedError("Function on_stock_order() must be implemented in class.")

    def cal_fee(self, transaction_money: Number, is_long: bool, *args, **kwargs) -> Decimal:
        """
        Calculate fee.
        Args:
            volume(int): volume of trade
            is_long(bool): direction of trade, True -> Long, False -> Short
        Returns:
            Fee
        """
        if transaction_money <= 0:
            GLOG.ERROR(f"Transaction Money should be greater than 0, {transaction_money} is illegal.")
            return 0
        # 印花税，仅卖出时收
        stamp_tax = transaction_money * Decimal("0.001") if not is_long else 0
        # 过户费，买卖均收
        transfer_fees = Decimal("0.00001") * transaction_money
        # 代收规费0.00687%，买卖均收
        collection_fees = Decimal("0.0000687") * transaction_money
        # 佣金，买卖均收
        commission = self.commission_rate * transaction_money
        commission = commission if commission > self.commission_min else self.commission_min

        res = stamp_tax + transfer_fees + collection_fees + commission
        res = round(res, 2)
        return to_decimal(res)

    def advance_time(self, time: any, *args, **kwargs) -> bool:
        """
        撮合引擎时间推进，包含专有的清理逻辑
        Args:
            time(any): new time
        Returns:
            bool: 时间推进是否成功
        """
        # 先调用TimeMixin的advance_time
        result = super().advance_time(time, *args, **kwargs)

        if result:
            # 撮合引擎专有逻辑：清理价格缓存和订单簿
            self._price_cache = pd.DataFrame()
            self._order_book = {}

        return result
