"""
性能: 218MB RSS, 1.91s, 7 tests [PASS]
BrokerInstanceCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置（portfolio_id, live_account_id, state）
- _get_enum_mappings: 枚举映射（SOURCE_TYPES）
- Business Helper: get_broker_by_portfolio, check_timeout
- 构造与类型检查
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 BrokerInstanceCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def crud_instance():
    """构造 BrokerInstanceCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.broker_instance_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.broker_instance_crud import BrokerInstanceCRUD
        crud = BrokerInstanceCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestBrokerInstanceCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, crud_instance):
        """配置包含 portfolio_id, live_account_id, state"""
        config = crud_instance._get_field_config()

        required_keys = {"portfolio_id", "live_account_id", "state"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_portfolio_id_validation(self, crud_instance):
        """portfolio_id 字段为 string 类型，min=1, max=32, required=True"""
        config = crud_instance._get_field_config()

        assert config["portfolio_id"]["type"] == "string"
        assert config["portfolio_id"]["min"] == 1
        assert config["portfolio_id"]["max"] == 32
        assert config["portfolio_id"]["required"] is True

    @pytest.mark.unit
    def test_field_config_state_validation(self, crud_instance):
        """state 字段为 string 类型，min=5, max=20"""
        config = crud_instance._get_field_config()

        assert config["state"]["type"] == "string"
        assert config["state"]["min"] == 5
        assert config["state"]["max"] == 20


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestBrokerInstanceCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_source(self, crud_instance):
        """映射包含 source 枚举"""
        mappings = crud_instance._get_enum_mappings()

        assert "source" in mappings
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# Business Helper 测试
# ============================================================


class TestBrokerInstanceCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_get_broker_by_portfolio(self, crud_instance):
        """get_broker_by_portfolio 构造正确的 filters 并调用 self.find"""
        crud_instance.find = MagicMock(return_value=[])

        result = crud_instance.get_broker_by_portfolio(portfolio_id="portfolio-001")

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert call_kwargs["filters"]["is_del"] is False
        assert call_kwargs["limit"] == 1
        assert result is None

    @pytest.mark.unit
    def test_check_timeout(self, crud_instance):
        """check_timeout 调用 self.find 查询所有活跃实例"""
        crud_instance.find = MagicMock(return_value=[])

        # patch datetime.timezone.utc 避免 AttributeError
        from datetime import datetime, timezone
        with patch("ginkgo.data.crud.broker_instance_crud.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 1, 1, tzinfo=timezone.utc)
            mock_dt.timezone = timezone

            result = crud_instance.check_timeout(timeout_seconds=30)

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["is_del"] is False
        assert result == []


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestBrokerInstanceCRUDConstruction:
    """BrokerInstanceCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction(self, crud_instance):
        """验证 model_class 为 MBrokerInstance，_is_mysql 为 True"""
        from ginkgo.data.models.model_broker_instance import MBrokerInstance

        assert crud_instance.model_class is MBrokerInstance
        assert crud_instance._is_mysql is True
        assert crud_instance._is_clickhouse is False

