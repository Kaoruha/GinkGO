# Upstream: LiveTrading API, Broker
# Downstream: MySQL Database
# Role: TradeRecordCRUD 交易记录数据访问层，处理交易历史的增删改查


from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, desc

from ginkgo.data.models.model_trade_record import MTradeRecord
from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.libs import GLOG


class TradeRecordCRUD(BaseCRUD[MTradeRecord]):
    """
    交易记录CRUD操作

    提供交易记录的增删改查功能，支持：
    - 批量添加交易记录
    - 按账号/交易对/时间范围查询
    - 统计聚合功能
    """

    _model_class = MTradeRecord

    def __init__(self):
        """初始化TradeRecordCRUD"""
        super().__init__(MTradeRecord)

    def add_trade_record(
        self,
        live_account_id: str,
        exchange: str,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        exchange_order_id: Optional[str] = None,
        exchange_trade_id: Optional[str] = None,
        broker_instance_id: Optional[str] = None,
        portfolio_id: Optional[str] = None,
        quote_quantity: Optional[float] = None,
        fee: Optional[float] = None,
        fee_currency: Optional[str] = None,
        order_type: Optional[str] = None,
        trade_time: Optional[datetime] = None,
        strategy_id: Optional[str] = None,
        signal_id: Optional[str] = None,
        remark: Optional[str] = None
    ) -> Optional[MTradeRecord]:
        """
        添加单条交易记录

        Args:
            live_account_id: 实盘账号ID
            exchange: 交易所名称
            symbol: 交易标的
            side: 交易方向 (buy/sell)
            price: 成交价格
            quantity: 成交数量
            exchange_order_id: 交易所订单ID
            exchange_trade_id: 交易所成交ID
            broker_instance_id: Broker实例ID
            portfolio_id: Portfolio ID
            quote_quantity: 成交金额
            fee: 手续费
            fee_currency: 手续费币种
            order_type: 订单类型
            trade_time: 成交时间
            strategy_id: 策略ID
            signal_id: 信号ID
            remark: 备注

        Returns:
            MTradeRecord: 创建的交易记录
        """
        import uuid

        trade_record = MTradeRecord(
            uuid=uuid.uuid4().hex,
            live_account_id=live_account_id,
            broker_instance_id=broker_instance_id,
            portfolio_id=portfolio_id,
            exchange=exchange,
            exchange_order_id=exchange_order_id,
            exchange_trade_id=exchange_trade_id,
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            quote_quantity=quote_quantity,
            fee=fee,
            fee_currency=fee_currency,
            order_type=order_type,
            trade_time=trade_time or datetime.now(),
            strategy_id=strategy_id,
            signal_id=signal_id,
            remark=remark
        )

        return self.add(trade_record)

    def add_trade_records(self, trade_records: List[Dict[str, Any]]) -> int:
        """
        批量添加交易记录

        Args:
            trade_records: 交易记录列表

        Returns:
            int: 成功添加的记录数
        """
        import uuid

        records_to_add = []
        for record_data in trade_records:
            trade_record = MTradeRecord(
                uuid=uuid.uuid4().hex,
                live_account_id=record_data.get("live_account_id"),
                broker_instance_id=record_data.get("broker_instance_id"),
                portfolio_id=record_data.get("portfolio_id"),
                exchange=record_data.get("exchange"),
                exchange_order_id=record_data.get("exchange_order_id"),
                exchange_trade_id=record_data.get("exchange_trade_id"),
                symbol=record_data.get("symbol"),
                side=record_data.get("side"),
                price=record_data.get("price"),
                quantity=record_data.get("quantity"),
                quote_quantity=record_data.get("quote_quantity"),
                fee=record_data.get("fee"),
                fee_currency=record_data.get("fee_currency"),
                order_type=record_data.get("order_type"),
                time_in_force=record_data.get("time_in_force"),
                trade_time=record_data.get("trade_time") or datetime.now(),
                strategy_id=record_data.get("strategy_id"),
                signal_id=record_data.get("signal_id"),
                remark=record_data.get("remark")
            )
            records_to_add.append(trade_record)

        return self.add_batch(records_to_add)

    def get_trades_by_account(
        self,
        live_account_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbol: Optional[str] = None,
        limit: int = 1000
    ) -> List[MTradeRecord]:
        """
        获取指定账号的交易记录

        Args:
            live_account_id: 实盘账号ID
            start_date: 开始日期
            end_date: 结束日期
            symbol: 过滤交易标的
            limit: 返回记录数限制

        Returns:
            List[MTradeRecord]: 交易记录列表
        """
        filters = {
            "live_account_id": live_account_id,
            "is_del": False
        }

        if start_date or end_date:
            date_filter = []
            if start_date:
                date_filter.append(MTradeRecord.trade_time >= start_date)
            if end_date:
                date_filter.append(MTradeRecord.trade_time <= end_date)

        if symbol:
            filters["symbol"] = symbol

        return self.find(
            filters=filters,
            order_by="trade_time",
            desc_order=True,
            limit=limit
        )

    def get_trades_by_portfolio(
        self,
        portfolio_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[MTradeRecord]:
        """
        获取指定Portfolio的交易记录

        Args:
            portfolio_id: Portfolio ID
            start_date: 开始日期
            end_date: 结束日期
            limit: 返回记录数限制

        Returns:
            List[MTradeRecord]: 交易记录列表
        """
        filters = {
            "portfolio_id": portfolio_id,
            "is_del": False
        }

        if start_date or end_date:
            date_filter = []
            if start_date:
                date_filter.append(MTradeRecord.trade_time >= start_date)
            if end_date:
                date_filter.append(MTradeRecord.trade_time <= end_date)

        return self.find(
            filters=filters,
            order_by="trade_time",
            desc_order=True,
            limit=limit
        )

    def get_trade_statistics(
        self,
        live_account_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        获取交易统计数据

        Args:
            live_account_id: 实盘账号ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            Dict: 统计数据
            {
                "total_trades": int,          # 总交易次数
                "buy_trades": int,             # 买入次数
                "sell_trades": int,            # 卖出次数
                "total_quantity": float,       # 总成交量
                "total_value": float,          # 总成交额
                "total_fee": float,            # 总手续费
                "symbols_traded": List[str],   # 交易过的标的
                "first_trade_time": datetime,  # 首笔交易时间
                "last_trade_time": datetime    # 末笔交易时间
            }
        """
        trades = self.get_trades_by_account(
            live_account_id=live_account_id,
            start_date=start_date,
            end_date=end_date,
            limit=100000  # 大量获取用于统计
        )

        if not trades:
            return {
                "total_trades": 0,
                "buy_trades": 0,
                "sell_trades": 0,
                "total_quantity": 0,
                "total_value": 0,
                "total_fee": 0,
                "symbols_traded": [],
                "first_trade_time": None,
                "last_trade_time": None
            }

        buy_trades = [t for t in trades if t.side == "buy"]
        sell_trades = [t for t in trades if t.side == "sell"]

        total_quantity = sum(float(t.quantity) for t in trades)
        total_value = sum(float(t.quote_quantity or 0) for t in trades)
        total_fee = sum(float(t.fee or 0) for t in trades)

        symbols_traded = list(set(t.symbol for t in trades))

        return {
            "total_trades": len(trades),
            "buy_trades": len(buy_trades),
            "sell_trades": len(sell_trades),
            "total_quantity": total_quantity,
            "total_value": total_value,
            "total_fee": total_fee,
            "symbols_traded": symbols_traded,
            "first_trade_time": trades[-1].trade_time,
            "last_trade_time": trades[0].trade_time
        }

    def get_daily_trade_summary(
        self,
        live_account_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        获取每日交易汇总

        Args:
            live_account_id: 实盘账号ID
            days: 查询天数

        Returns:
            List[Dict]: 每日汇总数据
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        trades = self.get_trades_by_account(
            live_account_id=live_account_id,
            start_date=start_date,
            end_date=end_date,
            limit=100000
        )

        # 按日期分组
        daily_summary = {}
        for trade in trades:
            date_key = trade.trade_time.date()

            if date_key not in daily_summary:
                daily_summary[date_key] = {
                    "date": date_key,
                    "total_trades": 0,
                    "buy_trades": 0,
                    "sell_trades": 0,
                    "total_quantity": 0,
                    "total_value": 0,
                    "total_fee": 0
                }

            summary = daily_summary[date_key]
            summary["total_trades"] += 1
            if trade.side == "buy":
                summary["buy_trades"] += 1
            else:
                summary["sell_trades"] += 1
            summary["total_quantity"] += float(trade.quantity)
            summary["total_value"] += float(trade.quote_quantity or 0)
            summary["total_fee"] += float(trade.fee or 0)

        # 转换为列表并排序
        result = list(daily_summary.values())
        result.sort(key=lambda x: x["date"], reverse=True)

        return result

    def export_to_csv(
        self,
        live_account_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> str:
        """
        导出交易记录为CSV格式字符串

        Args:
            live_account_id: 实盘账号ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            str: CSV格式字符串
        """
        import csv
        from io import StringIO

        trades = self.get_trades_by_account(
            live_account_id=live_account_id,
            start_date=start_date,
            end_date=end_date,
            limit=100000
        )

        output = StringIO()
        writer = csv.writer(output)

        # CSV 表头
        headers = [
            "成交时间", "交易对", "方向", "价格", "数量",
            "成交金额", "手续费", "手续费币种", "交易所订单ID",
            "交易所成交ID", "订单类型", "策略ID", "备注"
        ]
        writer.writerow(headers)

        # 数据行
        for trade in trades:
            row = [
                trade.trade_time.strftime("%Y-%m-%d %H:%M:%S"),
                trade.symbol,
                trade.side,
                float(trade.price),
                float(trade.quantity),
                float(trade.quote_quantity or 0),
                float(trade.fee or 0),
                trade.fee_currency or "",
                trade.exchange_order_id or "",
                trade.exchange_trade_id or "",
                trade.order_type or "",
                trade.strategy_id or "",
                trade.remark or ""
            ]
            writer.writerow(row)

        return output.getvalue()
