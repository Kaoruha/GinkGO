"""
BacktestTaskCRUD 集成测试 - 连接真实 MySQL 数据库

覆盖范围：
- 单条/批量添加回测任务
- 按引擎ID、组合ID、UUID查询
- 分页筛选查询
- 计数、删除操作

测试数据隔离：使用 SOURCE_TYPES.TEST 标记 + 特定 engine_id/portfolio_id，测试后自动清理
数据库：MySQL (MBacktestTask 继承 MMysqlBase)
"""

import pytest
from datetime import datetime

from ginkgo.data.crud.backtest_task_crud import BacktestTaskCRUD
from ginkgo.enums import SOURCE_TYPES


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def crud_instance():
    """创建 BacktestTaskCRUD 实例"""
    return BacktestTaskCRUD()


@pytest.fixture
def cleanup(crud_instance):
    """测试后清理测试数据（使用 TEST source + 特定 engine_id 隔离）"""
    yield
    try:
        crud_instance.remove(
            filters={"engine_id": "TEST_ENGINE_BT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
    except Exception:
        pass


@pytest.fixture
def sample_task_params():
    """标准测试回测任务参数"""
    return {
        "engine_id": "TEST_ENGINE_BT_INTEG",
        "portfolio_id": "TEST_PORT_BT_INTEG",
        "name": "集成测试回测任务",
        "status": "created",
        "source": SOURCE_TYPES.TEST,
    }


@pytest.fixture
def sample_task_batch():
    """批量测试回测任务参数列表"""
    return [
        {
            "engine_id": "TEST_ENGINE_BT_INTEG",
            "portfolio_id": "TEST_PORT_BT_INTEG",
            "name": f"测试任务_{i}",
            "status": "created" if i < 3 else "completed",
            "source": SOURCE_TYPES.TEST,
        }
        for i in range(5)
    ]


# ============================================================================
# 测试类：添加操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestBacktestTaskCRUDAdd:
    """BacktestTaskCRUD 添加操作集成测试"""

    def test_add_single_task(self, crud_instance, cleanup, sample_task_params):
        """添加单条回测任务，查回验证"""
        task = crud_instance.create(**sample_task_params)

        assert task is not None
        assert task.engine_id == "TEST_ENGINE_BT_INTEG"
        assert task.portfolio_id == "TEST_PORT_BT_INTEG"
        assert task.name == "集成测试回测任务"

        # 查回验证
        results = crud_instance.find(
            filters={"engine_id": "TEST_ENGINE_BT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert len(results) >= 1

    def test_add_batch_tasks(self, crud_instance, cleanup, sample_task_batch):
        """批量添加回测任务"""
        models = [crud_instance._create_from_params(**p) for p in sample_task_batch]
        result = crud_instance.add_batch(models)

        assert len(result) == 5

        found = crud_instance.find(
            filters={"engine_id": "TEST_ENGINE_BT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert len(found) == 5


# ============================================================================
# 测试类：查询操作
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestBacktestTaskCRUDFind:
    """BacktestTaskCRUD 查询操作集成测试"""

    def test_find_by_engine(self, crud_instance, cleanup, sample_task_batch):
        """按引擎ID查询回测任务"""
        models = [crud_instance._create_from_params(**p) for p in sample_task_batch]
        crud_instance.add_batch(models)

        results = crud_instance.find(
            filters={"engine_id": "TEST_ENGINE_BT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert len(results) == 5

    def test_find_by_uuid(self, crud_instance, cleanup, sample_task_params):
        """通过 UUID 查询回测任务"""
        task = crud_instance.create(**sample_task_params)
        assert task.uuid is not None

        found = crud_instance.get_by_uuid(task.uuid)
        assert found is not None
        assert found.name == "集成测试回测任务"

    def test_find_by_portfolio(self, crud_instance, cleanup, sample_task_batch):
        """按组合ID查询回测任务"""
        models = [crud_instance._create_from_params(**p) for p in sample_task_batch]
        crud_instance.add_batch(models)

        results = crud_instance.get_tasks_by_portfolio("TEST_PORT_BT_INTEG")
        assert len(results) >= 1

    def test_find_empty(self, crud_instance, cleanup):
        """查询不存在的数据返回空列表"""
        results = crud_instance.find(filters={"engine_id": "NONEXISTENT_ENGINE_99999"})
        assert len(results) == 0


# ============================================================================
# 测试类：计数与删除
# ============================================================================


@pytest.mark.database
@pytest.mark.integration
class TestBacktestTaskCRUDCountAndRemove:
    """BacktestTaskCRUD 计数与删除操作集成测试"""

    def test_count(self, crud_instance, cleanup, sample_task_batch):
        """计数操作"""
        models = [crud_instance._create_from_params(**p) for p in sample_task_batch]
        crud_instance.add_batch(models)

        cnt = crud_instance.count(
            filters={"engine_id": "TEST_ENGINE_BT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert cnt == 5

    def test_remove(self, crud_instance, cleanup, sample_task_batch):
        """删除操作"""
        models = [crud_instance._create_from_params(**p) for p in sample_task_batch]
        crud_instance.add_batch(models)

        cnt_before = crud_instance.count(
            filters={"engine_id": "TEST_ENGINE_BT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert cnt_before == 5

        crud_instance.remove(
            filters={"engine_id": "TEST_ENGINE_BT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )

        cnt_after = crud_instance.count(
            filters={"engine_id": "TEST_ENGINE_BT_INTEG", "source": SOURCE_TYPES.TEST.value}
        )
        assert cnt_after == 0
