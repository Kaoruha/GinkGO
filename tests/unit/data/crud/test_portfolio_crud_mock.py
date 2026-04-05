"""
PortfolioCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MPortfolio 模型
- Business Helper: find_by_uuid, find_by_name_pattern
- 构造与类型检查
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES, PORTFOLIO_MODE_TYPES, PORTFOLIO_RUNSTATE_TYPES


# ============================================================
# 辅助：构造 PortfolioCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def portfolio_crud():
    """构造 PortfolioCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.portfolio_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.portfolio_crud import PortfolioCRUD
        crud = PortfolioCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestPortfolioCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, portfolio_crud):
        """配置包含 name/desc/mode/state"""
        config = portfolio_crud._get_field_config()

        required_keys = {"name", "desc", "mode", "state"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_name_validation(self, portfolio_crud):
        """name 字段为 string 类型，min=1, max=64"""
        config = portfolio_crud._get_field_config()

        assert config["name"]["type"] == "string"
        assert config["name"]["min"] == 1
        assert config["name"]["max"] == 64

    @pytest.mark.unit
    def test_field_config_mode_is_enum(self, portfolio_crud):
        """mode 字段为枚举类型，默认值为 BACKTEST"""
        config = portfolio_crud._get_field_config()

        assert config["mode"]["type"] == "enum"
        assert config["mode"]["enum_class"] is PORTFOLIO_MODE_TYPES
        assert config["mode"]["default"] == PORTFOLIO_MODE_TYPES.BACKTEST.value

    @pytest.mark.unit
    def test_field_config_state_is_enum(self, portfolio_crud):
        """state 字段为枚举类型，默认值为 INITIALIZED"""
        config = portfolio_crud._get_field_config()

        assert config["state"]["type"] == "enum"
        assert config["state"]["enum_class"] is PORTFOLIO_RUNSTATE_TYPES
        assert config["state"]["default"] == PORTFOLIO_RUNSTATE_TYPES.INITIALIZED.value


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestPortfolioCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_three_enums(self, portfolio_crud):
        """映射包含 source/mode/state 三个枚举"""
        mappings = portfolio_crud._get_enum_mappings()

        assert "source" in mappings
        assert "mode" in mappings
        assert "state" in mappings
        assert mappings["source"] is SOURCE_TYPES
        assert mappings["mode"] is PORTFOLIO_MODE_TYPES
        assert mappings["state"] is PORTFOLIO_RUNSTATE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestPortfolioCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, portfolio_crud):
        """传入完整参数，返回 MPortfolio 模型且属性正确"""
        from ginkgo.data.models import MPortfolio

        params = {
            "name": "my_portfolio",
            "desc": "测试组合",
            "mode": PORTFOLIO_MODE_TYPES.LIVE,
            "state": PORTFOLIO_RUNSTATE_TYPES.RUNNING,
        }

        mportfolio = portfolio_crud._create_from_params(**params)

        assert isinstance(mportfolio, MPortfolio)
        assert mportfolio.name == "my_portfolio"
        assert mportfolio.desc == "测试组合"
        # MPortfolio 模型将枚举存储为 int 值
        assert mportfolio.mode == PORTFOLIO_MODE_TYPES.LIVE.value
        assert mportfolio.state == PORTFOLIO_RUNSTATE_TYPES.RUNNING.value

    @pytest.mark.unit
    def test_create_from_params_defaults(self, portfolio_crud):
        """缺失字段使用默认值"""
        mportfolio = portfolio_crud._create_from_params()

        assert mportfolio.name == "test_portfolio"
        assert mportfolio.mode == PORTFOLIO_MODE_TYPES.BACKTEST.value
        assert mportfolio.state == PORTFOLIO_RUNSTATE_TYPES.INITIALIZED.value
        assert mportfolio.source == SOURCE_TYPES.SIM.value
        assert mportfolio.initial_capital == 100000.0


# ============================================================
# Business Helper 测试
# ============================================================


class TestPortfolioCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_uuid(self, portfolio_crud):
        """find_by_uuid 构造正确的 filters 并调用 self.find"""
        portfolio_crud.find = MagicMock(return_value=[])

        portfolio_crud.find_by_uuid(uuid="portfolio-uuid-001")

        portfolio_crud.find.assert_called_once()
        call_kwargs = portfolio_crud.find.call_args[1]
        assert call_kwargs["filters"]["uuid"] == "portfolio-uuid-001"
        assert call_kwargs["page_size"] == 1

    @pytest.mark.unit
    def test_find_by_name_pattern(self, portfolio_crud):
        """find_by_name_pattern 构造正确的 filters 并调用 self.find"""
        portfolio_crud.find = MagicMock(return_value=[])

        portfolio_crud.find_by_name_pattern(name_pattern="%test%")

        portfolio_crud.find.assert_called_once()
        call_kwargs = portfolio_crud.find.call_args[1]
        assert call_kwargs["filters"]["name__like"] == "%test%"
        assert call_kwargs["desc_order"] is True
        assert call_kwargs["order_by"] == "update_at"


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestPortfolioCRUDConstruction:
    """PortfolioCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_portfolio_crud_construction(self, portfolio_crud):
        """验证 model_class 为 MPortfolio，_is_mysql 为 True"""
        from ginkgo.data.models import MPortfolio

        assert portfolio_crud.model_class is MPortfolio
        assert portfolio_crud._is_mysql is True
        assert portfolio_crud._is_clickhouse is False

    @pytest.mark.unit
    def test_portfolio_crud_has_required_methods(self, portfolio_crud):
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
            assert hasattr(portfolio_crud, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(portfolio_crud, method_name)), f"不可调用: {method_name}"
