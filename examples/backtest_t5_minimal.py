"""
回测最小装配样例（T5、纯事件驱动、无订阅/广播）

要点：
- 使用 TimeControlledEventEngine 驱动时间（无需 Feeder 广播）
- 用 EventInterestUpdate 通告兴趣标的（无需 Feeder 订阅）
- 设置 SimBroker 的市场数据 + 注入价格事件，提交限价单后触发：ACK → 部分成交 → 完全成交
"""

import time
from datetime import datetime, timezone
import pandas as pd

from ginkgo.enums import (
    EVENT_TYPES,
    DIRECTION_TYPES,
    ORDER_TYPES,
    FREQUENCY_TYPES,
)
from ginkgo.trading.engines.time_controlled_engine import (
    TimeControlledEventEngine,
    EngineConfig,
    ExecutionMode,
)
from ginkgo.trading.events import (
    EventInterestUpdate,
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
    # 1) 创建 T5 回测引擎（时间控制）
    config = EngineConfig(mode=ExecutionMode.BACKTEST)
    engine = TimeControlledEventEngine(config=config, name="Backtest-T5-Minimal")

    # 2) 撮合：BrokerMatchMaking + SimBroker（ACK→异步部分/完全成交）
    broker = SimBroker(config={})
    matchmaking = Router(broker)
    engine.bind_matchmaking(matchmaking)
    engine.register(EVENT_TYPES.ORDERSUBMITTED, matchmaking.on_order_received)
    engine.register(EVENT_TYPES.PRICEUPDATE, matchmaking.on_price_received)

    # 3) 打印订单生命周期事件
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

    # 3.1) 维护「感兴趣标的」集合，并响应 EventInterestUpdate
    interested = set()

    def on_interest(e: EventInterestUpdate):
        interested.update(e.codes)
        print(f"[INTEREST] {sorted(interested)}")

    engine.register(EVENT_TYPES.INTERESTUPDATE, on_interest)

    # 4) 启动引擎
    engine.start()

    # 5) 通告兴趣标的（无订阅/广播，只用事件）
    codes = ["DEMO.SZ", "MOCK.SZ"]
    engine.put(EventInterestUpdate(portfolio_id="demo_portfolio", codes=codes, timestamp=datetime.now(timezone.utc)))

    # 6) 推进时间到某一刻（T5 引擎会触发时钟与阶段屏障；此处不绑定 Feeder，直接注入价格事件）
    t = datetime.now(timezone.utc)
    engine.advance_time_to(t)

    # 7) 针对「感兴趣标的」逐一注入市场数据 + 价格事件
    def emit_price_for(code: str, close: float):
        row = pd.Series({
            "code": code,
            "open": close - 0.2,
            "high": close + 0.3,
            "low": close - 0.4,
            "close": close,
            "volume": 1_000_000,
        })
        broker.set_market_data(code, row)
        bar = Bar(code, row["open"], row["high"], row["low"], row["close"], row["volume"], 0,
                  frequency=FREQUENCY_TYPES.DAY, timestamp=t)
        engine.put(EventPriceUpdate(price_info=bar))

    # 为所有兴趣标的推送一笔价格（可按需拉实盘/历史数据替换 close 值）
    base_close = {c: 10.2 for c in interested}  # 这里用常量演示
    for c in sorted(interested):
        emit_price_for(c, base_close[c])

    # 9) 构造一个限价单并提交（≥200 演示部分成交 + 完全成交）
    order = Order(
        code=codes[0],
        direction=DIRECTION_TYPES.LONG,
        order_type=ORDER_TYPES.LIMITORDER,
        volume=300,
        limit_price=10.1,
        timestamp=t,
    )
    # 创建订单确认事件而不是提交事件
    engine.put(EventOrderAck(order, broker_order_id=f"BROKER_{order.uuid[:8]}"))

    # 可选：定时轮询未完成订单（SimBroker 主要靠回调即可）
    # engine.register_timer(matchmaking._timer_check_order_status)

    # 10) 等待异步撮合回报
    time.sleep(1.0)
    engine.stop()


if __name__ == "__main__":
    main()
