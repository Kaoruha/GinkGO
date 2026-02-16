# Upstream: ginkgo.enums, ginkgo.data.models
# Downstream: ginkgo.trading.paper.paper_engine, ginkgo.trading.comparison
# Role: Paper Trading 数据模型 - 状态、信号、结果

"""
Paper Trading 数据模型

定义 Paper Trading 相关的数据结构:
- PaperTradingState: Paper Trading 状态
- PaperTradingSignal: Paper Trading 信号
- PaperTradingResult: Paper Trading 结果
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum


class PaperTradingStatus(Enum):
    """Paper Trading 状态枚举"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class PaperTradingState:
    """
    Paper Trading 状态

    记录 Paper Trading 实例的运行状态。

    Attributes:
        portfolio_id: 关联的 Portfolio ID
        paper_id: Paper Trading 实例 ID
        status: 当前状态
        started_at: 启动时间
        current_date: 当前交易日
        total_signals: 总信号数
        total_orders: 总订单数
        last_signal_date: 最后信号日期
        error_message: 错误信息
    """
    portfolio_id: str
    paper_id: str = ""
    status: PaperTradingStatus = PaperTradingStatus.STOPPED
    started_at: Optional[datetime] = None
    current_date: Optional[str] = None
    total_signals: int = 0
    total_orders: int = 0
    last_signal_date: Optional[str] = None
    error_message: Optional[str] = None
    config: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if not self.paper_id:
            import uuid
            self.paper_id = f"paper_{uuid.uuid4().hex[:8]}"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "portfolio_id": self.portfolio_id,
            "paper_id": self.paper_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "current_date": self.current_date,
            "total_signals": self.total_signals,
            "total_orders": self.total_orders,
            "last_signal_date": self.last_signal_date,
            "error_message": self.error_message,
            "config": self.config,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperTradingState":
        """从字典反序列化"""
        if isinstance(data.get("status"), str):
            data["status"] = PaperTradingStatus(data["status"])
        if isinstance(data.get("started_at"), str):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        return cls(**data)


@dataclass
class PaperTradingSignal:
    """
    Paper Trading 信号

    记录 Paper Trading 生成的交易信号。

    Attributes:
        signal_id: 信号 ID
        paper_id: Paper Trading 实例 ID
        date: 信号日期
        code: 股票代码
        direction: 交易方向 (LONG/SHORT)
        order_price: 下单价格 (含滑点)
        original_price: 原始价格 (不含滑点)
        volume: 交易量
        reason: 信号原因
        timestamp: 生成时间戳
    """
    signal_id: str
    paper_id: str
    date: str
    code: str
    direction: str  # DIRECTION_TYPES value
    order_price: Decimal
    original_price: Optional[Decimal] = None
    volume: int = 0
    reason: str = ""
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if not self.signal_id:
            import uuid
            self.signal_id = f"sig_{uuid.uuid4().hex[:8]}"
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if isinstance(self.order_price, (int, float)):
            self.order_price = Decimal(str(self.order_price))
        if self.original_price is not None and isinstance(self.original_price, (int, float)):
            self.original_price = Decimal(str(self.original_price))

    @property
    def slippage(self) -> Optional[Decimal]:
        """计算滑点"""
        if self.original_price is None or self.original_price == 0:
            return None
        return self.order_price - self.original_price

    @property
    def slippage_pct(self) -> Optional[Decimal]:
        """计算滑点百分比"""
        if self.original_price is None or self.original_price == 0:
            return None
        return (self.order_price - self.original_price) / self.original_price

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "signal_id": self.signal_id,
            "paper_id": self.paper_id,
            "date": self.date,
            "code": self.code,
            "direction": self.direction,
            "order_price": str(self.order_price),
            "original_price": str(self.original_price) if self.original_price else None,
            "volume": self.volume,
            "reason": self.reason,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata,
        }


@dataclass
class PaperTradingResult:
    """
    Paper Trading 结果

    用于对比 Paper Trading 与回测结果。

    Attributes:
        paper_id: Paper Trading 实例 ID
        portfolio_id: 关联的 Portfolio ID
        paper_return: Paper Trading 收益率
        backtest_return: 回测收益率
        threshold: 可接受差异阈值 (默认 10%)
    """
    paper_id: str
    portfolio_id: str
    paper_return: Decimal = Decimal("0")
    backtest_return: Decimal = Decimal("0")
    threshold: Decimal = Decimal("0.10")  # 10% 默认阈值
    paper_signals: int = 0
    backtest_signals: int = 0
    matching_signals: int = 0
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.paper_return, (int, float)):
            self.paper_return = Decimal(str(self.paper_return))
        if isinstance(self.backtest_return, (int, float)):
            self.backtest_return = Decimal(str(self.backtest_return))
        if isinstance(self.threshold, (int, float)):
            self.threshold = Decimal(str(self.threshold))

    @property
    def difference(self) -> Decimal:
        """计算收益差异 (Paper - Backtest)"""
        return self.paper_return - self.backtest_return

    @property
    def difference_pct(self) -> Decimal:
        """计算收益差异百分比 (相对于回测收益)"""
        if self.backtest_return == 0:
            if self.paper_return == 0:
                return Decimal("0")
            return Decimal("Infinity") if self.paper_return > 0 else Decimal("-Infinity")
        return self.difference / abs(self.backtest_return)

    @property
    def is_acceptable(self) -> bool:
        """判断差异是否可接受 (在阈值范围内)"""
        return abs(self.difference_pct) <= self.threshold

    @property
    def signal_matching_rate(self) -> Decimal:
        """计算信号匹配率"""
        if self.backtest_signals == 0:
            return Decimal("1.0") if self.paper_signals == 0 else Decimal("0")
        return Decimal(str(self.matching_signals)) / Decimal(str(self.backtest_signals))

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "paper_id": self.paper_id,
            "portfolio_id": self.portfolio_id,
            "paper_return": str(self.paper_return),
            "backtest_return": str(self.backtest_return),
            "difference": str(self.difference),
            "difference_pct": str(self.difference_pct),
            "is_acceptable": self.is_acceptable,
            "threshold": str(self.threshold),
            "paper_signals": self.paper_signals,
            "backtest_signals": self.backtest_signals,
            "matching_signals": self.matching_signals,
            "signal_matching_rate": str(self.signal_matching_rate),
            "start_date": self.start_date,
            "end_date": self.end_date,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperTradingResult":
        """从字典反序列化"""
        decimal_fields = ["paper_return", "backtest_return", "threshold"]
        for field_name in decimal_fields:
            if field_name in data and isinstance(data[field_name], str):
                data[field_name] = Decimal(data[field_name])
        return cls(**data)
