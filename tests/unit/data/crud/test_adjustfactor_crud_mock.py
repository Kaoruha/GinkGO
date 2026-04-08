"""
性能: 217MB RSS, 1.93s, 11 tests [PASS]
AdjustfactorCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MAdjustfactor 模型
- Business Helper: find_by_code, count_by_code
- 构造与类型检查
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 AdjustfactorCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def adjustfactor_crud():
    """构造 AdjustfactorCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.adjustfactor_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.adjustfactor_crud import AdjustfactorCRUD
        crud = AdjustfactorCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestAdjustfactorCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, adjustfactor_crud):
        """配置包含 code/foreadjustfactor/backadjustfactor/adjustfactor/timestamp"""
        config = adjustfactor_crud._get_field_config()

        required_keys = {
            "code", "foreadjustfactor", "backadjustfactor",
            "adjustfactor", "timestamp",
        }
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_code_is_string(self, adjustfactor_crud):
        """code 字段类型为 string，min=1"""
        config = adjustfactor_crud._get_field_config()

        assert config["code"]["type"] == "string"
        assert config["code"]["min"] == 1

    @pytest.mark.unit
    def test_field_config_factor_validation(self, adjustfactor_crud):
        """复权因子字段 min=0.001"""
        config = adjustfactor_crud._get_field_config()

        for field in ("foreadjustfactor", "backadjustfactor", "adjustfactor"):
            assert field in config, f"缺少字段: {field}"
            assert config[field]["min"] == 0.001, f"{field} 的 min 应为 0.001"

    @pytest.mark.unit
    def test_field_config_factor_types(self, adjustfactor_crud):
        """复权因子字段支持 decimal/float/int"""
        config = adjustfactor_crud._get_field_config()

        for field in ("foreadjustfactor", "backadjustfactor", "adjustfactor"):
            assert isinstance(config[field]["type"], list), f"{field} type 应为列表"


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestAdjustfactorCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_source(self, adjustfactor_crud):
        """映射包含 source 枚举"""
        mappings = adjustfactor_crud._get_enum_mappings()

        assert "source" in mappings
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestAdjustfactorCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, adjustfactor_crud):
        """传入完整参数，返回 MAdjustfactor 模型且属性正确"""
        params = {
            "code": "000001.SZ",
            "foreadjustfactor": Decimal("1.5"),
            "backadjustfactor": Decimal("0.8"),
            "adjustfactor": Decimal("1.2"),
            "timestamp": datetime(2024, 1, 15, 9, 30, 0),
            "source": SOURCE_TYPES.TUSHARE,
        }

        model = adjustfactor_crud._create_from_params(**params)

        assert model.code == "000001.SZ"
        assert model.foreadjustfactor == Decimal("1.5")
        assert model.backadjustfactor == Decimal("0.8")
        assert model.adjustfactor == Decimal("1.2")

    @pytest.mark.unit
    def test_create_from_params_defaults(self, adjustfactor_crud):
        """缺失因子字段使用默认值 1.0"""
        model = adjustfactor_crud._create_from_params(code="000002.SZ")

        assert model.code == "000002.SZ"
        assert model.foreadjustfactor == Decimal("1.0")
        assert model.backadjustfactor == Decimal("1.0")
        assert model.adjustfactor == Decimal("1.0")
        assert model.source == SOURCE_TYPES.TUSHARE.value

    @pytest.mark.unit
    def test_create_from_params_timestamp_normalized(self, adjustfactor_crud):
        """timestamp 经过 datetime_normalize 处理"""
        with patch("ginkgo.data.crud.adjustfactor_crud.datetime_normalize") as mock_normalize:
            mock_normalize.return_value = datetime(2024, 6, 1)

            model = adjustfactor_crud._create_from_params(code="000001.SZ", timestamp="2024-06-01")

            mock_normalize.assert_called_once_with("2024-06-01")
            assert model.timestamp == datetime(2024, 6, 1)


# ============================================================
# Business Helper 测试
# ============================================================


class TestAdjustfactorCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_code(self, adjustfactor_crud):
        """find_by_code 构造正确的 filters 并调用 self.find"""
        adjustfactor_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.adjustfactor_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            adjustfactor_crud.find_by_code(
                code="000001.SZ",
                start_date="2024-01-01",
                end_date="2024-12-31",
            )

        adjustfactor_crud.find.assert_called_once()
        call_kwargs = adjustfactor_crud.find.call_args[1]
        assert call_kwargs["filters"]["code"] == "000001.SZ"
        assert call_kwargs["order_by"] == "timestamp"

    @pytest.mark.unit
    def test_count_by_code(self, adjustfactor_crud):
        """count_by_code 调用 self.count 并传入正确 filters"""
        adjustfactor_crud.count = MagicMock(return_value=42)

        result = adjustfactor_crud.count_by_code("000001.SZ")

        assert result == 42
        adjustfactor_crud.count.assert_called_once_with({"code": "000001.SZ"})


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestAdjustfactorCRUDConstruction:
    """AdjustfactorCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_adjustfactor_crud_construction(self, adjustfactor_crud):
        """验证 model_class 为 MAdjustfactor，_is_clickhouse 为 True"""
        from ginkgo.data.models import MAdjustfactor

        assert adjustfactor_crud.model_class is MAdjustfactor
        assert adjustfactor_crud._is_clickhouse is True
        assert adjustfactor_crud._is_mysql is False

