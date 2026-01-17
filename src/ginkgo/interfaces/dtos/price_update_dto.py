# Upstream: LiveDataFeeder (实时数据源)
# Downstream: DataManager, ExecutionNode (数据消费)
# Role: 实时Tick数据传输对象

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class PriceUpdateDTO(BaseModel):
    """
    实时Tick数据传输对象

    用于从LiveDataFeeder传输实时Tick数据到DataManager，
    再通过Kafka发布到ExecutionNode。
    """

    # 基础字段
    symbol: str = Field(..., description="股票代码")
    timestamp: datetime = Field(default_factory=datetime.now, description="数据时间戳")

    # 价格字段
    price: Optional[float] = Field(None, description="最新价")
    bid_price: Optional[float] = Field(None, description="买一价")
    ask_price: Optional[float] = Field(None, description="卖一价")
    open_price: Optional[float] = Field(None, description="开盘价")
    high_price: Optional[float] = Field(None, description="最高价")
    low_price: Optional[float] = Field(None, description="最低价")

    # 成交量字段
    volume: Optional[float] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    bid_volume: Optional[float] = Field(None, description="买一量")
    ask_volume: Optional[float] = Field(None, description="卖一量")

    # 数据来源
    source: Optional[str] = Field(None, description="数据源标识（eastmoney/fushu/alpaca）")

    @classmethod
    def from_tick(cls, tick_event) -> "PriceUpdateDTO":
        """
        从Tick事件创建DTO

        Args:
            tick_event: EventPriceUpdate事件对象

        Returns:
            PriceUpdateDTO实例
        """
        return cls(
            symbol=tick_event.code,
            timestamp=tick_event.timestamp,
            price=getattr(tick_event, 'price', None),
            bid_price=getattr(tick_event, 'bid_price', None),
            ask_price=getattr(tick_event, 'ask_price', None),
            open_price=getattr(tick_event, 'open_price', None),
            high_price=getattr(tick_event, 'high_price', None),
            low_price=getattr(tick_event, 'low_price', None),
            volume=getattr(tick_event, 'volume', None),
            amount=getattr(tick_event, 'amount', None),
            bid_volume=getattr(tick_event, 'bid_volume', None),
            ask_volume=getattr(tick_event, 'ask_volume', None),
        )

    def to_bar_dict(self) -> dict:
        """
        转换为K线数据字典（用于当日K线推送）

        Returns:
            K线数据字典
        """
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "open": self.open_price or self.price,
            "high": self.high_price or self.price,
            "low": self.low_price or self.price,
            "close": self.price,
            "volume": self.volume or 0,
            "amount": self.amount or 0,
        }
