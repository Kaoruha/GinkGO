"""
性能: 219MB RSS, 1.9s, 13 tests [PASS]
"""

# Upstream: BaseMongoCRUD (继承)、MPortfolioConfig (模型)
# Downstream: None (单元测试)
# Role: PortfolioConfigCRUD 投资组合配置 CRUD 单元测试（Mock MongoDB 驱动）


"""
PortfolioConfigCRUD 单元测试（Mock MongoDB 驱动）

覆盖范围：
- 构造与类型检查：model_class、driver 绑定
- get_by_portfolio：按投资组合UUID查询，验证排序/过滤
- get_all_versions：查询所有版本，验证排序
- get_active_config：获取活跃配置，委托 get_by_portfolio
- create_version：创建新版本，验证版本号递增和字段继承
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
import sys


# ============================================================
# 辅助：为 MPortfolioConfig 模型注册 mock（模型文件尚不存在）
# ============================================================


@pytest.fixture(autouse=True)
def _mock_model_module(monkeypatch):
    """确保 model_portfolio_config 模块可导入，使用 monkeypatch 自动清理"""
    if "ginkgo.data.models.model_portfolio_config" in sys.modules:
        yield
        return

    import types
    mock_model_module = types.ModuleType("ginkgo.data.models.model_portfolio_config")
    mock_model_module.__path__ = []

    from ginkgo.data.models.model_mongobase import MMongoBase

    class MockPortfolioConfig(MMongoBase):
        __collection__ = "portfolio_configs"
        portfolio_uuid: str = ""
        graph_data: str = "{}"
        mode: str = "BACKTEST"
        version: int = 1
        name: str = ""
        description: str = ""
        is_template: bool = False
        is_public: bool = False
        config_locked: bool = False
        initial_cash: float = 100000.0
        usage_count: int = 0
        tags: list = []
        parent_uuid: str | None = None
        user_uuid: str = ""

    mock_model_module.MPortfolioConfig = MockPortfolioConfig
    monkeypatch.setitem(sys.modules, "ginkgo.data.models.model_portfolio_config", mock_model_module)
    yield


# ============================================================
# 辅助：构造 PortfolioConfigCRUD 实例（mock MongoDB 驱动）
# ============================================================


@pytest.fixture
def mock_driver():
    """mock GinkgoMongo 驱动"""
    driver = MagicMock()
    driver.get_collection.return_value = MagicMock()
    return driver


@pytest.fixture
def crud(mock_driver):
    """构造 PortfolioConfigCRUD 实例，注入 mock 驱动"""
    with patch("ginkgo.data.crud.base_mongo_crud.GLOG", MagicMock()), \
         patch("ginkgo.data.crud.base_mongo_crud.ModelCRUDMapping.register"):
        from ginkgo.data.crud.portfolio_config_crud import PortfolioConfigCRUD
        from ginkgo.data.models.model_portfolio_config import MPortfolioConfig
        return PortfolioConfigCRUD(driver=mock_driver)


# ============================================================
# 构造与类型检查
# ============================================================


class TestPortfolioConfigCRUDConstruction:
    """PortfolioConfigCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_model_class_is_correct(self, crud):
        """验证 model_class 为 MPortfolioConfig"""
        from ginkgo.data.models.model_portfolio_config import MPortfolioConfig
        assert crud.model_class is MPortfolioConfig

    @pytest.mark.unit
    def test_driver_is_bound(self, crud, mock_driver):
        """验证 driver 正确绑定"""
        assert crud._driver is mock_driver

    @pytest.mark.unit
    def test_get_collection_delegates_to_driver(self, crud, mock_driver):
        """_get_collection 调用 driver.get_collection"""
        crud._get_collection()
        mock_driver.get_collection.assert_called_once()

    @pytest.mark.unit
    def test_class_level_model_class(self):
        """类属性 _model_class 正确设置"""
        with patch("ginkgo.data.crud.base_mongo_crud.GLOG", MagicMock()), \
             patch("ginkgo.data.crud.base_mongo_crud.ModelCRUDMapping.register"):
            from ginkgo.data.crud.portfolio_config_crud import PortfolioConfigCRUD
            from ginkgo.data.models.model_portfolio_config import MPortfolioConfig
            assert PortfolioConfigCRUD._model_class is MPortfolioConfig


# ============================================================
# get_by_portfolio 按投资组合UUID查询
# ============================================================


