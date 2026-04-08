"""
性能: 221MB RSS, 1.94s, 16 tests [PASS]
StockInfoCRUD 单元测试 - Mock 数据库连接

测试覆盖范围:
- 字段配置结构验证
- 枚举映射验证
- _create_from_params 参数创建模型
- 构造函数验证
- 必要 Hook 方法存在性检查
- 业务辅助方法测试（find_by_market, find_by_industry, search_by_name, get_all_codes,
  _convert_input_item, _convert_models_to_business_objects）
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
from ginkgo.data.models import MStockInfo
from ginkgo.enums import MARKET_TYPES, CURRENCY_TYPES, SOURCE_TYPES


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def crud_instance():
    """绕过访问控制装饰器，创建 StockInfoCRUD 实例"""
    with patch("ginkgo.data.access_control.service_only", lambda f: f):
        with patch("ginkgo.data.crud.base_crud.GLOG") as mock_glog:
            mock_glog.DEBUG = MagicMock()
            mock_glog.INFO = MagicMock()
            mock_glog.ERROR = MagicMock()
            mock_glog.WARN = MagicMock()
            yield StockInfoCRUD()


# ============================================================================
# 字段配置与枚举映射测试
# ============================================================================


class TestStockInfoFieldConfig:
    """字段配置结构测试"""

    @pytest.mark.unit
    def test_field_config_structure(self, crud_instance):
        """验证 _get_field_config 返回正确的键和结构"""
        config = crud_instance._get_field_config()

        # 验证必填字段存在
        required_fields = ['code', 'code_name', 'industry', 'market', 'currency', 'list_date', 'source']
        for field in required_fields:
            assert field in config, f"缺少必填字段配置: {field}"

        # 验证每个字段配置都有 'type' 键
        for field_name, field_def in config.items():
            assert 'type' in field_def, f"字段 {field_name} 缺少 'type' 配置"

    @pytest.mark.unit
    def test_field_config_string_fields_have_min_max(self, crud_instance):
        """验证字符串类型字段有 min/max 限制"""
        config = crud_instance._get_field_config()

        for field_name in ['code', 'code_name', 'industry']:
            field_def = config[field_name]
            assert field_def['type'] == 'string'
            assert 'min' in field_def
            assert 'max' in field_def


class TestStockInfoEnumMappings:
    """枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings(self, crud_instance):
        """验证 _get_enum_mappings 返回正确的字段-枚举映射"""
        mappings = crud_instance._get_enum_mappings()

        assert 'market' in mappings
        assert 'currency' in mappings
        assert 'source' in mappings
        assert mappings['market'] is MARKET_TYPES
        assert mappings['currency'] is CURRENCY_TYPES
        assert mappings['source'] is SOURCE_TYPES


# ============================================================================
# _create_from_params 测试
# ============================================================================


