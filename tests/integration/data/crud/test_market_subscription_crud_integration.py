"""
MarketSubscriptionCRUD 集成测试 - 连接真实 MySQL 数据库

覆盖范围：
- 添加市场数据订阅
- 按用户ID查询订阅列表
- 获取所有活跃交易对
- 删除订阅操作

测试数据隔离：使用特定 user_id 隔离，测试后自动清理
数据库：MySQL (MMarketSubscription 继承 MMysqlBase)
"""

import pytest

from ginkgo.data.crud.market_subscription_crud import MarketSubscriptionCRUD
from ginkgo.enums import SOURCE_TYPES


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def crud_instance():
    """创建 MarketSubscriptionCRUD 实例"""
    return MarketSubscriptionCRUD()


@pytest.fixture
def cleanup(crud_instance):
    """测试后清理测试数据（使用特定 user_id 隔离）"""
    yield
    try:
        crud_instance.remove(filters={"user_id": "TEST_USER_SUB_INTEG"})
    except Exception:
        pass


@pytest.fixture
def sample_subscription_params():
    """标准测试订阅参数"""
    return {
        "user_id": "TEST_USER_SUB_INTEG",
        "exchange": "okx",
        "symbol": "BTC-USDT",
        "environment": "testnet",
        "is_active": True,
        "source": SOURCE_TYPES.TEST,
    }


@pytest.fixture
def sample_subscription_batch():
    """批量测试订阅参数列表"""
    symbols = ["BTC-USDT", "ETH-USDT", "SOL-USDT", "DOGE-USDT", "XRP-USDT"]
    return [
        {
            "user_id": "TEST_USER_SUB_INTEG",
            "exchange": "okx",
            "symbol": symbol,
            "environment": "testnet",
            "is_active": True,
            "source": SOURCE_TYPES.TEST,
        }
        for symbol in symbols
    ]


# ============================================================================
# 测试类：添加操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestMarketSubscriptionCRUDAdd:
    """MarketSubscriptionCRUD 添加操作集成测试"""

    def test_add_subscription(self, crud_instance, cleanup, sample_subscription_params):
        """添加单条订阅，查回验证"""
        subscription = crud_instance.create(**sample_subscription_params)

        assert subscription is not None
        assert subscription.user_id == "TEST_USER_SUB_INTEG"
        assert subscription.symbol == "BTC-USDT"

        # 查回验证
        results = crud_instance.find(
            filters={"user_id": "TEST_USER_SUB_INTEG"}
        )
        assert len(results) >= 1

    def test_add_batch_subscriptions(self, crud_instance, cleanup, sample_subscription_batch):
        """批量添加订阅"""
        models = [crud_instance._create_from_params(**p) for p in sample_subscription_batch]
        result = crud_instance.add_batch(models)

        assert len(result) == 5

        found = crud_instance.find(
            filters={"user_id": "TEST_USER_SUB_INTEG"}
        )
        assert len(found) == 5


# ============================================================================
# 测试类：查询操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestMarketSubscriptionCRUDFind:
    """MarketSubscriptionCRUD 查询操作集成测试"""

    def test_find_user_subscriptions(self, crud_instance, cleanup, sample_subscription_batch):
        """按用户ID查询订阅列表"""
        models = [crud_instance._create_from_params(**p) for p in sample_subscription_batch]
        crud_instance.add_batch(models)

        results = crud_instance.get_user_subscriptions("TEST_USER_SUB_INTEG", active_only=False)
        assert len(results) == 5

    def test_find_all_active_symbols(self, crud_instance, cleanup, sample_subscription_batch):
        """获取所有活跃交易对"""
        models = [crud_instance._create_from_params(**p) for p in sample_subscription_batch]
        crud_instance.add_batch(models)

        symbols = crud_instance.get_all_active_symbols(exchange="okx")
        # 验证测试数据中的交易对在结果中
        found = [s for s in symbols if s["user_id"] == "TEST_USER_SUB_INTEG"]
        assert len(found) == 5

    def test_find_empty(self, crud_instance, cleanup):
        """查询不存在的数据返回空列表"""
        results = crud_instance.find(filters={"user_id": "NONEXISTENT_USER_99999"})
        assert len(results) == 0


# ============================================================================
# 测试类：计数与删除
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestMarketSubscriptionCRUDCountAndRemove:
    """MarketSubscriptionCRUD 计数与删除操作集成测试"""

    def test_count(self, crud_instance, cleanup, sample_subscription_batch):
        """计数操作"""
        models = [crud_instance._create_from_params(**p) for p in sample_subscription_batch]
        crud_instance.add_batch(models)

        cnt = crud_instance.count(filters={"user_id": "TEST_USER_SUB_INTEG"})
        assert cnt == 5

    def test_remove(self, crud_instance, cleanup, sample_subscription_batch):
        """删除操作"""
        models = [crud_instance._create_from_params(**p) for p in sample_subscription_batch]
        crud_instance.add_batch(models)

        cnt_before = crud_instance.count(filters={"user_id": "TEST_USER_SUB_INTEG"})
        assert cnt_before == 5

        crud_instance.remove(filters={"user_id": "TEST_USER_SUB_INTEG"})

        cnt_after = crud_instance.count(filters={"user_id": "TEST_USER_SUB_INTEG"})
        assert cnt_after == 0