class TestPortfolioConfigCRUDGetByPortfolio:
    """get_by_portfolio 按投资组合UUID查询测试"""

    @pytest.mark.unit
    def test_latest_version_query_sort(self, crud):
        """查询最新版本时使用 version 降序排序"""
        mock_collection = crud._driver.get_collection.return_value
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = [{}]
        mock_collection.find.return_value = mock_cursor

        with patch.object(crud.model_class, "from_mongo", return_value=MagicMock()):
            crud.get_by_portfolio("portfolio_123")

        # 验证 sort 参数
        mock_cursor.sort.assert_called_once_with([("version", -1)])
        mock_cursor.limit.assert_called_once_with(1)

    @pytest.mark.unit
    def test_specific_version_query(self, crud):
        """指定版本号时查询条件包含 version"""
        mock_collection = crud._driver.get_collection.return_value
        mock_collection.find_one.return_value = {
            "uuid": "cfg_uuid",
            "portfolio_uuid": "portfolio_123",
            "version": 3,
            "is_del": False,
        }

        with patch.object(crud.model_class, "from_mongo", return_value=MagicMock()):
            crud.get_by_portfolio("portfolio_123", version=3)

        call_args = mock_collection.find_one.call_args[0][0]
        assert call_args["portfolio_uuid"] == "portfolio_123"
        assert call_args["version"] == 3
        assert call_args["is_del"] is False

    @pytest.mark.unit
    def test_returns_none_when_not_found(self, crud):
        """未找到配置返回 None"""
        mock_collection = crud._driver.get_collection.return_value
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.limit.return_value = []
        mock_collection.find.return_value = mock_cursor

        result = crud.get_by_portfolio("nonexistent")

        assert result is None


# ============================================================
# get_all_versions / get_active_config
# ============================================================


class TestPortfolioConfigCRUDVersions:
    """版本管理查询测试"""

    @pytest.mark.unit
    def test_get_all_versions_sort_descending(self, crud):
        """get_all_versions 按版本号降序排列"""
        mock_collection = crud._driver.get_collection.return_value
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_collection.find.return_value = mock_cursor

        with patch.object(crud.model_class, "from_mongo", return_value=MagicMock()):
            result = crud.get_all_versions("portfolio_123")

        mock_collection.find.assert_called_once()
        call_args = mock_collection.find.call_args[0][0]
        assert call_args["portfolio_uuid"] == "portfolio_123"
        assert call_args["is_del"] is False
        mock_cursor.sort.assert_called_once_with([("version", -1)])

    @pytest.mark.unit
    def test_get_active_config_delegates(self, crud):
        """get_active_config 委托 get_by_portfolio(version=None)"""
        with patch.object(crud, "get_by_portfolio", return_value="active_config") as mock_get:
            result = crud.get_active_config("portfolio_123")

            assert result == "active_config"
            mock_get.assert_called_once_with("portfolio_123", version=None)

    @pytest.mark.unit
    def test_get_all_versions_empty(self, crud):
        """无版本时返回空列表"""
        mock_collection = crud._driver.get_collection.return_value
        mock_cursor = MagicMock()
        mock_cursor.sort.return_value = mock_cursor
        mock_collection.find.return_value = mock_cursor

        # 模拟空迭代
        mock_cursor.__iter__ = MagicMock(return_value=iter([]))

        result = crud.get_all_versions("portfolio_123")

        assert result == []


# ============================================================
# create_version 创建新版本
# ============================================================


class TestPortfolioConfigCRUDCreateVersion:
    """create_version 创建新版本测试"""

    @pytest.mark.unit
    def test_creates_version_increment(self, crud):
        """基于现有配置创建新版本，版本号+1"""
        mock_current = MagicMock()
        mock_current.version = 2
        mock_current.uuid = "parent_uuid"
        mock_current.mode = "LIVE"
        mock_current.user_uuid = "user_123"
        mock_current.name = "现有配置"
        mock_current.description = "原描述"
        mock_current.tags = ["策略A"]

        mock_collection = crud._driver.get_collection.return_value
        mock_result = MagicMock()
        mock_result.inserted_id = "new_id"
        mock_collection.insert_one.return_value = mock_result

        with patch.object(crud, "get_active_config", return_value=mock_current):
            with patch.object(crud, "add", return_value="new_config_uuid") as mock_add:
                result = crud.create_version(
                    portfolio_uuid="portfolio_123",
                    graph_data={"nodes": [], "edges": []},
                )

                assert result == "new_config_uuid"
                # 验证 add 被调用
                mock_add.assert_called_once()
                new_config = mock_add.call_args[0][0]
                assert new_config.version == 3  # 2 + 1
                assert new_config.portfolio_uuid == "portfolio_123"
                assert new_config.parent_uuid == "parent_uuid"

    @pytest.mark.unit
    def test_creates_first_version_when_none_exists(self, crud):
        """无现有配置时创建第一个版本（version=1）"""
        mock_collection = crud._driver.get_collection.return_value
        mock_result = MagicMock()
        mock_result.inserted_id = "new_id"
        mock_collection.insert_one.return_value = mock_result

        with patch.object(crud, "get_active_config", return_value=None):
            with patch.object(crud, "add", return_value="new_config_uuid") as mock_add:
                result = crud.create_version(
                    portfolio_uuid="portfolio_123",
                    graph_data={"nodes": [1], "edges": []},
                    name="新配置",
                )

                assert result == "new_config_uuid"
                new_config = mock_add.call_args[0][0]
                assert new_config.version == 1
                assert new_config.mode == "BACKTEST"  # 默认值
                assert new_config.name == "新配置"

    @pytest.mark.unit
    def test_create_version_error_returns_none(self, crud):
        """异常时返回 None"""
        with patch.object(crud, "get_active_config", side_effect=Exception("DB error")):
            result = crud.create_version(
                portfolio_uuid="portfolio_123",
                graph_data={"nodes": []},
            )

            assert result is None
