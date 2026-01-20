# Upstream: BarService (历史K线数据服务)
# Downstream: DataManager, ExecutionNode (数据消费)
# Role: K线数据传输对象

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class BarDTO(BaseModel):
    """
    K线数据传输对象

    用于传输历史K线数据（日K、分钟K等）。
    DataManager从BarService获取当日K线后，封装为BarDTO发布到Kafka。
    """

    # 基础字段
    symbol: str = Field(..., description="股票代码")
    period: str = Field(default="1d", description="K线周期（1m/5m/15m/30m/60m/1d等）")
    timestamp: datetime = Field(..., description="K线时间戳")

    # OHLCV字段
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: float = Field(default=0, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    turnover: Optional[float] = Field(None, description="换手率")

    # 涨跌字段
    change: Optional[float] = Field(None, description="涨跌额")
    change_pct: Optional[float] = Field(None, description="涨跌幅(%)")

    # 数据来源
    source: Optional[str] = Field(None, description="数据来源标识")

    @classmethod
    def from_bar(cls, bar) -> "BarDTO":
        """
        从Bar对象创建DTO

        Args:
            bar: MBar对象或其他K线数据对象

        Returns:
            BarDTO实例
        """
        return cls(
            symbol=bar.code,
            timestamp=bar.timestamp,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            amount=getattr(bar, 'amount', None),
            turnover=getattr(bar, 'turnover', None),
            change=getattr(bar, 'change', None),
            change_pct=getattr(bar, 'change_pct', None),
        )

    def to_price_update(self) -> dict:
        """
        转换为PriceUpdate格式（用于复用Portfolio.on_price_update()）

        Returns:
            PriceUpdate格式字典
        """
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "price": self.close,
            "open_price": self.open,
            "high_price": self.high,
            "low_price": self.low,
            "volume": self.volume,
            "amount": self.amount,
            "source": "bar_snapshot",
        }
