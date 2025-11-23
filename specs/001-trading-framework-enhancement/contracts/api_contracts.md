# API Contracts: Trading Framework Enhancement

**Branch**: `001-trading-framework-enhancement` | **Date**: 2025-01-17
**Purpose**: Define API contracts for enhanced framework components

## 核心接口合约

### 1. 策略接口合约 (IStrategy)

```python
from typing import Protocol, Dict, Any, List, Optional
from abc import ABC, abstractmethod
from dataclasses import dataclass

class IStrategy(Protocol):
    """交易策略接口协议"""

    def cal(self, portfolio_info: Dict[str, Any], event: Any) -> List[Signal]:
        """
        计算交易信号

        Args:
            portfolio_info: 投资组合信息，包含持仓、资金等
            event: 市场事件，如价格更新等

        Returns:
            List[Signal]: 交易信号列表

        Raises:
            ValueError: 参数无效时抛出
            RuntimeError: 计算错误时抛出
        """
        ...

    def on_data_updated(self, symbols: List[str]) -> None:
        """
        数据更新回调

        Args:
            symbols: 更新的标的列表

        Note:
            此方法用于策略在数据更新时进行预处理
        """
        ...

    def get_strategy_info(self) -> Dict[str, Any]:
        """
        获取策略信息

        Returns:
            Dict[str, Any]: 策略元信息，包括名称、参数、性能指标等
        """
        ...

    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """
        验证参数有效性

        Args:
            params: 待验证的参数字典

        Returns:
            bool: 参数是否有效

        Raises:
            ValueError: 参数格式或范围错误时抛出
        """
        ...

    def initialize(self, context: Dict[str, Any]) -> None:
        """
        初始化策略

        Args:
            context: 初始化上下文，包含数据源、时间范围等
        """
        ...

    def finalize(self) -> Dict[str, Any]:
        """
        策略结束清理

        Returns:
            Dict[str, Any]: 策略执行结果和统计信息
        """
        ...
```

### 2. 风险管理接口合约 (IRiskManagement)

```python
class IRiskManagement(Protocol):
    """风险管理接口协议"""

    def validate_order(self, portfolio_info: Dict[str, Any], order: Order) -> Order:
        """
        验证并调整订单

        Args:
            portfolio_info: 投资组合信息
            order: 原始订单

        Returns:
            Order: 调整后的订单（可能调整数量、价格等）

        Note:
            被动风控机制，在订单生成时进行拦截调整
        """
        ...

    def generate_risk_signals(self, portfolio_info: Dict[str, Any], event: Any) -> List[Signal]:
        """
        生成风控信号

        Args:
            portfolio_info: 投资组合信息
            event: 触发事件

        Returns:
            List[Signal]: 风控信号，如止损、止盈等

        Note:
            主动风控机制，根据市场情况主动发出风控信号
        """
        ...

    def check_risk_limits(self, portfolio_info: Dict[str, Any]) -> List[RiskAlert]:
        """
        检查风险限制

        Args:
            portfolio_info: 投资组合信息

        Returns:
            List[RiskAlert]: 风险警报列表
        """
        ...

    def update_risk_parameters(self, parameters: Dict[str, float]) -> None:
        """
        更新风控参数

        Args:
            parameters: 新的风控参数

        Raises:
            ValueError: 参数无效时抛出
        """
        ...

    def get_risk_metrics(self, portfolio_info: Dict[str, Any]) -> Dict[str, float]:
        """
        获取风险指标

        Args:
            portfolio_info: 投资组合信息

        Returns:
            Dict[str, float]: 风险指标，如VaR、最大回撤等
        """
        ...
```

### 3. 投资组合接口合约 (IPortfolio)

```python
class IPortfolio(Protocol):
    """投资组合接口协议"""

    def add_strategy(self, strategy: IStrategy) -> None:
        """
        添加策略

        Args:
            strategy: 策略实例

        Raises:
            ValueError: 策略无效时抛出
        """
        ...

    def remove_strategy(self, strategy_id: str) -> None:
        """
        移除策略

        Args:
            strategy_id: 策略ID
        """
        ...

    def process_signals(self, signals: List[Signal]) -> List[Order]:
        """
        处理交易信号

        Args:
            signals: 交易信号列表

        Returns:
            List[Order]: 生成的订单列表
        """
        ...

    def update_position(self, symbol: str, quantity: float, price: float) -> None:
        """
        更新持仓

        Args:
            symbol: 标的代码
            quantity: 数量变化（正数为买入，负数为卖出）
            price: 成交价格
        """
        ...

    def get_portfolio_info(self) -> Dict[str, Any]:
        """
        获取投资组合信息

        Returns:
            Dict[str, Any]: 包含持仓、资金、指标等信息
        """
        ...

    def add_risk_manager(self, risk_manager: IRiskManagement) -> None:
        """
        添加风险管理器

        Args:
            risk_manager: 风险管理器实例
        """
        ...

    def get_position(self, symbol: str) -> Optional[Position]:
        """
        获取指定标的的持仓

        Args:
            symbol: 标的代码

        Returns:
            Optional[Position]: 持仓信息，无持仓时返回None
        """
        ...

    def get_total_value(self) -> float:
        """
        获取投资组合总价值

        Returns:
            float: 总价值
        """
        ...

    def get_available_cash(self) -> float:
        """
        获取可用资金

        Returns:
            float: 可用资金
        """
        ...
```

