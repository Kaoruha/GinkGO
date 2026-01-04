# Phase 3: User Story 1 - 单Portfolio实盘运行 (P1)

**状态**: ⚪ 未开始
**开始日期**: 待定
**预计完成**: 待定
**依赖**: Phase 1-2完成
**任务总数**: 14
**User Story**: 作为交易者，我希望在实盘环境中运行单个投资组合，策略能够接收实时行情、生成信号并自动执行交易

---

## 📋 验收标准

- [ ] ExecutionNode可以启动并加载Portfolio配置
- [ ] ExecutionNode订阅Kafka market.data topic并接收EventPriceUpdate
- [ ] Portfolio.on_price_update()方法可以处理事件并生成Signal
- [ ] Signal通过Sizer计算生成Order
- [ ] Order通过ExecutionNode.submit_order()提交到Kafka orders.submission topic
- [ ] LiveEngine订阅orders.submission topic并处理订单
- [ ] TradeGateway模拟执行订单并返回EventOrderFilled
- [ ] Portfolio.on_order_filled()更新持仓和现金
- [ ] 持仓和现金同步写入ClickHouse和MySQL
- [ ] 端到端延迟 < 200ms

---

## 🎯 活跃任务 (最多5个)

> 根据Constitution任务管理原则，从下面的任务池中选择最多5个任务作为当前活跃任务

**当前活跃任务**: (暂无，请从待办任务池中选择)

---

## 📥 待办任务池 (14个)

### 3.1 ExecutionNode基础 (5个任务)

### T017 [P] 创建ExecutionNode主类
- **文件**: `src/ginkgo/workers/execution_node/node.py`
- **依赖**: 无
- **并行**: 是
- **描述**: 创建ExecutionNode主类，包含__init__, start, stop方法，支持加载Portfolio配置
- **详细步骤**:
  1. 创建文件 `src/ginkgo/workers/execution_node/node.py`
  2. 实现ExecutionNode类：
     ```python
     from typing import Dict, List, Optional
     from threading import Thread, Lock
     from queue import Queue
     import redis
     from kafka import KafkaConsumer

     from ginkgo.workers.execution_node.portfolio_processor import PortfolioProcessor
     from ginkgo.workers.execution_node.interest_map import InterestMap
     from ginkgo.workers.execution_node.backpressure import BackpressureChecker
     from ginkgo.data.cruds.portfolio_crud import PortfolioCRUD

     class ExecutionNode:
         """ExecutionNode执行节点，运行多个Portfolio实例"""

         def __init__(self, node_id: str, max_portfolios: int = 5):
             self.node_id = node_id
             self.max_portfolios = max_portfolios
             self.portfolios: Dict[str, PortfolioProcessor] = {}
             self.interest_map = InterestMap()
             self.backpressure_checker = BackpressureChecker(max_size=1000)
             self.kafka_consumer: Optional[KafkaConsumer] = None
             self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
             self.is_running = False
             self.lock = Lock()

         def start(self):
             """启动ExecutionNode"""
             self.is_running = True
             # 启动Kafka消费者线程
             # 启动心跳上报线程

         def stop(self):
             """停止ExecutionNode"""
             self.is_running = False
             # 停止所有Portfolio
             # 关闭Kafka消费者
             # 关闭Redis连接

         def load_portfolio(self, portfolio_id: str):
             """从数据库加载Portfolio配置"""
             portfolio_crud = PortfolioCRUD()
             portfolio = portfolio_crud.get_portfolio_by_id(portfolio_id)
             # 创建PortfolioProcessor实例
             processor = PortfolioProcessor(portfolio_id, portfolio)
             with self.lock:
                 self.portfolios[portfolio_id] = processor
                 self.interest_map.add_portfolio(portfolio_id, portfolio.interest_set)

         def subscribe_market_data(self):
             """订阅Kafka market.data topic"""
             self.kafka_consumer = KafkaConsumer(
                 'ginkgo.live.market.data',
                 bootstrap_servers=['localhost:9092'],
                 group_id=f'execution_node_{self.node_id}',
                 auto_offset_reset='latest',
                 enable_auto_commit=False
             )
     ```
  3. 添加头部注释（Upstream/Downstream/Role）
- **验收**: ExecutionNode类创建成功，可以实例化

---

