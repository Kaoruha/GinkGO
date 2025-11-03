"""
BrokerMatchMaking - 基于Broker的新一代MatchMaking架构

将MatchMaking从具体的撮合逻辑中解耦，通过注入不同的Broker实现
统一的订单处理流程。支持模拟撮合、OKX实盘等多种执行方式。
"""

from typing import Dict, Any, Optional, List
import pandas as pd
import asyncio
import threading

from ginkgo.trading.routing.base_matchmaking import MatchMakingBase
from ginkgo.trading.brokers.sync_facade import SyncBrokerFacade
from ginkgo.trading.brokers.base_broker import BaseBroker, ExecutionResult, ExecutionStatus
from ginkgo.trading.events import (
    EventOrderAck, EventOrderPartiallyFilled, EventOrderRejected, 
    EventOrderExpired, EventOrderCancelAck
)
from ginkgo.trading.entities import Order
from ginkgo.enums import DIRECTION_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES
from ginkgo.libs import GLOG


class BrokerMatchMaking(MatchMakingBase):
    """
    基于Broker的MatchMaking实现

    核心思想：
    - MatchMaking专注于订单流程管控（验证、路由、结果处理）
    - Broker专注于具体的执行逻辑（模拟撮合、实盘交易）
    - 通过依赖注入实现不同执行环境的统一管理

    特性：
    - 支持多种Broker类型（sim、okx、ibkr等）
    - 统一的订单生命周期管理
    - 完整的事件驱动架构
    - 灵活的配置管理
    """

    def __init__(self, broker: BaseBroker, *args, async_runtime_enabled: Optional[bool] = None, **kwargs):
        """
        初始化BrokerMatchMaking

        Args:
            broker: 通过DI注入的Broker实例
            *args, **kwargs: 传递给父类的参数
        """
        self.broker = broker
        self.broker_type = broker.__class__.__name__

        super().__init__(*args, **kwargs)

        # 订单跟踪
        # 统一的订单队列和跟踪
        self._pending_orders_queue = []  # 待处理订单队列
        self._processing_orders = {}     # {broker_order_id: order_info} 正在处理的订单
        self._order_results = {}  # {order_id: ExecutionResult}

        # 连接状态 - 延迟到async环境中建立连接
        self._connection_established = False

        # NEW: 执行模式识别和处理
        self.execution_mode = broker.execution_mode
        self._supports_manual_confirmation = broker.requires_manual_confirmation()
        self._supports_immediate_execution = broker.supports_immediate_execution()
        self._supports_api_trading = broker.supports_api_trading()

        # 回测同步模式开关（默认：对“立即执行”的Broker禁用异步运行时）
        if async_runtime_enabled is None:
            self._async_runtime_enabled = not self._supports_immediate_execution
        else:
            self._async_runtime_enabled = bool(async_runtime_enabled)

        # 同步封装（仅在回测同步模式使用）
        self._sync_facade: Optional[SyncBrokerFacade] = None
        if not self._async_runtime_enabled:
            self._sync_facade = SyncBrokerFacade(self.broker)

        # 人工确认相关（ManualBroker）
        if self._supports_manual_confirmation:
            self._confirmation_handler = None
            self._setup_manual_confirmation_support()

        # API轮询相关（AutoBroker + SimBroker）
        if self._supports_api_trading or self.broker_type == "SimBroker":
            self._polling_interval = 5  # 秒
            # 回测同步模式下不注册异步状态回调，改为同步直传处理
            if self._async_runtime_enabled:
                self._setup_api_polling_support()

        # 持久事件循环（承载Broker异步任务与回调）
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_thread: Optional[threading.Thread] = None
        self._loop_ready = threading.Event()

    async def initialize_broker_connection(self):
        """在async环境中建立broker连接"""
        if not self._connection_established:
            connected = await self.broker.connect()
            if not connected:
                self.log("ERROR", f"Failed to connect to {self.broker_type} broker")
                raise RuntimeError(f"Broker connection failed")
            self._connection_established = True
            self.log("INFO", f"Broker {self.broker_type} connected successfully")

    def __del__(self):
        """析构函数，确保Broker连接正确关闭"""
        # TODO(human): 修复async disconnect调用
        pass

    @property
    def name(self) -> str:
        """获取MatchMaking名称"""
        return f"BrokerMatchMaking({self.broker_type})"

    def on_order_received(self, event, *args, **kwargs) -> None:
        """
        统一的订单接收处理 - 兼容SimBroker和实盘Broker

        Args:
            event: 订单提交事件
        """
        order = event.value
        
        self.log("DEBUG", f"{self.name} received order {order.code}_{order.direction}")
        
        # 基础验证
        if not self._validate_order_basic(order):
            self._handle_order_rejected(order, "Order validation failed")
            return
            
        # 业务规则验证
        if not self._validate_order_business(order):
            self._handle_order_rejected(order, "Business validation failed")
            return
        
        # 将订单加入待处理队列
        self._pending_orders_queue.append(order)
        self.log("DEBUG", f"Order {order.uuid} queued for processing")

    def on_price_received(self, event, *args, **kwargs) -> None:
        """
        统一的价格更新处理

        - 兼容 EventPriceUpdate(Bar/Tick) → 转换为 DataFrame
        - 兼容直接传入 DataFrame/pd.Series
        """
        price_data = None

        # 优先使用事件提供的 to_dataframe（EventPriceUpdate 提供）
        try:
            if hasattr(event, "to_dataframe"):
                df = event.to_dataframe()
                if df is not None:
                    price_data = df
        except Exception:
            price_data = None

        # 回退：从 event.value 构造
        if price_data is None and hasattr(event, "value"):
            v = getattr(event, "value", None)
            try:
                # 一些价格对象（如 Bar）可被上层事件转为DF；此处保底处理
                if hasattr(event, "to_dataframe"):
                    df = event.to_dataframe()
                    if df is not None:
                        price_data = df
                else:
                    price_data = v
            except Exception:
                price_data = v

        # 兼容直接传入DataFrame/Series的情况
        if price_data is None:
            price_data = event

        self._update_price_cache(price_data)

        # 价格更新时处理待处理订单
        self._process_all_pending_orders()

    def cancel_order(self, order: Order) -> None:
        """
        撤销订单

        Args:
            order: 要撤销的订单
        """
        try:
            # 同步/异步两条路径
            if not self._async_runtime_enabled and self._sync_facade is not None:
                res = self._sync_facade.cancel_order(order.uuid)
            else:
                # 在持久事件循环中执行取消
                res = self._run_coro_sync(self.broker.cancel_order(order.uuid))
            if res and res.status == ExecutionStatus.CANCELED:
                self.log("INFO", f"Order {order.uuid} cancelled successfully")
                self._handle_order_cancelled(order, res.message)
            else:
                msg = getattr(res, 'message', 'unknown')
                self.log("ERROR", f"Failed to cancel order {order.uuid}: {msg}")
        except Exception as e:
            self.log("ERROR", f"Order cancellation failed: {str(e)}")

    async def get_broker_info(self) -> Dict[str, Any]:
        """
        获取Broker信息 - 扩展包含执行模式信息

        Returns:
            Dict: Broker信息字典
        """
        try:
            account_info = await self.broker.get_account_info() if hasattr(self.broker, "get_account_info") else None
            positions = await self.broker.get_positions() if hasattr(self.broker, "get_positions") else []
        except Exception as e:
            self.log("ERROR", f"Failed to get broker info: {e}")
            account_info = None
            positions = []

        broker_info = {
            "broker_type": self.broker_type,
            "execution_mode": self.execution_mode,
            "is_connected": self.broker.is_connected,
            "capabilities": {
                "supports_manual_confirmation": self._supports_manual_confirmation,
                "supports_immediate_execution": self._supports_immediate_execution,
                "supports_api_trading": self._supports_api_trading,
            },
        }

        # 账户信息
        if account_info:
            broker_info["account_info"] = {
                "total_asset": account_info.total_asset,
                "available_cash": account_info.available_cash,
                "market_value": account_info.market_value,
                "total_pnl": account_info.total_pnl,
            }

        # 持仓信息
        if positions:
            broker_info.update(
                {
                    "positions_count": len(positions),
                    "positions": [
                        {
                            "code": getattr(pos, "code", "Unknown"),
                            "volume": getattr(pos, "volume", 0),
                            "direction": (
                                getattr(pos, "direction", {}).get("value", "Unknown")
                                if hasattr(getattr(pos, "direction", None), "value")
                                else "Unknown"
                            ),
                            "unrealized_pnl": getattr(pos, "unrealized_pnl", 0.0),
                        }
                        for pos in positions
                    ],
                }
            )
        else:
            broker_info.update({"positions_count": 0, "positions": []})

        # 执行模式特定信息
        if self._supports_manual_confirmation:
            broker_info["manual_confirmation"] = {
                "pending_orders": self.get_pending_manual_orders(),
                "confirmation_handler_available": self._confirmation_handler is not None,
            }

        if self._supports_api_trading:
            broker_info["api_trading"] = self.get_api_trading_status()

        if self._supports_immediate_execution:
            broker_info["immediate_execution"] = {
                "pending_orders_count": len(self._processing_orders),
                "completed_orders_count": len(self._order_results),
            }

        return broker_info

    # ==================== NEW: 执行模式支持方法 ====================

    def _setup_manual_confirmation_support(self):
        """设置人工确认支持（ManualBroker）"""
        try:
            # TODO: Move confirmation functionality to events module
            # from ginkgo.trading.events.execution_confirmation import ConfirmationHandler

            self._confirmation_handler = ConfirmationHandler()
            self.log("INFO", f"Manual confirmation support enabled for {self.broker_type}")
        except Exception as e:
            self.log("WARN", f"Failed to setup manual confirmation: {e}")
            self._confirmation_handler = None

    def _setup_api_polling_support(self):
        """设置API轮询支持（AutoBroker）"""
        try:
            # 为AutoBroker设置状态回调
            if hasattr(self.broker, "register_status_callback"):
                self.broker.register_status_callback(self._on_broker_status_update)
            self.log("INFO", f"API polling support enabled for {self.broker_type}")
        except Exception as e:
            self.log("WARN", f"Failed to setup API polling: {e}")

    async def _on_broker_status_update(self, result: ExecutionResult):
        """
        Broker状态回调处理器（AutoBroker使用）

        Args:
            result: Broker推送的执行结果
        """
        try:
            # 兼容两种存储形态：dict({'order': order}) 或直接保存order
            order_info = self._processing_orders.get(result.order_id)
            if isinstance(order_info, dict):
                order = order_info.get('order')
            else:
                order = order_info

            if order is not None:
                await self._handle_execution_result(order, result)
            else:
                self.log("WARN", f"Received status update for unknown order: {result.order_id}")

        except Exception as e:
            self.log("ERROR", f"Failed to handle broker status update: {e}")

    async def handle_manual_confirmation(
        self, order_id: str, actual_price: float, actual_volume: int, notes: str = ""
    ) -> bool:
        """
        处理人工确认（ManualBroker专用）

        Args:
            order_id: 订单ID
            actual_price: 实际成交价格
            actual_volume: 实际成交数量
            notes: 备注信息

        Returns:
            bool: 确认是否成功
        """
        if not self._supports_manual_confirmation:
            self.log("ERROR", "Manual confirmation not supported by current broker")
            return False

        if not hasattr(self.broker, "confirm_order_execution"):
            self.log("ERROR", "Broker does not support manual confirmation")
            return False

        try:
            # 通过ManualBroker确认订单
            result = await self.broker.confirm_order_execution(order_id, actual_price, actual_volume, notes)

            if result.is_success:
                self.log("INFO", f"Manual confirmation successful for order {order_id}")

                # 查找并处理对应的订单
                order_info = self._processing_orders.get(result.order_id)
                order = order_info.get('order') if isinstance(order_info, dict) else order_info
                if order is not None:
                    await self._handle_execution_result(order, result)

                return True
            else:
                self.log("ERROR", f"Manual confirmation failed: {result.message}")
                return False

        except Exception as e:
            self.log("ERROR", f"Manual confirmation error: {e}")
            return False

    def get_pending_manual_orders(self) -> List[Dict[str, Any]]:
        """
        获取等待人工确认的订单（ManualBroker专用）

        Returns:
            List[Dict]: 等待确认的订单列表
        """
        if not self._supports_manual_confirmation:
            return []

        if hasattr(self.broker, "get_pending_orders"):
            return self.broker.get_pending_orders()

        return []

    def get_api_trading_status(self) -> Dict[str, Any]:
        """
        获取API交易状态（AutoBroker专用）

        Returns:
            Dict: API交易状态信息
        """
        if not self._supports_api_trading:
            return {"supported": False}

        status = {"supported": True}

        if hasattr(self.broker, "get_active_orders_count"):
            status["active_orders_count"] = self.broker.get_active_orders_count()

        if hasattr(self.broker, "get_polling_status"):
            status.update(self.broker.get_polling_status())

        return status

    # ==================== Private Methods ====================

    def _validate_order_basic(self, order: Order) -> bool:
        """基础订单验证"""
        return self.broker.validate_order(order)

    def _validate_order_business(self, order: Order) -> bool:
        """业务规则验证（可根据需要扩展）"""
        # 检查股票代码格式
        if not order.code or len(order.code) < 6:
            self.log("WARN", f"Invalid stock code: {order.code}")
            return False

        # 检查数量是否为100的倍数（A股规则）
        if order.volume % 100 != 0:
            self.log("WARN", f"Order volume must be multiple of 100: {order.volume}")
            return False

        return True

    def _update_broker_price_cache(self) -> None:
        """更新Broker的价格缓存"""
        if hasattr(self.broker, "update_price_cache") and hasattr(self, "_price_cache"):
            if not self._price_cache.empty:
                self.broker.update_price_cache(self._price_cache)

    async def _handle_execution_result(self, order: Order, result: ExecutionResult) -> None:
        """处理执行结果 (T5新增方法)"""
        try:
            # 根据执行结果发布相应的生命周期事件
            if result.status == ExecutionStatus.SUBMITTED:
                # 仅在SUBMITTED状态时发布ACK事件
                await self._publish_order_ack_event(order, result)
            elif result.status == ExecutionStatus.FILLED:
                await self._publish_order_filled_event(order, result)
            elif result.status == ExecutionStatus.PARTIALLY_FILLED:
                await self._publish_order_partially_filled_event(order, result)
            elif result.status == ExecutionStatus.REJECTED:
                await self._publish_order_rejected_event(order, result)
            elif result.status == ExecutionStatus.EXPIRED:
                await self._publish_order_expired_event(order, result)
                
        except Exception as e:
            self.log("ERROR", f"Failed to handle execution result: {e}")

    
    # ==================== T5 事件发布方法 ====================
    
    async def _publish_order_ack_event(self, order: Order, result: ExecutionResult) -> None:
        """发布订单确认事件 (T5新增)"""
        try:
            from ginkgo.trading.events import EventOrderAck
            
            ack_event = EventOrderAck(
                order=order,
                broker_order_id=result.broker_order_id or result.order_id,
                ack_message=result.message or "Order accepted by broker"
            )
            ack_event.set_source(SOURCE_TYPES.BROKERMATCHMAKING)
            
            if self.put:
                self.put(ack_event)
                self.log("INFO", f"Published OrderAck event for {order.uuid}")
                
        except Exception as e:
            self.log("ERROR", f"Failed to publish OrderAck event: {e}")
    
    async def _publish_partial_fill_event(self, order: Order, result: ExecutionResult) -> None:
        """发布部分成交事件 (T5新增)"""
        try:
            from ginkgo.trading.events import EventOrderPartiallyFilled
            from decimal import Decimal
            
            partial_fill_event = EventOrderPartiallyFilled(
                order=order,
                filled_quantity=float(result.filled_quantity or 0),
                fill_price=float(result.filled_price or 0),
                trade_id=result.trade_id,
                commission=Decimal(str(result.fees or 0))
            )
            partial_fill_event.set_source(SOURCE_TYPES.BROKERMATCHMAKING)
            
            if self.put:
                self.put(partial_fill_event)
                self.log("INFO", f"Published PartiallyFilled event for {order.uuid}: {result.filled_quantity}@{result.filled_price}")
                
        except Exception as e:
            self.log("ERROR", f"Failed to publish PartiallyFilled event: {e}")

    # 兼容命名：_publish_order_partially_filled_event -> 调用统一实现
    async def _publish_order_partially_filled_event(self, order: Order, result: ExecutionResult) -> None:
        await self._publish_partial_fill_event(order, result)
    
    async def _publish_order_rejected_event(self, order: Order, result: ExecutionResult) -> None:
        """发布订单拒绝事件 (T5新增)"""
        try:
            from ginkgo.trading.events import EventOrderRejected
            
            rejected_event = EventOrderRejected(
                order=order,
                reject_reason=result.message or "Order rejected by broker",
                reject_code=result.error_code
            )
            rejected_event.set_source(SOURCE_TYPES.BROKERMATCHMAKING)
            
            if self.put:
                self.put(rejected_event)
                self.log("INFO", f"Published OrderRejected event for {order.uuid}: {result.message}")
                
        except Exception as e:
            self.log("ERROR", f"Failed to publish OrderRejected event: {e}")
    
    async def _publish_order_cancel_ack_event(self, order: Order, result: ExecutionResult) -> None:
        """发布撤销确认事件 (T5新增)"""
        try:
            from ginkgo.trading.events import EventOrderCancelAck
            
            cancel_ack_event = EventOrderCancelAck(
                order=order,
                cancelled_quantity=float(result.cancelled_quantity or order.volume),
                cancel_reason=result.message or "Order cancelled by broker"
            )
            cancel_ack_event.set_source(SOURCE_TYPES.BROKERMATCHMAKING)
            
            if self.put:
                self.put(cancel_ack_event)
                self.log("INFO", f"Published OrderCancelAck event for {order.uuid}")
                
        except Exception as e:
            self.log("ERROR", f"Failed to publish OrderCancelAck event: {e}")
    
    async def _publish_order_expired_event(self, order: Order, expire_reason: str = "Time expired") -> None:
        """发布订单过期事件 (T5新增)"""
        try:
            from ginkgo.trading.events import EventOrderExpired
            
            expired_event = EventOrderExpired(
                order=order,
                expire_reason=expire_reason
            )
            expired_event.set_source(SOURCE_TYPES.BROKERMATCHMAKING)
            
            if self.put:
                self.put(expired_event)
                self.log("INFO", f"Published OrderExpired event for {order.uuid}: {expire_reason}")
                
        except Exception as e:
            self.log("ERROR", f"Failed to publish OrderExpired event: {e}")
    
    def check_and_expire_orders(self) -> None:
        """检查并处理过期订单 (T5增强)"""
        try:
            from datetime import datetime, timedelta
            from ginkgo.trading.time.clock import now as clock_now
            
            current_time = clock_now()
            expired_orders = []
            
            # 检查处理中的订单是否过期
            for order_id, order_info in list(self._processing_orders.items()):
                if isinstance(order_info, dict) and 'submit_time' in order_info:
                    submit_time = order_info['submit_time']
                    # 假设订单30分钟后过期
                    if current_time - submit_time > timedelta(minutes=30):
                        expired_orders.append((order_id, order_info['order']))
                        
            # 处理过期订单
            for order_id, order in expired_orders:
                self.log("WARN", f"Order {order_id} expired after 30 minutes")
                
                # 发布过期事件（在持久事件循环中）
                try:
                    self._run_coro_sync(self._publish_order_expired_event(order, "Timeout after 30 minutes"))
                except Exception as e:
                    self.log("ERROR", f"Publish expired event failed: {e}")
                
                # 清理过期订单
                self._processing_orders.pop(order_id, None)
                
                # 发布取消事件（过期相当于被取消）
                cancel_event = EventOrderCancelAck(
                    order=order,
                    cancelled_quantity=float(order.volume),
                    cancel_reason="Timeout after 30 minutes"
                )
                cancel_event.set_source(SOURCE_TYPES.SIMMATCH)
                if self.put:
                    self.put(cancel_event)
                    
        except Exception as e:
            self.log("ERROR", f"Error checking expired orders: {e}")

    async def process_broker_execution_result(self, order: Order, result: ExecutionResult) -> None:
        """
        处理Broker执行结果 - 支持统一的ExecutionResult并发布T5事件

        Args:
            order: 原始订单
            result: Broker执行结果
        """
        # 记录订单映射
        if result.broker_order_id:
            self._processing_orders[result.order_id] = order
        self._order_results[result.order_id] = result

        self.log("DEBUG", f"Execution result: {result}")

        # 根据执行状态处理并发布相应的T5事件
        if result.status == ExecutionStatus.SUBMITTED:
            # 发布订单确认事件 (T5新增)
            await self._publish_order_ack_event(order, result)
            self.log("INFO", f"Order {result.order_id} submitted to broker, waiting for fill")
            
        elif result.status == ExecutionStatus.FILLED:
            await self._handle_order_filled(result)
            
        elif result.status == ExecutionStatus.PARTIALLY_FILLED:
            # 发布部分成交事件 (T5新增) 
            await self._publish_partial_fill_event(order, result)
            await self._handle_order_partially_filled(result)

        elif result.status == ExecutionStatus.REJECTED:
            # 发布订单拒绝事件 (T5新增)
            await self._publish_order_rejected_event(order, result)
            await self._handle_order_rejected_with_result(result)

        elif result.status == ExecutionStatus.CANCELED:
            # 发布撤销确认事件 (T5新增)
            await self._publish_order_cancel_ack_event(order, result)
            await self._handle_order_cancelled_with_result(result)

        elif result.status == ExecutionStatus.FAILED:
            await self._handle_order_failed_with_result(result)
        else:
            self.log("WARN", f"Unknown execution status: {result.status}")

    async def _handle_order_filled(self, result: ExecutionResult) -> None:
        """
        处理订单完全成交 - 适配新的ExecutionResult结构

        Args:
            result: 执行结果
        """
        order = self._processing_orders.get(result.order_id)
        if not order:
            self.log("ERROR", f"Order {result.order_id} not found in processing orders")
            return

        try:
            # 更新订单信息
            order.transaction_price = result.filled_price
            order.transaction_volume = int(result.filled_quantity)
            order.fee = result.fees
            order.fill()  # 标记为已成交

            # 创建成交事件
            fill_event = EventOrderPartiallyFilled(
                order=order,
                filled_quantity=float(result.filled_quantity),
                fill_price=float(result.filled_price),
                trade_id=result.trade_id if hasattr(result, 'trade_id') else None,
                commission=result.fees or 0
            )
            fill_event.set_source(SOURCE_TYPES.BROKERMATCHMAKING)

            # 发送事件
            self.put(fill_event)

            # 清理处理中订单
            self._processing_orders.pop(result.order_id, None)

            self.log("INFO", f"Order {result.order_id} filled: {result.filled_quantity}@{result.filled_price}")

        except Exception as e:
            self.log("ERROR", f"Failed to handle order filled: {e}")

    # 兼容命名：_publish_order_filled_event -> 实际委托到 _handle_order_filled
    async def _publish_order_filled_event(self, order: Order, result: ExecutionResult) -> None:
        await self._handle_order_filled(result)

    async def _handle_order_partially_filled(self, result: ExecutionResult) -> None:
        """
        处理订单部分成交

        Args:
            result: 执行结果
        """
        order = self._processing_orders.get(result.order_id)
        if not order:
            self.log("ERROR", f"Order {result.order_id} not found in processing orders")
            return

        # 更新部分成交信息
        order.transaction_price = result.filled_price
        order.transaction_volume = result.filled_quantity
        order.fee = result.fees

        self.log("INFO", f"Order {result.order_id} partially filled: {result.filled_quantity}/{order.volume}")

        # 继续等待剩余部分成交
        # 注意：这里可能需要根据具体业务逻辑决定是否拆分订单

    async def _handle_order_rejected_with_result(self, result: ExecutionResult) -> None:
        """
        处理订单被拒绝 - 基于ExecutionResult

        Args:
            result: 执行结果
        """
        order = self._processing_orders.get(result.order_id)
        if order:
            # 创建取消事件（订单被拒绝相当于被取消）
            cancel_event = EventOrderCancelAck(
                order=order,
                cancelled_quantity=float(order.volume),
                cancel_reason=result.message or "Order rejected"
            )
            cancel_event.set_source(SOURCE_TYPES.BROKERMATCHMAKING)
            self.put(cancel_event)

            # 清理处理中订单
            self._processing_orders.pop(result.order_id, None)

        self.log("WARN", f"Order {result.order_id} rejected: {result.message}")

    async def _handle_order_cancelled_with_result(self, result: ExecutionResult) -> None:
        """
        处理订单被取消 - 基于ExecutionResult

        Args:
            result: 执行结果
        """
        order = self._processing_orders.get(result.order_id)
        if order:
            # 创建取消事件
            cancel_event = EventOrderCancelAck(
                order=order,
                cancelled_quantity=float(result.cancelled_quantity or order.volume),
                cancel_reason=result.message or "Order cancelled"
            )
            cancel_event.set_source(SOURCE_TYPES.BROKERMATCHMAKING)
            self.put(cancel_event)

            # 清理处理中订单
            self._processing_orders.pop(result.order_id, None)

        self.log("INFO", f"Order {result.order_id} cancelled: {result.message}")

    async def _handle_order_failed_with_result(self, result: ExecutionResult) -> None:
        """
        处理订单执行失败 - 基于ExecutionResult

        Args:
            result: 执行结果
        """
        order = self._processing_orders.get(result.order_id)
        if order:
            # 创建取消事件（执行失败相当于被取消）
            cancel_event = EventOrderCancelAck(
                order=order,
                cancelled_quantity=float(order.volume),
                cancel_reason=result.message or "Order failed"
            )
            cancel_event.set_source(SOURCE_TYPES.BROKERMATCHMAKING)
            self.put(cancel_event)

            # 清理处理中订单
            self._processing_orders.pop(result.order_id, None)

        self.log("ERROR", f"Order {result.order_id} failed: {result.message} (Code: {result.error_code})")

    def _update_broker_market_data(self) -> None:
        """
        更新Broker的市场数据 - 专门为SimBroker提供价格信息
        """
        if hasattr(self.broker, "set_market_data") and hasattr(self, "_price_cache"):
            # 如果有价格缓存，传递给SimBroker
            if hasattr(self._price_cache, "iterrows"):
                for index, row in self._price_cache.iterrows():
                    if "code" in row:
                        self.broker.set_market_data(row["code"], row)

    def _handle_order_rejected(self, order: Order, message: str) -> None:
        """处理订单被拒绝"""
        order.cancel()
        
        # 从待处理队列中移除订单（如果存在）
        if order in self._pending_orders_queue:
            self._pending_orders_queue.remove(order)
        
        # 从处理中订单字典中移除订单（如果存在）
        self._processing_orders.pop(order.uuid, None)

        self.log("WARN", f"Order {order.uuid} rejected: {message}")
        # 可以发送订单拒绝事件（如果需要）

    def _handle_order_cancelled(self, order: Order, message: str) -> None:
        """处理订单撤销"""
        order.cancel()
        
        # 从待处理队列中移除订单（如果存在）
        if order in self._pending_orders_queue:
            self._pending_orders_queue.remove(order)
        
        # 从处理中订单字典中移除订单（如果存在）
        self._processing_orders.pop(order.uuid, None)

        self.log("INFO", f"Order {order.uuid} cancelled: {message}")
        # 可以发送订单撤销事件（如果需要）

    def _handle_order_failed(self, order: Order, message: str) -> None:
        """处理订单执行失败"""
        order.cancel()
        
        # 从待处理队列中移除订单（如果存在）
        if order in self._pending_orders_queue:
            self._pending_orders_queue.remove(order)
        
        # 从处理中订单字典中移除订单（如果存在）
        self._processing_orders.pop(order.uuid, None)

        self.log("ERROR", f"Order {order.uuid} failed: {message}")

    async def _check_pending_orders(self) -> None:
        """检查待处理订单状态（主要用于实盘交易）"""
        if not self._processing_orders:
            return

        # 遍历正在处理的订单
        for order_id, order in list(self._processing_orders.items()):
            try:
                # 查询订单状态
                status = await self.broker.query_order_status(order_id)
                
                if status:
                    # 根据状态更新订单
                    if status.status == ExecutionStatus.FILLED:
                        await self._handle_order_filled(order, status)
                    elif status.status == ExecutionStatus.CANCELED:
                        await self._handle_order_cancelled_with_result(status)
                    elif status.status == ExecutionStatus.REJECTED:
                        await self._handle_order_rejected_with_result(status)
                    elif status.status == ExecutionStatus.FAILED:
                        await self._handle_order_failed_with_result(status)
                        
            except Exception as e:
                self.log("ERROR", f"Failed to check order {order_id} status: {e}")
                
        self.log("DEBUG", f"Checked {len(self._processing_orders)} processing orders")

    def _update_price_cache(self, price_data):
        """更新价格缓存并尽量合并为DataFrame以供Broker使用"""
        try:
            import pandas as _pd

            # 统一为 DataFrame
            df = None
            if isinstance(price_data, _pd.DataFrame):
                df = price_data
            elif isinstance(price_data, _pd.Series):
                df = _pd.DataFrame(price_data).T
            elif hasattr(price_data, "to_frame"):
                # 兜底（极少见）
                try:
                    df = price_data.to_frame().T
                except Exception:
                    df = None

            if df is not None:
                # 合并缓存
                if hasattr(self, "_price_cache") and isinstance(self._price_cache, _pd.DataFrame) and not self._price_cache.empty:
                    self._price_cache = _pd.concat([self._price_cache, df], ignore_index=True)
                else:
                    self._price_cache = df
            else:
                # 无法转DF时，直接覆盖缓存，交由 broker.set_market_data 在后续处理
                self._price_cache = price_data

            # 同步给Broker（SimBroker依赖）
            if hasattr(self.broker, 'set_market_data'):
                self._update_broker_market_data()

            size_desc = None
            if isinstance(self._price_cache, _pd.DataFrame):
                size_desc = self._price_cache.shape[0]
            elif hasattr(self._price_cache, '__len__'):
                size_desc = len(self._price_cache)
            else:
                size_desc = 1
            self.log("DEBUG", f"Updated price cache with {size_desc} records")

        except Exception as e:
            self.log("ERROR", f"Failed to update price cache: {e}")
    
    def _process_all_pending_orders(self):
        """处理所有待处理订单"""
        if not self._pending_orders_queue:
            return
            
        orders_to_process = self._pending_orders_queue.copy()
        self._pending_orders_queue.clear()
        
        self.log("DEBUG", f"Processing {len(orders_to_process)} pending orders")
        
        for order in orders_to_process:
            try:
                if not self._async_runtime_enabled and self._sync_facade is not None:
                    # 同步提交并直接处理执行结果
                    self._submit_to_broker_sync(order)
                else:
                    # 将协程提交到持久事件循环中执行
                    self._run_coro_sync(self._submit_to_broker(order))
            except Exception as e:
                self.log("ERROR", f"Failed to process order {order.uuid}: {e}")
                self._handle_order_failed(order, f"Processing error: {str(e)}")
    
    async def _submit_to_broker(self, order):
        """统一的Broker提交接口 - 不区分SimBroker和实盘Broker"""
        try:
            # 更新市场数据（对SimBroker特别重要）
            if hasattr(self.broker, 'set_market_data'):
                self._update_broker_market_data()
                
            # 调用Broker的统一接口
            result = await self.broker.submit_order(order)
            
            if result.status == ExecutionStatus.SUBMITTED:
                # 需要跟踪的订单（实盘Broker常见）
                self._track_order(order, result)
            else:
                # 立即完成的订单（SimBroker常见）
                await self._handle_execution_result(order, result)
                
        except Exception as e:
            self.log("ERROR", f"Broker submission failed for {order.uuid}: {e}")
            self._handle_order_failed(order, f"Submission error: {str(e)}")

    def _submit_to_broker_sync(self, order):
        """回测同步路径：直接通过同步Facade提交并发布事件。"""
        # 更新市场数据（对SimBroker特别重要）
        if hasattr(self.broker, 'set_market_data'):
            self._update_broker_market_data()

        # 对SimBroker：尽量获得完整执行序列（含部分成交）
        try:
            if hasattr(self.broker, "_simulate_execution_core"):
                broker_order_id = f"SIM_{order.uuid[:8]}"
                results = getattr(self.broker, "_simulate_execution_core")(order, broker_order_id)
                for r in results:
                    # 逐个处理执行结果并发布相应事件
                    self._run_coro_sync(self._handle_execution_result(order, r))
                return
        except Exception as e:
            # 回退到简单路径
            self.log("WARN", f"Simulate core not available, fallback to single submit: {e}")

        # 通用回退：单结果
        res = self._sync_facade.submit_order(order) if self._sync_facade else None
        if res is None:
            self._handle_order_failed(order, "No execution result from sync facade")
            return

        if res.status == ExecutionStatus.SUBMITTED:
            self._track_order(order, res)
        else:
            self._run_coro_sync(self._handle_execution_result(order, res))
    
    def _track_order(self, order, result):
        """跟踪提交的订单"""
        from ginkgo.trading.time.clock import now as clock_now
        self._processing_orders[result.order_id] = {
            'order': order,
            'result': result,
            'submit_time': clock_now()
        }
        self.log("DEBUG", f"Tracking order {result.order_id}")
    
    def _timer_check_order_status(self):
        """定时器：检查订单状态（统一处理SimBroker和实盘）"""
        if not self._processing_orders:
            return
            
        for order_id, info in list(self._processing_orders.items()):
            try:
                result = self._run_coro_sync(self.broker.query_order(order_id))
                if result and result.is_final_status:
                    self._run_coro_sync(self._handle_execution_result(info['order'], result))
                    self._processing_orders.pop(order_id, None)
                    self.log("DEBUG", f"Order {order_id} completed with status {result.status}")
            except Exception as e:
                self.log("ERROR", f"Order status check failed for {order_id}: {e}")

    # ==================== 持久事件循环托管 ====================
    def _ensure_loop_running(self):
        if self._loop and self._loop.is_running():
            return
        def _runner():
            try:
                loop = asyncio.new_event_loop()
                self._loop = loop
                asyncio.set_event_loop(loop)
                self._loop_ready.set()
                loop.run_forever()
            finally:
                try:
                    pending = asyncio.all_tasks(loop=self._loop)
                    for t in pending:
                        t.cancel()
                except Exception:
                    pass
                try:
                    loop.stop()
                except Exception:
                    pass
                try:
                    loop.close()
                except Exception:
                    pass
        self._loop_ready.clear()
        self._loop_thread = threading.Thread(target=_runner, name="BrokerMM-Loop", daemon=True)
        self._loop_thread.start()
        self._loop_ready.wait(timeout=3)

    def _run_coro_sync(self, coro, timeout: Optional[float] = 10.0):
        """在持久事件循环中执行协程并返回结果。"""
        self._ensure_loop_running()
        if not self._loop:
            raise RuntimeError("Persistent event loop not available")
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=timeout)

    def shutdown_async_loop(self, timeout: float = 2.0):
        """关闭持久事件循环。"""
        try:
            if self._loop and self._loop.is_running():
                self._loop.call_soon_threadsafe(self._loop.stop)
                if self._loop_thread and self._loop_thread.is_alive():
                    self._loop_thread.join(timeout=timeout)
        except Exception as e:
            self.log("WARN", f"Shutdown async loop error: {e}")

    def log(self, level: str, message: str) -> None:
        """统一的日志接口"""
        getattr(GLOG, level)(f"[{self.name}] {message}")
