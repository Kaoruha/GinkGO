# Upstream: 实盘账号 API (accounts/{id}/trades*)
# Downstream: BaseService (继承), TradeRecordCRUD (数据访问)
# Role: 成交记录查询服务——列表/统计/日汇总/CSV 导出，Model→前端契约序列化

"""
Trade Record Service

成交记录的业务服务层：
- get_trades: 按账户查询成交列表（日期补全语义：end 含当天 23:59:59）
- get_statistics: 汇总统计（次数/买卖分解/量额费/首末时间）
- get_daily_summary: 按日汇总
- export_csv: CSV 字符串导出

序列化契约对齐前端 TradeHistory 页面（uuid/symbol/side/price:float/
quantity:float/fee/fee_currency/exchange_order_id/exchange_trade_id/
order_type/trade_time:ISO）；DECIMAL(20,8) 列在 service 层 float() 化。
"""

from datetime import datetime
from typing import Optional

from ginkgo.data.services.base_service import BaseService, ServiceResult


def _serialize_trade(trade) -> dict:
    """MTradeRecord → 前端 TradeHistory 契约 dict（Decimal→float，datetime→ISO）"""
    return {
        "uuid": trade.uuid,
        "symbol": trade.symbol,
        "side": trade.side,
        "price": float(trade.price),
        "quantity": float(trade.quantity),
        "quote_quantity": float(trade.quote_quantity) if trade.quote_quantity is not None else None,
        "fee": float(trade.fee) if trade.fee is not None else None,
        "fee_currency": trade.fee_currency,
        "exchange_order_id": trade.exchange_order_id,
        "exchange_trade_id": trade.exchange_trade_id,
        "order_type": trade.order_type,
        "trade_time": trade.trade_time.isoformat() if trade.trade_time else None,
    }


def _parse_date_range(start_date: Optional[str], end_date: Optional[str]):
    """'YYYY-MM-DD' 字符串 → (datetime, datetime)。

    end 补全到当天 23:59:59（否则当天交易被排除，照 backtest logs 端点先例）。
    """
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end_dt = (
        datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S") if end_date else None
    )
    return start_dt, end_dt


class TradeRecordService(BaseService):
    """
    成交记录服务

    提供：
    - get_trades: 按账户+日期区间+标的查询成交列表
    - get_statistics: 账户维度汇总统计
    - get_daily_summary: 按日汇总
    - export_csv: CSV 字符串
    """

    def get_trades(
        self,
        live_account_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 1000,
    ) -> ServiceResult:
        """
        按账户查询成交列表

        Args:
            live_account_id: 实盘账号 uuid
            start_date/end_date: 'YYYY-MM-DD'（end 含当天全天）
            symbol: 过滤交易标的
            limit: 返回上限

        Returns:
            ServiceResult: data 为 list[dict]（前端期望裸数组）
        """
        try:
            start_dt, end_dt = _parse_date_range(start_date, end_date)
            records = self._crud_repo.get_trades_by_account(
                live_account_id=live_account_id,
                start_date=start_dt,
                end_date=end_dt,
                symbol=symbol,
                limit=limit,
            )
            data = [_serialize_trade(r) for r in records]
            return ServiceResult.success(
                data=data,
                message=f"Found {len(data)} trade records",
            )
        except Exception as e:
            return ServiceResult.error(f"Failed to get trades: {str(e)}")

    def get_statistics(
        self,
        live_account_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ServiceResult:
        """
        账户维度汇总统计（次数/买卖分解/量额费/首末时间）
        """
        try:
            start_dt, end_dt = _parse_date_range(start_date, end_date)
            stats = self._crud_repo.get_trade_statistics(
                live_account_id=live_account_id,
                start_date=start_dt,
                end_date=end_dt,
            )
            # CRUD 返回 datetime 的两个时间键转 ISO，其余原样（数值已 float）
            for key in ("first_trade_time", "last_trade_time"):
                if stats.get(key) is not None:
                    stats[key] = stats[key].isoformat()
            return ServiceResult.success(data=stats, message="Trade statistics")
        except Exception as e:
            return ServiceResult.error(f"Failed to get trade statistics: {str(e)}")

    def get_daily_summary(self, live_account_id: str, days: int = 30) -> ServiceResult:
        """
        按日汇总成交（默认近 30 天）
        """
        try:
            summary = self._crud_repo.get_daily_trade_summary(
                live_account_id=live_account_id,
                days=days,
            )
            for day in summary:
                if day.get("date") is not None:
                    day["date"] = day["date"].isoformat()
            return ServiceResult.success(data=summary, message="Daily trade summary")
        except Exception as e:
            return ServiceResult.error(f"Failed to get daily trade summary: {str(e)}")

    def export_csv(
        self,
        live_account_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> ServiceResult:
        """
        导出 CSV 字符串（handler 层负责裸 Response + BOM）
        """
        try:
            start_dt, end_dt = _parse_date_range(start_date, end_date)
            csv_str = self._crud_repo.export_to_csv(
                live_account_id=live_account_id,
                start_date=start_dt,
                end_date=end_dt,
            )
            return ServiceResult.success(data=csv_str, message="Trade records exported")
        except Exception as e:
            return ServiceResult.error(f"Failed to export trades: {str(e)}")