### T018 [P] 创建PortfolioProcessor线程类
- **文件**: `src/ginkgo/workers/execution_node/portfolio_processor.py`
- **依赖**: 无
- **并行**: 是
- **描述**: 创建PortfolioProcessor线程类，包含queue和portfolio实例
- **详细步骤**:
  1. 创建文件 `src/ginkgo/workers/execution_node/portfolio_processor.py`
  2. 实现PortfolioProcessor类：
     ```python
     from threading import Thread
     from queue import Queue
     from typing import Optional
     from ginkgo.core.portfolios.portfolio import Portfolio

     class PortfolioProcessor(Thread):
         """Portfolio处理器线程，每个Portfolio一个独立线程"""

         def __init__(self, portfolio_id: str, portfolio: Portfolio, max_queue_size: int = 1000):
             super().__init__(daemon=True)
             self.portfolio_id = portfolio_id
             self.portfolio = portfolio
             self.queue = Queue(maxsize=max_queue_size)
             self.is_running = False

         def run(self):
             """主循环：从queue获取事件并调用portfolio.on_event()"""
             self.is_running = True
             while self.is_running:
                 try:
                     event = self.queue.get(timeout=1)
                     self.portfolio.on_event(event)
                     self.queue.task_done()
                 except:
                     continue

         def stop(self):
             """停止处理器"""
             self.is_running = False
             self.join()

         def put_event(self, event):
             """向队列放入事件（非阻塞）"""
             try:
                 self.queue.put(event, block=False)
                 return True
             except:
                 return False  # Queue已满

         def get_queue_size(self) -> int:
             """获取当前队列大小"""
             return self.queue.qsize()
     ```
  3. 添加头部注释
- **验收**: PortfolioProcessor类创建成功，继承Thread

---

### T019 实现ExecutionNode.load_portfolio()方法
- **文件**: `src/ginkgo/workers/execution_node/node.py`
- **依赖**: T017
- **并行**: 否
- **描述**: 实现从数据库加载Portfolio配置的完整逻辑
- **详细步骤**:
  1. 扩展ExecutionNode.load_portfolio()方法
  2. 实现数据库查询逻辑：
     ```python
     def load_portfolio(self, portfolio_id: str):
         """从数据库加载Portfolio配置"""
         from ginkgo.data.cruds.portfolio_crud import PortfolioCRUD
         from ginkgo import services

         # 从数据库查询Portfolio配置
         portfolio_crud = services.data.cruds.portfolio()
         portfolio_model = portfolio_crud.get_portfolio_by_id(portfolio_id)

         # 验证is_live=True
         if not portfolio_model.is_live:
             raise ValueError(f"Portfolio {portfolio_id} is not a live portfolio")

         # 创建Portfolio实例（需扩展Portfolio基类支持实盘交易）
         portfolio = Portfolio(
             portfolio_id=portfolio_model.uuid,
             name=portfolio_model.name,
             initial_cash=portfolio_model.initial_cash
         )

         # 加载策略、Sizer、风控配置（通过MPortfolioFileMapping）
         # ... (配置加载逻辑)

         # 创建PortfolioProcessor实例
         processor = PortfolioProcessor(portfolio_id, portfolio, max_queue_size=1000)
         processor.start()

         # 注册到ExecutionNode
         with self.lock:
             self.portfolios[portfolio_id] = processor
             self.interest_map.add_portfolio(portfolio_id, portfolio.get_interest_set())

         # 更新Redis状态
         self.redis_client.hset(
             f"portfolio:{portfolio_id}:status",
             mapping={
                 "status": "running",
                 "node": self.node_id,
                 "started_at": datetime.now().isoformat()
             }
         )

         return processor
     ```
  3. 添加错误处理和日志记录
- **验收**: load_portfolio()方法可以从数据库加载配置并创建PortfolioProcessor

---

