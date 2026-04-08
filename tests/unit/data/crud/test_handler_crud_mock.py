"""
性能: 220MB RSS, 1.89s, 8 tests [PASS]
HandlerCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MHandler 模型
- Business Helper: find_by_uuid, find_by_name_pattern
- 构造与类型检查
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 HandlerCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def handler_crud():
    """构造 HandlerCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.handler_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.handler_crud import HandlerCRUD
        crud = HandlerCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestHandlerCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, handler_crud):
        """配置包含 name"""
        config = handler_crud._get_field_config()

        assert "name" in config

    @pytest.mark.unit
    def test_field_config_name_validation(self, handler_crud):
        """name 字段为 string 类型，min=1, max=32"""
        config = handler_crud._get_field_config()

        assert config["name"]["type"] == "string"
        assert config["name"]["min"] == 1
        assert config["name"]["max"] == 32


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestHandlerCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_source(self, handler_crud):
        """映射包含 source 枚举"""
        mappings = handler_crud._get_enum_mappings()

        assert "source" in mappings
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestHandlerCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, handler_crud):
        """传入完整参数，返回 MHandler 模型且属性正确"""
        from ginkgo.data.models import MHandler

        params = {
            "name": "my_handler",
            "lib_path": "/path/to/lib.py",
            "func_name": "handle_event",
        }

        mhandler = handler_crud._create_from_params(**params)

        assert isinstance(mhandler, MHandler)
        assert mhandler.name == "my_handler"
        assert mhandler.lib_path == "/path/to/lib.py"
        assert mhandler.func_name == "handle_event"

    @pytest.mark.unit
    def test_create_from_params_defaults(self, handler_crud):
        """缺失字段使用默认值"""
        mhandler = handler_crud._create_from_params()

        assert mhandler.name == "test_handler"
        assert mhandler.lib_path == ""
        assert mhandler.func_name == ""
        assert mhandler.source == SOURCE_TYPES.SIM.value


# ============================================================
# Business Helper 测试
# ============================================================


class TestHandlerCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_uuid(self, handler_crud):
        """find_by_uuid 构造正确的 filters 并调用 self.find"""
        handler_crud.find = MagicMock(return_value=[])

        handler_crud.find_by_uuid(uuid="handler-uuid-001")

        handler_crud.find.assert_called_once()
        call_kwargs = handler_crud.find.call_args[1]
        assert call_kwargs["filters"]["uuid"] == "handler-uuid-001"
        assert call_kwargs["page_size"] == 1

    @pytest.mark.unit
    def test_find_by_name_pattern(self, handler_crud):
        """find_by_name_pattern 构造正确的 filters 并调用 self.find"""
        handler_crud.find = MagicMock(return_value=[])

        handler_crud.find_by_name_pattern(name_pattern="%risk%")

        handler_crud.find.assert_called_once()
        call_kwargs = handler_crud.find.call_args[1]
        assert call_kwargs["filters"]["name__like"] == "%risk%"
        assert call_kwargs["desc_order"] is True
        assert call_kwargs["order_by"] == "update_at"


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestHandlerCRUDConstruction:
    """HandlerCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_handler_crud_construction(self, handler_crud):
        """验证 model_class 为 MHandler，_is_mysql 为 True"""
        from ginkgo.data.models import MHandler

        assert handler_crud.model_class is MHandler
        assert handler_crud._is_mysql is True
        assert handler_crud._is_clickhouse is False

