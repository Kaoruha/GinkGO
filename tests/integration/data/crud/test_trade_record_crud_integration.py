"""
TradeRecordCRUD 集成测试 - 连接真实 MySQL 数据库

覆盖范围：
- 单条/批量添加交易记录
- 按实盘账号ID、组合ID查询
- 每日交易汇总
- 计数、删除操作

测试数据隔离：使用特定 portfolio_id 隔离，测试后自动清理
数据库：MySQL (MTradeRecord 继承 MMysqlBase)
"""

import pytest
from datetime import datetime, timedelta

from ginkgo.data.crud.trade_record_crud import TradeRecordCRUD


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def crud_instance():
    """创建 TradeRecordCRUD 实例"""
    return TradeRecordCRUD()


@pytest.fixture
def cleanup(crud_instance):
    """测试后清理测试数据（使用特定 portfolio_id 隔离）"""
    yield
    try:
        crud_instance.remove(filters={"portfolio_id": "TEST_PORT_TRADE_INTEG"})
    except Exception:
        pass


@pytest.fixture
def sample_trade_params():
    """标准测试交易记录参数"""
    return {
        "live_account_id": "TEST_ACCT_TRADE_INTEG",
        "exchange": "okx",
        "symbol": "BTC-USDT",
        "side": "buy",
        "price": 50000.0,
        "quantity": 0.01,
        "quote_quantity": 500.0,
        "fee": 0.5,
        "fee_currency": "USDT",
        "portfolio_id": "TEST_PORT_TRADE_INTEG",
        "trade_time": datetime(2024, 6, 15, 10, 0, 0),
    }


@pytest.fixture
def sample_trade_batch():
    """批量测试交易记录参数列表"""
    base = datetime(2024, 6, 15, 10, 0, 0)
    symbols = ["BTC-USDT", "ETH-USDT", "BTC-USDT", "ETH-USDT", "SOL-USDT"]
    sides = ["buy", "buy", "sell", "sell", "buy"]
    return [
        {
            "live_account_id": "TEST_ACCT_TRADE_INTEG",
            "exchange": "okx",
            "symbol": symbols[i],
            "side": sides[i],
            "price": 50000.0 + i * 1000,
            "quantity": 0.01 * (i + 1),
            "quote_quantity": (50000.0 + i * 1000) * 0.01 * (i + 1),
            "fee": 0.5 * (i + 1),
            "fee_currency": "USDT",
            "portfolio_id": "TEST_PORT_TRADE_INTEG",
            "trade_time": base + timedelta(hours=i),
        }
        for i in range(5)
    ]


# ============================================================================
# 测试类：添加操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestTradeRecordCRUDAdd:
    """TradeRecordCRUD 添加操作集成测试"""

    def test_add_single_trade(self, crud_instance, cleanup, sample_trade_params):
        """添加单条交易记录，查回验证"""
        record = crud_instance.add_trade_record(**sample_trade_params)

        assert record is not None
        assert record.symbol == "BTC-USDT"
        assert record.side == "buy"
        assert record.portfolio_id == "TEST_PORT_TRADE_INTEG"

        # 查回验证
        results = crud_instance.find(
            filters={"portfolio_id": "TEST_PORT_TRADE_INTEG", "is_del": False}
        )
        assert len(results) >= 1

    def test_add_batch_trades(self, crud_instance, cleanup, sample_trade_batch):
        """批量添加交易记录"""
        count = crud_instance.add_trade_records(sample_trade_batch)
        assert count == 5

        found = crud_instance.find(
            filters={"portfolio_id": "TEST_PORT_TRADE_INTEG", "is_del": False}
        )
        assert len(found) == 5


# ============================================================================
# 测试类：查询操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestTradeRecordCRUDFind:
    """TradeRecordCRUD 查询操作集成测试"""

    def test_find_by_portfolio(self, crud_instance, cleanup, sample_trade_batch):
        """按 Portfolio ID 查询交易记录"""
        crud_instance.add_trade_records(sample_trade_batch)

        results = crud_instance.get_trades_by_portfolio("TEST_PORT_TRADE_INTEG")
        assert len(results) == 5

    def test_find_by_account(self, crud_instance, cleanup, sample_trade_batch):
        """按实盘账号ID查询交易记录"""
        crud_instance.add_trade_records(sample_trade_batch)

        results = crud_instance.get_trades_by_account("TEST_ACCT_TRADE_INTEG")
        assert len(results) == 5

    def test_find_empty(self, crud_instance, cleanup):
        """查询不存在的数据返回空列表"""
        results = crud_instance.find(filters={"portfolio_id": "NONEXISTENT_PORTFOLIO_99999"})
        assert len(results) == 0


# ============================================================================
# 测试类：计数与删除
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestTradeRecordCRUDCountAndRemove:
    """TradeRecordCRUD 计数与删除操作集成测试"""

    def test_count(self, crud_instance, cleanup, sample_trade_batch):
        """计数操作"""
        crud_instance.add_trade_records(sample_trade_batch)

        cnt = crud_instance.count(filters={"portfolio_id": "TEST_PORT_TRADE_INTEG"})
        assert cnt == 5

    def test_remove(self, crud_instance, cleanup, sample_trade_batch):
        """删除操作"""
        crud_instance.add_trade_records(sample_trade_batch)

        cnt_before = crud_instance.count(filters={"portfolio_id": "TEST_PORT_TRADE_INTEG"})
        assert cnt_before == 5

        crud_instance.remove(filters={"portfolio_id": "TEST_PORT_TRADE_INTEG"})

        cnt_after = crud_instance.count(filters={"portfolio_id": "TEST_PORT_TRADE_INTEG"})
        assert cnt_after == 0
