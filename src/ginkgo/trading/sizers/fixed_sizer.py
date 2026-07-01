# Upstream: PortfolioBase, ComponentFactoryService
# Downstream: BaseSizer, Signal, Order, DIRECTION_TYPES, to_decimal
# Role: 固定仓位管理器，按固定数量下单并自动根据可用资金调整






import datetime
from decimal import Decimal
from typing import Tuple, Optional


from ginkgo.trading.bases.sizer_base import SizerBase as BaseSizer
from ginkgo.entities import Order, Signal
from ginkgo.entities.mixins import LotAlignableMixin
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs import to_decimal, GLOG


class FixedSizer(LotAlignableMixin, BaseSizer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    """
    FixedSizer, set the volume for each order at a fixed amount.
    """
    __abstract__ = False

    def __init__(
        self,
        name: str = "FixedSizer",
        volume: str = "150",
        commission_rate: float = 0.0003,
        commission_min: float = 5,
        stamp_tax: float = 0.001,
        lot_size: int = 100,
        *args,
        **kwargs,
    ):
        """
        Args:
            volume(str): The volume of each order.
            commission_rate(float): 手续费率，默认对齐 SimBroker (0.0003)。
            commission_min(float): 最小手续费（元），默认对齐 SimBroker (5)。
            stamp_tax(float): 印花税率（仅卖出收取），默认 0.001；买入估算不计。
            lot_size(int): 最小交易单位（手），A 股默认 100；参数化以支持
                美股(1)/港股等不同最小交易单位（#6498）。仅作用于开仓(LONG)
                路径的递减步长；平仓(SHORT)路径全量下单不受影响。
        """
        super().__init__(name, *args, **kwargs)
        self._volume = self._convert_to_int(volume, 150)
        self._commission_rate = Decimal(str(commission_rate))
        self._commission_min = Decimal(str(commission_min))
        self._stamp_tax = Decimal(str(stamp_tax))
        self._lot_size = lot_size

    @property
    def volume(self) -> float:
        return self._volume

    def _estimate_cost(self, last_price: Decimal, size: int) -> Decimal:
        """
        估算订单资金占用：成交额 + 手续费（与 SimBroker sim_broker.py:456-457 一致）。

        手续费 = max(成交额 × commission_rate, commission_min)；
        印花税仅在卖出收取，买入（LONG）估算不计（stamp_tax 预留给卖出场景）。
        """
        price = to_decimal(last_price)
        transaction_money = price * size
        commission = transaction_money * self._commission_rate
        if commission < self._commission_min:
            commission = self._commission_min
        return transaction_money + commission

    def calculate_order_size(
        self, initial_size: int, last_price: Decimal, cash: Decimal, *args, **kwargs
    ) -> Tuple[int, Decimal]:
        """
        Calculate the order size.
        """
        size = initial_size
        while size > 0:
            planned_cost = self._estimate_cost(last_price, size)
            if cash >= planned_cost:
                return (size, planned_cost)
            size -= self._lot_size
        return (0, 0)

    def cal(self, portfolio_info, signal: Signal, *args, **kwargs) -> Optional[Order]:
        """
        Calculate the order size with improved error handling.
        """
        # 改进1：Signal验证
        if signal is None:
            GLOG.ERROR(f"Sizer:{self.name} received None signal")
            return None
            
        if not signal.is_valid():
            GLOG.ERROR(f"Sizer:{self.name} received invalid signal: {signal}")
            return None
        
        # 改进2：Portfolio信息验证
        if portfolio_info is None:
            GLOG.ERROR(f"Sizer:{self.name} received None portfolio_info")
            return None
            
        required_fields = ["positions", "cash"]
        for field in required_fields:
            if field not in portfolio_info:
                GLOG.ERROR(f"Sizer:{self.name} missing required portfolio field: {field}")
                return None
        
        GLOG.DEBUG(f"Sizer:{self.name} processing signal for {signal.code}")
        
        try:
            code = signal.code
            direction = signal.direction

            # Check if the position exists
            if direction == DIRECTION_TYPES.SHORT and code not in portfolio_info["positions"].keys():
                GLOG.DEBUG(f"Position {code} does not exist. Skip short signal. {self.get_time_provider().now()}")
                return None
        except Exception as e:
            GLOG.ERROR(f"Sizer:{self.name} error processing signal: {e}")
            return None

        # 改进2：Order创建错误处理
        try:
            current_time = self.get_time_provider().now()
            if signal.direction == DIRECTION_TYPES.LONG:
                if self._data_feeder is None:
                    GLOG.ERROR(f"Sizer:{self.name} has no data_feeder bound")
                    return None
                # If LONG, get the price info of last month, in case the data is not available, use yesterday's price
                last_month_day = current_time + datetime.timedelta(days=-30)
                yester_day = current_time + datetime.timedelta(days=-1)
                past_price = self._data_feeder.get_historical_data(
                    symbols=[code],
                    start_time=last_month_day,
                    end_time=yester_day,
                )
                if past_price is None or past_price.shape[0] == 0:
                    GLOG.CRITICAL(f"{code} has no data from {last_month_day} to {yester_day}.It should not happened. {current_time}")
                    return None
                last_price = past_price.iloc[-1]["close"]
                last_price = to_decimal(last_price)
                cash = portfolio_info["cash"]
                planned_size, planned_cost = self.calculate_order_size(self._volume, last_price, cash)
                GLOG.DEBUG(f"planned_size: {planned_size}, planned_cost: {planned_cost}.")

                if planned_size == 0:
                    GLOG.DEBUG(f"No order generated. {current_time}")
                    return None

                o = self.create_order(
                    code=code,
                    direction=DIRECTION_TYPES.LONG,
                    volume=planned_size,
                    limit_price=0,
                    frozen_money=planned_cost,
                    transaction_price=0,
                    transaction_volume=0,
                    remain=planned_cost,
                    fee=0,
                    timestamp=current_time,
                    business_timestamp=signal.business_timestamp if hasattr(signal, 'business_timestamp') else current_time,
                )
            elif signal.direction == DIRECTION_TYPES.SHORT:
                pos = portfolio_info["positions"].get(code)

                if pos is None:
                    GLOG.DEBUG(f"Position {code} does not exist. Skip short signal. {current_time}")
                    return None

                GLOG.WARN(f"Try Generate SHORT ORDER. {current_time}")

                o = self.create_order(
                    code=code,
                    direction=DIRECTION_TYPES.SHORT,
                    volume=pos.volume,
                    limit_price=0,
                    frozen_money=0,
                    frozen_volume=0,
                    transaction_price=0,
                    transaction_volume=0,
                    remain=0,
                    fee=0,
                    timestamp=current_time,
                    business_timestamp=signal.business_timestamp if hasattr(signal, 'business_timestamp') else current_time,
                )
            return o
        except Exception as e:
            GLOG.ERROR(f"Sizer:{self.name} failed to create order: {e}")
            return None