class TestStockInfoCreateFromParams:
    """_create_from_params 参数创建模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, crud_instance):
        """使用必填字段创建 MStockInfo 模型"""
        model = crud_instance._create_from_params(
            code="000001.SZ",
            code_name="平安银行",
            industry="银行",
        )

        assert isinstance(model, MStockInfo)
        assert model.code == "000001.SZ"
        assert model.code_name == "平安银行"
        assert model.industry == "银行"

    @pytest.mark.unit
    def test_create_from_params_defaults(self, crud_instance):
        """缺失可选字段时使用默认值"""
        model = crud_instance._create_from_params(code="600000.SH")

        # 默认值验证
        assert model.code == "600000.SH"
        # MStockInfo 模型的默认值为 "ginkgo_test_name" / "ginkgo_test_industry"
        assert model.code_name == "ginkgo_test_name"
        assert model.industry == "ginkgo_test_industry"
        assert model.market == MARKET_TYPES.CHINA.value
        assert model.currency == CURRENCY_TYPES.CNY.value

    @pytest.mark.unit
    def test_create_from_params_with_all_fields(self, crud_instance):
        """传入所有字段创建完整模型"""
        model = crud_instance._create_from_params(
            code="AAPL",
            code_name="Apple Inc.",
            industry="Technology",
            market=MARKET_TYPES.NASDAQ,
            currency=CURRENCY_TYPES.USD,
            list_date="2020-01-01",
            delist_date="2025-12-31",
            source=SOURCE_TYPES.YAHOO,
        )

        assert isinstance(model, MStockInfo)
        assert model.code == "AAPL"
        assert model.market == MARKET_TYPES.NASDAQ.value
        assert model.currency == CURRENCY_TYPES.USD.value
        assert model.source == SOURCE_TYPES.YAHOO.value

    @pytest.mark.unit
    def test_create_from_params_string_market(self, crud_instance):
        """字符串形式的 market 值应被正确转换为枚举"""
        model = crud_instance._create_from_params(
            code="000001.SZ",
            market="NASDAQ",
        )
        assert model.market == MARKET_TYPES.NASDAQ.value

    @pytest.mark.unit
    def test_create_from_params_string_currency(self, crud_instance):
        """字符串形式的 currency 值应被正确转换为枚举"""
        model = crud_instance._create_from_params(
            code="000001.SZ",
            currency="USD",
        )
        assert model.currency == CURRENCY_TYPES.USD.value


# ============================================================================
# 构造函数与 Hook 方法测试
# ============================================================================


class TestStockInfoConstruction:
    """构造函数测试"""

    @pytest.mark.unit
    def test_construction(self, crud_instance):
        """验证 model_class 正确设置"""
        assert crud_instance.model_class is MStockInfo
        assert crud_instance._model_class is MStockInfo

    @pytest.mark.unit
    def test_is_mysql(self, crud_instance):
        """验证 StockInfoCRUD 使用 MySQL 存储"""
        assert crud_instance._is_mysql is True
        assert crud_instance._is_clickhouse is False


# ============================================================================
# 业务辅助方法测试
# ============================================================================


class TestStockInfoBusinessMethods:
    """业务辅助方法测试"""

    @pytest.mark.unit
    def test_find_by_market_calls_find_with_correct_filter(self, crud_instance):
        """find_by_market 应调用 find 并传入正确的 market 过滤条件"""
        crud_instance.find = MagicMock(return_value=[])
        crud_instance.find_by_market("CHINA")

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args
        filters = call_kwargs.kwargs.get('filters', call_kwargs[1].get('filters'))
        assert filters['market'] == MARKET_TYPES.CHINA

    @pytest.mark.unit
    def test_find_by_industry_calls_find_with_correct_filter(self, crud_instance):
        """find_by_industry 应调用 find 并传入正确的 industry 过滤条件"""
        crud_instance.find = MagicMock(return_value=[])
        crud_instance.find_by_industry("银行")

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args
        filters = call_kwargs.kwargs.get('filters', call_kwargs[1].get('filters'))
        assert filters['industry'] == "银行"

    @pytest.mark.unit
    def test_search_by_name_calls_find_with_like_filter(self, crud_instance):
        """search_by_name 应使用 code_name__like 模糊查询"""
        crud_instance.find = MagicMock(return_value=[])
        crud_instance.search_by_name("平安")

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args
        filters = call_kwargs.kwargs.get('filters', call_kwargs[1].get('filters'))
        assert filters['code_name__like'] == "平安"

    @pytest.mark.unit
    def test_get_all_codes_without_market(self, crud_instance):
        """get_all_codes 不传 market 时应使用空 filters"""
        crud_instance.find = MagicMock(return_value=["000001.SZ", "600000.SH"])
        codes = crud_instance.get_all_codes()

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args
        filters = call_kwargs.kwargs.get('filters', call_kwargs[1].get('filters'))
        assert filters == {}
        assert call_kwargs.kwargs.get('distinct_field') == "code"
        assert codes == ["000001.SZ", "600000.SH"]

    @pytest.mark.unit
    def test_convert_input_item_returns_none_for_unsupported_type(self, crud_instance):
        """_convert_input_item 对不支持的类型应返回 None（需要 mock _logger）"""
        crud_instance._logger = MagicMock()
        result = crud_instance._convert_input_item("not_a_stock_info")
        assert result is None

    @pytest.mark.unit
    def test_convert_models_to_business_objects(self, crud_instance):
        """_convert_models_to_business_objects 应将 MStockInfo 列表转换为 StockInfo 业务对象"""
        from ginkgo.entities import StockInfo

        model = MStockInfo(
            code="000001.SZ",
            code_name="平安银行",
            industry="银行",
        )
        model.market = MARKET_TYPES.CHINA.value
        model.currency = CURRENCY_TYPES.CNY.value
        model.source = SOURCE_TYPES.TUSHARE.value

        # Mock StockInfo.from_model 返回
        mock_stock_info = MagicMock(spec=StockInfo)
        with patch.object(StockInfo, 'from_model', return_value=mock_stock_info):
            result = crud_instance._convert_models_to_business_objects([model])

        assert len(result) == 1
        assert result[0] is mock_stock_info
