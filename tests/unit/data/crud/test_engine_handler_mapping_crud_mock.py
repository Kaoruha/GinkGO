"""
性能: 220MB RSS, 1.97s, 9 tests [PASS]
EngineHandlerMappingCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MEngineHandlerMapping 模型
- Business Helper: find_by_engine, find_by_handler
- 构造与类型检查
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 EngineHandlerMappingCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def mapping_crud():
    """构造 EngineHandlerMappingCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.engine_handler_mapping_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.engine_handler_mapping_crud import EngineHandlerMappingCRUD
        crud = EngineHandlerMappingCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestMappingFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, mapping_crud):
        """配置包含 engine_id 和 handler_id"""
        config = mapping_crud._get_field_config()

        required_keys = {"engine_id", "handler_id"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_engine_id_validation(self, mapping_crud):
        """engine_id 字段为 string 类型，min=1"""
        config = mapping_crud._get_field_config()

        assert config["engine_id"]["type"] == "string"
        assert config["engine_id"]["min"] == 1

    @pytest.mark.unit
    def test_field_config_handler_id_validation(self, mapping_crud):
        """handler_id 字段为 string 类型，min=1"""
        config = mapping_crud._get_field_config()

        assert config["handler_id"]["type"] == "string"
        assert config["handler_id"]["min"] == 1


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestMappingEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_source(self, mapping_crud):
        """映射包含 source 枚举"""
        mappings = mapping_crud._get_enum_mappings()

        assert "source" in mappings
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestMappingCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, mapping_crud):
        """传入完整参数，返回 MEngineHandlerMapping 模型且属性正确"""
        from ginkgo.data.models import MEngineHandlerMapping

        params = {
            "engine_id": "engine-001",
            "handler_id": "handler-001",
        }

        model = mapping_crud._create_from_params(**params)

        assert isinstance(model, MEngineHandlerMapping)
        assert model.engine_id == "engine-001"
        assert model.handler_id == "handler-001"

    @pytest.mark.unit
    def test_create_from_params_default_source(self, mapping_crud):
        """缺失 source 字段使用默认值 SOURCE_TYPES.SIM"""
        model = mapping_crud._create_from_params(
            engine_id="engine-001",
            handler_id="handler-001",
        )

        assert model.source == SOURCE_TYPES.SIM.value


# ============================================================
# Business Helper 测试
# ============================================================


class TestMappingBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_engine(self, mapping_crud):
        """find_by_engine 构造正确的 filters 并调用 self.find"""
        mapping_crud.find = MagicMock(return_value=[])

        mapping_crud.find_by_engine(engine_id="engine-001")

        mapping_crud.find.assert_called_once()
        call_kwargs = mapping_crud.find.call_args[1]
        assert call_kwargs["filters"]["engine_id"] == "engine-001"
        assert call_kwargs["order_by"] == "uuid"

    @pytest.mark.unit
    def test_find_by_handler(self, mapping_crud):
        """find_by_handler 构造正确的 filters 并调用 self.find"""
        mapping_crud.find = MagicMock(return_value=[])

        mapping_crud.find_by_handler(handler_id="handler-001")

        mapping_crud.find.assert_called_once()
        call_kwargs = mapping_crud.find.call_args[1]
        assert call_kwargs["filters"]["handler_id"] == "handler-001"
        assert call_kwargs["order_by"] == "uuid"


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestMappingConstruction:
    """EngineHandlerMappingCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_mapping_crud_construction(self, mapping_crud):
        """验证 model_class 为 MEngineHandlerMapping，_is_mysql 为 True"""
        from ginkgo.data.models import MEngineHandlerMapping

        assert mapping_crud.model_class is MEngineHandlerMapping
        assert mapping_crud._is_mysql is True
        assert mapping_crud._is_clickhouse is False

