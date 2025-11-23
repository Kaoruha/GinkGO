import time
import datetime
from decimal import Decimal
from rich.console import Console
from typing import Dict

from ginkgo.trading.bases.portfolio_base import PortfolioBase
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.position import Position
from ginkgo.trading.events import (
    EventOrderAck,
    EventOrderPartiallyFilled,
    EventOrderCancelAck,
    EventSignalGeneration,
    EventPriceUpdate,
)

from ginkgo.enums import (
    DIRECTION_TYPES,
    SOURCE_TYPES,
    ORDERSTATUS_TYPES,
    RECORDSTAGE_TYPES,
)
from ginkgo.data.models import MOrder
from ginkgo.data.drivers import add

from ginkgo.libs import GinkgoSingleLinkedList, datetime_normalize, to_decimal
from ginkgo.libs.core.config import GCONF
from ginkgo.libs.utils.display import base_repr

from ginkgo.data.containers import container
from ginkgo.interfaces.notification_interface import INotificationService, NotificationServiceFactory

console = Console()


class PortfolioLive(PortfolioBase):
    """
    Portfolio for live system.
    """

    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, notification_service: INotificationService = None, *args, **kwargs):
        super(PortfolioLive, self).__init__(*args, **kwargs)
        # 使用依赖注入的通知服务，如果没有提供则自动创建
        self._notification_service = notification_service or NotificationServiceFactory.create_service()

    def reset_positions(self, *args, **kwargs) -> Dict[str, Position]:
        """
        Recover Positions from Order Records.
        Args:
            None
        Returns:
            Dict of Positions
        """
        # 1. Remove position data in db.
        position_crud = container.cruds.position()
        result_pos = position_crud.delete_filtered(portfolio_id=self.uuid)
        # TODO
        # 2. Get Records from db.
        order_record_crud = container.cruds.order_record()
        order_df = order_record_crud.delete_filtered(portfolio_id=self.uuid)
        print(order_df)
        # 3. Recal positions
        l = []
        pos = []
        for code in order_df["code"].unique():
            temp_df = order_df[order_df["code"] == code]
            temp_df = temp_df.sort_values(by="timestamp", ascending=True)
            p = Position(code=code)
            # T6: 使用run_id替代backtest_id
            p.set_run_id(self.uuid)
            for i, r in temp_df.iterrows():
                if r.direction == DIRECTION_TYPES.SHORT:
                    p.freeze(r.volume)
                p.deal(r.direction, r.transaction_price, r.volume)
            if p.volume <= 0:
                continue
            pos.append(p)
            self._positions[code] = p
        # 4. Store in db.
        self.record_positions()

        return self.positions

    def get_position(self, code: str) -> Position:
        if code in self.positions.keys():
            return self.positions[code]
        return None

    def cal_signals(self, time: any) -> list:
        """
        Calculate signals on specific time.
        Args:
            time[any]: any format of time
        Returns:
            List of Signal
        """
        # TODO
        return

    def cal_suggestions(self, time: any = None) -> list:
        """
        Calculate Suggestions on specific day.
        使用事件驱动架构生成建议
        Args:
            time[any]: any format of time
        Returns:
            List of Suggestions(same as Order)
        """
        from ginkgo.trading.time.clock import now as clock_now
        now = clock_now()
        time = datetime_normalize(time) if time else now
        self.advance_time(time)
        
        if self._engine_put is None:
            return []
        if self.selector is None:
            return []
            
        # 获取感兴趣的股票代码
        codes = self.selector.pick(time)
        suggestions = []
        
        # 为每个代码创建时间事件，生成策略和风控信号
        from ginkgo.trading.events import EventPriceUpdate
        
        for code in codes:
            # 创建时间事件 - 这里需要获取当前价格数据
            # TODO: 获取实时价格数据创建EventPriceUpdate
            # 暂时创建一个基础事件
            try:
                event = EventPriceUpdate()
                event.code = code
                event.timestamp = time
                
                # 使用新的信号生成方法
                strategy_signals = self.generate_strategy_signals(event)
                risk_signals = self.generate_risk_signals(event)
                
                # 处理所有信号
                all_signals = strategy_signals + risk_signals
                
                for signal in all_signals:
                    if signal is None:
                        continue
                        
                    # 使用sizer计算订单
                    order = self.sizer.cal(self.get_info(), signal)
                    if order is None:
                        continue
                        
                    # 依次通过所有风控模块处理订单
                    order_adjusted = order
                    for risk_manager in self.risk_managers:
                        order_adjusted = risk_manager.cal(self.get_info(), order_adjusted)
                        if order_adjusted is None:
                            break
                    
                    if order_adjusted is None or order_adjusted.volume == 0:
                        continue
                        
                    suggestions.append(order_adjusted)
                    
                    # 保存到数据库
                    mo = MOrder()
                    mo.set(
                        order_adjusted.uuid,
                        order_adjusted.code,
                        order_adjusted.direction,
                        order_adjusted.type,
                        order_adjusted.status,
                        order_adjusted.volume,
                        order_adjusted.limit_price,
                        order_adjusted.frozen,
                        order_adjusted.transaction_price,
                        order_adjusted.remain,
                        order_adjusted.fee,
                        time,
                        self.engine_id,
                    )
                    add(mo)
                    
            except Exception as e:
                self.log("ERROR", f"Failed to generate suggestions for {code}: {e}")
                continue
                
        return suggestions

    def advance_time(self, time: any, *args, **kwargs):
        """
        Go next time.
        Args:
            time[any]: time
        Returns:
            None
        """
        # Time goes
        super(PortfolioLive, self).advance_time(time, *args, **kwargs)

    def on_signal(self, event: EventSignalGeneration):
        """
        处理信号事件
        1. 接收信号
        2. 通过sizer计算订单大小
        3. 通过风控管理器处理订单
        4. 提交订单到引擎
        """
        self.log("INFO", f"{self.name} got a {event.direction} signal about {event.code}  --> {event.direction}.")
        
        # Check Everything.
        if not self.is_all_set():
            return

        # 1. Transfer signal to sizer
        order = self.sizer.cal(self.get_info(), event.payload)
        if order is None:
            self.log("INFO", f"No order generated by sizer for signal {event.code}")
            return

        # 2. Transfer the order to risk_managers (依次处理)
        order_adjusted = order
        for risk_manager in self.risk_managers:
            order_adjusted = risk_manager.cal(self.get_info(), order_adjusted)
            if order_adjusted is None:
                self.log("INFO", f"Order for {event.code} blocked by risk manager {risk_manager.name}")
                break

        # 3. Check final order
        if order_adjusted is None:
            return

        if order_adjusted.volume == 0:
            self.log("INFO", f"Order for {event.code} has zero volume")
            return

        # 4. Submit order to engine
        try:
            order_event = EventOrderAck(order_adjusted, broker_order_id=f"BROKER_{order_adjusted.uuid[:8]}")
            self.put(order_event)
            self.log("INFO", f"Order submitted for {event.code}: {order_adjusted.direction} {order_adjusted.volume}")
            self._notification_service.beep()
        except Exception as e:
            self.log("ERROR", f"Failed to submit order for {event.code}: {e}")

    def on_price_received(self, event: EventPriceUpdate):
        """使用基类通用处理。"""
        if not self.is_all_set():
            return
        self.process_price_update(event)

    def on_order_partially_filled(self, event: EventOrderPartiallyFilled):
        try:
            if self.is_event_from_future(event):
                return

            order = getattr(event, "order", None)
            if order is None:
                self.log("ERROR", "Partial fill event missing order payload")
                return

            qty = int(getattr(event, "filled_quantity", 0) or 0)
            price = to_decimal(getattr(event, "fill_price", 0) or 0)
            fee = to_decimal(getattr(event, "commission", 0) or 0)
            if qty <= 0 or price <= 0:
                self.log("WARN", f"Partial fill ignored due to invalid qty/price: {qty}/{price}")
                return

            direction = getattr(order, "direction", None) or getattr(event, "direction", None)
            code = event.code
            fill_cost = price * qty + fee

            # 更新订单累计成交与剩余冻结
            try:
                order.transaction_volume = min(order.volume, order.transaction_volume + qty)
            except Exception as e:
                self.log("ERROR", f"Failed to update transaction_volume: {e}")

            if not hasattr(order, "remain") or order.remain is None:
                order.remain = order.frozen_money
            order.remain = to_decimal(order.remain)
            order.remain = max(Decimal("0"), order.remain - fill_cost)

            is_final = getattr(event, "order_status", None) == ORDERSTATUS_TYPES.FILLED or order.transaction_volume >= order.volume

            if direction == DIRECTION_TYPES.LONG:
                unfreeze_remain = order.remain if is_final else None
                self.deduct_from_frozen(cost=fill_cost, unfreeze_remain=unfreeze_remain)
                if is_final:
                    order.remain = Decimal("0")
                self.add_fee(fee)

                pos = self.get_position(code)
                if pos is None:
                    p = Position(
                        portfolio_id=self.uuid,
                        engine_id=self.engine_id,
                        run_id=self.run_id,
                        code=code,
                        cost=price,
                        volume=qty,
                        price=price,
                        frozen=0,
                        fee=fee,
                        uuid=order.uuid if hasattr(order, "uuid") else "",
                    )
                    self.add_position(p)
                else:
                    pos.deal(DIRECTION_TYPES.LONG, price, qty)

                self.log(
                    "INFO",
                    f"PARTIAL LONG filled {code}: {qty}@{price}, fee={fee}, remain_frozen={order.remain}",
                )
            elif direction == DIRECTION_TYPES.SHORT:
                proceeds = price * qty - fee
                self.add_cash(proceeds)
                self.add_fee(fee)

                pos = self.get_position(code)
                if pos is None:
                    self.log("ERROR", f"Partial SHORT fill but no position found for {code}")
                else:
                    pos.deal(DIRECTION_TYPES.SHORT, price, qty)
                    self.clean_positions()

                self.log("INFO", f"PARTIAL SHORT filled {code}: {qty}@{price}, fee={fee}")
            else:
                self.log("WARN", f"Partial fill with unknown direction for {code}")

            self.update_worth()
            self.update_profit()
        except Exception as e:
            self.log("ERROR", f"on_order_partially_filled failed: {e}")

    def update_worth(self):
        pass

    def update_profit(self):
        pass

    def on_order_cancel_ack(self, event: EventOrderCancelAck) -> None:
        """
        处理订单取消事件
        Args:
            event: 订单取消事件
        """
        # 激活分析器钩子
        for func in self._analyzer_activate_hook[RECORDSTAGE_TYPES.ORDERCANCELED]:
            func(RECORDSTAGE_TYPES.ORDERCANCELED, self.get_info())
        for func in self._analyzer_record_hook[RECORDSTAGE_TYPES.ORDERCANCELED]:
            func(RECORDSTAGE_TYPES.ORDERCANCELED, self.get_info())
        
        self.log("WARN", f"Dealing with CANCELED ORDER. {self.get_time_provider().now()}")
        
        # 检查事件时间
        if self.is_event_from_future(event):
            return

        # 根据方向处理冻结资金
        if event.direction == DIRECTION_TYPES.LONG:
            order = getattr(event, "order", None)
            remain = None
            if order is not None:
                remain = getattr(order, "remain", None)
                if remain is None:
                    remain = getattr(order, "frozen_money", 0)
            if remain is None:
                self.log("ERROR", f"Cancel event missing remain for {event.code}")
                return
            remain = to_decimal(remain)
            if remain > 0:
                self.unfreeze(remain)
                if order is not None:
                    order.remain = Decimal("0")
            self.log("INFO", f"Order {event.code} CANCELED. Released frozen cash {remain}")
        elif event.direction == DIRECTION_TYPES.SHORT:
            # 卖单取消的处理逻辑
            if event.code in self._positions:
                cancel_vol = int(getattr(event, "cancelled_quantity", 0) or 0)
                if cancel_vol > 0:
                    self._positions[event.code].unfreeze(cancel_vol)
            self.log("INFO", f"Short order {event.code} CANCELED. Released frozen volume {getattr(event, 'cancelled_quantity', 0)}")

    # def __repr__(self) -> str:
    #     return base_repr(self, PortfolioLive.__name__, 24, 60)
