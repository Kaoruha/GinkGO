"""
T5 最小可运行示例

演示要点：
- 创建 TimeControlledEventEngine（回测模式）
- 注册 BrokerMatchMaking（基于 SimBroker）
- 人工注入一个限价单提交事件和一条价格更新事件
- 观察 T5 生命周期事件：OrderAck、PartiallyFilled、Filled
"""

import time
import pandas as pd
from datetime import datetime, timezone

from ginkgo.enums import EVENT_TYPES, DIRECTION_TYPES, ORDER_TYPES, FREQUENCY_TYPES
from ginkgo.trading.engines.time_controlled_engine import (
    TimeControlledEventEngine,
    EngineConfig,
    ExecutionMode,
)
from ginkgo.trading.events import (
    EventOrderAck,
    EventPriceUpdate,
    EventOrderAck,
    EventOrderPartiallyFilled,
    EventOrderPartiallyFilled as EventOrderFilled,  # 保持兼容性
)
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.routing.router import Router
from ginkgo.trading.brokers.sim_broker import SimBroker


def main():
    # 1) 创建回测引擎（时间控制）
    config = EngineConfig(mode=ExecutionMode.BACKTEST)
    engine = TimeControlledEventEngine(config=config, name="T5-Minimal-Engine")

    # 2) 创建并绑定基于 Broker 的路由中心（SimBroker）
    broker = SimBroker(config={})
    matchmaking = Router(broker)
    engine.bind_matchmaking(matchmaking)

    # 3) 注册路由中心的事件处理器（订单提交 + 价格更新）
    engine.register(EVENT_TYPES.ORDERSUBMITTED, matchmaking.on_order_received)
    engine.register(EVENT_TYPES.PRICEUPDATE, matchmaking.on_price_received)

    # 4) 注册简单打印的生命周期事件处理
    def on_ack(e: EventOrderAck):
        print(f"[ACK] order_id={e.order.uuid[:8]} broker_id={e.broker_order_id}")

    def on_partially_filled(e: EventOrderPartiallyFilled):
        print(
            f"[PARTIAL] order_id={e.order.uuid[:8]} filled={e.filled_quantity}@{e.fill_price} remaining≈{e.remaining_quantity}"
        )

    def on_filled(e: EventOrderFilled):
        print(f"[FILLED] order_id={e.value.uuid[:8]} price={e.value.transaction_price} qty={e.value.transaction_volume}")

    engine.register(EVENT_TYPES.ORDERACK, on_ack)
    engine.register(EVENT_TYPES.ORDERPARTIALLYFILLED, on_partially_filled)
    engine.register(EVENT_TYPES.ORDERFILLED, on_filled)

    # 5) 启动引擎（回测线程 + 事件循环）
    engine.start()

    # 6) 准备市场数据（供 SimBroker 使用）
    code = "TEST.SZ"
    price_row = pd.Series(
        {
            "code": code,
            "open": 10.0,
            "high": 10.5,
            "low": 9.8,
            "close": 10.2,
            "volume": 1000000,
        }
    )
    broker.set_market_data(code, price_row)

    # 7) 构造一个简单限价单并提交
    order = Order(
        code=code,
        direction=DIRECTION_TYPES.LONG,
        order_type=ORDER_TYPES.LIMITORDER,
        volume=300,  # >=200 将演示一次部分成交 + 最终成交
        limit_price=10.1,
        timestamp=datetime.now(timezone.utc),
    )
    # 创建订单确认事件而不是提交事件
    submit_event = EventOrderAck(order, broker_order_id=f"BROKER_{order.uuid[:8]}")
    engine.put(submit_event)

    # 8) 构造价格更新事件（触发路由器处理待处理订单）
    bar = Bar(code, 10.0, 10.5, 9.8, 10.2, 1000000, 0, frequency=FREQUENCY_TYPES.DAY, timestamp=datetime.now(timezone.utc))
    price_event = EventPriceUpdate(price_info=bar)
    engine.put(price_event)

    # 9) 等待异步撮合完成
    time.sleep(1.0)

    # 10) 停止引擎
    engine.stop()


if __name__ == "__main__":
    main()