### 4. 回测引擎接口合约 (IBacktestEngine)

```python
class IBacktestEngine(Protocol):
    """回测引擎接口协议"""

    def initialize(self, config: EngineConfig, portfolio: IPortfolio) -> None:
        """
        初始化引擎

        Args:
            config: 引擎配置
            portfolio: 投资组合实例

        Raises:
            ValueError: 配置无效时抛出
            RuntimeError: 初始化失败时抛出
        """
        ...

    def run_backtest(self) -> BacktestResult:
        """
        运行回测

        Returns:
            BacktestResult: 回测结果

        Raises:
            RuntimeError: 回测执行失败时抛出
        """
        ...

    def add_data_source(self, data_source: IMarketData) -> None:
        """
        添加数据源

        Args:
            data_source: 市场数据源
        """
        ...

    def get_progress(self) -> float:
        """
        获取回测进度

        Returns:
            float: 进度比例，0.0-1.0
        """
        ...

    def pause(self) -> None:
        """暂停回测"""
        ...

    def resume(self) -> None:
        """恢复回测"""
        ...

    def stop(self) -> None:
        """停止回测"""
        ...

    def get_engine_statistics(self) -> Dict[str, Any]:
        """
        获取引擎统计信息

        Returns:
            Dict[str, Any]: 包含事件处理、性能等统计
        """
        ...
```

## 数据模型合约

### 1. 信号模型 (Signal)

```python
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

class SignalDirection(Enum):
    LONG = "long"
    SHORT = "short"
    CLOSE = "close"

@dataclass
class Signal:
    """交易信号"""
    signal_id: str
    symbol: str
    direction: SignalDirection
    quantity: Optional[float] = None
    price: Optional[float] = None
    strategy_id: str
    timestamp: datetime
    reason: Optional[str] = None
    confidence: float = 1.0  # 信号置信度 0-1
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def is_valid(self) -> bool:
        """验证信号有效性"""
        return (
            self.signal_id and
            self.symbol and
            self.strategy_id and
            0 <= self.confidence <= 1
        )
```

### 2. 订单模型 (Order)

```python
class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"

@dataclass
class Order:
    """订单"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    created_time: datetime = None
    updated_time: datetime = None
    strategy_id: Optional[str] = None
    parent_signal_id: Optional[str] = None

    def fill(self, quantity: float, price: float) -> None:
        """填充订单"""
        self.filled_quantity += quantity
        if self.filled_quantity > 0:
            self.avg_fill_price = (
                (self.avg_fill_price * (self.filled_quantity - quantity) + price * quantity) /
                self.filled_quantity
            )

        if self.filled_quantity >= self.quantity:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIAL_FILLED

    def cancel(self) -> None:
        """取消订单"""
        if self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
            self.status = OrderStatus.CANCELED

    def is_complete(self) -> bool:
        """检查订单是否完全成交"""
        return self.status == OrderStatus.FILLED
```

### 3. 持仓模型 (Position)

```python
@dataclass
class Position:
    """持仓"""
    symbol: str
    quantity: float
    avg_price: float
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    last_updated: datetime = None

    def update_price(self, new_price: float) -> None:
        """更新价格"""
        self.current_price = new_price
        self.market_value = abs(self.quantity) * new_price
        self.unrealized_pnl = self.calculate_unrealized_pnl()
        self.last_updated = datetime.now()

    def calculate_unrealized_pnl(self) -> float:
        """计算未实现盈亏"""
        if self.quantity == 0:
            return 0.0

        if self.quantity > 0:  # 多头持仓
            return (self.current_price - self.avg_price) * self.quantity
        else:  # 空头持仓
            return (self.avg_price - self.current_price) * abs(self.quantity)

    def get_pnl_ratio(self) -> float:
        """获取盈亏比例"""
        if self.avg_price == 0 or self.quantity == 0:
            return 0.0
        return self.unrealized_pnl / (abs(self.quantity) * self.avg_price)
```

## 事件合约

### 1. 事件基类合约

