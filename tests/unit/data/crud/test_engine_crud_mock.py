"""
EngineCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MEngine 模型
- Business Helper: find_by_uuid, find_by_status
- 构造与类型检查
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from ginkgo.enums import ENGINESTATUS_TYPES, SOURCE_TYPES


# ============================================================
# 辅助：构造 EngineCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def engine_crud():
    """构造 EngineCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.engine_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.engine_crud import EngineCRUD
        crud = EngineCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestEngineCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, engine_crud):
        """配置包含 name/status/source/is_live/backtest_start_date/backtest_end_date"""
        config = engine_crud._get_field_config()

        required_keys = {"name", "status", "source", "is_live", "backtest_start_date", "backtest_end_date"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_name_validation(self, engine_crud):
        """name 字段为 string 类型，min=1, max=100"""
        config = engine_crud._get_field_config()

        assert config["name"]["type"] == "string"
        assert config["name"]["min"] == 1
        assert config["name"]["max"] == 100

    @pytest.mark.unit
    def test_field_config_status_default(self, engine_crud):
        """status 字段默认值为 ENGINESTATUS_TYPES.IDLE"""
        config = engine_crud._get_field_config()

        assert config["status"]["type"] == "ENGINESTATUS_TYPES"
        assert config["status"]["default"] == ENGINESTATUS_TYPES.IDLE.value

    @pytest.mark.unit
    def test_field_config_optional_date_fields(self, engine_crud):
        """backtest_start_date/backtest_end_date 为可选 datetime"""
        config = engine_crud._get_field_config()

        assert config["backtest_start_date"]["type"] == "datetime"
        assert config["backtest_start_date"]["required"] is False
        assert config["backtest_end_date"]["type"] == "datetime"
        assert config["backtest_end_date"]["required"] is False


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestEngineCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_status_and_source(self, engine_crud):
        """映射包含 status 和 source 两个枚举"""
        mappings = engine_crud._get_enum_mappings()

        assert "status" in mappings
        assert "source" in mappings
        assert mappings["status"] is ENGINESTATUS_TYPES
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestEngineCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, engine_crud):
        """传入完整参数，返回 MEngine 模型且属性正确"""
        from ginkgo.data.models import MEngine

        params = {
            "name": "test_backtest_engine",
            "status": ENGINESTATUS_TYPES.RUNNING,
            "is_live": False,
            "source": SOURCE_TYPES.BACKTEST,
        }

        mengine = engine_crud._create_from_params(**params)

        assert isinstance(mengine, MEngine)
        assert mengine.name == "test_backtest_engine"
        assert mengine.is_live is False
        # MEngine 模型将枚举存储为 int 值
        assert mengine.status == ENGINESTATUS_TYPES.RUNNING.value
        assert mengine.source == SOURCE_TYPES.BACKTEST.value

    @pytest.mark.unit
    def test_create_from_params_defaults(self, engine_crud):
        """缺失字段使用默认值"""
        mengine = engine_crud._create_from_params()

        assert mengine.name == "test_engine"
        # validate_input(None) 对 status 返回 -1，对 source 返回 SIM.value=1
        assert mengine.status == -1
        assert mengine.source == SOURCE_TYPES.SIM.value
        assert mengine.is_live is False


# ============================================================
# Business Helper 测试
# ============================================================


class TestEngineCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_uuid(self, engine_crud):
        """find_by_uuid 构造正确的 filters 并调用 self.find"""
        engine_crud.find = MagicMock(return_value=[])

        engine_crud.find_by_uuid(uuid="engine-uuid-001")

        engine_crud.find.assert_called_once()
        call_kwargs = engine_crud.find.call_args[1]
        assert call_kwargs["filters"]["uuid"] == "engine-uuid-001"
        assert call_kwargs["page_size"] == 1

    @pytest.mark.unit
    def test_find_by_status(self, engine_crud):
        """find_by_status 调用 self.find 且 desc_order=True"""
        engine_crud.find = MagicMock(return_value=[])

        engine_crud.find_by_status(status=ENGINESTATUS_TYPES.RUNNING)

        engine_crud.find.assert_called_once()
        call_kwargs = engine_crud.find.call_args[1]
        assert call_kwargs["filters"]["status"] == ENGINESTATUS_TYPES.RUNNING
        assert call_kwargs["desc_order"] is True
        assert call_kwargs["order_by"] == "update_at"


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestEngineCRUDConstruction:
    """EngineCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_engine_crud_construction(self, engine_crud):
        """验证 model_class 为 MEngine，_is_mysql 为 True"""
        from ginkgo.data.models import MEngine

        assert engine_crud.model_class is MEngine
        assert engine_crud._is_mysql is True
        assert engine_crud._is_clickhouse is False

    @pytest.mark.unit
    def test_engine_crud_has_required_methods(self, engine_crud):
        """验证 BaseCRUD 的关键 hook 方法都存在且可调用"""
        required_methods = [
            "_do_add",
            "_do_find",
            "_do_modify",
            "_do_remove",
            "_do_count",
            "_get_field_config",
            "_get_enum_mappings",
            "_create_from_params",
            "_convert_input_item",
        ]

        for method_name in required_methods:
            assert hasattr(engine_crud, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(engine_crud, method_name)), f"不可调用: {method_name}"
