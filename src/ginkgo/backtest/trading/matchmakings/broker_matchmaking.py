"""
BrokerMatchMaking - 基于Broker的新一代MatchMaking架构

将MatchMaking从具体的撮合逻辑中解耦，通过注入不同的Broker实现
统一的订单处理流程。支持模拟撮合、OKX实盘等多种执行方式。
"""

from typing import Dict, Any, Optional
import pandas as pd

from .base_matchmaking import MatchMakingBase
from ..brokers.base_broker import BaseBroker
from ..brokers.base_broker import ExecutionResult, ExecutionStatus
from ginkgo.backtest.execution.events import EventOrderSubmitted, EventOrderFilled, EventOrderCanceled
from ginkgo.backtest.entities import Order
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
    
    def __init__(self, broker: BaseBroker, *args, **kwargs):
        """
        初始化BrokerMatchMaking
        
        Args:
            broker: 通过DI注入的Broker实例
            *args, **kwargs: 传递给父类的参数
        """
        super().__init__(*args, **kwargs)
        
        self.broker = broker
        self.broker_type = broker.__class__.__name__
        
        # 订单跟踪
        self._pending_orders = {}  # {order_id: Order}
        self._order_results = {}   # {order_id: ExecutionResult}
        
        # 连接Broker
        if not self.broker.connect():
            self.log("ERROR", f"Failed to connect to {self.broker_type} broker")
            raise RuntimeError(f"Broker connection failed")
    
    def __del__(self):
        """析构函数，确保Broker连接正确关闭"""
        if hasattr(self, 'broker') and self.broker:
            self.broker.disconnect()
    
    @property
    def name(self) -> str:
        """获取MatchMaking名称"""
        return f"BrokerMatchMaking({self.broker_type})"
    
    def on_order_received(self, event: EventOrderSubmitted, *args, **kwargs) -> None:
        """
        处理订单提交事件
        
        Args:
            event: 订单提交事件
        """
        order = event.value
        order_id = event.order_id
        
        self.log("DEBUG", f"{self.name} received order {order.code}_{order.direction}")
        
        try:
            # 基础验证
            if not self._validate_order_basic(order):
                self._handle_order_rejected(order, "Order validation failed")
                return
                
            # 业务规则验证
            if not self._validate_order_business(order):
                self._handle_order_rejected(order, "Business validation failed")
                return
            
            # 更新价格缓存（对SimBroker特别重要）
            self._update_broker_price_cache()
            
            # 提交到Broker执行
            execution_result = self.broker.submit_order(order)
            
            # 处理执行结果
            self._handle_execution_result(order, execution_result)
            
        except Exception as e:
            self.log("ERROR", f"Order processing failed: {str(e)}")
            self._handle_order_failed(order, f"Processing error: {str(e)}")
    
    def on_price_received(self, price_data: pd.DataFrame, *args, **kwargs) -> None:
        """
        处理价格更新事件
        
        Args:
            price_data: 价格数据
        """
        self._price_cache = price_data
        self.log("DEBUG", f"Updated price cache with {len(price_data)} records")
        
        # 检查待处理订单是否可以执行
        self._check_pending_orders()
    
    def cancel_order(self, order: Order) -> None:
        """
        撤销订单
        
        Args:
            order: 要撤销的订单
        """
        try:
            result = self.broker.cancel_order(order.uuid)
            
            if result.status == ExecutionStatus.CANCELLED:
                self.log("INFO", f"Order {order.uuid} cancelled successfully")
                self._handle_order_cancelled(order, result.message)
            else:
                self.log("ERROR", f"Failed to cancel order {order.uuid}: {result.message}")
                
        except Exception as e:
            self.log("ERROR", f"Order cancellation failed: {str(e)}")
    
    def get_broker_info(self) -> Dict[str, Any]:
        """
        获取Broker信息
        
        Returns:
            Dict: Broker信息字典
        """
        account_info = self.broker.get_account_info()
        positions = self.broker.get_positions()
        
        return {
            'broker_type': self.broker_type,
            'is_connected': self.broker.is_connected,
            'account_info': {
                'total_asset': account_info.total_asset,
                'available_cash': account_info.available_cash,
                'market_value': account_info.market_value,
                'total_pnl': account_info.total_pnl
            },
            'positions_count': len(positions),
            'positions': [
                {
                    'code': pos.code,
                    'volume': pos.volume,
                    'direction': pos.direction.value,
                    'unrealized_pnl': pos.unrealized_pnl
                }
                for pos in positions
            ]
        }
    
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
        if hasattr(self.broker, 'update_price_cache') and hasattr(self, '_price_cache'):
            if not self._price_cache.empty:
                self.broker.update_price_cache(self._price_cache)
    
    def _handle_execution_result(self, order: Order, result: ExecutionResult) -> None:
        """
        处理订单执行结果
        
        Args:
            order: 原始订单
            result: 执行结果
        """
        self._order_results[order.uuid] = result
        
        if result.status == ExecutionStatus.SUBMITTED:
            # 订单已提交，等待成交
            self._pending_orders[order.uuid] = order
            self.log("INFO", f"Order {order.uuid} submitted successfully")
            
        elif result.status == ExecutionStatus.FILLED:
            # 订单完全成交
            self._handle_order_filled(order, result)
            
        elif result.status == ExecutionStatus.PARTIALLY_FILLED:
            # 订单部分成交
            self._handle_order_partially_filled(order, result)
            
        elif result.status == ExecutionStatus.REJECTED:
            # 订单被拒绝
            self._handle_order_rejected(order, result.message)
            
        elif result.status == ExecutionStatus.FAILED:
            # 订单执行失败
            self._handle_order_failed(order, result.message)
    
    def _handle_order_filled(self, order: Order, result: ExecutionResult) -> None:
        """处理订单完全成交"""
        # 更新订单信息
        order.transaction_price = result.filled_price
        order.transaction_volume = result.filled_volume
        order.fee = result.commission
        order.set_source(SOURCE_TYPES.BROKER)
        order.fill()
        
        # 从待处理订单中移除
        self._pending_orders.pop(order.uuid, None)
        
        # 发送成交事件
        self.put(EventOrderFilled(order))
        
        self.log("INFO", f"Order {order.uuid} filled: {result.filled_volume}@{result.filled_price}")
    
    def _handle_order_partially_filled(self, order: Order, result: ExecutionResult) -> None:
        """处理订单部分成交"""
        # 更新部分成交信息
        order.transaction_price = result.filled_price
        order.transaction_volume = result.filled_volume
        order.fee = result.commission
        
        self.log("INFO", f"Order {order.uuid} partially filled: {result.filled_volume}/{order.volume}")
        
        # 继续等待剩余部分成交
        # 注意：这里可能需要根据具体业务逻辑决定是否拆分订单
    
    def _handle_order_rejected(self, order: Order, message: str) -> None:
        """处理订单被拒绝"""
        order.cancel()
        self._pending_orders.pop(order.uuid, None)
        
        self.log("WARN", f"Order {order.uuid} rejected: {message}")
        # 可以发送订单拒绝事件（如果需要）
    
    def _handle_order_cancelled(self, order: Order, message: str) -> None:
        """处理订单撤销"""
        order.cancel()
        self._pending_orders.pop(order.uuid, None)
        
        # 发送撤销事件
        self.put(EventOrderCanceled(order, message))
        
        self.log("INFO", f"Order {order.uuid} cancelled: {message}")
    
    def _handle_order_failed(self, order: Order, message: str) -> None:
        """处理订单执行失败"""
        order.cancel()
        self._pending_orders.pop(order.uuid, None)
        
        self.log("ERROR", f"Order {order.uuid} failed: {message}")
    
    def _check_pending_orders(self) -> None:
        """检查待处理订单状态（主要用于实盘交易）"""
        if not self._pending_orders:
            return
            
        for order_id, order in list(self._pending_orders.items()):
            try:
                result = self.broker.query_order(order_id)
                
                if result.is_final_status:
                    self._handle_execution_result(order, result)
                    
            except Exception as e:
                self.log("ERROR", f"Failed to check order {order_id} status: {str(e)}")
    
    def log(self, level: str, message: str) -> None:
        """统一的日志接口"""
        getattr(GLOG, level)(f"[{self.name}] {message}")