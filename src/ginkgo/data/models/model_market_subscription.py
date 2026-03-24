# Upstream: MarketSubscriptionCRUD (订阅CRUD操作)
# Downstream: MySQL Database (market_subscriptions表)
# Role: 市场数据订阅模型 - 存储用户订阅的交易对配置


import uuid
import datetime
from typing import Optional
from sqlalchemy import String, Boolean, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.mysql import TINYINT

from ginkgo.data.models.model_mysqlbase import MMysqlBase


class SubscriptionDataType(str):
    """订阅数据类型枚举"""
    TICKER = "ticker"
    CANDLESTICKS = "candlesticks"
    TRADES = "trades"
    ORDERBOOK = "orderbook"

    @classmethod
    def from_str(cls, value: str) -> str:
        """从字符串转换为枚举值"""
        value = value.lower()
        if value in [cls.TICKER, cls.CANDLESTICKS, cls.TRADES, cls.ORDERBOOK]:
            return value
        raise ValueError(f"Unknown data type: {value}")

    @classmethod
    def validate(cls, value: str) -> bool:
        """验证数据类型是否有效"""
        return value in [cls.TICKER, cls.CANDLESTICKS, cls.TRADES, cls.ORDERBOOK]

    @classmethod
    def all_types(cls) -> list[str]:
        """返回所有数据类型"""
        return [cls.TICKER, cls.CANDLESTICKS, cls.TRADES, cls.ORDERBOOK]


class MMarketSubscription(MMysqlBase):
    """
    市场数据订阅模型

    存储用户订阅的交易对配置和数据类型。
    支持多交易所（OKX、Binance等）。

    Attributes:
        uuid: 订阅唯一标识
        user_id: 所属用户ID
        exchange: 交易所类型 (okx/binance)
        environment: 环境类型 (production/testnet)
        symbol: 交易对代码 (如 BTC-USDT)
        data_types: 订阅的数据类型 (JSON数组: ["ticker", "candlesticks"])
        is_active: 是否激活订阅
        is_del: 软删除标记
        create_at: 创建时间
        update_at: 更新时间
    """
    __tablename__ = "market_subscriptions"

    # 用户关联
    user_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="所属用户ID")

    # 交易所配置
    exchange: Mapped[str] = mapped_column(String(20), nullable=False, comment="交易所类型 (okx/binance)")
    environment: Mapped[str] = mapped_column(String(20), nullable=False, default="testnet", comment="环境 (production/testnet)")

    # 订阅配置
    symbol: Mapped[str] = mapped_column(String(50), nullable=False, index=True, comment="交易对代码")
    data_types: Mapped[str] = mapped_column(Text, nullable=False, default='["ticker"]', comment="订阅数据类型(JSON数组)")

    # 状态
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否激活订阅")

    def __init__(self, **kwargs):
        """初始化MMarketSubscription实例"""
        super().__init__(**kwargs)
        # 处理 data_types 转换为 JSON 字符串
        if 'data_types' in kwargs:
            if isinstance(kwargs['data_types'], list):
                import json
                self.data_types = json.dumps(kwargs['data_types'])
            else:
                self.data_types = kwargs['data_types']

    def get_data_types(self) -> list[str]:
        """
        获取订阅的数据类型列表

        Returns:
            list[str]: 数据类型列表
        """
        try:
            import json
            return json.loads(self.data_types)
        except Exception:
            return [SubscriptionDataType.TICKER]

    def set_data_types(self, data_types: list[str]) -> None:
        """
        设置订阅的数据类型

        Args:
            data_types: 数据类型列表
        """
        import json
        # 验证数据类型
        valid_types = []
        for dt in data_types:
            if SubscriptionDataType.validate(dt):
                valid_types.append(dt)
        self.data_types = json.dumps(valid_types)

    def add_data_type(self, data_type: str) -> None:
        """
        添加数据类型

        Args:
            data_type: 要添加的数据类型
        """
        types_list = self.get_data_types()
        if data_type not in types_list and SubscriptionDataType.validate(data_type):
            types_list.append(data_type)
            self.set_data_types(types_list)

    def remove_data_type(self, data_type: str) -> None:
        """
        移除数据类型

        Args:
            data_type: 要移除的数据类型
        """
        types_list = self.get_data_types()
        if data_type in types_list:
            types_list.remove(data_type)
            self.set_data_types(types_list)

    def has_data_type(self, data_type: str) -> bool:
        """
        检查是否订阅了指定数据类型

        Args:
            data_type: 数据类型

        Returns:
            bool: 是否已订阅
        """
        return data_type in self.get_data_types()

    def to_dict(self) -> dict:
        """
        转换为字典

        Returns:
            dict: 订阅信息字典
        """
        return {
            "uuid": self.uuid,
            "user_id": self.user_id,
            "exchange": self.exchange,
            "environment": self.environment,
            "symbol": self.symbol,
            "data_types": self.get_data_types(),
            "is_active": self.is_active,
            "is_del": self.is_del,
            "create_at": self.create_at.isoformat() if self.create_at else None,
            "update_at": self.update_at.isoformat() if self.update_at else None,
        }

    def __repr__(self) -> str:
        """字符串表示"""
        return f"<MMarketSubscription(uuid={self.uuid}, user_id={self.user_id}, symbol={self.symbol}, exchange={self.exchange})>"
