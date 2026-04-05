"""
BrokerInstanceCRUD 集成测试 - 连接真实 MySQL 数据库

覆盖范围：
- 添加 Broker 实例
- 按 Portfolio ID 查询 Broker
- 查询活跃 Broker 列表
- 计数、删除操作

测试数据隔离：使用特定 portfolio_id/live_account_id 隔离，测试后自动清理
数据库：MySQL (MBrokerInstance 继承 MMysqlBase)
"""

import pytest

from ginkgo.data.crud.broker_instance_crud import BrokerInstanceCRUD


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def crud_instance():
    """创建 BrokerInstanceCRUD 实例"""
    return BrokerInstanceCRUD()


@pytest.fixture
def cleanup(crud_instance):
    """测试后清理测试数据（使用特定 portfolio_id 隔离）"""
    yield
    try:
        crud_instance.remove(filters={"portfolio_id": "TEST_PORT_BROKER_INTEG"})
    except Exception:
        pass


@pytest.fixture
def sample_broker_params():
    """标准测试 Broker 实例参数"""
    return {
        "portfolio_id": "TEST_PORT_BROKER_INTEG",
        "live_account_id": "TEST_ACCT_BROKER_INTEG",
        "state": "uninitialized",
    }


@pytest.fixture
def sample_broker_batch():
    """批量测试 Broker 实例参数列表"""
    return [
        {
            "portfolio_id": f"TEST_PORT_BROKER_INTEG_{i}",
            "live_account_id": "TEST_ACCT_BROKER_INTEG",
            "state": "uninitialized",
        }
        for i in range(5)
    ]


# ============================================================================
# 测试类：添加操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestBrokerInstanceCRUDAdd:
    """BrokerInstanceCRUD 添加操作集成测试"""

    def test_add_broker_instance(self, crud_instance, cleanup, sample_broker_params):
        """添加单条 Broker 实例，查回验证"""
        broker = crud_instance.add_broker_instance(**sample_broker_params)

        assert broker is not None
        assert broker.portfolio_id == "TEST_PORT_BROKER_INTEG"
        assert broker.live_account_id == "TEST_ACCT_BROKER_INTEG"
        assert broker.state == "uninitialized"

        # 查回验证
        results = crud_instance.find(
            filters={"portfolio_id": "TEST_PORT_BROKER_INTEG", "is_del": False}
        )
        assert len(results) >= 1

    def test_add_batch_brokers(self, crud_instance, cleanup, sample_broker_batch):
        """批量添加 Broker 实例"""
        from ginkgo.data.models.model_broker_instance import MBrokerInstance

        models = []
        for params in sample_broker_batch:
            models.append(MBrokerInstance(**params))
        result = crud_instance.add_batch(models)

        assert len(result) == 5


# ============================================================================
# 测试类：查询操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestBrokerInstanceCRUDFind:
    """BrokerInstanceCRUD 查询操作集成测试"""

    def test_find_by_portfolio(self, crud_instance, cleanup, sample_broker_params):
        """按 Portfolio ID 查询 Broker 实例"""
        crud_instance.add_broker_instance(**sample_broker_params)

        broker = crud_instance.get_broker_by_portfolio("TEST_PORT_BROKER_INTEG")
        assert broker is not None
        assert broker.portfolio_id == "TEST_PORT_BROKER_INTEG"

    def test_find_by_live_account(self, crud_instance, cleanup, sample_broker_batch):
        """按实盘账号ID查询 Broker 实例"""
        from ginkgo.data.models.model_broker_instance import MBrokerInstance

        models = [MBrokerInstance(**p) for p in sample_broker_batch]
        crud_instance.add_batch(models)

        results = crud_instance.get_broker_by_live_account("TEST_ACCT_BROKER_INTEG")
        assert len(results) == 5

    def test_find_empty(self, crud_instance, cleanup):
        """查询不存在的数据返回空列表"""
        broker = crud_instance.get_broker_by_portfolio("NONEXISTENT_PORTFOLIO_99999")
        assert broker is None


# ============================================================================
# 测试类：计数与删除
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestBrokerInstanceCRUDCountAndRemove:
    """BrokerInstanceCRUD 计数与删除操作集成测试"""

    def test_count(self, crud_instance, cleanup, sample_broker_batch):
        """计数操作"""
        from ginkgo.data.models.model_broker_instance import MBrokerInstance

        models = [MBrokerInstance(**p) for p in sample_broker_batch]
        crud_instance.add_batch(models)

        cnt = crud_instance.count(filters={"live_account_id": "TEST_ACCT_BROKER_INTEG"})
        assert cnt == 5

    def test_remove(self, crud_instance, cleanup, sample_broker_batch):
        """删除操作"""
        from ginkgo.data.models.model_broker_instance import MBrokerInstance

        models = [MBrokerInstance(**p) for p in sample_broker_batch]
        crud_instance.add_batch(models)

        cnt_before = crud_instance.count(filters={"live_account_id": "TEST_ACCT_BROKER_INTEG"})
        assert cnt_before == 5

        crud_instance.remove(filters={"live_account_id": "TEST_ACCT_BROKER_INTEG"})

        cnt_after = crud_instance.count(filters={"live_account_id": "TEST_ACCT_BROKER_INTEG"})
        assert cnt_after == 0
