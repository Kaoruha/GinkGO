"""
FileCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MFile 模型
- Business Helper: find_by_filename, find_by_type
- 构造与类型检查
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import FILE_TYPES, SOURCE_TYPES


# ============================================================
# 辅助：构造 FileCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def file_crud():
    """构造 FileCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.file_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.file_crud import FileCRUD
        crud = FileCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestFileCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, file_crud):
        """配置包含 type/name/data"""
        config = file_crud._get_field_config()

        required_keys = {"type", "name", "data"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_type_is_enum(self, file_crud):
        """type 字段为枚举类型"""
        config = file_crud._get_field_config()

        assert config["type"]["type"] == "enum"
        assert "choices" in config["type"]

    @pytest.mark.unit
    def test_field_config_name_validation(self, file_crud):
        """name 字段为 string 类型，min=1, max=40"""
        config = file_crud._get_field_config()

        assert config["name"]["type"] == "string"
        assert config["name"]["min"] == 1
        assert config["name"]["max"] == 40

    @pytest.mark.unit
    def test_field_config_data_is_bytes(self, file_crud):
        """data 字段类型为 bytes"""
        config = file_crud._get_field_config()

        assert config["data"]["type"] == "bytes"


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestFileCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_type(self, file_crud):
        """映射包含 type 枚举"""
        mappings = file_crud._get_enum_mappings()

        assert "type" in mappings
        assert mappings["type"] is FILE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestFileCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, file_crud):
        """传入完整参数，返回 MFile 模型且属性正确"""
        from ginkgo.data.models import MFile

        params = {
            "type": FILE_TYPES.STRATEGY,
            "name": "my_strategy.py",
            "data": b"print('hello')",
        }

        mfile = file_crud._create_from_params(**params)

        assert isinstance(mfile, MFile)
        assert mfile.name == "my_strategy.py"
        assert mfile.data == b"print('hello')"
        assert mfile.type == FILE_TYPES.STRATEGY.value

    @pytest.mark.unit
    def test_create_from_params_defaults(self, file_crud):
        """缺失字段使用默认值"""
        mfile = file_crud._create_from_params()

        assert mfile.name == "ginkgo_file"
        assert mfile.data == b""
        assert mfile.type == FILE_TYPES.OTHER.value
        assert mfile.source == SOURCE_TYPES.SIM.value

    @pytest.mark.unit
    def test_create_from_params_string_type_conversion(self, file_crud):
        """字符串类型自动映射到枚举值"""
        mfile = file_crud._create_from_params(
            type="PYTHON",
            name="test.py",
        )

        assert mfile.type == FILE_TYPES.STRATEGY.value


# ============================================================
# Business Helper 测试
# ============================================================


class TestFileCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_filename(self, file_crud):
        """find_by_filename 构造正确的 filters 并调用 self.find"""
        file_crud.find = MagicMock(return_value=[])

        file_crud.find_by_filename(filename="%strategy%")

        file_crud.find.assert_called_once()
        call_kwargs = file_crud.find.call_args[1]
        assert call_kwargs["filters"]["name__like"] == "%strategy%"
        assert call_kwargs["desc_order"] is True
        assert call_kwargs["order_by"] == "update_at"

    @pytest.mark.unit
    def test_find_by_type(self, file_crud):
        """find_by_type 构造正确的 filters 并调用 self.find"""
        file_crud.find = MagicMock(return_value=[])

        file_crud.find_by_type(file_type="STRATEGY")

        file_crud.find.assert_called_once()
        call_kwargs = file_crud.find.call_args[1]
        assert call_kwargs["filters"]["type"] == FILE_TYPES.STRATEGY
        assert call_kwargs["desc_order"] is True


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestFileCRUDConstruction:
    """FileCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_file_crud_construction(self, file_crud):
        """验证 model_class 为 MFile，_is_mysql 为 True"""
        from ginkgo.data.models import MFile

        assert file_crud.model_class is MFile
        assert file_crud._is_mysql is True
        assert file_crud._is_clickhouse is False

    @pytest.mark.unit
    def test_file_crud_has_required_methods(self, file_crud):
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
            assert hasattr(file_crud, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(file_crud, method_name)), f"不可调用: {method_name}"
