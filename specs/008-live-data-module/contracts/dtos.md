# DTO契约定义

**Feature**: 008-live-data-module
**Version**: 1.0.0
**Date**: 2026-01-09

## 一、DTO概述

### 1.1 DTO定义

DTO（Data Transfer Object）是数据传输对象，用于在Kafka Topic之间传递数据。所有DTO基于Pydantic BaseModel，提供类型验证和序列化功能。

### 1.2 DTO列表

| DTO名称 | 用途 | Topic | 方向 |
|---------|------|-------|------|
| InterestUpdateDTO | 订阅更新消息 | ginkgo.live.interest.updates | Portfolio → DataManager/TaskTimer |
| PriceUpdateDTO | 实时Tick数据 | ginkgo.live.market.data | DataManager → ExecutionNode |
| BarDTO | K线数据 | ginkgo.live.market.data | TaskTimer → ExecutionNode |

---

## 二、InterestUpdateDTO

### 2.1 用途

Portfolio通过Kafka发送订阅标的更新到DataManager和TaskTimer。

### 2.2 定义

```python
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class InterestUpdateDTO(BaseModel):
    """
    订阅更新DTO

    用途：Portfolio通过Kafka发送订阅标的更新到DataManager和TaskTimer
    Topic: ginkgo.live.interest.updates
    """

    portfolio_id: str = Field(..., description="Portfolio ID")
    node_id: str = Field(..., description="ExecutionNode ID")
    symbols: List[str] = Field(..., description="订阅标的列表（如['000001.SZ', '600000.SH']）")
    timestamp: datetime = Field(default_factory=datetime.now, description="更新时间戳")

    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": "portfolio_001",
                "node_id": "node_001",
                "symbols": ["000001.SZ", "600000.SH", "00700.HK"],
                "timestamp": "2026-01-09T19:00:00"
            }
        }
```

### 2.3 字段说明

| 字段名 | 类型 | 必需 | 说明 | 示例 |
|-------|------|------|------|------|
| portfolio_id | str | 是 | Portfolio唯一标识 | "portfolio_001" |
| node_id | str | 是 | ExecutionNode唯一标识 | "node_001" |
| symbols | List[str] | 是 | 订阅标的列表 | ["000001.SZ", "600000.SH"] |
| timestamp | datetime | 是 | 更新时间戳（ISO 8601格式） | "2026-01-09T19:00:00" |

### 2.4 Kafka消息格式

**Topic**: `ginkgo.live.interest.updates`

**Key**: `portfolio_id`（用于分区）

**Value** (JSON):
```json
{
  "portfolio_id": "portfolio_001",
  "node_id": "node_001",
  "symbols": ["000001.SZ", "600000.SH", "00700.HK"],
  "timestamp": "2026-01-09T19:00:00"
}
```

---

## 三、PriceUpdateDTO

### 3.1 用途

DataManager将实时Tick数据发布到Kafka，触发ExecutionNode策略计算。

