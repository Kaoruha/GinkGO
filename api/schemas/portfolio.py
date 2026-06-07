"""Portfolio analytics & event timeline schemas."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PortfolioMetrics(BaseModel):
    """All available performance metrics for a portfolio."""
    net_value: Optional[float] = None
    annual_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    win_rate: Optional[float] = None
    signal_count: Optional[int] = None
    total_pnl: Optional[float] = None
    total_trades: Optional[int] = None
    profit_factor: Optional[float] = None
    volatility: Optional[float] = None


class NetValueDataPoint(BaseModel):
    """Single data point in the net value series."""
    time: str
    value: float


class PortfolioAnalyticsResponse(BaseModel):
    """Response for GET /portfolios/{uuid}/analytics."""
    metrics: PortfolioMetrics
    net_value_series: List[NetValueDataPoint] = Field(default_factory=list)


class PortfolioEventItem(BaseModel):
    """Single event in the unified timeline."""
    event_type: str
    timestamp: Optional[str] = None
    symbol: Optional[str] = None
    direction: Optional[str] = None
    # Signal fields
    signal_reason: Optional[str] = None
    signal_volume: Optional[float] = None
    signal_weight: Optional[float] = None
    signal_confidence: Optional[float] = None
    # Order fields
    order_id: Optional[str] = None
    order_type: Optional[str] = None
    limit_price: Optional[str] = None
    # Fill fields
    transaction_price: Optional[str] = None
    transaction_volume: Optional[int] = None
    commission: Optional[str] = None
    slippage: Optional[str] = None
    # Reject/Cancel fields
    reject_code: Optional[str] = None
    reject_reason: Optional[str] = None
    cancel_reason: Optional[str] = None
    # Risk fields
    risk_type: Optional[str] = None
    risk_reason: Optional[str] = None
    risk_limit: Optional[str] = None
    risk_actual_value: Optional[str] = None
    # Raw message as fallback
    message: Optional[str] = None


class PortfolioEventsResponse(BaseModel):
    """Response for GET /portfolios/{uuid}/events."""
    data: List[PortfolioEventItem] = Field(default_factory=list)
    total: int = 0
    limit: int = 50
    offset: int = 0
