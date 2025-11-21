"""
统一Router - 支持多模式多市场的统一路由器

基于BaseRouter和OrderManagementMixin，支持：
- 回测、模拟盘、实盘三种执行模式
- 多市场Broker路由（A股、港股、美股、期货等）
- 统一的订单生命周期事件处理
- 纯内存管理，高性能
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from ginkgo.trading.bases.base_router import BaseRouter
from ginkgo.trading.interfaces.broker_interface import IBroker, BrokerExecutionResult
from ginkgo.trading.entities import Order
from ginkgo.enums import EVENT_TYPES, ORDERSTATUS_TYPES, DIRECTION_TYPES
from ginkgo.trading.events.order_lifecycle_events import (
    EventOrderAck, EventOrderPartiallyFilled, EventOrderRejected,
    EventOrderExpired, EventOrderCancelAck
)


class Router(BaseRouter):
    """
    统一Router - 支持多模式多市场的路由器

    特性：
    - 支持回测、模拟盘、实盘三种模式
    - 自动路由订单到对应市场的Broker
    - 使用OrderManagementMixin进行内存订单管理
    - 统一的事件驱动架构
    - 纯内存操作，高性能
    """

    def __init__(self, brokers: List[IBroker], name: str = "MultiMarketRouter"):
        """
        初始化Router

        Args:
            brokers: Broker实例列表
            name: Router名称
        """
        super().__init__(name=name)

        # 支持单个Broker或Broker列表
        if isinstance(brokers, IBroker):
            self.brokers = [brokers]
        elif isinstance(brokers, list):
            self.brokers = brokers
        else:
            raise ValueError("brokers must be IBroker instance or list of IBroker instances")

        # 为兼容性保留self.broker属性（默认使用第一个）
        self.broker = self.brokers[0] if self.brokers else None

        # 建立市场到Broker的映射
        self._market_mapping: Dict[str, IBroker] = {}
        self._code_market_mapping: Dict[str, str] = {}

        # 设置市场映射
        self._setup_market_mapping()

        # 设置异步执行结果回调
        self._setup_broker_callbacks()

        # Portfolio事件路由映射
        self._portfolio_handlers: Dict[str, Any] = {}

        self.log("INFO", f"Initialized {self.name} with {len(self.brokers)} brokers")
        self._log_market_mapping()

    def _setup_market_mapping(self):
        """建立市场到Broker的映射"""
        for broker in self.brokers:
            if hasattr(broker, 'market'):
                self._market_mapping[broker.market] = broker
                self.log("INFO", f"Registered {broker.market} broker: {broker.__class__.__name__}")

        # 建立股票代码到市场的映射规则
        self._code_market_mapping.update({
            # A股
            '000001.SZ': 'A股', '000002.SZ': 'A股', '000001.SH': 'A股', '600000.SH': 'A股',
            '300001.SZ': 'A股', '002594.SZ': 'A股',
            # 港股
            '00700.HK': '港股', '00941.HK': '港股', '03690.HK': '港股',
            # 美股（示例）
            'AAPL': '美股', 'TSLA': '美股', 'MSFT': '美股', 'GOOG': '美股',
            # 期货（示例）
            'IF2312': '期货', 'IC2312': '期货', 'IH2312': '期货',
        })

        # 如果有SIM市场的broker，让它作为所有市场的默认broker
        if "SIM" in self._market_mapping:
            sim_broker = self._market_mapping["SIM"]
            # 为所有没有专门broker的市场设置SIM broker作为默认
            default_markets = ['A股', '港股', '美股', '期货']
            for market in default_markets:
                if market not in self._market_mapping:
                    self._market_mapping[market] = sim_broker
                    self.log("INFO", f"Set SIM broker as default for {market} market")

    def _setup_broker_callbacks(self):
        """设置Broker的异步结果回调"""
        for broker in self.brokers:
            broker.set_result_callback(self._handle_async_result)

    def _log_market_mapping(self):
        """记录市场映射信息"""
        for market, broker in self._market_mapping.items():
            self.log("DEBUG", f"Market '{market}' -> Broker '{broker.__class__.__name__}'")

    def _detect_execution_mode(self, broker: IBroker) -> str:
        """检测Broker执行模式"""
        if broker.supports_immediate_execution():
            return "backtest"  # 回测模式
        elif broker.requires_manual_confirmation():
            return "paper"     # 模拟盘模式
        else:
            return "live"      # 实盘模式

    def _get_market_by_code(self, code: str) -> Optional[str]:
        """根据股票代码判断市场"""
        # 1. 直接查找映射
        if code in self._code_market_mapping:
            return self._code_market_mapping[code]

        # 2. 根据代码格式判断
        if code.endswith(('.SZ', '.SH')):
            return 'A股'
        elif code.endswith('.HK'):
            return '港股'
        elif '.' not in code and code.replace('-', '').isalpha():
            # 纯字母代码，可能是美股
            return '美股'
        elif code.startswith(('IF', 'IC', 'IH')) and len(code) >= 6:
            # 期货合约代码
            return '期货'

        return 'A股'  # 默认为A股

    def get_broker_for_order(self, order: Order) -> Optional[IBroker]:
        """
        根据订单选择合适的Broker

        Args:
            order: 订单对象

        Returns:
            Optional[IBroker]: 选择的Broker，如果找不到返回None
        """
        # 1. 根据股票代码判断市场
        market = self._get_market_by_code(order.code)
        if not market:
            self.log("WARN", f"Cannot determine market for {order.code}")
            return None

        # 2. 找到对应市场的Broker
        broker = self._market_mapping.get(market)
        if not broker:
            self.log("ERROR", f"No broker available for market: {market}")
            return None

        self.log("DEBUG", f"Order {order.code} routed to {market} broker: {broker.__class__.__name__}")
        return broker

    def on_order_ack(self, event, *args, **kwargs) -> None:
        """
        统一订单确认处理 - 支持同步/异步模式

        Args:
            event: 订单确认事件 (EventOrderAck)
        """
        # 🔍 详细日志跟踪ORDERACK事件
        self.log("INFO", f"🔥 [ROUTER] ORDERACK事件接收开始")
        self.log("INFO", f"🔥 [ROUTER] 事件详情: {type(event).__name__}")
        self.log("INFO", f"🔥 [ROUTER] 事件portfolio_id: {getattr(event, 'portfolio_id', 'None')}")

        order = event.payload
        self.log("INFO", f"🔥 [ROUTER] 订单信息: {order.direction.name} {order.volume} {order.code}")
        self.log("INFO", f"🔥 [ROUTER] 订单UUID: {order.uuid}")
        self.log("INFO", f"📦 ORDER RECEIVED: {order.direction.name} {order.volume} {order.code}")

        # 基础验证
        if not self._validate_order_basic(order):
            return

        # 选择合适的Broker
        selected_broker = self.get_broker_for_order(order)
        if not selected_broker:
            self.log("ERROR", f"No suitable broker found for {order.code}")
            return

        # 检查Broker级别的验证
        if not selected_broker.validate_order(order):
            self.log("WARN", f"Order validation failed by {selected_broker.__class__.__name__}: {order.uuid[:8]}")
            return

        # 执行模式判断和处理
        execution_mode = self._detect_execution_mode(selected_broker)
        self.log("DEBUG", f"Execution mode for {selected_broker.__class__.__name__}: {execution_mode}")

        if execution_mode == "backtest":
            # 回测：同步执行
            self._handle_sync_execution(order, selected_broker, event)
        else:
            # 模拟盘/实盘：异步执行
            self._handle_async_execution(order, selected_broker, execution_mode)

    def on_price_received(self, event, *args, **kwargs) -> None:
        """
        价格接收处理 - 只对回测模式传递价格

        Args:
            event: 价格事件
        """
        price_data = event.payload

        # 检查是否有回测模式的Broker需要价格数据
        for broker in self.brokers:
            if self._detect_execution_mode(broker) == "backtest":
                if hasattr(broker, 'update_price_data'):
                    broker.update_price_data(price_data)
                    break  # 回测通常只有一个，找到就停止

        # 触发待处理订单（价格更新可能影响撮合逻辑）
        self._process_pending_orders()

    def _handle_sync_execution(self, order: Order, broker: IBroker, event) -> None:
        """
        处理同步执行（回测模式）

        Args:
            order: 订单对象
            broker: 选择的Broker
            event: 原始事件对象（包含上下文信息）
        """
        try:
            self.log("DEBUG", f"Processing order synchronously with {broker.__class__.__name__}")

            # 提交事件给broker
            result = broker.submit_order_event(event)

            # 立即处理执行结果
            self._handle_execution_result(result)

        except Exception as e:
            self.log("ERROR", f"Sync execution failed for {order.uuid[:8]}: {e}")
            # 发布错误事件
            error_result = BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                error_message=f"Sync execution error: {str(e)}"
            )
            self._handle_execution_result(error_result)

    def _handle_async_execution(self, order: Order, broker: IBroker, execution_mode: str) -> None:
        """
        处理异步执行（模拟盘/实盘模式）

        Args:
            order: 订单对象
            broker: 选择的Broker
            execution_mode: 执行模式（paper/live）
        """
        try:
            self.log("DEBUG", f"Processing order asynchronously with {broker.__class__.__name__}")

            # 异步提交订单
            result = broker.submit_order(order)

            if result.status == ORDERSTATUS_TYPES.SUBMITTED:
                # 成功提交，开始跟踪订单
                self.track_order(result.broker_order_id, {
                    'order': order,
                    'result': result,
                    'broker': broker,
                    'submit_time': datetime.now(),
                    'execution_mode': execution_mode,
                    'timeout_seconds': self._get_timeout_for_mode(execution_mode)
                })

                self.log("INFO", f"📤 SUBMITTED to {broker.__class__.__name__}: {result.broker_order_id}")

                # SimBroker会直接发布事件，这里不需要额外处理

                # 启动超时检查（如果需要）
                self._schedule_timeout_check(result.broker_order_id)

            else:
                # 立即失败的情况（如验证失败）
                self.log("WARN", f"Async submission failed for {order.uuid[:8]}: {result.error_message}")
                self._handle_execution_result(result)

        except Exception as e:
            self.log("ERROR", f"Async execution failed for {order.uuid[:8]}: {e}")
            # 发布错误事件
            error_result = BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                error_message=f"Async execution error: {str(e)}"
            )
            self._handle_execution_result(error_result)

    def _get_timeout_for_mode(self, execution_mode: str) -> int:
        """
        根据执行模式获取超时时间（秒）

        Args:
            execution_mode: 执行模式

        Returns:
            int: 超时秒数
        """
        timeout_map = {
            "paper": 300,    # 5分钟（模拟盘）
            "live": 30,      # 30秒（实盘）
        }
        return timeout_map.get(execution_mode, 300)  # 默认5分钟

    def _schedule_timeout_check(self, broker_order_id: str) -> None:
        """
        安排超时检查（简化版本，实际实现可能需要定时器）

        Args:
            broker_order_id: Broker订单ID
        """
        # 这里可以实现定时器或其他超时机制
        # 当前版本只是记录日志
        self.log("DEBUG", f"Scheduled timeout check for {broker_order_id}")

    def _process_pending_orders(self):
        """处理所有待处理订单"""
        pending_orders = self.get_pending_orders()
        if not pending_orders:
            return

        self.clear_pending_orders()

        for order in pending_orders:
            # 重新为每个订单选择Broker并执行
            selected_broker = self.get_broker_for_order(order)
            if selected_broker:
                self._submit_order_to_broker(order, selected_broker)

    def _submit_order_to_broker(self, order: Order, broker: IBroker):
        """提交订单到指定Broker"""
        execution_mode = self._detect_execution_mode(broker)

        if execution_mode == "backtest":
            result = broker.submit_order(order)
            self._handle_execution_result(result)
        else:
            result = broker.submit_order(order)
            if result.status == ORDERSTATUS_TYPES.SUBMITTED:
                self.track_order(result.broker_order_id, {
                    'order': order,
                    'result': result,
                    'broker': broker,
                    'submit_time': datetime.datetime.now(),
                    'execution_mode': execution_mode
                })

    def _handle_execution_result(self, result: BrokerExecutionResult):
        """
        处理执行结果并发布对应的事件

        Args:
            result: 执行结果（包含完整的Order对象）
        """
        if result.status == ORDERSTATUS_TYPES.FILLED or result.status == ORDERSTATUS_TYPES.PARTIAL_FILLED:
            code = result.order.code if result.order else "Unknown"
            self.log("INFO", f"✅ ORDER FILLED: {result.filled_volume} {code} @ {result.filled_price}")

            # 获取engine_id和run_id（Router从绑定的engine获取）
            engine_id = self._bound_engine.engine_id if self._bound_engine else None
            run_id = getattr(self._bound_engine, 'run_id', None) if self._bound_engine else None

            # 发布订单成交事件
            self.log("INFO", f"🔥 [ROUTER] Creating event with engine_id={engine_id}, run_id={run_id}")
            event = result.to_event(engine_id=engine_id, run_id=run_id, event_publisher=self.publish_event)
            self.log("INFO", f"🔥 [ROUTER] Event created: {type(event).__name__ if event else 'None'}")
            if event:
                self.log("INFO", f"🔥 [ROUTER] Event portfolio_id: {event.portfolio_id}")
                self.log("INFO", f"🔥 [ROUTER] Event engine_id: {event.engine_id}")
                self.log("INFO", f"🔥 [ROUTER] ✅ Event created successfully, calling publish_event...")
                # 立即推送事件到引擎
                self.publish_event(event)
                self.log("INFO", f"🔥 [ROUTER] ✅ Event published to engine")
            else:
                self.log("ERROR", f"🔥 [ROUTER] ❌ Failed to create event!")

        elif result.status == ORDERSTATUS_TYPES.NEW:  # REJECTED
            self.log("WARN", f"❌ ORDER REJECTED: {result.error_message}")

        elif result.status == ORDERSTATUS_TYPES.SUBMITTED:
            # 对于异步提交，这里不需要发布事件，将在回调中处理
            pass

        elif result.status == ORDERSTATUS_TYPES.CANCELED:
            self.log("INFO", f"🚫 CANCELED by {broker.__class__.__name__}: {result.broker_order_id}")

            # 发布订单取消事件
            event = result.to_event(order, original_event, self.publish_event)

        # 更新订单跟踪状态
        if result.broker_order_id and hasattr(self, '_processing_orders'):
            # 如果有跟踪的订单，移除跟踪
            if result.status in [ORDERSTATUS_TYPES.FILLED, ORDERSTATUS_TYPES.CANCELED, ORDERSTATUS_TYPES.NEW]:
                self.remove_tracked_order(result.broker_order_id)

    def _update_position(self, order: Order, result: BrokerExecutionResult):
        """更新持仓信息"""
        # 这里可以添加持仓更新逻辑
        # 持仓更新通常由Portfolio处理，Router只负责事件发布
        pass

    def _validate_order_basic(self, order: Order) -> bool:
        """基础订单验证"""
        if not order or not hasattr(order, 'uuid'):
            return False
        if not order.code or not isinstance(order.code, str):
            return False
        if order.volume <= 0:
            return False
        return True

    def _handle_async_result(self, result: BrokerExecutionResult):
        """
        处理异步执行结果 - 完整的异步回调处理

        Args:
            result: Broker执行结果
        """
        if result.broker_order_id not in self._processing_orders:
            self.log("WARN", f"Received async result for unknown order: {result.broker_order_id}")
            return

        order_info = self.get_tracked_order(result.broker_order_id)
        if not order_info:
            self.log("ERROR", f"Order info missing for: {result.broker_order_id}")
            return

        order = order_info['order']
        broker = order_info.get('broker')
        submit_time = order_info.get('submit_time')

        # 计算处理时间
        processing_time = (datetime.now() - submit_time).total_seconds() if submit_time else 0

        self.log("INFO", f"📨 ASYNC RESULT: {result.status.name} for {order.uuid[:8]} "
                       f"(took {processing_time:.2f}s)")

        # 处理不同的执行结果
        if result.status in [ORDERSTATUS_TYPES.FILLED, ORDERSTATUS_TYPES.PARTIAL_FILLED]:
            self.log("INFO", f"✅ ASYNC FILL: {result.filled_volume} {order.code} @ {result.filled_price}")
        elif result.status == ORDERSTATUS_TYPES.NEW:  # REJECTED
            self.log("WARN", f"❌ ASYNC REJECT: {result.error_message}")
        elif result.status == ORDERSTATUS_TYPES.CANCELED:
            self.log("INFO", f"🚫 ASYNC CANCEL: {result.broker_order_id}")

        # 处理执行结果并发布事件
        self._handle_execution_result(result)

        # 移除订单跟踪（仅在最终状态时）
        if result.status in [ORDERSTATUS_TYPES.FILLED, ORDERSTATUS_TYPES.NEW,  # REJECTED
                             ORDERSTATUS_TYPES.CANCELED]:
            self.remove_tracked_order(result.broker_order_id)
            self.log("DEBUG", f"Removed tracking for completed order: {result.broker_order_id}")

        # 如果是部分成交，继续跟踪
        elif result.status == ORDERSTATUS_TYPES.PARTIAL_FILLED:
            # 更新跟踪信息，但继续跟踪
            self.track_order(result.broker_order_id, {
                **order_info,
                'last_update_time': datetime.now(),
                'filled_volume': result.filled_volume,
                'remaining_volume': order.volume - result.filled_volume
            }, update=True)

    def check_order_timeouts(self) -> None:
        """
        检查订单超时 - 应该被定时调用

        Returns:
            List[str]: 超时的订单ID列表
        """
        current_time = datetime.now()
        timeout_orders = []

        for broker_order_id, order_info in self.get_tracked_orders().items():
            timeout_seconds = order_info.get('timeout_seconds', 300)
            submit_time = order_info.get('submit_time')

            if submit_time:
                elapsed_seconds = (current_time - submit_time).total_seconds()
                if elapsed_seconds > timeout_seconds:
                    timeout_orders.append(broker_order_id)
                    self._handle_order_timeout(broker_order_id, order_info)

        return timeout_orders

    def _handle_order_timeout(self, broker_order_id: str, order_info: Dict[str, Any]) -> None:
        """
        处理订单超时

        Args:
            broker_order_id: 超时的订单ID
            order_info: 订单跟踪信息
        """
        order = order_info.get('order')
        broker = order_info.get('broker')
        execution_mode = order_info.get('execution_mode', 'unknown')

        self.log("WARN", f"⏰ ORDER TIMEOUT: {broker_order_id} ({execution_mode} mode)")

        # 尝试取消订单（如果Broker支持）
        try:
            if broker and hasattr(broker, 'cancel_order'):
                cancel_result = broker.cancel_order(broker_order_id)
                self.log("INFO", f"Cancel request sent for timeout order: {broker_order_id}")

                # 发布取消事件
                self._handle_execution_result(cancel_result)

        except Exception as e:
            self.log("ERROR", f"Failed to cancel timeout order {broker_order_id}: {e}")

        # 无论取消是否成功，都移除跟踪
        self.remove_tracked_order(broker_order_id)

    def track_order(self, broker_order_id: str, order_info: Dict[str, Any], update: bool = False) -> None:
        """
        跟踪订单 - 增强版本支持更新

        Args:
            broker_order_id: Broker订单ID
            order_info: 订单信息
            update: 是否更新现有跟踪信息
        """
        if update and broker_order_id in self._processing_orders:
            # 更新现有跟踪信息
            self._processing_orders[broker_order_id].update(order_info)
        else:
            # 新增跟踪信息
            super().track_order(broker_order_id, order_info)

        self.log("DEBUG", f"Tracking order: {broker_order_id} (update={update})")

    def get_async_order_status(self, broker_order_id: str) -> Optional[Dict[str, Any]]:
        """
        获取异步订单状态

        Args:
            broker_order_id: Broker订单ID

        Returns:
            Optional[Dict[str, Any]]: 订单状态信息，如果不存在返回None
        """
        order_info = self.get_tracked_order(broker_order_id)
        if not order_info:
            return None

        current_time = datetime.now()
        submit_time = order_info.get('submit_time', current_time)
        elapsed_seconds = (current_time - submit_time).total_seconds()

        return {
            'broker_order_id': broker_order_id,
            'order_uuid': order_info['order'].uuid[:8] if order_info.get('order') else 'unknown',
            'execution_mode': order_info.get('execution_mode', 'unknown'),
            'submit_time': submit_time,
            'elapsed_seconds': elapsed_seconds,
            'timeout_seconds': order_info.get('timeout_seconds', 300),
            'is_timeout': elapsed_seconds > order_info.get('timeout_seconds', 300),
            'broker_class': order_info.get('broker', {}).__class__.__name__ if order_info.get('broker') else 'unknown',
            'filled_volume': order_info.get('filled_volume', 0),
            'remaining_volume': order_info.get('remaining_volume', 0)
        }

    
    def set_event_publisher(self, publisher):
        """设置事件发布器"""
        self._event_publisher = publisher

    def _publish_event_internal(self, event):
        """内部事件发布方法"""
        if hasattr(self, '_event_publisher') and self._event_publisher:
            self._event_publisher(event)
        else:
            self.publish_event(event)

    # 多市场支持接口
    def get_broker_status(self) -> Dict[str, Any]:
        """获取所有Broker状态"""
        status = {}
        for i, broker in enumerate(self.brokers):
            broker_name = f"broker_{i}_{broker.__class__.__name__}"
            status[broker_name] = {
                'execution_mode': self._detect_execution_mode(broker),
                'market': getattr(broker, 'market', 'Unknown'),
                'active': True,
                'tracked_orders': self._get_tracked_orders_for_broker(broker)
            }
        return status

    def get_pending_orders_by_broker(self) -> Dict[str, List[str]]:
        """按Broker分组获取待处理订单"""
        pending = {}
        for broker in self.brokers:
            broker_name = broker.__class__.__name__
            if hasattr(broker, 'get_pending_orders'):
                pending[broker_name] = broker.get_pending_orders()
            else:
                pending[broker_name] = []
        return pending

    def _get_tracked_orders_for_broker(self, broker: IBroker) -> List[str]:
        """获取特定Broker的跟踪订单"""
        if not hasattr(broker, 'get_pending_orders'):
            return []

        broker_name = broker.__class__.__name__
        tracked_orders = []

        for broker_order_id, order_info in self.get_tracked_orders().items():
            if (order_info.get('broker') and
                order_info['broker'].__class__.__name__ == broker_name):
                tracked_orders.append(broker_order_id)

        return tracked_orders

    def confirm_manual_order(self, broker_name: str, broker_order_id: str,
                              filled_volume: int, filled_price: float):
        """手动确认订单（模拟盘用）"""
        for broker in self.brokers:
            if broker.__class__.__name__ == broker_name:
                if hasattr(broker, 'confirm_execution'):
                    broker.confirm_execution(broker_order_id, filled_volume, filled_price)
                    self.log("INFO", f"Manual execution confirmed: {broker_order_id}")
                break

    def add_broker(self, broker: IBroker):
        """动态添加Broker"""
        self.brokers.append(broker)

        if hasattr(broker, 'market'):
            self._market_mapping[broker.market] = broker
            broker.set_result_callback(self._handle_async_result)

        self.log("INFO", f"Added broker: {broker.__class__.__name__}")

    def remove_broker(self, broker: IBroker):
        """移除Broker"""
        if broker in self.brokers:
            self.brokers.remove(broker)

            # 清理市场映射
            markets_to_remove = [m for m, b in self._market_mapping.items() if b == broker]
            for market in markets_to_remove:
                del self._market_mapping[market]

            self.log("INFO", f"Removed broker: {broker.__class__.__name__}")

    def get_order_status_summary(self) -> Dict[str, int]:
        """获取订单状态摘要"""
        summary = super().get_order_status_summary()
        summary['total_brokers'] = len(self.brokers)
        summary['market_mapping'] = len(self._market_mapping)
        summary['registered_portfolios'] = len(self._portfolio_handlers)
        return summary

    # Portfolio事件路由功能
    def register_portfolio(self, portfolio) -> None:
        """
        注册Portfolio到路由映射

        Args:
            portfolio: Portfolio对象，需要包含portfolio_id和on_order_partially_filled方法
        """
        portfolio_id = getattr(portfolio, 'uuid', None)
        if portfolio_id is None:
            self.log("ERROR", "Portfolio missing uuid, cannot register")
            return

        if not hasattr(portfolio, 'on_order_partially_filled'):
            self.log("ERROR", f"Portfolio {portfolio_id} missing on_order_partially_filled method")
            return

        self._portfolio_handlers[portfolio_id] = portfolio
        self.log("INFO", f"Portfolio {portfolio_id} registered for ORDERPARTIALLYFILLED routing")

    def on_order_partially_filled(self, event) -> None:
        """
        处理ORDERPARTIALLYFILLED事件，按portfolio_id路由到对应的Portfolio

        Args:
            event: EventOrderPartiallyFilled事件
        """
        # 🔍 详细日志跟踪事件流转
        self.log("INFO", f"🔥 [ROUTER] ORDERPARTIALLYFILLED事件接收开始")
        self.log("INFO", f"🔥 [ROUTER] 事件详情: {type(event).__name__}")

        portfolio_id = getattr(event, 'portfolio_id', None)
        self.log("INFO", f"🔥 [ROUTER] 提取的portfolio_id: {portfolio_id}")

        if portfolio_id is None:
            self.log("ERROR", "ORDERPARTIALLYFILLED event missing portfolio_id, cannot route")
            return

        # 检查当前注册的Portfolio
        registered_portfolios = list(self._portfolio_handlers.keys())
        self.log("INFO", f"🔥 [ROUTER] 已注册的Portfolio列表: {registered_portfolios}")

        portfolio = self._portfolio_handlers.get(portfolio_id)
        if portfolio is None:
            self.log("WARN", f"No registered portfolio found for portfolio_id: {portfolio_id}")
            self.log("WARN", f"🔥 [ROUTER] Portfolio注册失败，无法路由事件")
            return

        self.log("INFO", f"🔥 [ROUTER] 找到目标Portfolio: {type(portfolio).__name__}")

        # 记录事件关键信息
        if hasattr(event, 'order'):
            order = event.order
            self.log("INFO", f"🔥 [ROUTER] 订单信息: code={order.code}, volume={order.volume}, direction={order.direction}")

        if hasattr(event, 'filled_quantity'):
            self.log("INFO", f"🔥 [ROUTER] 成交数量: {event.filled_quantity}")

        if hasattr(event, 'fill_price'):
            self.log("INFO", f"🔥 [ROUTER] 成交价格: {event.fill_price}")

        # 路由事件到对应的Portfolio
        try:
            self.log("INFO", f"🔥 [ROUTER] 开始调用Portfolio.on_order_partially_filled...")
            portfolio.on_order_partially_filled(event)
            self.log("INFO", f"🔥 [ROUTER] Portfolio.on_order_partially_filled调用成功")

            # 检查Portfolio的持仓状态
            if hasattr(portfolio, 'get_positions'):
                positions = portfolio.get_positions()
                self.log("INFO", f"🔥 [ROUTER] Portfolio当前持仓数量: {len(positions)}")
                for code, position in positions.items():
                    self.log("INFO", f"🔥 [ROUTER] 持仓详情: {code} - {position.volume}股")

            if hasattr(portfolio, 'cash'):
                self.log("INFO", f"🔥 [ROUTER] Portfolio当前现金: {portfolio.cash}")

            self.log("DEBUG", f"ORDERPARTIALLYFILLED event routed to portfolio {portfolio_id}")
        except Exception as e:
            self.log("ERROR", f"Error routing ORDERPARTIALLYFILLED to portfolio {portfolio_id}: {e}")
            import traceback
            self.log("ERROR", f"🔥 [ROUTER] 异常堆栈: {traceback.format_exc()}")

        self.log("INFO", f"🔥 [ROUTER] ORDERPARTIALLYFILLED事件处理完成")

    def get_registered_portfolios(self) -> Dict[str, Any]:
        """
        获取已注册的Portfolio映射

        Returns:
            Dict[str, Any]: portfolio_id到Portfolio对象的映射
        """
        return dict(self._portfolio_handlers)