### T020 实现ExecutionNode.subscribe_market_data()方法
- **文件**: `src/ginkgo/workers/execution_node/node.py`
- **依赖**: T017
- **并行**: 否
- **描述**: 实现订阅Kafka market.data topic的完整逻辑
- **详细步骤**:
  1. 扩展ExecutionNode.subscribe_market_data()方法
  2. 实现Kafka消息消费和路由：
     ```python
     def subscribe_market_data(self):
         """订阅Kafka market.data topic并路由消息到Portfolio"""
         import json
         from ginkgo.trading.events.price_update import EventPriceUpdate

         self.kafka_consumer = KafkaConsumer(
             'ginkgo.live.market.data',
             bootstrap_servers=['localhost:9092'],
             group_id=f'execution_node_{self.node_id}',
             auto_offset_reset='latest',
             enable_auto_commit=False,
             value_deserializer=lambda m: json.loads(m.decode('utf-8'))
         )

         def consume_loop():
             while self.is_running:
                 for message in self.kafka_consumer:
                     # 解析EventPriceUpdate
                     event_data = message.value
                     event = EventPriceUpdate(
                         code=event_data['code'],
                         timestamp=datetime.fromisoformat(event_data['timestamp']),
                         price=event_data['price'],
                         volume=event_data.get('volume', 0)
                     )

                     # 使用interest_map路由到对应的Portfolio
                     portfolio_ids = self.interest_map.get_portfolios(event.code)
                     for portfolio_id in portfolio_ids:
                         if portfolio_id in self.portfolios:
                             processor = self.portfolios[portfolio_id]
                             # 检查backpressure
                             if self.backpressure_checker.check_and_alert(processor):
                                 processor.put_event(event)

                     # 手动提交offset
                     self.kafka_consumer.commit()

         # 启动消费线程
         self.consumer_thread = Thread(target=consume_loop, daemon=True)
         self.consumer_thread.start()
     ```
  3. 添加异常处理和日志
- **验收**: subscribe_market_data()方法可以订阅Kafka并正确路由消息

---

### T021 实现PortfolioProcessor.run()主循环
- **文件**: `src/ginkgo/workers/execution_node/portfolio_processor.py`
- **依赖**: T018
- **并行**: 否
- **描述**: 完善PortfolioProcessor.run()主循环，实现事件分发逻辑
- **详细步骤**:
  1. 扩展PortfolioProcessor.run()方法
  2. 实现完整的事件处理循环：
     ```python
     def run(self):
         """主循环：从queue获取事件并调用portfolio.on_event()"""
         self.is_running = True
         from ginkgo import GLOG

         GLOG.info(f"PortfolioProcessor {self.portfolio_id} started")

         while self.is_running:
             try:
                 # 从Queue获取事件（超时1秒）
                 event = self.queue.get(timeout=1)

                 # 根据事件类型分发
                 if isinstance(event, EventPriceUpdate):
                     self.portfolio.on_price_update(event)
                 elif isinstance(event, EventOrderPartiallyFilled):
                     self.portfolio.on_order_filled(event)
                 else:
                     self.portfolio.on_event(event)

                 self.queue.task_done()

             except Exception as e:
                 GLOG.error(f"PortfolioProcessor {self.portfolio_id} error: {e}")
                 continue

         GLOG.info(f"PortfolioProcessor {self.portfolio_id} stopped")
     ```
  3. 添加异常处理和日志
- **验收**: run()主循环可以正确处理各类事件

---

### 3.2 Portfolio事件处理 (4个任务)

### T022 [P] 扩展Portfolio添加on_price_update()方法
- **文件**: `src/ginkgo/core/portfolios/portfolio.py`
- **依赖**: 无
- **并行**: 是
- **描述**: 扩展Portfolio基类，添加on_price_update()方法处理实时行情并生成Signal
- **详细步骤**:
  1. 读取 `src/ginkgo/core/portfolios/portfolio.py`
  2. 添加on_price_update()方法：
     ```python
     def on_price_update(self, event: EventPriceUpdate):
         """处理实时行情事件，生成交易信号"""
         from ginkgo import GLOG

         # 更新最新价格数据
         self._update_price_data(event.code, event.price, event.timestamp)

         # 调用策略生成信号
         signals = self.strategy.cal(
             portfolio_info=self.get_portfolio_info(),
             event=event
         )

         # 处理生成的信号
         for signal in signals:
             self._on_signal(signal)

         GLOG.debug(f"Portfolio {self.portfolio_id} processed price update for {event.code}")
     ```
  3. 添加辅助方法：_update_price_data(), _on_signal()
- **验收**: on_price_update()方法可以处理EventPriceUpdate并生成Signal

---

