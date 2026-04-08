"""
性能: 220MB RSS, 1.93s, 11 tests [PASS]
ParamCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MParam 模型
- Business Helper: find_by_mapping_id, get_param_value
- 构造与类型检查
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 ParamCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def param_crud():
    """构造 ParamCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.param_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.param_crud import ParamCRUD
        crud = ParamCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestParamCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, param_crud):
        """配置包含 mapping_id/index/value"""
        config = param_crud._get_field_config()

        required_keys = {"mapping_id", "index", "value"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_mapping_id_validation(self, param_crud):
        """mapping_id 字段为 string 类型，min=1"""
        config = param_crud._get_field_config()

        assert config["mapping_id"]["type"] == "string"
        assert config["mapping_id"]["min"] == 1

    @pytest.mark.unit
    def test_field_config_index_validation(self, param_crud):
        """index 字段为 int 类型，min=0"""
        config = param_crud._get_field_config()

        assert config["index"]["type"] == "int"
        assert config["index"]["min"] == 0

    @pytest.mark.unit
    def test_field_config_value_is_string(self, param_crud):
        """value 字段类型为 string"""
        config = param_crud._get_field_config()

        assert config["value"]["type"] == "string"


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestParamCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_source(self, param_crud):
        """映射包含 source 枚举"""
        mappings = param_crud._get_enum_mappings()

        assert "source" in mappings
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestParamCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, param_crud):
        """传入完整参数，返回 MParam 模型且属性正确"""
        from ginkgo.data.models import MParam

        params = {
            "mapping_id": "mapping-001",
            "index": 0,
            "value": "100",
        }

        mparam = param_crud._create_from_params(**params)

        assert isinstance(mparam, MParam)
        assert mparam.mapping_id == "mapping-001"
        assert mparam.index == 0
        assert mparam.value == "100"

    @pytest.mark.unit
    def test_create_from_params_defaults(self, param_crud):
        """缺失字段使用默认值"""
        mparam = param_crud._create_from_params()

        assert mparam.mapping_id == ""
        assert mparam.index == 0
        assert mparam.value == ""
        assert mparam.source == SOURCE_TYPES.SIM.value


# ============================================================
# Business Helper 测试
# ============================================================


class TestParamCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_mapping_id(self, param_crud):
        """find_by_mapping_id 构造正确的 filters 并调用 self.find"""
        param_crud.find = MagicMock(return_value=[])

        param_crud.find_by_mapping_id(mapping_id="mapping-001")

        param_crud.find.assert_called_once()
        call_kwargs = param_crud.find.call_args[1]
        assert call_kwargs["filters"]["mapping_id"] == "mapping-001"
        assert call_kwargs["order_by"] == "index"

    @pytest.mark.unit
    def test_get_param_value_with_result(self, param_crud):
        """get_param_value 有结果时返回参数值"""
        mock_param = MagicMock()
        mock_param.value = "200"
        param_crud.find = MagicMock(return_value=[mock_param])

        result = param_crud.get_param_value(mapping_id="mapping-001", index=0)

        assert result == "200"
        param_crud.find.assert_called_once()
        call_kwargs = param_crud.find.call_args[1]
        assert call_kwargs["filters"]["mapping_id"] == "mapping-001"
        assert call_kwargs["filters"]["index"] == 0

    @pytest.mark.unit
    def test_get_param_value_no_result(self, param_crud):
        """get_param_value 无结果时返回默认值"""
        param_crud.find = MagicMock(return_value=[])

        result = param_crud.get_param_value(mapping_id="mapping-001", index=99, default_value="N/A")

        assert result == "N/A"


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestParamCRUDConstruction:
    """ParamCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_param_crud_construction(self, param_crud):
        """验证 model_class 为 MParam，_is_mysql 为 True"""
        from ginkgo.data.models import MParam

        assert param_crud.model_class is MParam
        assert param_crud._is_mysql is True
        assert param_crud._is_clickhouse is False

