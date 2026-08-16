# Issue: 前端 /accounts/{id}/trades* 四端点 404——后端无路由
# Upstream: api.api.accounts.get_account_trades / statistics / daily_summary / export
# Downstream: TradeRecordService（Decimal→float、end 日期补全 23:59:59）
# Role: 端点契约——trades 裸数组无 meta、export 裸 CSV+BOM、归属校验 403

"""
trade history 端点测试

验证：
1. GET trades 返回裸数组信封（data 为 list、无 meta——分页信封会毁前端页面）
2. 日期 query 透传到 service（end 补全 23:59:59）
3. service 序列化：Decimal→float、datetime→ISO
4. export 返回裸 CSV（BOM + text/csv，非信封 dict）
5. 失败路径：service error → BusinessError；非 owner → 403
"""

import asyncio
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest


def run_async(coro):
    return asyncio.run(coro)


def _fake_request(user_uuid="u1"):
    return SimpleNamespace(state=SimpleNamespace(user_uuid=user_uuid))


def _account_service(account_exists=True, owner="u1"):
    svc = MagicMock()
    if account_exists:
        svc.get_account_by_uuid.return_value = {
            "success": True,
            "data": {"user_id": owner},
        }
    else:
        svc.get_account_by_uuid.return_value = {"success": False, "data": None}
    return svc


def _trade(trade_time=datetime(2026, 8, 1, 10, 30, 0)):
    """模拟 MTradeRecord（DECIMAL 列为 Decimal）"""
    return SimpleNamespace(
        uuid="t-1",
        symbol="BTC-USDT",
        side="buy",
        price=Decimal("42000.12345678"),
        quantity=Decimal("0.5"),
        quote_quantity=Decimal("21000.06"),
        fee=Decimal("1.25"),
        fee_currency="USDT",
        exchange_order_id="o-1",
        exchange_trade_id="x-1",
        order_type="market",
        trade_time=trade_time,
    )


class TestGetAccountTrades:
    """GET /accounts/{account_id}/trades"""

    def test_returns_bare_array_envelope(self):
        from api.accounts import get_account_trades

        trade_service = MagicMock()
        trade_service.get_trades.return_value = MagicMock(
            is_success=lambda: True,
            data=[{
                "uuid": "t-1", "symbol": "BTC-USDT", "side": "buy",
                "price": 42000.0, "quantity": 0.5,
            }],
        )

        with patch("api.accounts.get_live_account_service", return_value=_account_service()), \
             patch("api.accounts.get_trade_record_service", return_value=trade_service):
            result = run_async(get_account_trades("acc-1", _fake_request()))

        assert result["code"] == 0
        assert isinstance(result["data"], list)
        assert "meta" not in result  # 裸数组契约：分页信封会触发前端拦截器重组毁页面

    def test_dates_passed_with_end_inclusive(self):
        from api.accounts import get_account_trades

        trade_service = MagicMock()
        trade_service.get_trades.return_value = MagicMock(is_success=lambda: True, data=[])

        with patch("api.accounts.get_live_account_service", return_value=_account_service()), \
             patch("api.accounts.get_trade_record_service", return_value=trade_service):
            run_async(get_account_trades(
                "acc-1", _fake_request(),
                start_date="2026-01-01", end_date="2026-01-31",
            ))

        kwargs = trade_service.get_trades.call_args.kwargs
        assert kwargs["start_date"] == "2026-01-01"
        assert kwargs["end_date"] == "2026-01-31"

    def test_service_error_raises_business_error(self):
        from api.accounts import get_account_trades
        from core.exceptions import BusinessError

        trade_service = MagicMock()
        trade_service.get_trades.return_value = MagicMock(
            is_success=lambda: False, error="db down"
        )

        with patch("api.accounts.get_live_account_service", return_value=_account_service()), \
             patch("api.accounts.get_trade_record_service", return_value=trade_service):
            with pytest.raises(BusinessError):
                run_async(get_account_trades("acc-1", _fake_request()))

    def test_non_owner_gets_403(self):
        from api.accounts import get_account_trades
        from core.exceptions import BusinessError

        trade_service = MagicMock()

        with patch("api.accounts.get_live_account_service", return_value=_account_service(owner="someone-else")), \
             patch("api.accounts.get_trade_record_service", return_value=trade_service):
            with pytest.raises(BusinessError) as exc_info:
                run_async(get_account_trades("acc-1", _fake_request(user_uuid="u1")))

        assert exc_info.value.code == 403
        trade_service.get_trades.assert_not_called()

    def test_missing_account_raises_not_found(self):
        from api.accounts import get_account_trades
        from core.exceptions import NotFoundError

        with patch("api.accounts.get_live_account_service", return_value=_account_service(account_exists=False)):
            with pytest.raises(NotFoundError):
                run_async(get_account_trades("nope", _fake_request()))


