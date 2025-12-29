# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Interfaces经纪商继承BaseBroker提供BrokerInterfaces交易模拟支持相关功能






"""
交易代理接口定义

提供统一的交易代理接口抽象，支持：
- 模拟交易 (Simulation) 
- 纸面交易 (Paper Trading)
- 实盘交易 (Live Trading)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from ginkgo.trading.time.clock import now as clock_now
from decimal import Decimal
from enum import Enum, IntEnum
from typing import Dict, List, Optional, Union, Any, Callable
from uuid import UUID, uuid4

from ginkgo.libs import GLOG

# 为了匹配实际Broker实现，需要导入entities.Order和ExecutionResult
# 注意：这里采用TYPE_CHECKING避免循环导入
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ginkgo.trading.entities.order import Order


class BrokerType(Enum):
    """交易代理类型"""
    SIM = "simulation"          # 模拟交易
    PAPER = "paper"            # 纸面交易  
    LIVE = "live"              # 实盘交易
    MANUAL = "manual"          # 人工确认交易


class OrderType(Enum):
    """订单类型"""
    MARKET = "market"          # 市价单
    LIMIT = "limit"            # 限价单
    STOP = "stop"              # 止损单
    STOP_LIMIT = "stop_limit"  # 止损限价单
    TRAILING_STOP = "trailing_stop"  # 跟踪止损单


class OrderSide(Enum):
    """订单方向"""
    BUY = "buy"               # 买入
    SELL = "sell"             # 卖出
    SHORT = "short"           # 卖空
    COVER = "cover"           # 平仓


class OrderStatus(IntEnum):
    """订单状态"""
    PENDING = 0               # 待处理
    SUBMITTED = 1             # 已提交
    ACCEPTED = 2              # 已接受
    PARTIALLY_FILLED = 3      # 部分成交
    FILLED = 4                # 完全成交
    CANCELLED = 5             # 已取消
    REJECTED = 6              # 已拒绝
    EXPIRED = 7               # 已过期


class PositionSide(Enum):
    """持仓方向"""
    LONG = "long"             # 多头
    SHORT = "short"           # 空头
    FLAT = "flat"             # 平仓


class ManualConfirmationRequired(Exception):
    """人工确认异常"""
    
    def __init__(self, message: str, order_data: Dict[str, Any]):
        self.message = message
        self.order_data = order_data
        super().__init__(message)


@dataclass
class TradingOrder:
    """交易订单数据类"""
    
    # 基本订单信息
    symbol: str                           # 交易标的
    side: OrderSide                       # 订单方向
    order_type: OrderType                 # 订单类型
    quantity: Decimal                     # 数量
    
    # 价格信息
    price: Optional[Decimal] = None       # 限价单价格
    stop_price: Optional[Decimal] = None  # 止损价格
    
    # 订单标识
    order_id: Optional[str] = None        # 订单ID
    client_order_id: str = field(default_factory=lambda: str(uuid4()))  # 客户端订单ID
    
    # 状态信息
    status: OrderStatus = OrderStatus.PENDING  # 订单状态
    filled_quantity: Decimal = Decimal('0')    # 已成交数量
    average_fill_price: Optional[Decimal] = None  # 平均成交价格
    
    # 时间信息
    created_time: datetime = field(default_factory=datetime.now)  # 创建时间
    updated_time: Optional[datetime] = None    # 更新时间
    
    # 扩展信息
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展元数据
    
    @property
    def remaining_quantity(self) -> Decimal:
        """剩余数量"""
        return self.quantity - self.filled_quantity
    
    @property  
    def is_filled(self) -> bool:
        """是否完全成交"""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_active(self) -> bool:
        """是否为活跃订单"""
        return self.status in {OrderStatus.PENDING, OrderStatus.SUBMITTED, 
                              OrderStatus.ACCEPTED, OrderStatus.PARTIALLY_FILLED}


@dataclass
class BrokerPosition:
    """Broker持仓数据类（避免与entities.Position冲突）"""
    
    # 基本持仓信息
    symbol: str                           # 交易标的
    side: PositionSide                    # 持仓方向
    quantity: Decimal                     # 持仓数量
    average_price: Decimal                # 平均成本价
    
    # 市值信息
    current_price: Optional[Decimal] = None   # 当前价格
    market_value: Optional[Decimal] = None    # 市值
    
    # 盈亏信息
    unrealized_pnl: Optional[Decimal] = None  # 未实现盈亏
    realized_pnl: Decimal = Decimal('0')      # 已实现盈亏
    
    # 时间信息
    opened_time: datetime = field(default_factory=datetime.now)  # 开仓时间
    updated_time: Optional[datetime] = None    # 更新时间
    
    # 扩展信息
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展元数据
    
    @property
    def total_cost(self) -> Decimal:
        """总成本"""
        return self.quantity * self.average_price
    
    @property
    def pnl_percentage(self) -> Optional[Decimal]:
        """盈亏百分比"""
        if self.current_price is None:
            return None
        return (self.current_price - self.average_price) / self.average_price * 100


@dataclass  
class BrokerTrade:
    """Broker交易成交数据类（避免与其他Trade类冲突）"""
    
    # 基本成交信息
    symbol: str                           # 交易标的
    side: OrderSide                       # 交易方向
    quantity: Decimal                     # 成交数量
    price: Decimal                        # 成交价格
    
    # 标识信息
    trade_id: str = field(default_factory=lambda: str(uuid4()))  # 成交ID
    order_id: Optional[str] = None        # 关联订单ID
    
    # 费用信息
    commission: Decimal = Decimal('0')     # 佣金
    fees: Decimal = Decimal('0')          # 其他费用
    
    # 时间信息
    execution_time: datetime = field(default_factory=datetime.now)  # 成交时间
    
    # 扩展信息
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展元数据
    
    @property
    def total_amount(self) -> Decimal:
        """成交总额"""
        return self.quantity * self.price
    
    @property
    def net_amount(self) -> Decimal:
        """净成交额(扣除费用)"""
        return self.total_amount - self.commission - self.fees


@dataclass
class AccountBalance:
    """账户余额数据类"""
    
    # 资金信息
    total_equity: Decimal                 # 总权益
    available_cash: Decimal               # 可用资金
    used_margin: Decimal                  # 已用保证金
    free_margin: Decimal                  # 可用保证金
    
    # 盈亏信息
    unrealized_pnl: Decimal = Decimal('0')  # 未实现盈亏
    realized_pnl: Decimal = Decimal('0')    # 已实现盈亏
    
    # 时间信息
    updated_time: datetime = field(default_factory=datetime.now)  # 更新时间
    
    # 扩展信息
    metadata: Dict[str, Any] = field(default_factory=dict)  # 扩展元数据
    
    @property
    def buying_power(self) -> Decimal:
        """购买力"""
        return self.available_cash + self.free_margin
    
    @property
    def margin_ratio(self) -> Decimal:
        """保证金比率"""
        if self.total_equity == 0:
            return Decimal('0')
        return self.used_margin / self.total_equity


@dataclass
class BrokerStats:
    """代理统计数据类"""
    
    # 基本统计
    total_orders: int = 0                 # 总订单数
    filled_orders: int = 0                # 已成交订单数
    cancelled_orders: int = 0             # 已取消订单数
    rejected_orders: int = 0              # 已拒绝订单数
    
    # 交易统计  
    total_trades: int = 0                 # 总成交数
    total_volume: Decimal = Decimal('0')  # 总成交量
    total_turnover: Decimal = Decimal('0')  # 总成交额
    
    # 费用统计
    total_commission: Decimal = Decimal('0')  # 总佣金
    total_fees: Decimal = Decimal('0')        # 总费用
    
    # 时间统计
    start_time: Optional[datetime] = None     # 开始时间
    last_update: datetime = field(default_factory=datetime.now)  # 最后更新时间
    
    @property
    def fill_rate(self) -> float:
        """成交率"""
        if self.total_orders == 0:
            return 0.0
        return self.filled_orders / self.total_orders
    
    @property
    def average_trade_size(self) -> Decimal:
        """平均成交量"""
        if self.total_trades == 0:
            return Decimal('0')
        return self.total_volume / self.total_trades


class IBroker(ABC):
    """交易代理接口"""
    
    def __init__(self, broker_type: BrokerType):
        """初始化交易代理"""
        self._broker_type = broker_type
        self._is_connected = False
        self._stats = BrokerStats()
        self._order_callbacks: Dict[str, List[Callable]] = {}
        
    @property
    def broker_type(self) -> BrokerType:
        """获取代理类型"""
        return self._broker_type
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._is_connected
    
    @property
    def stats(self) -> BrokerStats:
        """获取统计信息"""
        return self._stats
    
    # === 连接管理 ===
    
    @abstractmethod
    async def connect(self) -> bool:
        """连接到交易系统"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """断开交易系统连接"""
        pass
    
    # === 订单管理 ===
    
    @abstractmethod  
    async def submit_order(self, order: "Order") -> Any:
        """提交订单
        
        Args:
            order: entities.Order订单对象
            
        Returns:
            执行结果，具体类型由实现决定 (通常为ExecutionResult)
        """
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        pass
    
    @abstractmethod
    async def modify_order(self, order_id: str, **modifications) -> Any:
        """修改订单
        
        Returns:
            修改结果，具体类型由实现决定
        """
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str) -> Optional[TradingOrder]:
        """获取订单信息"""
        pass
    
    @abstractmethod
    async def get_orders(self, symbol: Optional[str] = None, 
                        status: Optional[OrderStatus] = None) -> List[TradingOrder]:
        """获取订单列表"""
        pass
    
    # === 持仓管理 ===
    
    @abstractmethod
    async def get_position(self, symbol: str) -> Optional[BrokerPosition]:
        """获取持仓信息"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[BrokerPosition]:
        """获取所有持仓"""
        pass
    
    # === 成交管理 ===
    
    @abstractmethod
    async def get_trades(self, symbol: Optional[str] = None,
                        start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None) -> List[BrokerTrade]:
        """获取成交记录"""
        pass
    
    # === 账户管理 ===
    
    @abstractmethod
    async def get_account_balance(self) -> AccountBalance:
        """获取账户余额"""
        pass
    
    # === 回调管理 ===
    
    def add_order_callback(self, order_id: str, callback: Callable[[TradingOrder], None]):
        """添加订单状态变更回调"""
        if order_id not in self._order_callbacks:
            self._order_callbacks[order_id] = []
        self._order_callbacks[order_id].append(callback)
    
    def remove_order_callback(self, order_id: str, callback: Optional[Callable] = None):
        """移除订单状态变更回调"""
        if order_id in self._order_callbacks:
            if callback is None:
                del self._order_callbacks[order_id]
            else:
                self._order_callbacks[order_id].remove(callback)
    
    def _notify_order_callbacks(self, order: TradingOrder):
        """通知订单状态变更回调"""
        if order.order_id in self._order_callbacks:
            for callback in self._order_callbacks[order.order_id]:
                try:
                    callback(order)
                except Exception as e:
                    GLOG.ERROR(f"订单回调执行失败: {e}")
    
    # === 辅助方法 ===
    
    def _update_stats(self, order: Optional[TradingOrder] = None, 
                     trade: Optional[BrokerTrade] = None):
        """更新统计信息"""
        if order:
            if order.status == OrderStatus.SUBMITTED and order.order_id:
                self._stats.total_orders += 1
            elif order.status == OrderStatus.FILLED:
                self._stats.filled_orders += 1
            elif order.status == OrderStatus.CANCELED:
                self._stats.cancelled_orders += 1
            elif order.status == OrderStatus.REJECTED:
                self._stats.rejected_orders += 1
        
        if trade:
            self._stats.total_trades += 1
            self._stats.total_volume += trade.quantity
            self._stats.total_turnover += trade.total_amount
            self._stats.total_commission += trade.commission
            self._stats.total_fees += trade.fees
        
        self._stats.last_update = clock_now()


# 为向后兼容性提供别名
Position = BrokerPosition
Trade = BrokerTrade
