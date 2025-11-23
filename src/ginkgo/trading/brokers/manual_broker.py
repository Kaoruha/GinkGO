"""
ManualBroker - 人工确认执行器

专门用于实盘交易中需要人工确认的场景，订单提交后等待用户通过CLI确认
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from ginkgo.trading.time.clock import now as clock_now
from decimal import Decimal

from ginkgo.trading.brokers.base_broker import (
    BaseBroker, ExecutionResult, ExecutionStatus, BrokerCapabilities
)
from ginkgo.libs import GLOG
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES


class ManualBroker(BaseBroker):
    """
    人工确认Broker
    
    核心特点：
    - 订单提交后返回SUBMITTED状态，等待人工确认
    - 集成通知系统，通过各种渠道通知用户
    - 支持CLI确认接口，用户可通过命令行确认订单
    - 支持超时自动取消，避免订单长时间挂起
    - 完整的确认状态追踪和日志记录
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化ManualBroker
        
        Args:
            config: 配置字典，包含：
                - confirmation_timeout_minutes: 确认超时时间（分钟，默认30）
                - notification_channels: 通知渠道列表 ['console', 'telegram', 'email']
                - auto_cancel_on_timeout: 超时是否自动取消（默认True）
        """
        super().__init__(config)
        
        # 确认配置
        self._confirmation_timeout_minutes = config.get('confirmation_timeout_minutes', 30)
        self._notification_channels = config.get('notification_channels', ['console'])
        self._auto_cancel_on_timeout = config.get('auto_cancel_on_timeout', True)
        
        # 等待确认的订单
        self._pending_orders: Dict[str, Dict[str, Any]] = {}
        
        # 确认处理器（延迟加载）
        self._confirmation_handler = None
        self._notifier = None
        
    def _init_capabilities(self) -> BrokerCapabilities:
        """初始化ManualBroker的能力描述"""
        caps = BrokerCapabilities()
        caps.execution_type = "manual"  # 人工确认执行
        caps.supports_streaming = False
        caps.supports_batch_ops = False  # 人工确认不支持批量
        caps.supports_market_data = False
        caps.supports_positions = False
        caps.max_orders_per_second = 10  # 人工确认有限制
        caps.max_concurrent_orders = 50
        caps.order_timeout_seconds = self._confirmation_timeout_minutes * 60
        caps.supported_order_types = ["MARKET", "LIMIT"]
        caps.supported_time_in_force = ["DAY", "GTC"]
        return caps
    
    def _detect_execution_mode(self) -> str:
        """
        ManualBroker专用于手动确认模式
        
        Returns:
            str: 'manual'
        """
        return 'manual'
    
    @property
    def confirmation_handler(self):
        """延迟加载确认处理器"""
        if self._confirmation_handler is None:
            # TODO: Move confirmation functionality to events module
            # from ginkgo.trading.events.execution_confirmation import ConfirmationHandler
            self._confirmation_handler = ConfirmationHandler()
        return self._confirmation_handler
    
    @property
    def notifier(self):
        """延迟加载通知器"""
        if self._notifier is None:
            try:
                from ginkgo import services
                self._notifier = services.notification.notifier()
            except Exception as e:
                self._logger.WARN(f"Failed to load notifier: {e}")
                self._notifier = None
        return self._notifier
    
    # ============= 连接管理 =============
    async def connect(self) -> bool:
        """连接ManualBroker（初始化确认系统）"""
        try:
            # 初始化确认处理器
            _ = self.confirmation_handler
            
            # 测试通知系统
            if self.notifier:
                await self._test_notification_system()
            
            self._connected = True
            self._logger.INFO("ManualBroker connected successfully")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to connect ManualBroker: {e}")
            return False
    
    async def disconnect(self) -> bool:
        """断开ManualBroker连接"""
        try:
            # 取消所有等待确认的订单
            await self._cancel_pending_orders("Broker disconnecting")
            
            self._connected = False
            self._logger.INFO("ManualBroker disconnected")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to disconnect ManualBroker: {e}")
            return False
    
    # ============= 订单管理 =============
    async def submit_order(self, order: "Order") -> ExecutionResult:
        """
        提交订单并发送确认通知
        
        Args:
            order: 订单对象
            
        Returns:
            ExecutionResult: 提交结果，状态为SUBMITTED（等待确认）
        """
        if not self.is_connected:
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.FAILED,
                message="ManualBroker not connected",
                execution_mode=self.execution_mode,
                requires_confirmation=True
            )
        
        # 基础验证
        if not self.validate_order(order):
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.REJECTED,
                message="Order validation failed",
                execution_mode=self.execution_mode,
                requires_confirmation=True
            )
        
        try:
            # 计算确认截止时间
            confirmation_deadline = clock_now() + timedelta(
                minutes=self._confirmation_timeout_minutes
            )
            
            # 创建等待确认的订单记录
            pending_info = {
                'order': order,
                'submitted_at': clock_now(),
                'confirmation_deadline': confirmation_deadline,
                'notification_sent': False
            }
            self._pending_orders[order.uuid] = pending_info
            
            # 发送确认通知
            await self._send_confirmation_notification(order, confirmation_deadline)
            
            # 创建执行结果
            result = ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.SUBMITTED,
                broker_order_id=f"MANUAL_{order.uuid[:8]}",
                message="Order submitted, awaiting manual confirmation",
                execution_mode=self.execution_mode,
                requires_confirmation=True,
                confirmation_deadline=confirmation_deadline
            )
            
            # 更新缓存
            self._update_order_status(result)
            
            # 启动超时检查任务
            asyncio.create_task(self._monitor_confirmation_timeout(order.uuid))
            
            return result
            
        except Exception as e:
            self._logger.ERROR(f"Failed to submit order {order.uuid}: {e}")
            return ExecutionResult(
                order_id=order.uuid,
                status=ExecutionStatus.FAILED,
                message=f"Submission error: {str(e)}",
                execution_mode=self.execution_mode,
                requires_confirmation=True
            )
    
    async def cancel_order(self, order_id: str) -> ExecutionResult:
        """
        取消订单（包括等待确认的订单）
        
        Args:
            order_id: 订单ID
            
        Returns:
            ExecutionResult: 取消结果
        """
        try:
            # 检查是否在等待确认中
            if order_id in self._pending_orders:
                del self._pending_orders[order_id]
                
                result = ExecutionResult(
                    order_id=order_id,
                    status=ExecutionStatus.CANCELED,
                    message="Order cancelled before confirmation",
                    execution_mode=self.execution_mode,
                    requires_confirmation=True
                )
                
                self._update_order_status(result)
                return result
            
            # 检查缓存中的状态
            cached_result = self.get_cached_order_status(order_id)
            if cached_result and cached_result.is_final_status:
                return ExecutionResult(
                    order_id=order_id,
                    status=ExecutionStatus.REJECTED,
                    message="Cannot cancel finalized order",
                    execution_mode=self.execution_mode,
                    requires_confirmation=True
                )
            
            # 默认取消结果
            result = ExecutionResult(
                order_id=order_id,
                status=ExecutionStatus.CANCELED,
                message="Order cancelled",
                execution_mode=self.execution_mode,
                requires_confirmation=True
            )
            
            self._update_order_status(result)
            return result
            
        except Exception as e:
            self._logger.ERROR(f"Failed to cancel order {order_id}: {e}")
            return ExecutionResult(
                order_id=order_id,
                status=ExecutionStatus.FAILED,
                message=f"Cancel error: {str(e)}",
                execution_mode=self.execution_mode,
                requires_confirmation=True
            )
    
    async def query_order(self, order_id: str) -> ExecutionResult:
        """
        查询订单状态
        
        Args:
            order_id: 订单ID
            
        Returns:
            ExecutionResult: 订单状态
        """
        # 首先检查等待确认状态
        if order_id in self._pending_orders:
            pending_info = self._pending_orders[order_id]
            
            # 检查是否超时
            if clock_now() > pending_info['confirmation_deadline']:
                if self._auto_cancel_on_timeout:
                    await self._handle_confirmation_timeout(order_id)
                    return self.get_cached_order_status(order_id)
            
            # 返回等待确认状态
            return ExecutionResult(
                order_id=order_id,
                status=ExecutionStatus.SUBMITTED,
                message="Awaiting manual confirmation",
                execution_mode=self.execution_mode,
                requires_confirmation=True,
                confirmation_deadline=pending_info['confirmation_deadline']
            )
        
        # 查询缓存状态
        cached_result = self.get_cached_order_status(order_id)
        if cached_result:
            return cached_result
        
        # 订单不存在
        return ExecutionResult(
            order_id=order_id,
            status=ExecutionStatus.FAILED,
            message="Order not found",
            execution_mode=self.execution_mode,
            requires_confirmation=True
        )
    
    # ============= 账户管理 =============
    async def get_account_info(self) -> "AccountInfo":
        """获取模拟账户信息（ManualBroker用于测试）"""
        from ginkgo.trading.brokers.base_broker import AccountInfo
        return AccountInfo(
            total_asset=1000000.0,
            available_cash=1000000.0,
            frozen_cash=0.0,
            market_value=0.0,
            total_pnl=0.0
        )
    
    async def get_positions(self) -> List["Position"]:
        """获取持仓信息（返回空列表，由Portfolio管理）"""
        return []
    
    # ============= 确认处理逻辑 =============
    async def confirm_order_execution(
        self, 
        order_id: str, 
        actual_price: float, 
        actual_volume: int,
        notes: str = ""
    ) -> ExecutionResult:
        """
        确认订单执行 - 供CLI调用
        
        Args:
            order_id: 订单ID（支持短ID）
            actual_price: 实际成交价格
            actual_volume: 实际成交数量
            notes: 备注信息
            
        Returns:
            ExecutionResult: 确认结果
        """
        try:
            # 查找等待确认的订单
            pending_order = None
            full_order_id = None
            
            for pending_id, pending_info in self._pending_orders.items():
                if pending_id.startswith(order_id) or pending_id == order_id:
                    pending_order = pending_info
                    full_order_id = pending_id
                    break
            
            if not pending_order:
                return ExecutionResult(
                    order_id=order_id,
                    status=ExecutionStatus.FAILED,
                    message="Order not found or not pending confirmation",
                    execution_mode=self.execution_mode,
                    requires_confirmation=True
                )
            
            # 检查确认是否超时
            if clock_now() > pending_order['confirmation_deadline']:
                return ExecutionResult(
                    order_id=full_order_id,
                    status=ExecutionStatus.EXPIRED,
                    message="Confirmation deadline expired",
                    execution_mode=self.execution_mode,
                    requires_confirmation=True
                )
            
            # 计算执行延迟和费用
            execution_delay = int(
                (clock_now() - pending_order['submitted_at']).total_seconds()
            )
            fees = self._calculate_manual_fees(actual_price, actual_volume)
            
            # 创建确认结果
            result = ExecutionResult(
                order_id=full_order_id,
                status=ExecutionStatus.FILLED,
                broker_order_id=f"MANUAL_{full_order_id[:8]}",
                filled_quantity=float(actual_volume),
                filled_price=actual_price,
                remaining_quantity=0.0,
                average_price=actual_price,
                fees=fees,
                message=f"Manual confirmation completed: {notes}",
                execution_mode=self.execution_mode,
                requires_confirmation=True,
                delay_seconds=execution_delay
            )
            
            # 清理等待列表
            del self._pending_orders[full_order_id]
            
            # 更新缓存并触发回调
            self._update_order_status(result)
            
            self._logger.INFO(f"Order {full_order_id} manually confirmed")
            return result
            
        except Exception as e:
            self._logger.ERROR(f"Failed to confirm order {order_id}: {e}")
            return ExecutionResult(
                order_id=order_id,
                status=ExecutionStatus.FAILED,
                message=f"Confirmation error: {str(e)}",
                execution_mode=self.execution_mode,
                requires_confirmation=True
            )
    
    # ============= 通知和超时处理 =============
    async def _send_confirmation_notification(self, order: "Order", deadline: datetime):
        """发送确认通知"""
        try:
            notification_message = self._build_notification_message(order, deadline)
            
            # 控制台通知
            if 'console' in self._notification_channels:
                self._logger.INFO(f"\n{'='*60}")
                self._logger.INFO(f"[MANUAL CONFIRMATION REQUIRED]")
                self._logger.INFO(notification_message)
                self._logger.INFO(f"{'='*60}")
            
            # 其他通知渠道
            if self.notifier:
                for channel in self._notification_channels:
                    if channel != 'console':
                        await self._send_notification_via_channel(
                            channel, notification_message
                        )
                        
            # 标记通知已发送
            if order.uuid in self._pending_orders:
                self._pending_orders[order.uuid]['notification_sent'] = True
                
        except Exception as e:
            self._logger.ERROR(f"Failed to send confirmation notification: {e}")
    
    def _build_notification_message(self, order: "Order", deadline: datetime) -> str:
        """构建确认通知消息"""
        direction_text = "BUY" if order.direction == DIRECTION_TYPES.LONG else "SELL"
        order_type_text = order.order_type.name if hasattr(order, 'order_type') else "MARKET"
        
        message = f"""