class TestExportAccountTrades:
    """GET /accounts/{account_id}/trades/export"""

    def test_returns_raw_csv_with_bom(self):
        from api.accounts import export_account_trades

        trade_service = MagicMock()
        trade_service.export_csv.return_value = MagicMock(
            is_success=lambda: True, data="时间,标的,方向\n2026-08-01,BTC-USDT,buy\n"
        )

        with patch("api.accounts.get_live_account_service", return_value=_account_service()), \
             patch("api.accounts.get_trade_record_service", return_value=trade_service):
            resp = run_async(export_account_trades("acc-12345678", _fake_request()))

        assert not isinstance(resp, dict)  # 不是信封
        assert resp.media_type == "text/csv; charset=utf-8"
        assert resp.body.startswith("﻿".encode("utf-8"))  # BOM
        assert 'filename="trades_acc-1234.csv"' in resp.headers.get("content-disposition", "")


class TestTradeRecordServiceSerialization:
    """TradeRecordService 序列化契约"""

    def _service(self, crud):
        from ginkgo.data.services.trade_record_service import TradeRecordService
        return TradeRecordService(crud_repo=crud)

    def test_get_trades_converts_decimal_and_datetime(self):
        crud = MagicMock()
        crud.get_trades_by_account.return_value = [_trade()]

        result = self._service(crud).get_trades("acc-1")

        assert result.is_success()
        row = result.data[0]
        assert row["price"] == 42000.12345678 and isinstance(row["price"], float)
        assert row["quantity"] == 0.5 and isinstance(row["quantity"], float)
        assert row["fee"] == 1.25
        assert row["trade_time"] == "2026-08-01T10:30:00"

    def test_get_trades_end_date_inclusive(self):
        crud = MagicMock()
        crud.get_trades_by_account.return_value = []

        self._service(crud).get_trades("acc-1", start_date="2026-01-01", end_date="2026-01-31")

        kwargs = crud.get_trades_by_account.call_args.kwargs
        assert kwargs["start_date"] == datetime(2026, 1, 1, 0, 0, 0)
        assert kwargs["end_date"] == datetime(2026, 1, 31, 23, 59, 59)

    def test_statistics_serializes_times(self):
        crud = MagicMock()
        crud.get_trade_statistics.return_value = {
            "total_trades": 2, "buy_trades": 1, "sell_trades": 1,
            "first_trade_time": datetime(2026, 8, 1, 9, 0, 0),
            "last_trade_time": datetime(2026, 8, 2, 9, 0, 0),
        }

        result = self._service(crud).get_statistics("acc-1")

        assert result.data["first_trade_time"] == "2026-08-01T09:00:00"
        assert result.data["last_trade_time"] == "2026-08-02T09:00:00"

    def test_daily_summary_serializes_dates(self):
        crud = MagicMock()
        crud.get_daily_trade_summary.return_value = [{"date": datetime(2026, 8, 1).date(), "total_trades": 3}]

        result = self._service(crud).get_daily_summary("acc-1")

        assert result.data[0]["date"] == "2026-08-01"
