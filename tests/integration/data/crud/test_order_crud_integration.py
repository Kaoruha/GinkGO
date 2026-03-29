"""
OrderCRUD 集成测试 - 连接真实 MySQL 数据库

覆盖范围：
- 单条添加订单
- 按组合ID、股票代码、状态过滤查询
- 待处理订单查询
- 计数、删除、更新操作
- 业务辅助方法（find_by_portfolio, count_by_portfolio 等）

测试数据隔离：使用 SOURCE_TYPES.TEST 标记，测试后自动清理
数据库：MySQL (MOrder 继承 MMysqlBase)
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.data.crud.order_crud import OrderCRUD
from ginkgo.enums import (
    SOURCE_TYPES,
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def order_crud():
    """创建 OrderCRUD 实例"""
    return OrderCRUD()


@pytest.fixture
def cleanup(order_crud):
    """测试后清理测试数据（使用 TEST source + 特定 portfolio_id 隔离）"""
    yield
    try:
        order_crud.remove(filters={"portfolio_id": "TEST_PORT_INTEG", "source": SOURCE_TYPES.TEST.value})
    except Exception:
        pass


@pytest.fixture
def sample_order_params():
    """标准测试订单参数"""
    return {
        "portfolio_id": "TEST_PORT_INTEG",
        "engine_id": "TEST_ENGINE_INTEG",
        "code": "TEST_ORDER_001",
        "direction": DIRECTION_TYPES.LONG,
        "order_type": ORDER_TYPES.LIMITORDER,
        "status": ORDERSTATUS_TYPES.NEW,
        "volume": 1000,
        "limit_price": 10.50,
        "frozen": 10500.0,
        "transaction_price": 0,
        "transaction_volume": 0,
        "remain": 1000.0,
        "fee": 0.0,
        "timestamp": datetime(2024, 1, 15, 9, 30, 0),
        "source": SOURCE_TYPES.TEST,
    }


@pytest.fixture
def sample_order_batch():
    """批量测试订单参数列表（不同状态）"""
    base = datetime(2024, 1, 15, 9, 30, 0)
    return [
        {
            "portfolio_id": "TEST_PORT_INTEG",
            "engine_id": "TEST_ENGINE_INTEG",
            "code": f"TEST_ORDER_{i:03d}",
            "direction": DIRECTION_TYPES.LONG if i % 2 == 0 else DIRECTION_TYPES.SHORT,
            "order_type": ORDER_TYPES.LIMITORDER,
            "status": ORDERSTATUS_TYPES.NEW if i < 3 else ORDERSTATUS_TYPES.FILLED,
            "volume": 1000 * (i + 1),
            "limit_price": 10.0 + i,
            "frozen": 10000.0 * (i + 1),
            "transaction_price": 10.0 + i if i >= 3 else 0,
            "transaction_volume": 1000 * (i + 1) if i >= 3 else 0,
            "remain": 0.0 if i >= 3 else 1000.0 * (i + 1),
            "fee": 5.0 if i >= 3 else 0.0,
            "timestamp": base + timedelta(minutes=i),
            "source": SOURCE_TYPES.TEST,
        }
        for i in range(5)
    ]


# ============================================================================
# 测试类：添加操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestOrderCRUDAdd:
    """OrderCRUD 添加操作集成测试"""

    def test_add_single_order(self, order_crud, cleanup, sample_order_params):
        """添加单条订单，查回验证"""
        order = order_crud.create(**sample_order_params)

        assert order is not None
        assert order.portfolio_id == "TEST_PORT_INTEG"
        assert order.code == "TEST_ORDER_001"
        assert order.volume == 1000

        # 查回验证
        results = order_crud.find(filters={"portfolio_id": "TEST_PORT_INTEG", "source": SOURCE_TYPES.TEST.value})
        assert len(results) >= 1

    def test_add_batch_orders(self, order_crud, cleanup, sample_order_batch):
        """批量添加订单"""
        models = [order_crud._create_from_params(**p) for p in sample_order_batch]
        result = order_crud.add_batch(models)

        assert len(result) == 5

        found = order_crud.find(filters={"portfolio_id": "TEST_PORT_INTEG", "source": SOURCE_TYPES.TEST.value})
        assert len(found) == 5


# ============================================================================
# 测试类：查询操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestOrderCRUDFind:
    """OrderCRUD 查询操作集成测试"""

    def test_find_by_portfolio(self, order_crud, cleanup, sample_order_batch):
        """按组合ID查询订单"""
        models = [order_crud._create_from_params(**p) for p in sample_order_batch]
        order_crud.add_batch(models)

        results = order_crud.find(filters={"portfolio_id": "TEST_PORT_INTEG", "source": SOURCE_TYPES.TEST.value})
        assert len(results) == 5

    def test_find_by_code(self, order_crud, cleanup, sample_order_batch):
        """按股票代码查询订单"""
        models = [order_crud._create_from_params(**p) for p in sample_order_batch]
        order_crud.add_batch(models)

        results = order_crud.find(
            filters={
                "portfolio_id": "TEST_PORT_INTEG",
                "code": "TEST_ORDER_000",
                "source": SOURCE_TYPES.TEST.value,
            }
        )
        assert len(results) == 1
        assert results[0].code == "TEST_ORDER_000"

    def test_find_pending_orders(self, order_crud, cleanup, sample_order_batch):
        """按状态过滤查询待处理订单"""
        models = [order_crud._create_from_params(**p) for p in sample_order_batch]
        order_crud.add_batch(models)

        # sample_order_batch 中 index 0,1,2 是 NEW 状态
        results = order_crud.find(filters={"portfolio_id": "TEST_PORT_INTEG", "status": ORDERSTATUS_TYPES.NEW, "source": SOURCE_TYPES.TEST.value})
        assert len(results) == 3

    def test_find_empty(self, order_crud, cleanup):
        """查询不存在的数据返回空列表"""
        results = order_crud.find(filters={"portfolio_id": "NONEXISTENT_PORTFOLIO_99999"})
        assert len(results) == 0


# ============================================================================
# 测试类：计数与删除
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestOrderCRUDCountAndRemove:
    """OrderCRUD 计数与删除操作集成测试"""

    def test_count(self, order_crud, cleanup, sample_order_batch):
        """计数操作"""
        models = [order_crud._create_from_params(**p) for p in sample_order_batch]
        order_crud.add_batch(models)

        cnt = order_crud.count(filters={"portfolio_id": "TEST_PORT_INTEG", "source": SOURCE_TYPES.TEST.value})
        assert cnt == 5

    def test_remove(self, order_crud, cleanup, sample_order_batch):
        """删除操作"""
        models = [order_crud._create_from_params(**p) for p in sample_order_batch]
        order_crud.add_batch(models)

        cnt_before = order_crud.count(filters={"portfolio_id": "TEST_PORT_INTEG", "source": SOURCE_TYPES.TEST.value})
        assert cnt_before == 5

        order_crud.remove(filters={"portfolio_id": "TEST_PORT_INTEG", "source": SOURCE_TYPES.TEST.value})

        cnt_after = order_crud.count(filters={"portfolio_id": "TEST_PORT_INTEG", "source": SOURCE_TYPES.TEST.value})
        assert cnt_after == 0


# ============================================================================
# 测试类：更新操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestOrderCRUDUpdate:
    """OrderCRUD 更新操作集成测试"""

    def test_update_status(self, order_crud, cleanup, sample_order_params):
        """更新订单状态"""
        order_crud.create(**sample_order_params)

        # 更新状态为 FILLED
        order_crud.modify(
            filters={"portfolio_id": "TEST_PORT_INTEG", "code": "TEST_ORDER_001", "source": SOURCE_TYPES.TEST.value},
            updates={"status": ORDERSTATUS_TYPES.FILLED.value, "transaction_price": 10.50, "transaction_volume": 1000, "remain": 0},
        )

        results = order_crud.find(filters={"portfolio_id": "TEST_PORT_INTEG", "code": "TEST_ORDER_001", "source": SOURCE_TYPES.TEST.value})
        assert len(results) == 1
        assert results[0].status == ORDERSTATUS_TYPES.FILLED


# ============================================================================
# 测试类：业务辅助方法
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestOrderCRUDBusinessHelpers:
    """OrderCRUD 业务辅助方法集成测试"""

    def test_find_by_portfolio_helper(self, order_crud, cleanup, sample_order_batch):
        """业务方法：按组合ID查询订单"""
        models = [order_crud._create_from_params(**p) for p in sample_order_batch]
        order_crud.add_batch(models)

        results = order_crud.find_by_portfolio("TEST_PORT_INTEG")
        assert len(results) == 5

    def test_count_by_portfolio(self, order_crud, cleanup, sample_order_batch):
        """业务方法：按组合ID计数"""
        models = [order_crud._create_from_params(**p) for p in sample_order_batch]
        order_crud.add_batch(models)

        cnt = order_crud.count_by_portfolio("TEST_PORT_INTEG")
        assert cnt == 5

    def test_find_by_code_helper(self, order_crud, cleanup, sample_order_batch):
        """业务方法：按代码查询订单"""
        models = [order_crud._create_from_params(**p) for p in sample_order_batch]
        order_crud.add_batch(models)

        results = order_crud.find_by_code("TEST_ORDER_000", portfolio_id="TEST_PORT_INTEG")
        assert len(results) == 1

    def test_find_pending_orders_helper(self, order_crud, cleanup, sample_order_batch):
        """业务方法：查询待处理订单"""
        models = [order_crud._create_from_params(**p) for p in sample_order_batch]
        order_crud.add_batch(models)

        results = order_crud.find_pending_orders(portfolio_id="TEST_PORT_INTEG")
        assert len(results) == 3

    def test_cancel_pending_orders(self, order_crud, cleanup, sample_order_batch):
        """业务方法：取消待处理订单"""
        models = [order_crud._create_from_params(**p) for p in sample_order_batch]
        order_crud.add_batch(models)

        cancelled = order_crud.cancel_pending_orders(portfolio_id="TEST_PORT_INTEG")
        assert cancelled == 3

        # 验证已删除
        remaining = order_crud.find_pending_orders(portfolio_id="TEST_PORT_INTEG")
        assert len(remaining) == 0

    def test_count_by_status(self, order_crud, cleanup, sample_order_batch):
        """业务方法：按状态计数"""
        models = [order_crud._create_from_params(**p) for p in sample_order_batch]
        order_crud.add_batch(models)

        new_cnt = order_crud.count_by_status(ORDERSTATUS_TYPES.NEW, portfolio_id="TEST_PORT_INTEG")
        filled_cnt = order_crud.count_by_status(ORDERSTATUS_TYPES.FILLED, portfolio_id="TEST_PORT_INTEG")
        assert new_cnt == 3
        assert filled_cnt == 2
