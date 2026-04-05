"""
DeploymentCRUD 集成测试

测试部署记录的创建、查询和删除操作。
DeploymentCRUD 继承 BaseCRUD，使用 MDeployment 模型，存储在 MySQL 中。
部署记录追踪回测到纸上交易/实盘的部署历史。

测试范围：
1. 插入操作 - 通过 BaseCRUD 的 create 方法创建部署记录
2. 查询操作 - get_by_target_portfolio, get_by_source_task
3. 删除操作 - 通过 BaseCRUD 的 remove 方法清理
"""
import pytest
import sys
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.deployment_crud import DeploymentCRUD
from ginkgo.data.models.model_deployment import MDeployment, DEPLOYMENT_STATUS
from ginkgo.enums import SOURCE_TYPES


@pytest.fixture
def crud_instance():
    """创建 DeploymentCRUD 实例"""
    return DeploymentCRUD()


@pytest.fixture
def cleanup(crud_instance):
    """测试后清理测试数据"""
    yield
    try:
        crud_instance.remove(
            filters={"source_task_id": "test_task_integration_001", "source": SOURCE_TYPES.TEST.value}
        )
        crud_instance.remove(
            filters={"source_task_id": "test_task_integration_002", "source": SOURCE_TYPES.TEST.value}
        )
    except Exception:
        pass


@pytest.mark.database
@pytest.mark.integration
class TestDeploymentCRUDInsert:
    """1. 部署记录插入操作测试"""

    def test_create_deployment(self, crud_instance, cleanup):
        """测试创建部署记录"""
        print("\n" + "=" * 60)
        print("开始测试: DeploymentCRUD 创建部署记录")
        print("=" * 60)

        deployment = MDeployment(
            source_task_id="test_task_integration_001",
            target_portfolio_id="test_portfolio_deploy_001",
            source_portfolio_id="test_portfolio_source_001",
            mode=1,  # 纸上交易
            status=DEPLOYMENT_STATUS.PENDING,
            source=SOURCE_TYPES.TEST
        )
        crud_instance.add(deployment)
        print(f"-> 创建部署记录: source_task_id={deployment.source_task_id}")

        # 验证
        results = crud_instance.find(
            filters={"source_task_id": "test_task_integration_001"}
        )
        assert len(results) >= 1, "应查询到插入的部署记录"
        assert results[0].mode == 1, "运行模式应匹配"
        print("✓ 部署记录创建成功")

    def test_create_live_deployment(self, crud_instance, cleanup):
        """测试创建实盘部署记录"""
        print("\n" + "=" * 60)
        print("开始测试: DeploymentCRUD 创建实盘部署记录")
        print("=" * 60)

        deployment = MDeployment(
            source_task_id="test_task_integration_002",
            target_portfolio_id="test_portfolio_live_001",
            source_portfolio_id="test_portfolio_source_002",
            mode=2,  # 实盘
            account_id="test_account_001",
            status=DEPLOYMENT_STATUS.PENDING,
            source=SOURCE_TYPES.TEST
        )
        crud_instance.add(deployment)
        print(f"-> 创建实盘部署: account_id={deployment.account_id}")

        # 验证
        results = crud_instance.find(
            filters={"source_task_id": "test_task_integration_002"}
        )
        assert len(results) >= 1, "应查询到实盘部署记录"
        assert results[0].account_id == "test_account_001", "账号ID应匹配"
        print("✓ 实盘部署记录创建成功")


@pytest.mark.database
@pytest.mark.integration
class TestDeploymentCRUDQuery:
    """2. 部署记录查询操作测试"""

    def test_get_by_target_portfolio(self, crud_instance, cleanup):
        """测试按目标 Portfolio 查询部署记录"""
        print("\n" + "=" * 60)
        print("开始测试: DeploymentCRUD 按目标 Portfolio 查询")
        print("=" * 60)

        # 先插入
        deployment = MDeployment(
            source_task_id="test_task_integration_001",
            target_portfolio_id="test_portfolio_deploy_001",
            source_portfolio_id="test_portfolio_source_001",
            mode=1,
            status=DEPLOYMENT_STATUS.DEPLOYED,
            source=SOURCE_TYPES.TEST
        )
        crud_instance.add(deployment)

        # 按目标 Portfolio 查询
        results = crud_instance.get_by_target_portfolio("test_portfolio_deploy_001")
        print(f"-> 查询到 {len(results)} 条部署记录")

        assert len(results) >= 1, "应查询到至少1条记录"
        assert results[0].target_portfolio_id == "test_portfolio_deploy_001"
        print("✓ 按目标 Portfolio 查询成功")

    def test_get_by_source_task(self, crud_instance, cleanup):
        """测试按源回测任务查询部署记录"""
        print("\n" + "=" * 60)
        print("开始测试: DeploymentCRUD 按源任务查询")
        print("=" * 60)

        # 先插入
        deployment = MDeployment(
            source_task_id="test_task_integration_002",
            target_portfolio_id="test_portfolio_live_001",
            source_portfolio_id="test_portfolio_source_002",
            mode=2,
            status=DEPLOYMENT_STATUS.PENDING,
            source=SOURCE_TYPES.TEST
        )
        crud_instance.add(deployment)

        # 按源任务查询
        results = crud_instance.get_by_source_task("test_task_integration_002")
        print(f"-> 查询到 {len(results)} 条部署记录")

        assert len(results) >= 1, "应查询到至少1条记录"
        assert results[0].source_task_id == "test_task_integration_002"
        print("✓ 按源任务查询成功")


@pytest.mark.database
@pytest.mark.integration
class TestDeploymentCRUDDelete:
    """3. 部署记录删除操作测试"""

    def test_remove_deployment_by_filters(self, crud_instance, cleanup):
        """测试按条件删除部署记录"""
        print("\n" + "=" * 60)
        print("开始测试: DeploymentCRUD 按条件删除")
        print("=" * 60)

        # 先插入
        deployment = MDeployment(
            source_task_id="test_task_integration_001",
            target_portfolio_id="test_portfolio_to_delete",
            source_portfolio_id="test_portfolio_source_del",
            mode=0,
            status=DEPLOYMENT_STATUS.STOPPED,
            source=SOURCE_TYPES.TEST
        )
        crud_instance.add(deployment)

        # 确认插入
        results = crud_instance.find(
            filters={"target_portfolio_id": "test_portfolio_to_delete"}
        )
        assert len(results) >= 1, "删除前应存在记录"

        # 删除
        crud_instance.remove(
            filters={"target_portfolio_id": "test_portfolio_to_delete", "source": SOURCE_TYPES.TEST.value}
        )
        print("-> 删除完成")

        # 验证删除
        results = crud_instance.find(
            filters={"target_portfolio_id": "test_portfolio_to_delete"}
        )
        assert len(results) == 0, "删除后不应存在记录"
        print("✓ 删除成功")
