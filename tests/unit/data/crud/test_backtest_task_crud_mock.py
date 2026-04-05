"""
BacktestTaskCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置（run_id 自动生成，配置为空）
- _create_from_params: 参数转 MBacktestTask 模型
- Business Helper: get_tasks_by_engine, count_by_status, get_by_uuid
- 构造与类型检查
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 BacktestTaskCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def crud_instance():
    """构造 BacktestTaskCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.backtest_task_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.backtest_task_crud import BacktestTaskCRUD
        crud = BacktestTaskCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestBacktestTaskCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_is_empty(self, crud_instance):
        """run_id 自动生成，字段配置为空字典"""
        config = crud_instance._get_field_config()
        assert config == {}


# ============================================================
# _create_from_params 测试
# ============================================================


class TestBacktestTaskCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, crud_instance):
        """传入完整参数，返回 MBacktestTask 模型且属性正确"""
        from ginkgo.data.models import MBacktestTask

        params = {
            "run_id": "run-001",
            "name": "测试回测任务",
            "engine_id": "engine-001",
            "portfolio_id": "portfolio-001",
            "status": "running",
        }

        model = crud_instance._create_from_params(**params)

        assert isinstance(model, MBacktestTask)
        assert model.run_id == "run-001"
        assert model.uuid == "run-001"
        assert model.name == "测试回测任务"
        assert model.status == "running"

    @pytest.mark.unit
    def test_create_from_params_auto_generates_run_id(self, crud_instance):
        """未提供 run_id 时自动生成"""
        model = crud_instance._create_from_params()

        assert model.run_id is not None
        assert model.run_id == model.uuid
        assert model.status == "created"

    @pytest.mark.unit
    def test_create_from_params_default_source(self, crud_instance):
        """默认 source 为 SIM"""
        model = crud_instance._create_from_params()
        assert model.source == SOURCE_TYPES.SIM.value


# ============================================================
# Business Helper 测试
# ============================================================


class TestBacktestTaskCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_get_tasks_by_engine(self, crud_instance):
        """get_tasks_by_engine 构造正确的 filters 并调用 self.find"""
        crud_instance.find = MagicMock(return_value=[])

        crud_instance.get_tasks_by_engine(engine_id="engine-001", page=0, page_size=20)

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["engine_id"] == "engine-001"
        assert call_kwargs["filters"]["is_del"] is False
        assert call_kwargs["order_by"] == "create_at"
        assert call_kwargs["desc_order"] is True

    @pytest.mark.unit
    def test_count_by_status(self, crud_instance):
        """count_by_status 构造正确的 filters 并调用 self.count"""
        crud_instance.count = MagicMock(return_value=5)

        result = crud_instance.count_by_status(status="running")

        crud_instance.count.assert_called_once()
        call_kwargs = crud_instance.count.call_args[1]
        assert call_kwargs["filters"]["status"] == "running"
        assert call_kwargs["filters"]["is_del"] is False
        assert result == 5

    @pytest.mark.unit
    def test_get_by_uuid(self, crud_instance):
        """get_by_uuid 构造正确的 filters 并调用 self.find"""
        crud_instance.find = MagicMock(return_value=[])

        result = crud_instance.get_by_uuid(uuid="task-uuid-001")

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["uuid"] == "task-uuid-001"
        assert call_kwargs["filters"]["is_del"] is False
        assert result is None


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestBacktestTaskCRUDConstruction:
    """BacktestTaskCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction(self, crud_instance):
        """验证 model_class 为 MBacktestTask，_is_mysql 为 True"""
        from ginkgo.data.models import MBacktestTask

        assert crud_instance.model_class is MBacktestTask
        assert crud_instance._is_mysql is True
        assert crud_instance._is_clickhouse is False

    @pytest.mark.unit
    def test_has_required_methods(self, crud_instance):
        """验证 BaseCRUD 的关键 hook 方法都存在且可调用"""
        required_methods = [
            "_do_add", "_do_find", "_do_modify", "_do_remove", "_do_count",
            "_get_field_config", "_create_from_params",
        ]

        for method_name in required_methods:
            assert hasattr(crud_instance, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(crud_instance, method_name)), f"不可调用: {method_name}"
