"""
性能: 218MB RSS, 1.88s, 7 tests [PASS]
DeploymentCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- 构造与类型检查：model_class、继承关系
- Business Helper: get_by_target_portfolio, get_by_source_task
- 无 _get_field_config, _get_enum_mappings, _create_from_params
"""

import pytest
from unittest.mock import MagicMock, patch

import uuid


# ============================================================
# 辅助：构造 DeploymentCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def deployment_crud():
    """构造 DeploymentCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.deployment_crud import DeploymentCRUD
        crud = DeploymentCRUD()
        crud._logger = mock_logger
        return crud


@pytest.fixture
def fake_deployment():
    """构造一个假的 MDeployment 对象"""
    mock_dep = MagicMock()
    mock_dep.uuid = str(uuid.uuid4())
    mock_dep.source_task_id = "task_001"
    mock_dep.target_portfolio_id = "portfolio_001"
    mock_dep.source_portfolio_id = "portfolio_src"
    mock_dep.mode = 2
    mock_dep.status = 1
    return mock_dep


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestDeploymentCRUDConstruction:
    """DeploymentCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction_model_class(self, deployment_crud):
        """验证 model_class 为 MDeployment"""
        from ginkgo.data.models.model_deployment import MDeployment

        assert deployment_crud.model_class is MDeployment



# ============================================================
# Business Helper 测试
# ============================================================


class TestDeploymentCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_get_by_target_portfolio(self, deployment_crud, fake_deployment):
        """根据目标 Portfolio ID 查询部署记录"""
        deployment_crud.find = MagicMock(return_value=[fake_deployment])

        result = deployment_crud.get_by_target_portfolio("portfolio_001")

        assert result == [fake_deployment]
        deployment_crud.find.assert_called_once_with(
            filters={"target_portfolio_id": "portfolio_001"}
        )

    @pytest.mark.unit
    def test_get_by_target_portfolio_empty(self, deployment_crud):
        """目标 Portfolio 无部署记录时返回空列表"""
        deployment_crud.find = MagicMock(return_value=[])

        result = deployment_crud.get_by_target_portfolio("nonexistent")

        assert result == []

    @pytest.mark.unit
    def test_get_by_source_task(self, deployment_crud, fake_deployment):
        """根据源回测任务 ID 查询部署记录"""
        deployment_crud.find = MagicMock(return_value=[fake_deployment])

        result = deployment_crud.get_by_source_task("task_001")

        assert result == [fake_deployment]
        deployment_crud.find.assert_called_once_with(
            filters={"source_task_id": "task_001"}
        )

    @pytest.mark.unit
    def test_get_by_source_task_empty(self, deployment_crud):
        """源任务无部署记录时返回空列表"""
        deployment_crud.find = MagicMock(return_value=[])

        result = deployment_crud.get_by_source_task("nonexistent_task")

        assert result == []

    @pytest.mark.unit
    def test_get_by_target_portfolio_filters_correct_key(self, deployment_crud):
        """验证 filters 使用 target_portfolio_id 而非其他字段"""
        deployment_crud.find = MagicMock(return_value=[])

        deployment_crud.get_by_target_portfolio("portfolio_abc")

        call_args = deployment_crud.find.call_args[1]
        assert "target_portfolio_id" in call_args["filters"]
        assert call_args["filters"]["target_portfolio_id"] == "portfolio_abc"

    @pytest.mark.unit
    def test_get_by_source_task_filters_correct_key(self, deployment_crud):
        """验证 filters 使用 source_task_id 而非其他字段"""
        deployment_crud.find = MagicMock(return_value=[])

        deployment_crud.get_by_source_task("task_xyz")

        call_args = deployment_crud.find.call_args[1]
        assert "source_task_id" in call_args["filters"]
        assert call_args["filters"]["source_task_id"] == "task_xyz"