### 3.2 定义

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PriceUpdateDTO(BaseModel):
    """
    实时Tick价格更新DTO（完整版）

    用途：DataManager将Tick数据发布到Kafka，触发ExecutionNode策略计算
    Topic: ginkgo.live.market.data
    """

    # 基础字段
    symbol: str = Field(..., description="标的代码（如'000001.SZ'）")
    price: float = Field(..., description="最新价格")
    volume: int = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")

    # 五档行情
    bid_price: Optional[float] = Field(None, description="买一价")
    ask_price: Optional[float] = Field(None, description="卖一价")
    bid_volume: Optional[int] = Field(None, description="买一量")
    ask_volume: Optional[int] = Field(None, description="卖一量")

    # 当日行情
    open_price: Optional[float] = Field(None, description="开盘价")
    high_price: Optional[float] = Field(None, description="最高价")
    low_price: Optional[float] = Field(None, description="最低价")

    # 时间戳
    timestamp: datetime = Field(..., description="Tick时间戳")

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "000001.SZ",
                "price": 10.50,
                "volume": 10000,
                "amount": 105000.0,
                "bid_price": 10.49,
                "ask_price": 10.51,
                "bid_volume": 5000,
                "ask_volume": 8000,
                "open_price": 10.30,
                "high_price": 10.60,
                "low_price": 10.25,
                "timestamp": "2026-01-09T09:30:00.123456"
            }
        }

    @classmethod
    def from_tick(cls, tick: Tick) -> "PriceUpdateDTO":
        """
        从Tick对象转换为PriceUpdateDTO

        Args:
            tick: Tick对象（来自LiveDataFeeder）

        Returns:
            PriceUpdateDTO实例
        """
        return cls(
            symbol=tick.code,
            price=tick.price,
            volume=tick.volume,
            amount=getattr(tick, 'amount', 0.0),
            bid_price=getattr(tick, 'bid_price', None),
            ask_price=getattr(tick, 'ask_price', None),
            bid_volume=getattr(tick, 'bid_volume', None),
            ask_volume=getattr(tick, 'ask_volume', None),
            open_price=getattr(tick, 'open_price', None),
            high_price=getattr(tick, 'high_price', None),
            low_price=getattr(tick, 'low_price', None),
            timestamp=tick.timestamp
        )
```

### 3.3 字段说明

| 字段名 | 类型 | 必需 | 说明 | 示例 |
|-------|------|------|------|------|
| symbol | str | 是 | 标的代码（如'000001.SZ'） | "000001.SZ" |
| price | float | 是 | 最新价格 | 10.50 |
| volume | int | 是 | 成交量 | 10000 |
| amount | float | 是 | 成交额 | 105000.0 |
| bid_price | float | 否 | 买一价 | 10.49 |
| ask_price | float | 否 | 卖一价 | 10.51 |
| bid_volume | int | 否 | 买一量 | 5000 |
| ask_volume | int | 否 | 卖一量 | 8000 |
| open_price | float | 否 | 开盘价 | 10.30 |
| high_price | float | 否 | 最高价 | 10.60 |
| low_price | float | 否 | 最低价 | 10.25 |
| timestamp | datetime | 是 | Tick时间戳（ISO 8601格式） | "2026-01-09T09:30:00.123456" |

### 3.4 Kafka消息格式

**Topic**: `ginkgo.live.market.data`

**Key**: `symbol`（用于分区）

**Value** (JSON):
```json
{
  "symbol": "000001.SZ",
  "price": 10.50,
  "volume": 10000,
  "amount": 105000.0,
  "bid_price": 10.49,
  "ask_price": 10.51,
  "bid_volume": 5000,
  "ask_volume": 8000,
  "open_price": 10.30,
  "high_price": 10.60,
  "low_price": 10.25,
  "timestamp": "2026-01-09T09:30:00.123456"
}
```

---

## 四、BarDTO

### 4.1 用途

TaskTimer将K线数据发布到Kafka，触发策略分析。

### 4.2 定义

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class BarDTO(BaseModel):
    """
    K线数据DTO（完整版）

    用途：TaskTimer将K线数据发布到Kafka，触发策略分析
    Topic: ginkgo.live.market.data
    """

    # 基础字段
    symbol: str = Field(..., description="标的代码（如'000001.SZ'）")
    period: str = Field(..., description="周期（如'day', '1min', '5min'）")

    # OHLCV
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")

    # 扩展字段
    turnover: Optional[float] = Field(None, description="换手率")
    change: Optional[float] = Field(None, description="涨跌额")
    change_pct: Optional[float] = Field(None, description="涨跌幅(%)")

    # 时间戳
    timestamp: datetime = Field(..., description="K线时间戳")

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "000001.SZ",
                "period": "day",
                "open": 10.30,
                "high": 10.60,
                "low": 10.25,
                "close": 10.50,
                "volume": 1000000,
                "amount": 10500000.0,
                "turnover": 0.5,
                "change": 0.20,
                "change_pct": 1.94,
                "timestamp": "2026-01-09T00:00:00"
            }
        }

    @classmethod
    def from_bar(cls, bar: Bar) -> "BarDTO":
        """
        从Bar对象转换为BarDTO

        Args:
            bar: Bar对象（来自BarService）

        Returns:
            BarDTO实例
        """
        return cls(
            symbol=bar.code,
            period=bar.period,
            open=bar.open_price,
            high=bar.high_price,
            low=bar.low_price,
            close=bar.close_price,
            volume=bar.volume,
            amount=bar.amount,
            turnover=getattr(bar, 'turnover', None),
            change=getattr(bar, 'change', None),
            change_pct=getattr(bar, 'change_pct', None),
            timestamp=bar.timestamp
        )
```