🔔 Manual Order Confirmation Required

Order ID: {order.uuid[:8]}
Symbol: {order.code}
Direction: {direction_text}
Volume: {order.volume}
Type: {order_type_text}
"""
        
        if hasattr(order, 'limit_price') and order.limit_price:
            message += f"Limit Price: {order.limit_price}\n"
        
        message += f"""
Deadline: {deadline.strftime('%Y-%m-%d %H:%M:%S')}

Confirm via CLI:
ginkgo confirm {order.uuid[:8]} <actual_price> <actual_volume> [notes]

Example:
ginkgo confirm {order.uuid[:8]} 15.25 1000 "Manual execution completed"
"""
        
        return message
    
    async def _send_notification_via_channel(self, channel: str, message: str):
        """通过指定渠道发送通知"""
        try:
            if channel == 'telegram' and self.notifier:
                await self.notifier.send_telegram_message(message)
            elif channel == 'email' and self.notifier:
                await self.notifier.send_email_message("Manual Order Confirmation", message)
            else:
                self._logger.DEBUG(f"Notification channel '{channel}' not supported or not configured")
                
        except Exception as e:
            self._logger.ERROR(f"Failed to send notification via {channel}: {e}")
    
    async def _monitor_confirmation_timeout(self, order_id: str):
        """监控确认超时"""
        try:
            if order_id not in self._pending_orders:
                return
            
            pending_info = self._pending_orders[order_id]
            deadline = pending_info['confirmation_deadline']
            
            # 等待到超时时间
            wait_seconds = (deadline - clock_now()).total_seconds()
            if wait_seconds > 0:
                await asyncio.sleep(wait_seconds)
            
            # 检查订单是否仍在等待确认
            if order_id in self._pending_orders:
                await self._handle_confirmation_timeout(order_id)
                
        except Exception as e:
            self._logger.ERROR(f"Error monitoring timeout for order {order_id}: {e}")
    
    async def _handle_confirmation_timeout(self, order_id: str):
        """处理确认超时"""
        try:
            if order_id not in self._pending_orders:
                return
            
            pending_info = self._pending_orders[order_id]
            del self._pending_orders[order_id]
            
            if self._auto_cancel_on_timeout:
                status = ExecutionStatus.CANCELED
                message = "Auto-cancelled due to confirmation timeout"
            else:
                status = ExecutionStatus.EXPIRED
                message = "Confirmation deadline expired"
            
            result = ExecutionResult(
                order_id=order_id,
                status=status,
                message=message,
                execution_mode=self.execution_mode,
                requires_confirmation=True,
                delay_seconds=int(
                    (clock_now() - pending_info['submitted_at']).total_seconds()
                )
            )
            
            self._update_order_status(result)
            
            self._logger.WARN(f"Order {order_id} confirmation timeout: {message}")
            
        except Exception as e:
            self._logger.ERROR(f"Failed to handle timeout for order {order_id}: {e}")
    
    async def _cancel_pending_orders(self, reason: str):
        """取消所有等待确认的订单"""
        pending_order_ids = list(self._pending_orders.keys())
        
        for order_id in pending_order_ids:
            try:
                del self._pending_orders[order_id]
                
                result = ExecutionResult(
                    order_id=order_id,
                    status=ExecutionStatus.CANCELED,
                    message=reason,
                    execution_mode=self.execution_mode,
                    requires_confirmation=True
                )
                
                self._update_order_status(result)
                
            except Exception as e:
                self._logger.ERROR(f"Failed to cancel pending order {order_id}: {e}")
    
    async def _test_notification_system(self):
        """测试通知系统"""
        try:
            test_message = "ManualBroker notification system test"
            for channel in self._notification_channels:
                if channel == 'console':
                    self._logger.INFO(f"✓ Console notification channel ready")
                else:
                    await self._send_notification_via_channel(channel, test_message)
                    self._logger.INFO(f"✓ {channel.title()} notification channel tested")
                    
        except Exception as e:
            self._logger.WARN(f"Notification system test failed: {e}")
    
    def _calculate_manual_fees(self, price: float, volume: int) -> float:
        """计算人工确认的手续费（简化版）"""
        transaction_amount = price * volume
        fee_rate = 0.0003  # 0.03%
        min_fee = 5.0
        return max(transaction_amount * fee_rate, min_fee)
    
    # ============= 状态查询接口 =============
    def get_pending_orders(self) -> List[Dict[str, Any]]:
        """获取所有等待确认的订单"""
        pending_list = []
        for order_id, pending_info in self._pending_orders.items():
            pending_list.append({
                'order_id': order_id,
                'short_id': order_id[:8],
                'order': pending_info['order'],
                'submitted_at': pending_info['submitted_at'],
                'deadline': pending_info['confirmation_deadline'],
                'time_remaining': max(0, int(
                    (pending_info['confirmation_deadline'] - clock_now()).total_seconds()
                )),
                'notification_sent': pending_info['notification_sent']
            })
        return pending_list
    
    def get_pending_count(self) -> int:
        """获取等待确认订单数量"""
        return len(self._pending_orders)