### T023 [P] 扩展Portfolio添加on_order_filled()方法
- **文件**: `src/ginkgo/core/portfolios/portfolio.py`
- **依赖**: 无
- **并行**: 是
- **描述**: 扩展Portfolio基类，添加on_order_filled()方法处理订单成交并更新持仓和现金
- **详细步骤**:
  1. 在Portfolio类中添加on_order_filled()方法：
     ```python
     def on_order_filled(self, event: EventOrderPartiallyFilled):
         """处理订单成交事件，更新持仓和现金"""
         from ginkgo import GLOG

         # 更新持仓
         if event.direction == DIRECTION_TYPES.LONG:
             self._add_position(
                 code=event.code,
                 volume=event.filled_volume,
                 price=event.filled_price
             )
         else:  # SHORT
             self._reduce_position(
                 code=event.code,
                 volume=event.filled_volume,
                 price=event.filled_price
             )

         # 更新现金
         self._update_cash(event.filled_volume, event.filled_price, event.direction)

         # 同步到数据库
         self.sync_state_to_db()

         GLOG.info(f"Portfolio {self.portfolio_id} order filled: {event.order_id}")
     ```
  3. 添加辅助方法：_add_position(), _reduce_position(), _update_cash()
- **验收**: on_order_filled()方法可以处理EventOrderPartiallyFilled并更新状态

---

### T024 实现Portfolio.sync_state_to_db()方法
- **文件**: `src/ginkgo/core/portfolios/portfolio.py`
- **依赖**: T022, T023
- **并行**: 否
- **描述**: 实现同步写入持仓和现金到数据库的方法
- **详细步骤**:
  1. 在Portfolio类中实现sync_state_to_db()方法：
     ```python
     def sync_state_to_db(self):
         """同步持仓和现金到数据库"""
         from ginkgo import services, GLOG

         # 写入持仓到ClickHouse
         position_crud = services.data.cruds.position()
         for code, position in self.positions.items():
             position_crud.add_position(position)

         # 写入资金状态到MySQL
         # ... (需要实现资金状态的CRUD操作)

         GLOG.debug(f"Portfolio {self.portfolio_id} state synced to database")
     ```
  2. 使用@time_logger和@retry装饰器
  3. 添加错误处理
- **验收**: sync_state_to_db()方法可以正确同步状态到数据库

---

### T025 [P] 编写Portfolio事件处理单元测试
- **文件**: `tests/unit/live/test_portfolio_events.py`
- **依赖**: T022, T023, T024
- **并行**: 是
- **描述**: 编写Portfolio事件处理的单元测试
- **详细步骤**:
  1. 创建测试文件 `tests/unit/live/test_portfolio_events.py`
  2. 实现测试用例：
     ```python
     import pytest
     from ginkgo.core.portfolios.portfolio import Portfolio
     from ginkgo.trading.events.price_update import EventPriceUpdate
     from ginkgo.trading.events.order_lifecycle_events import EventOrderPartiallyFilled
     from ginkgo.trading.enums import DIRECTION_TYPES

     @pytest.mark.unit
     def test_portfolio_on_price_update():
         """测试Portfolio处理价格更新事件"""
         portfolio = Portfolio(portfolio_id="test", initial_cash=100000)
         event = EventPriceUpdate(
             code="000001.SZ",
             timestamp=datetime.now(),
             price=10.5,
             volume=1000
         )

         # Mock策略
         portfolio.strategy = MockStrategy()

         # 处理事件
         portfolio.on_price_update(event)

         # 验证信号生成
         assert len(portfolio.signals) > 0

     @pytest.mark.unit
     def test_portfolio_on_order_filled():
         """测试Portfolio处理订单成交事件"""
         portfolio = Portfolio(portfolio_id="test", initial_cash=100000)
         event = EventOrderPartiallyFilled(
             order_id="test_order",
             code="000001.SZ",
             direction=DIRECTION_TYPES.LONG,
             filled_volume=100,
             filled_price=10.5,
             timestamp=datetime.now()
         )

         # 处理事件
         portfolio.on_order_filled(event)

         # 验证持仓更新
         assert "000001.SZ" in portfolio.positions
         assert portfolio.positions["000001.SZ"].volume == 100
     ```
  3. 添加更多测试用例
- **验收**: 所有单元测试通过

---

### 3.3 LiveCore容器与订单提交流程 (5个任务)

### T026 实现ExecutionNode.submit_order()方法
- **文件**: `src/ginkgo/workers/execution_node/node.py`
- **依赖**: T019
- **并行**: 否
- **描述**: 实现将Order发布到Kafka orders.submission topic的方法
- **详细步骤**:
  1. 在ExecutionNode类中实现submit_order()方法：
     ```python
     def submit_order(self, order: Order):
         """将Order提交到Kafka orders.submission topic"""
         from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer
         import json

         producer = GinkgoProducer(bootstrap_servers="localhost:9092")

         # 序列化Order
         order_data = {
             "order_id": order.uuid,
             "portfolio_id": order.portfolio_id,
             "code": order.code,
             "direction": order.direction.value,
             "volume": order.volume,
             "price": order.price,
             "timestamp": order.timestamp.isoformat()
         }

         # 发送到Kafka
         producer.produce("ginkgo.live.orders.submission", json.dumps(order_data))
         producer.flush()

         from ginkgo import GLOG
         GLOG.info(f"Order {order.uuid} submitted to Kafka")
     ```
  2. 添加异常处理
