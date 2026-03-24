# Upstream: None (独立实体)
# Downstream: TradeRecordCRUD, LiveTrading API
# Role: MTradeRecord 交易记录模型，存储实盘交易历史数据


from datetime import datetime
from typing import Optional
from sqlalchemy import String, DECIMAL, DateTime, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ginkgo.data.models.model_mysqlbase import MMysqlBase


class MTradeRecord(MMysqlBase):
    """
    交易记录模型

    存储实盘交易的成交记录，用于历史查询和报表分析
    """
    __tablename__ = "trade_records"

    # 主键
    uuid: Mapped[str] = mapped_column(String(32), primary_key=True)

    # 关联信息
    live_account_id: Mapped[str] = mapped_column(String(32), index=True, comment="实盘账号ID")
    broker_instance_id: Mapped[Optional[str]] = mapped_column(String(32), comment="Broker实例ID")
    portfolio_id: Mapped[Optional[str]] = mapped_column(String(32), index=True, comment="Portfolio ID")

    # 交易信息
    exchange: Mapped[str] = mapped_column(String(20), comment="交易所名称")
    exchange_order_id: Mapped[Optional[str]] = mapped_column(String(64), comment="交易所订单ID")
    exchange_trade_id: Mapped[Optional[str]] = mapped_column(String(64), index=True, comment="交易所成交ID")
    symbol: Mapped[str] = mapped_column(String(32), index=True, comment="交易标的")
    side: Mapped[str] = mapped_column(String(10), comment="交易方向: buy/sell")

    # 成交信息
    price: Mapped[float] = mapped_column(DECIMAL(20, 8), comment="成交价格")
    quantity: Mapped[float] = mapped_column(DECIMAL(20, 8), comment="成交数量")
    quote_quantity: Mapped[Optional[float]] = mapped_column(DECIMAL(20, 8), comment="成交金额(计价货币)")
    fee: Mapped[Optional[float]] = mapped_column(DECIMAL(20, 8), comment="手续费")
    fee_currency: Mapped[Optional[str]] = mapped_column(String(20), comment="手续费币种")

    # 订单信息
    order_type: Mapped[Optional[str]] = mapped_column(String(20), comment="订单类型: market/limit/conditional")
    time_in_force: Mapped[Optional[str]] = mapped_column(String(20), comment="订单有效期: GTC/IOC/FOK")

    # 时间信息
    trade_time: Mapped[datetime] = mapped_column(DateTime, index=True, comment="成交时间")
    trade_timestamp: Mapped[Optional[int]] = mapped_column(Integer, comment="成交时间戳(毫秒)")
    create_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="记录创建时间")
    update_time: Mapped[Optional[datetime]] = mapped_column(DateTime, comment="记录更新时间")

    # 策略信息（如果是策略生成）
    strategy_id: Mapped[Optional[str]] = mapped_column(String(32), comment="策略ID")
    signal_id: Mapped[Optional[str]] = mapped_column(String(32), comment="信号ID")

    # 其他信息
    remark: Mapped[Optional[str]] = mapped_column(Text, comment="备注信息")
    is_del: Mapped[bool] = mapped_column(Integer, default=False, comment="是否删除")

    def __repr__(self):
        return (
            f"<MTradeRecord(uuid={self.uuid}, symbol={self.symbol}, "
            f"side={self.side}, price={self.price}, quantity={self.quantity})>"
        )
