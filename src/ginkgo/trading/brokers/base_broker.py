"""
交易代理基类实现

提供IBroker接口的基础实现，包括：
- 统一的执行结果/状态类型
- 订单生命周期管理
- 持仓计算逻辑  
- 成交记录管理
- 账户余额计算
- 统计信息收集
"""

import asyncio
from collections import defaultdict, deque
from datetime import datetime, timedelta
from ginkgo.trading.time.clock import now as clock_now
from decimal import Decimal
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Deque, Any, Callable
from uuid import uuid4

from ginkgo.libs import GLOG
from .interfaces import (
    IBroker, BrokerType, OrderType, OrderSide, OrderStatus, PositionSide,
    TradingOrder, BrokerPosition, BrokerTrade, AccountBalance, BrokerStats,
    ManualConfirmationRequired
)


# === 统一执行结果与能力定义（供所有Broker使用） ===
class ExecutionStatus(Enum):
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    FAILED = "failed"
    EXPIRED = "expired"


@dataclass
class BrokerCapabilities:
    execution_type: str = "sync"  # sync/async/manual
    supports_streaming: bool = False
    supports_batch_ops: bool = False
    supports_market_data: bool = False
    supports_positions: bool = False
    max_orders_per_second: int = 1
    max_concurrent_orders: int = 1
    order_timeout_seconds: int = 0
    supported_order_types: List[str] = field(default_factory=lambda: ["MARKET", "LIMIT"])
    supported_time_in_force: List[str] = field(default_factory=lambda: ["DAY"])


@dataclass
class AccountInfo:
    total_asset: float = 0.0
    available_cash: float = 0.0
    frozen_cash: float = 0.0
    market_value: float = 0.0
    total_pnl: float = 0.0


@dataclass
class ExecutionResult:
    order_id: str
    status: ExecutionStatus
    message: str = ""
    broker_order_id: Optional[str] = None
    filled_quantity: Optional[float] = None
    filled_price: Optional[float] = None
    remaining_quantity: Optional[float] = None
    average_price: Optional[float] = None
    fees: Optional[float] = None
    trade_id: Optional[str] = None
    execution_mode: Optional[str] = None
    requires_confirmation: bool = False
    error_code: Optional[str] = None
    cancelled_quantity: Optional[float] = None

    @property
    def is_success(self) -> bool:
        return self.status in {ExecutionStatus.SUBMITTED, ExecutionStatus.FILLED, ExecutionStatus.PARTIALLY_FILLED}

    @property
    def is_final_status(self) -> bool:
        return self.status in {
            ExecutionStatus.FILLED,
            ExecutionStatus.CANCELED,
            ExecutionStatus.REJECTED,
            ExecutionStatus.FAILED,
            ExecutionStatus.EXPIRED,
        }