- **验收**: submit_order()方法可以将Order发布到Kafka

---

### T027 [P] 创建LiveCore主入口（多线程容器）
- **文件**: `src/ginkgo/livecore/main.py`
- **依赖**: 无
- **并行**: 是
- **描述**: 创建LiveCore主入口，启动DataManager/LiveEngine/Scheduler线程
- **详细步骤**:
  1. 创建文件 `src/ginkgo/livecore/main.py`
  2. 实现LiveCore容器：
     ```python
     from threading import Thread
     import signal
     import sys

     class LiveCore:
         """LiveCore业务逻辑层容器（多线程）"""

         def __init__(self):
             self.threads = []
             self.is_running = False

         def start(self):
             """启动所有组件线程"""
             self.is_running = True

             # 启动DataManager线程
             from ginkgo.livecore.data_manager import DataManager
             data_manager = DataManager()
             data_thread = Thread(target=data_manager.run, daemon=True)
             data_thread.start()
             self.threads.append(data_thread)

             # 启动LiveEngine线程
             from ginkgo.livecore.live_engine import LiveEngine
             live_engine = LiveEngine()
             engine_thread = Thread(target=live_engine.run, daemon=True)
             engine_thread.start()
             self.threads.append(engine_thread)

             # 启动Scheduler线程
             from ginkgo.livecore.scheduler import Scheduler
             scheduler = Scheduler()
             scheduler_thread = Thread(target=scheduler.run, daemon=True)
             scheduler_thread.start()
             self.threads.append(scheduler_thread)

             # 注册信号处理
             signal.signal(signal.SIGINT, self._signal_handler)
             signal.signal(signal.SIGTERM, self._signal_handler)

         def _signal_handler(self, signum, frame):
             """处理停止信号"""
             from ginkgo import GLOG
             GLOG.info(f"Received signal {signum}, shutting down...")
             self.stop()

         def stop(self):
             """停止所有组件"""
             self.is_running = False
             for thread in self.threads:
                 thread.join(timeout=5)

         def wait(self):
             """等待所有线程结束"""
             for thread in self.threads:
                 thread.join()

     if __name__ == "__main__":
         livecore = LiveCore()
         livecore.start()
         livecore.wait()
     ```
  3. 添加头部注释
- **验收**: LiveCore可以启动所有组件线程

---

### T028 [P] 创建LiveEngine容器线程
- **文件**: `src/ginkgo/livecore/live_engine.py`
- **依赖**: 无
- **并行**: 是
- **描述**: 创建LiveEngine容器线程，订阅orders.submission topic
- **封装策略**: 封装现有`trading/engines/engine_live.py`中的EngineLive类，创建容器类调用其方法，而不是创建新类
- **详细步骤**:
  1. 创建文件 `src/ginkgo/livecore/live_engine.py`
  2. 实现LiveEngine容器类（封装EngineLive）：
     ```python
     from threading import Thread
     import json
     from ginkgo.trading.engines.engine_live import EngineLive
     from ginkgo.livecore.trade_gateway_adapter import TradeGatewayAdapter

     class LiveEngine:
         """LiveEngine实盘引擎容器线程（封装EngineLive）"""

         def __init__(self):
             # 封装现有的EngineLive实例
             self.engine = EngineLive()
             self.gateway = TradeGatewayAdapter()
             self.kafka_consumer = None

         def run(self):
             """运行LiveEngine：订阅Kafka orders.submission topic"""
             from kafka import KafkaConsumer
             from ginkgo import GLOG

             self.kafka_consumer = KafkaConsumer(
                 'ginkgo.live.orders.submission',
                 bootstrap_servers=['localhost:9092'],
                 group_id='live_engine',
                 auto_offset_reset='latest',
                 enable_auto_commit=False,
                 value_deserializer=lambda m: json.loads(m.decode('utf-8'))
             )

             GLOG.info("LiveEngine started, consuming orders...")

             while True:
                 for message in self.kafka_consumer:
                     order_data = message.value
                     # 调用封装的EngineLive处理订单
                     self._process_order(order_data)
                     self.kafka_consumer.commit()

         def _process_order(self, order_data: dict):
             """处理订单：调用EngineLive和TradeGateway执行"""
             from ginkgo import GLOG

             # 调用EngineLive处理订单（复用现有逻辑）
             fill_event = self.engine.process_order(order_data)

             # 如果EngineLive返回了成交事件，发布到Kafka
             if fill_event:
                 self._publish_order_feedback(fill_event)

             GLOG.info(f"Order {order_data['order_id']} processed")

         def _publish_order_feedback(self, fill_event):
             """发布订单回报到Kafka orders.feedback topic"""
             from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer

             producer = GinkgoProducer(bootstrap_servers="localhost:9092")
             producer.produce("ginkgo.live.orders.feedback", fill_event.to_json())
             producer.flush()
     ```
  3. 添加头部注释（Upstream: DataManager, Scheduler; Downstream: TradeGatewayAdapter; Role: 容器线程，封装EngineLive处理Kafka订单）