```python
class EventBase(ABC):
    """事件基类"""

    def __init__(self, name: str):
        self.name = name
        self.timestamp: datetime = datetime.now()
        self.correlation_id: Optional[str] = None
        self.causation_id: Optional[str] = None
        self.session_id: Optional[str] = None

    @abstractmethod
    def get_event_type(self) -> str:
        """获取事件类型"""
        pass

    @abstractmethod
    def get_data(self) -> Dict[str, Any]:
        """获取事件数据"""
        pass

    def set_correlation_id(self, correlation_id: str) -> None:
        """设置关联ID"""
        self.correlation_id = correlation_id

    def set_causation_id(self, causation_id: str) -> None:
        """设置因果ID"""
        self.causation_id = causation_id
```

### 2. 价格更新事件合约

```python
@dataclass
class EventPriceUpdate(EventBase):
    """价格更新事件"""
    symbol: str
    price: float
    volume: float = 0.0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        super().__init__(f"PriceUpdate_{self.symbol}")

    def get_event_type(self) -> str:
        return "price_update"

    def get_data(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "price": self.price,
            "volume": self.volume,
            "timestamp": self.timestamp.isoformat()
        }
```

## 配置合约

### 1. 引擎配置模型

```python
from pydantic import BaseModel, validator, Field

class EngineConfig(BaseModel):
    """引擎配置"""
    engine_id: str = Field(..., description="引擎唯一标识")
    mode: str = Field(default="backtest", regex="^(backtest|live|paper)$")
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(gt=0, description="初始资金")
    commission_rate: float = Field(default=0.001, ge=0, description="手续费率")
    slippage_rate: float = Field(default=0.001, ge=0, description="滑点率")
    benchmark: Optional[str] = None

    @validator('end_date')
    def end_date_after_start_date(cls, v, values):
        if 'start_date' in v and v <= values['start_date']:
            raise ValueError('结束日期必须晚于开始日期')
        return v
```

### 2. 策略配置模型

```python
class StrategyConfig(BaseModel):
    """策略配置"""
    strategy_id: str = Field(..., description="策略唯一标识")
    name: str = Field(..., description="策略名称")
    strategy_type: str = Field(..., description="策略类型")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="策略参数")
    risk_limits: Dict[str, float] = Field(default_factory=dict, description="风险限制")
    enabled: bool = Field(default=True, description="是否启用")

    @validator('parameters')
    def validate_parameters(cls, v, values):
        strategy_type = values.get('strategy_type')
        if strategy_type == 'trend_following':
            required_params = ['lookback_period', 'threshold']
            for param in required_params:
                if param not in v:
                    raise ValueError(f'趋势跟踪策略缺少必需参数: {param}')
        return v
```

## 错误处理合约

### 1. 异常类型定义

```python
class TradingFrameworkError(Exception):
    """框架基础异常"""
    pass

class StrategyError(TradingFrameworkError):
    """策略相关异常"""
    pass

class PortfolioError(TradingFrameworkError):
    """投资组合相关异常"""
    pass

class RiskManagementError(TradingFrameworkError):
    """风险管理相关异常"""
    pass

class EngineError(TradingFrameworkError):
    """引擎相关异常"""
    pass

class DataError(TradingFrameworkError):
    """数据相关异常"""
    pass
```

### 2. 错误响应格式

```python
@dataclass
class ErrorResponse:
    """错误响应"""
    error_code: str
    error_message: str
    error_type: str
    timestamp: datetime
    context: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.error_code,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context or {}
        }
```

## 验证合约

### 1. 参数验证器

```python
from typing import Any, Dict, List
import re

class ParameterValidator:
    """参数验证器"""

    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """验证标的代码格式"""
        pattern = r'^[0-9A-Z.]+$'
        return bool(re.match(pattern, symbol))

    @staticmethod
    def validate_quantity(quantity: float) -> bool:
        """验证数量"""
        return quantity > 0 and quantity == round(quantity, 4)  # 精度限制

    @staticmethod
    def validate_price(price: float) -> bool:
        """验证价格"""
        return price > 0 and price == round(price, 4)  # 精度限制

    @staticmethod
    def validate_strategy_parameters(strategy_type: str, params: Dict[str, Any]) -> bool:
        """验证策略参数"""
        validators = {
            'trend_following': ParameterValidator._validate_trend_following_params,
            'mean_reversion': ParameterValidator._validate_mean_reversion_params,
            'arbitrage': ParameterValidator._validate_arbitrage_params
        }

        validator = validators.get(strategy_type)
        if validator:
            return validator(params)
        return True  # 未知策略类型，跳过验证

    @staticmethod
    def _validate_trend_following_params(params: Dict[str, Any]) -> bool:
        """验证趋势跟踪策略参数"""
        required = ['lookback_period', 'threshold']
        for param in required:
            if param not in params:
                return False

        if not (5 <= params['lookback_period'] <= 200):
            return False

        if not (0.01 <= params['threshold'] <= 0.20):
            return False

        return True
```

这些API合约定义了Ginkgo量化交易框架的核心接口和数据模型，为TDD开发和系统集成提供了明确的契约规范。