class BaseBroker(IBroker):
    """交易代理基类"""
    
    def __init__(self, config_or_type: Any, initial_cash: Decimal = Decimal('1000000')):
        """初始化交易代理基类
        
        兼容两种调用：
        - 旧式：传入 BrokerType
        - 新式：传入 config(dict)
        """
        # 解析broker类型
        if isinstance(config_or_type, BrokerType):
            broker_type = config_or_type
            self._config: Dict[str, Any] = {}
        else:
            self._config = dict(config_or_type or {})
            # 根据子类检测到的执行模式映射BrokerType
            try:
                mode = getattr(self, "_detect_execution_mode", lambda: "backtest")()
            except Exception:
                mode = "backtest"
            mapper = {
                "backtest": BrokerType.SIM,
                "simulation": BrokerType.SIM,
                "manual": BrokerType.MANUAL,
                "live": BrokerType.LIVE,
            }
            broker_type = mapper.get(str(mode).lower(), BrokerType.SIM)

        super().__init__(broker_type)
        
        # 基础数据存储
        self._initial_cash = initial_cash
        self._orders: Dict[str, TradingOrder] = {}           # 订单存储
        self._positions: Dict[str, BrokerPosition] = {}      # 持仓存储  
        self._trades: List[BrokerTrade] = []                 # 成交记录
        self._account_balance = AccountBalance(
            total_equity=initial_cash,
            available_cash=initial_cash,
            used_margin=Decimal('0'),
            free_margin=initial_cash
        )
        # 状态回调
        self._status_callback: Optional[Callable[[ExecutionResult], None]] = None
        
        # 订单管理
        self._pending_orders: Set[str] = set()               # 待处理订单
        self._active_orders: Dict[str, TradingOrder] = {}    # 活跃订单
        self._order_history: Deque[TradingOrder] = deque(maxlen=10000)  # 订单历史
        
        # 价格缓存(用于计算未实现盈亏)
        self._current_prices: Dict[str, Decimal] = {}
        # 订单状态缓存（供查询）
        self._order_status_cache: Dict[str, ExecutionResult] = {}
        
        # 初始化能力与执行模式
        try:
            self._caps: BrokerCapabilities = self._init_capabilities()
        except Exception:
            self._caps = BrokerCapabilities()
        try:
            self.execution_mode: str = self._detect_execution_mode()
        except Exception:
            self.execution_mode = 'backtest'

        # 锁对象
        self._order_lock = asyncio.Lock()
        self._position_lock = asyncio.Lock()
        self._trade_lock = asyncio.Lock()

    # === 通用扩展 ===
    def register_status_callback(self, callback: Callable[[ExecutionResult], None]):
        self._status_callback = callback

    def _notify_status(self, result: ExecutionResult):
        if self._status_callback:
            try:
                import inspect, asyncio as _asyncio
                if inspect.iscoroutinefunction(self._status_callback):
                    _asyncio.create_task(self._status_callback(result))
                else:
                    self._status_callback(result)
            except Exception as e:
                GLOG.WARN(f"Status callback error: {e}")

    def _update_order_status(self, result: ExecutionResult):
        if result and result.order_id:
            self._order_status_cache[result.order_id] = result
            self._notify_status(result)

    def get_cached_order_status(self, order_id: str) -> Optional[ExecutionResult]:
        return self._order_status_cache.get(order_id)

    def validate_order(self, order: Any) -> bool:
        """基础订单校验（供路由中心调用）"""
        try:
            if not getattr(order, 'code', None):
                return False
            if getattr(order, 'volume', 0) <= 0:
                return False
            otype = getattr(order, 'order_type', None)
            if otype is not None:
                from ginkgo.enums import ORDER_TYPES
                if otype == ORDER_TYPES.LIMITORDER and not getattr(order, 'limit_price', None):
                    return False
            return True
        except Exception:
            return False
    
    # === 连接管理 ===
    
    async def connect(self) -> bool:
        """连接到交易系统 - 基类默认实现"""
        GLOG.INFO(f"连接{self._broker_type.value}交易代理")
        self._is_connected = True
        return True
    
    async def disconnect(self) -> bool:
        """断开交易系统连接 - 基类默认实现"""
        GLOG.INFO(f"断开{self._broker_type.value}交易代理连接")
        self._is_connected = False
        return True

    # 供SimBroker等接收价格
    def set_market_data(self, code: str, row: Any):
        try:
            price = Decimal(str(row["close"])) if isinstance(row, dict) else Decimal(str(row.close))
            self.update_current_price(code, price)
        except Exception:
            pass
    
    # === 订单管理 ===
    
    async def submit_order(self, order: TradingOrder) -> TradingOrder:
        """提交订单 - 基类通用实现"""
        if not self._is_connected:
            order.status = OrderStatus.REJECTED
            GLOG.WARN(f"交易代理未连接，订单被拒绝: {order.client_order_id}")
            return order
        
        async with self._order_lock:
            # 生成订单ID
            if not order.order_id:
                order.order_id = f"ORDER_{uuid4().hex[:8]}"
            
            # 订单前置检查
            validation_result = await self._validate_order(order)
            if not validation_result:
                order.status = OrderStatus.REJECTED
                GLOG.WARN(f"订单验证失败: {order.client_order_id}")
                self._update_stats(order=order)
                return order
            
            # 更新订单状态
            order.status = OrderStatus.SUBMITTED
            order.updated_time = clock_now()
            
            # 存储订单
            self._orders[order.order_id] = order
            self._active_orders[order.order_id] = order
            
            # 记录统计信息
            self._update_stats(order=order)
            
            GLOG.INFO(f"订单已提交: {order.order_id} - {order.symbol} {order.side.value} {order.quantity}")
            
            # 触发订单处理
            asyncio.create_task(self._process_order(order))
            
            return order
    
    async def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        async with self._order_lock:
            if order_id not in self._orders:
                GLOG.WARN(f"订单不存在: {order_id}")
                return False
            
            order = self._orders[order_id]
            if not order.is_active:
                GLOG.WARN(f"订单无法取消，当前状态: {order.status}")
                return False
            
            # 更新订单状态
            order.status = OrderStatus.CANCELED
            order.updated_time = clock_now()
            
            # 从活跃订单中移除
            if order_id in self._active_orders:
                del self._active_orders[order_id]
            
            # 添加到历史记录
            self._order_history.append(order)
            
            # 更新统计信息
            self._update_stats(order=order)
            
            # 触发回调
            self._notify_order_callbacks(order)
            
            GLOG.INFO(f"订单已取消: {order_id}")
            return True
    
    async def modify_order(self, order_id: str, **modifications) -> TradingOrder:
        """修改订单"""
        async with self._order_lock:
            if order_id not in self._orders:
                raise ValueError(f"订单不存在: {order_id}")
            
            order = self._orders[order_id]
            if not order.is_active:
                raise ValueError(f"订单无法修改，当前状态: {order.status}")
            
            # 应用修改
            for key, value in modifications.items():
                if hasattr(order, key):
                    setattr(order, key, value)
            
            order.updated_time = clock_now()
            
            GLOG.INFO(f"订单已修改: {order_id}")
            return order
    
    async def get_order(self, order_id: str) -> Optional[TradingOrder]:
        """获取订单信息"""
        return self._orders.get(order_id)
    
    async def get_orders(self, symbol: Optional[str] = None, 
                        status: Optional[OrderStatus] = None) -> List[TradingOrder]:
        """获取订单列表"""
        orders = list(self._orders.values())
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        if status:
            orders = [o for o in orders if o.status == status]
        
        # 按创建时间倒序排列
        orders.sort(key=lambda x: x.created_time, reverse=True)
        return orders
    
    # === 持仓管理 ===
    
    async def get_position(self, symbol: str) -> Optional[BrokerPosition]:
        """获取持仓信息"""
        position = self._positions.get(symbol)
        if position:
            # 更新当前价格和未实现盈亏
            await self._update_position_pnl(position)
        return position
    
    async def get_positions(self) -> List[BrokerPosition]:
        """获取所有持仓"""
        positions = list(self._positions.values())
        
        # 更新所有持仓的盈亏信息
        for position in positions:
            await self._update_position_pnl(position)
        
        return positions
    
    # === 成交管理 ===
    
    async def get_trades(self, symbol: Optional[str] = None,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None) -> List[BrokerTrade]:
        """获取成交记录"""
        trades = self._trades.copy()
        
        if symbol:
            trades = [t for t in trades if t.symbol == symbol]
        if start_time:
            trades = [t for t in trades if t.execution_time >= start_time]
        if end_time:
            trades = [t for t in trades if t.execution_time <= end_time]
        
        # 按成交时间倒序排列
        trades.sort(key=lambda x: x.execution_time, reverse=True)
        return trades
    
    # === 账户管理 ===
    
    async def get_account_balance(self) -> AccountBalance:
        """获取账户余额"""
        await self._update_account_balance()
        return self._account_balance

    # === 扩展：统一接口适配 ===
    async def get_account_info(self) -> AccountInfo:
        """获取统一账户信息（默认从本地余额推导）"""
        await self._update_account_balance()
        return AccountInfo(
            total_asset=float(self._account_balance.total_equity),
            available_cash=float(self._account_balance.available_cash),
            frozen_cash=float(self._account_balance.used_margin),
            market_value=float(self._account_balance.total_equity - self._account_balance.available_cash),
            total_pnl=float(self._account_balance.realized_pnl + self._account_balance.unrealized_pnl),
        )

    async def query_order_status(self, order_id: str) -> Optional[ExecutionResult]:
        """查询订单状态（默认从缓存读取）"""
        return self.get_cached_order_status(order_id)

    # === 能力判定 ===
    def requires_manual_confirmation(self) -> bool:
        return (getattr(self, '_caps', None) and self._caps.execution_type == 'manual')

    def supports_immediate_execution(self) -> bool:
        return (getattr(self, '_caps', None) and self._caps.execution_type == 'sync')

    def supports_api_trading(self) -> bool:
        return (getattr(self, '_caps', None) and self._caps.execution_type == 'async')

    # 供子类覆盖
    def _init_capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities()

    def _detect_execution_mode(self) -> str:
        return 'backtest'
    
    # === 内部实现方法 ===
    
    async def _validate_order(self, order: TradingOrder) -> bool:
        """订单验证"""
        # 检查基本参数
        if order.quantity <= 0:
            GLOG.WARN(f"订单数量无效: {order.quantity}")
            return False
        
        # 检查价格参数
        if order.order_type == OrderType.LIMIT and not order.price:
            GLOG.WARN("限价单缺少价格参数")
            return False
        
        if order.order_type in [OrderType.STOP, OrderType.STOP_LIMIT] and not order.stop_price:
            GLOG.WARN("止损单缺少止损价格参数")
            return False
        
        # 检查资金充足性(买单)
        if order.side in [OrderSide.BUY]:
            required_amount = self._calculate_required_amount(order)
            if required_amount > self._account_balance.available_cash:
                GLOG.WARN(f"资金不足: 需要{required_amount}, 可用{self._account_balance.available_cash}")
                return False
        
        # 检查持仓充足性(卖单)  
        if order.side in [OrderSide.SELL, OrderSide.SHORT]:
            position = self._positions.get(order.symbol)
            if not position or position.quantity < order.quantity:
                GLOG.WARN(f"持仓不足: 需要{order.quantity}, 持有{position.quantity if position else 0}")
                return False
        
        return True
    
    def _calculate_required_amount(self, order: TradingOrder) -> Decimal:
        """计算订单所需金额"""
        if order.order_type == OrderType.MARKET:
            # 市价单使用当前价格估算
            current_price = self._current_prices.get(order.symbol, Decimal('100'))
            return order.quantity * current_price
        elif order.order_type == OrderType.LIMIT:
            return order.quantity * order.price
        else:
            # 其他订单类型的保守估算
            current_price = self._current_prices.get(order.symbol, Decimal('100'))
            return order.quantity * current_price
    
    async def _process_order(self, order: TradingOrder):
        """处理订单 - 子类可重写"""
        # 基类默认立即执行订单(模拟场景)
        await asyncio.sleep(0.1)  # 模拟处理延迟
        
        # 生成成交
        fill_price = self._get_fill_price(order)
        await self._fill_order(order, order.quantity, fill_price)
    
    def _get_fill_price(self, order: TradingOrder) -> Decimal:
        """获取成交价格 - 子类可重写"""
        # 基类使用简单的价格模型
        current_price = self._current_prices.get(order.symbol, Decimal('100'))
        
        if order.order_type == OrderType.MARKET:
            return current_price
        elif order.order_type == OrderType.LIMIT:
            return order.price
        else:
            return current_price
    
    async def _fill_order(self, order: TradingOrder, fill_quantity: Decimal, fill_price: Decimal):
        """执行订单成交"""
        async with self._order_lock, self._position_lock, self._trade_lock:
            # 创建成交记录
            trade = BrokerTrade(
                symbol=order.symbol,
                side=order.side,
                quantity=fill_quantity,
                price=fill_price,
                order_id=order.order_id,
                commission=self._calculate_commission(order, fill_quantity, fill_price)
            )
            
            # 更新订单状态
            order.filled_quantity += fill_quantity
            order.average_fill_price = (
                (order.average_fill_price or Decimal('0')) * (order.filled_quantity - fill_quantity) +
                fill_price * fill_quantity
            ) / order.filled_quantity
            order.updated_time = clock_now()
            
            if order.filled_quantity >= order.quantity:
                order.status = OrderStatus.FILLED
                # 从活跃订单中移除
                if order.order_id in self._active_orders:
                    del self._active_orders[order.order_id]
                self._order_history.append(order)
            else:
                order.status = OrderStatus.PARTIALLY_FILLED
            
            # 更新持仓
            await self._update_position(trade)
            
            # 记录成交
            self._trades.append(trade)
            
            # 更新统计信息
            self._update_stats(order=order, trade=trade)
            
            # 触发回调
            self._notify_order_callbacks(order)
            
            GLOG.INFO(f"订单成交: {order.order_id} - {fill_quantity}@{fill_price}")
    
    def _calculate_commission(self, order: TradingOrder, quantity: Decimal, price: Decimal) -> Decimal:
        """计算佣金 - 子类可重写"""
        # 基类使用简单的固定费率模型
        commission_rate = Decimal('0.0003')  # 0.03%
        return quantity * price * commission_rate
    
    async def _update_position(self, trade: BrokerTrade):
        """更新持仓"""
        symbol = trade.symbol
        
        if symbol not in self._positions:
            # 创建新持仓
            side = PositionSide.LONG if trade.side in [OrderSide.BUY] else PositionSide.SHORT
            self._positions[symbol] = BrokerPosition(
                symbol=symbol,
                side=side,
                quantity=trade.quantity,
                average_price=trade.price
            )
        else:
            # 更新现有持仓
            position = self._positions[symbol]
            
            if trade.side in [OrderSide.BUY]:
                # 买入增加持仓
                total_cost = position.total_cost + trade.total_amount
                total_quantity = position.quantity + trade.quantity
                position.average_price = total_cost / total_quantity
                position.quantity = total_quantity
            elif trade.side in [OrderSide.SELL]:
                # 卖出减少持仓
                position.quantity -= trade.quantity
                if position.quantity <= 0:
                    # 持仓清空
                    del self._positions[symbol]
                    return
            
            position.updated_time = clock_now()
    
    async def _update_position_pnl(self, position: BrokerPosition):
        """更新持仓盈亏"""
        current_price = self._current_prices.get(position.symbol)
        if current_price:
            position.current_price = current_price
            position.market_value = position.quantity * current_price
            position.unrealized_pnl = position.market_value - position.total_cost
    
    async def _update_account_balance(self):
        """更新账户余额"""
        # 计算总持仓市值
        total_position_value = Decimal('0')
        total_unrealized_pnl = Decimal('0')
        
        for position in self._positions.values():
            await self._update_position_pnl(position)
            if position.market_value:
                total_position_value += position.market_value
            if position.unrealized_pnl:
                total_unrealized_pnl += position.unrealized_pnl
        
        # 计算已实现盈亏
        total_realized_pnl = sum(
            (trade.total_amount - trade.commission - trade.fees) * 
            (1 if trade.side in [OrderSide.SELL] else -1)
            for trade in self._trades
        )
        
        # 更新账户余额
        self._account_balance.total_equity = self._initial_cash + total_realized_pnl + total_unrealized_pnl
        self._account_balance.unrealized_pnl = total_unrealized_pnl
        self._account_balance.realized_pnl = total_realized_pnl
        self._account_balance.available_cash = self._initial_cash + total_realized_pnl - total_position_value
        self._account_balance.updated_time = clock_now()
    
    def update_current_price(self, symbol: str, price: Decimal):
        """更新当前价格"""
        self._current_prices[symbol] = price