### 4.3 字段说明

| 字段名 | 类型 | 必需 | 说明 | 示例 |
|-------|------|------|------|------|
| symbol | str | 是 | 标的代码（如'000001.SZ'） | "000001.SZ" |
| period | str | 是 | 周期（如'day', '1min', '5min'） | "day" |
| open | float | 是 | 开盘价 | 10.30 |
| high | float | 是 | 最高价 | 10.60 |
| low | float | 是 | 最低价 | 10.25 |
| close | float | 是 | 收盘价 | 10.50 |
| volume | int | 是 | 成交量 | 1000000 |
| amount | float | 是 | 成交额 | 10500000.0 |
| turnover | float | 否 | 换手率 | 0.5 |
| change | float | 否 | 涨跌额 | 0.20 |
| change_pct | float | 否 | 涨跌幅(%) | 1.94 |
| timestamp | datetime | 是 | K线时间戳（ISO 8601格式） | "2026-01-09T00:00:00" |

### 4.4 Kafka消息格式

**Topic**: `ginkgo.live.market.data`

**Key**: `symbol`（用于分区）

**Value** (JSON):
```json
{
  "symbol": "000001.SZ",
  "period": "day",
  "open": 10.30,
  "high": 10.60,
  "low": 10.25,
  "close": 10.50,
  "volume": 1000000,
  "amount": 10500000.0,
  "turnover": 0.5,
  "change": 0.20,
  "change_pct": 1.94,
  "timestamp": "2026-01-09T00:00:00"
}
```

---

## 五、DTO工厂模式

### 5.1 数据源格式转换

**目的**: 不同数据源返回不同格式，需要统一转换为Ginkgo标准DTO。

**实现**: DTO工厂方法，支持从不同数据源格式转换为标准DTO。

```python
class DTOFactory:
    """DTO工厂类"""

    @staticmethod
    def from_eastmoney(data: dict) -> PriceUpdateDTO:
        """从东方财富格式转换为PriceUpdateDTO"""
        return PriceUpdateDTO(
            symbol=data['code'] + ".SZ",
            price=float(data['price']),
            volume=int(data['volume']),
            amount=float(data['amount']),
            timestamp=datetime.fromtimestamp(data['timestamp'])
        )

    @staticmethod
    def from_fushu(data: dict) -> PriceUpdateDTO:
        """从FuShu格式转换为PriceUpdateDTO"""
        return PriceUpdateDTO(
            symbol=data['code'] + ".HK",
            price=float(data['price']),
            volume=int(data['volume']),
            amount=float(data.get('amount', 0)),
            timestamp=datetime.now()
        )

    @staticmethod
    def from_alpaca(data: dict) -> PriceUpdateDTO:
        """从Alpaca格式转换为PriceUpdateDTO"""
        return PriceUpdateDTO(
            symbol=data['symbol'],
            price=float(data['trade']['price']),
            volume=int(data['trade']['size']),
            amount=float(data['trade']['price']) * int(data['trade']['size']),
            timestamp=datetime.fromisoformat(data['timestamp'])
        )
```

---

## 六、版本历史

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| 1.0.0 | 2026-01-09 | 初始版本 |