- **验收**: LiveEngine可以订阅Kafka并正确封装EngineLive处理订单

---

### T029 [P] 创建TradeGateway适配器
- **文件**: `src/ginkgo/livecore/trade_gateway_adapter.py`
- **依赖**: 无
- **并行**: 是
- **描述**: 创建TradeGateway适配器，封装trading/gateway/trade_gateway.py
- **详细步骤**:
  1. 创建文件 `src/ginkgo/livecore/trade_gateway_adapter.py`
  2. 实现TradeGateway适配器：
     ```python
     from ginkgo.trading.gateway.trade_gateway import TradeGateway

     class TradeGatewayAdapter:
         """交易网关适配器，封装TradeGateway用于实盘交易"""

         def __init__(self):
             self.gateway = TradeGateway()

         def submit_order(self, order_data: dict):
             """提交订单到券商"""
             from ginkgo.trading.entities.order import Order
             from ginkgo.trading.enums import DIRECTION_TYPES, ORDER_TYPES

             # 构造Order对象
             order = Order(
                 portfolio_id=order_data['portfolio_id'],
                 code=order_data['code'],
                 direction=DIRECTION_TYPES(order_data['direction']),
                 volume=order_data['volume'],
                 price=order_data['price'],
                 order_type=ORDER_TYPES.LIMIT
             )

             # 调用TradeGateway执行
             fill_event = self.gateway.submit_order(order)

             return fill_event
     ```
  3. 添加头部注释
- **验收**: TradeGatewayAdapter可以正确封装TradeGateway

---

### T030 改造GinkgoProducer的acks=1为acks=all
- **文件**: `src/ginkgo/data/drivers/ginkgo_kafka.py`
- **依赖**: T014
- **并行**: 否
- **描述**: 改造GinkgoProducer的acks配置，从acks=1改为acks=all确保消息可靠性
- **详细步骤**:
  1. 读取 `src/ginkgo/data/drivers/ginkgo_kafka.py`
  2. 找到GinkgoProducer类的__init__方法
  3. 修改acks配置：
     ```python
     # 改造前
     self.producer = KafkaProducer(
         bootstrap_servers=bootstrap_servers,
         acks=1,  # ❌ 等待leader确认
         ...
     )

     # 改造后
     self.producer = KafkaProducer(
         bootstrap_servers=bootstrap_servers,
         acks="all",  # ✅ 等待所有副本确认
         enable_idempotence=True,  # ✅ 启用幂等性
         ...
     )
     ```
  4. 更新相关文档注释
- **验收**: GinkgoProducer使用acks=all和enable_idempotence=True

---

## ✅ 已完成任务 (0个)

*(暂无)*

---

## 📊 进度跟踪

| 指标 | 数值 |
|------|------|
| 总任务数 | 14 |
| 已完成 | 0 |
| 进行中 | 0 |
| 待办 | 14 |
| 完成进度 | 0% |

---

## 🔗 依赖关系

```
Phase 2: Foundational
    ↓
Phase 3: User Story 1 (本阶段) ← MVP
    ↓
Phase 4: User Story 2
Phase 6: User Story 4
```

---

## 📝 备注

- **本阶段是MVP核心**，完成即可验证实盘交易架构的基础功能
- T017-T021可以并行（4个任务）
- T022-T023可以并行
- T027-T029可以并行（3个任务）
- 本阶段完成后，即可进行端到端测试，验证延迟<200ms

---

**文档版本**: 1.0.0
**最后更新**: 2026-01-04
