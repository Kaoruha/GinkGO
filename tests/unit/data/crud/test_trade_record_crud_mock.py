"""
TradeRecordCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- Business Helper: get_trades_by_portfolio, get_trade_statistics
- 构造与类型检查

注意：TradeRecordCRUD 无 field_config、enum_mappings、create_from_params，仅测试构造和业务方法。
"""

import pytest
from unittest.mock import MagicMock, patch


# ============================================================
# 辅助：构造 TradeRecordCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def crud_instance():
    """构造 TradeRecordCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.trade_record_crud.GLOG", mock_logger):
        from ginkgo.data.crud.trade_record_crud import TradeRecordCRUD
        crud = TradeRecordCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestTradeRecordCRUDConstruction:
    """TradeRecordCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction(self, crud_instance):
        """验证 model_class 为 MTradeRecord，_is_mysql 为 True"""
        from ginkgo.data.models.model_trade_record import MTradeRecord

        assert crud_instance.model_class is MTradeRecord
        assert crud_instance._is_mysql is True
        assert crud_instance._is_clickhouse is False

    @pytest.mark.unit
    def test_has_required_methods(self, crud_instance):
        """验证 BaseCRUD 的关键 hook 方法都存在且可调用"""
        required_methods = [
            "_do_add", "_do_find", "_do_modify", "_do_remove", "_do_count",
        ]

        for method_name in required_methods:
            assert hasattr(crud_instance, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(crud_instance, method_name)), f"不可调用: {method_name}"


# ============================================================
# Business Helper 测试
# ============================================================


class TestTradeRecordCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_get_trades_by_portfolio(self, crud_instance):
        """get_trades_by_portfolio 构造正确的 filters 并调用 self.find"""
        crud_instance.find = MagicMock(return_value=[])

        result = crud_instance.get_trades_by_portfolio(portfolio_id="portfolio-001")

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert call_kwargs["filters"]["is_del"] is False
        assert call_kwargs["order_by"] == "trade_time"
        assert call_kwargs["desc_order"] is True
        assert result == []

    @pytest.mark.unit
    def test_get_trade_statistics_empty(self, crud_instance):
        """get_trade_statistics 无交易记录时返回空统计"""
        crud_instance.find = MagicMock(return_value=[])

        result = crud_instance.get_trade_statistics(live_account_id="account-001")

        assert result["total_trades"] == 0
        assert result["buy_trades"] == 0
        assert result["sell_trades"] == 0
        assert result["symbols_traded"] == []
        assert result["first_trade_time"] is None

    @pytest.mark.unit
    def test_get_trade_statistics_with_trades(self, crud_instance):
        """get_trade_statistics 有交易记录时正确统计"""
        mock_trade1 = MagicMock()
        mock_trade1.side = "buy"
        mock_trade1.quantity = 10.0
        mock_trade1.quote_quantity = 100.0
        mock_trade1.fee = 0.5
        mock_trade1.symbol = "BTC-USDT"
        mock_trade1.trade_time = MagicMock()

        mock_trade2 = MagicMock()
        mock_trade2.side = "sell"
        mock_trade2.quantity = 5.0
        mock_trade2.quote_quantity = 50.0
        mock_trade2.fee = 0.3
        mock_trade2.symbol = "ETH-USDT"
        mock_trade2.trade_time = MagicMock()

        crud_instance.find = MagicMock(return_value=[mock_trade1, mock_trade2])

        result = crud_instance.get_trade_statistics(live_account_id="account-001")

        assert result["total_trades"] == 2
        assert result["buy_trades"] == 1
        assert result["sell_trades"] == 1
        assert result["total_quantity"] == 15.0
        assert result["total_fee"] == 0.8
        assert set(result["symbols_traded"]) == {"BTC-USDT", "ETH-USDT"}
