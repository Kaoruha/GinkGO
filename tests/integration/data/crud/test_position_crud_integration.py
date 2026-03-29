"""
PositionCRUD 集成测试 - 连接真实 MySQL 数据库

覆盖范围：
- 单条添加持仓
- 按组合ID、股票代码过滤查询
- 活跃持仓查询
- 计数、删除、更新操作
- 业务辅助方法（find_by_portfolio, get_active_positions 等）

测试数据隔离：使用 SOURCE_TYPES.TEST 标记 + 特定 portfolio_id，测试后自动清理
数据库：MySQL (MPosition 继承 MMysqlBase)
"""

import pytest
from datetime import datetime
from decimal import Decimal

from ginkgo.data.crud.position_crud import PositionCRUD
from ginkgo.enums import SOURCE_TYPES


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def position_crud():
    """创建 PositionCRUD 实例"""
    return PositionCRUD()


@pytest.fixture
def cleanup(position_crud):
    """测试后清理测试数据（使用 TEST source + 特定 portfolio_id 隔离）"""
    yield
    try:
        position_crud.remove(
            filters={"portfolio_id": "TEST_PORT_POS_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
    except Exception:
        pass


@pytest.fixture
def sample_position_params():
    """标准测试持仓参数"""
    return {
        "portfolio_id": "TEST_PORT_POS_INTEG",
        "engine_id": "TEST_ENGINE_POS_INTEG",
        "code": "TEST_POS_001",
        "cost": 10500.0,
        "volume": 1000,
        "frozen_volume": 0,
        "frozen_money": 0,
        "price": 10.80,
        "fee": 5.25,
        "source": SOURCE_TYPES.TEST,
        "business_timestamp": datetime(2024, 1, 15, 15, 0, 0),
    }


@pytest.fixture
def sample_position_batch():
    """批量测试持仓参数列表"""
    return [
        {
            "portfolio_id": "TEST_PORT_POS_INTEG",
            "engine_id": "TEST_ENGINE_POS_INTEG",
            "code": f"TEST_POS_{i:03d}",
            "cost": 10000.0 * (i + 1),
            "volume": 1000 * (i + 1),
            "frozen_volume": 0,
            "frozen_money": 0,
            "price": 10.5 * (i + 1),
            "fee": 5.0 * (i + 1),
            "source": SOURCE_TYPES.TEST,
            "business_timestamp": datetime(2024, 1, 15, 15, 0, 0),
        }
        for i in range(5)
    ]


# ============================================================================
# 测试类：添加操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestPositionCRUDAdd:
    """PositionCRUD 添加操作集成测试"""

    def test_add_single_position(self, position_crud, cleanup, sample_position_params):
        """添加单条持仓，查回验证"""
        position = position_crud.create(**sample_position_params)

        assert position is not None
        assert position.portfolio_id == "TEST_PORT_POS_INTEG"
        assert position.code == "TEST_POS_001"
        assert position.volume == 1000

        # 查回验证
        results = position_crud.find(
            filters={"portfolio_id": "TEST_PORT_POS_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert len(results) >= 1

    def test_add_batch_positions(self, position_crud, cleanup, sample_position_batch):
        """批量添加持仓"""
        models = [position_crud._create_from_params(**p) for p in sample_position_batch]
        result = position_crud.add_batch(models)

        assert len(result) == 5

        found = position_crud.find(
            filters={"portfolio_id": "TEST_PORT_POS_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert len(found) == 5


# ============================================================================
# 测试类：查询操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestPositionCRUDFind:
    """PositionCRUD 查询操作集成测试"""

    def test_find_by_portfolio(self, position_crud, cleanup, sample_position_batch):
        """按组合ID查询持仓"""
        models = [position_crud._create_from_params(**p) for p in sample_position_batch]
        position_crud.add_batch(models)

        results = position_crud.find(
            filters={"portfolio_id": "TEST_PORT_POS_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert len(results) == 5

    def test_find_by_code(self, position_crud, cleanup, sample_position_batch):
        """按股票代码查询持仓"""
        models = [position_crud._create_from_params(**p) for p in sample_position_batch]
        position_crud.add_batch(models)

        results = position_crud.find(
            filters={
                "portfolio_id": "TEST_PORT_POS_INTEG",
                "code": "TEST_POS_000",
                "source": SOURCE_TYPES.TEST.value,
            }
        )
        assert len(results) == 1
        assert results[0].code == "TEST_POS_000"

    def test_find_active_positions(self, position_crud, cleanup, sample_position_batch):
        """查询活跃持仓（volume > 0）"""
        models = [position_crud._create_from_params(**p) for p in sample_position_batch]
        position_crud.add_batch(models)

        results = position_crud.find(
            filters={
                "portfolio_id": "TEST_PORT_POS_INTEG",
                "volume__gte": 1000,
                "source": SOURCE_TYPES.TEST.value,
            }
        )
        assert len(results) == 5

    def test_find_empty(self, position_crud, cleanup):
        """查询不存在的数据返回空列表"""
        results = position_crud.find(filters={"portfolio_id": "NONEXISTENT_PORTFOLIO_99999"})
        assert len(results) == 0


# ============================================================================
# 测试类：计数与删除
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestPositionCRUDCountAndRemove:
    """PositionCRUD 计数与删除操作集成测试"""

    def test_count(self, position_crud, cleanup, sample_position_batch):
        """计数操作"""
        models = [position_crud._create_from_params(**p) for p in sample_position_batch]
        position_crud.add_batch(models)

        cnt = position_crud.count(
            filters={"portfolio_id": "TEST_PORT_POS_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert cnt == 5

    def test_remove(self, position_crud, cleanup, sample_position_batch):
        """删除操作"""
        models = [position_crud._create_from_params(**p) for p in sample_position_batch]
        position_crud.add_batch(models)

        cnt_before = position_crud.count(
            filters={"portfolio_id": "TEST_PORT_POS_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert cnt_before == 5

        position_crud.remove(
            filters={"portfolio_id": "TEST_PORT_POS_INTEG", "source": SOURCE_TYPES.TEST.value}
        )

        cnt_after = position_crud.count(
            filters={"portfolio_id": "TEST_PORT_POS_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert cnt_after == 0


# ============================================================================
# 测试类：更新操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestPositionCRUDUpdate:
    """PositionCRUD 更新操作集成测试"""

    def test_update(self, position_crud, cleanup, sample_position_params):
        """更新持仓价格和数量"""
        position_crud.create(**sample_position_params)

        position_crud.modify(
            filters={
                "portfolio_id": "TEST_PORT_POS_INTEG",
                "code": "TEST_POS_001",
                "source": SOURCE_TYPES.TEST.value,
            },
            updates={"price": 11.50, "volume": 2000},
        )

        results = position_crud.find(
            filters={
                "portfolio_id": "TEST_PORT_POS_INTEG",
                "code": "TEST_POS_001",
                "source": SOURCE_TYPES.TEST.value,
            }
        )
        assert len(results) == 1
        assert results[0].volume == 2000
        assert float(results[0].price) == 11.50

    def test_close_position(self, position_crud, cleanup, sample_position_params):
        """平仓操作（volume 设为 0）"""
        position_crud.create(**sample_position_params)

        position_crud.close_position("TEST_PORT_POS_INTEG", "TEST_POS_001")

        results = position_crud.find(
            filters={
                "portfolio_id": "TEST_PORT_POS_INTEG",
                "code": "TEST_POS_001",
                "source": SOURCE_TYPES.TEST.value,
            }
        )
        assert len(results) == 1
        assert results[0].volume == 0
        assert results[0].frozen_volume == 0


# ============================================================================
# 测试类：业务辅助方法
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestPositionCRUDBusinessHelpers:
    """PositionCRUD 业务辅助方法集成测试"""

    def test_find_by_portfolio_helper(self, position_crud, cleanup, sample_position_batch):
        """业务方法：按组合ID查询持仓"""
        models = [position_crud._create_from_params(**p) for p in sample_position_batch]
        position_crud.add_batch(models)

        results = position_crud.find_by_portfolio("TEST_PORT_POS_INTEG")
        assert len(results) == 5

    def test_find_by_code_helper(self, position_crud, cleanup, sample_position_batch):
        """业务方法：按代码查询持仓"""
        models = [position_crud._create_from_params(**p) for p in sample_position_batch]
        position_crud.add_batch(models)

        results = position_crud.find_by_code("TEST_POS_000", portfolio_id="TEST_PORT_POS_INTEG")
        assert len(results) == 1
        assert results[0].code == "TEST_POS_000"

    def test_get_active_positions(self, position_crud, cleanup, sample_position_batch):
        """业务方法：获取活跃持仓"""
        models = [position_crud._create_from_params(**p) for p in sample_position_batch]
        position_crud.add_batch(models)

        results = position_crud.get_active_positions("TEST_PORT_POS_INTEG", min_volume=1)
        assert len(results) == 5

    def test_get_position(self, position_crud, cleanup, sample_position_params):
        """业务方法：获取特定持仓"""
        position_crud.create(**sample_position_params)

        result = position_crud.get_position("TEST_PORT_POS_INTEG", "TEST_POS_001")
        assert result is not None
        assert result.code == "TEST_POS_001"
        assert result.volume == 1000

    def test_get_portfolio_value(self, position_crud, cleanup, sample_position_batch):
        """业务方法：获取组合总价值"""
        models = [position_crud._create_from_params(**p) for p in sample_position_batch]
        position_crud.add_batch(models)

        summary = position_crud.get_portfolio_value("TEST_PORT_POS_INTEG")
        assert summary["portfolio_id"] == "TEST_PORT_POS_INTEG"
        assert summary["total_positions"] == 5
        assert summary["active_positions"] == 5
        assert summary["total_cost"] > 0
        assert summary["total_market_value"] > 0

    def test_update_position_helper(self, position_crud, cleanup, sample_position_params):
        """业务方法：更新持仓"""
        position_crud.create(**sample_position_params)

        position_crud.update_position("TEST_PORT_POS_INTEG", "TEST_POS_001", price=12.00, volume=500)

        results = position_crud.find(
            filters={
                "portfolio_id": "TEST_PORT_POS_INTEG",
                "code": "TEST_POS_001",
                "source": SOURCE_TYPES.TEST.value,
            }
        )
        assert len(results) == 1
        assert results[0].volume == 500
        assert float(results[0].price) == 12.00
