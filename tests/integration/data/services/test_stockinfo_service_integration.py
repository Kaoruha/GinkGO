"""
StockinfoService 集成测试 - 连接真实数据库通过CRUD操作

测试StockinfoService与MySQL数据库的集成，验证股票基础信息的查询、统计、
数据质量验证和完整性检查等功能。
需要数据库环境可用，使用 SOURCE_TYPES.TEST 隔离测试数据。

运行方式:
    pytest tests/integration/data/services/test_stockinfo_service_integration.py -v -m "database and integration"
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES, CURRENCY_TYPES
from ginkgo.data.services.stockinfo_service import StockinfoService
from ginkgo.data.services.base_service import ServiceResult


def _skip_if_db_unavailable(exc):
    """数据库不可用时跳过测试的辅助函数"""
    pytest.skip(f"数据库不可用，跳过集成测试: {exc}")


def _create_stockinfo_service():
    """创建连接真实数据库的StockinfoService实例"""
    from ginkgo.data.crud.stock_info_crud import StockInfoCRUD

    try:
        stockinfo_crud = StockInfoCRUD()
        return StockinfoService(
            crud_repo=stockinfo_crud,
            data_source=None
        )
    except Exception as e:
        _skip_if_db_unavailable(e)


@pytest.fixture(scope="module")
def stockinfo_service():
    """StockinfoService fixture - 模块级别共享"""
    return _create_stockinfo_service()


@pytest.fixture(scope="function")
def stockinfo_service_with_cleanup(stockinfo_service):
    """每次测试后清理测试数据的StockinfoService fixture"""
    yield stockinfo_service
    # 清理测试创建的股票信息
    try:
        stockinfo_service._crud_repo.remove(filters={"code": "999999.SZ"})
    except Exception:
        pass


@pytest.mark.database
@pytest.mark.integration
class TestStockinfoServiceConstruction:
    """1. StockinfoService构造与数据库连接测试"""

    def test_service_construction(self, stockinfo_service):
        """测试StockinfoService使用真实CRUD成功构造"""
        assert stockinfo_service is not None
        assert isinstance(stockinfo_service, StockinfoService)

    def test_service_crud_repo_connected(self, stockinfo_service):
        """测试CRUD仓库已正确注入"""
        assert stockinfo_service._crud_repo is not None

    def test_service_data_source_none(self, stockinfo_service):
        """测试无数据源时服务仍可正常创建"""
        assert stockinfo_service._data_source is None

    def test_service_name(self, stockinfo_service):
        """测试服务名称正确设置"""
        assert stockinfo_service.service_name == "StockinfoService"


@pytest.mark.database
@pytest.mark.integration
class TestStockinfoServiceQuery:
    """2. 股票信息查询测试"""

    def test_get_stockinfos(self, stockinfo_service):
        """测试查询所有股票信息"""
        result = stockinfo_service.get()

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None

    def test_get_stockinfo_by_code(self, stockinfo_service):
        """测试按股票代码查询"""
        result = stockinfo_service.get(code="000001.SZ")

        assert isinstance(result, ServiceResult)
        assert result.success is True

    def test_get_stockinfo_with_limit(self, stockinfo_service):
        """测试分页查询股票信息"""
        result = stockinfo_service.get(limit=5)

        assert isinstance(result, ServiceResult)
        assert result.success is True

    def test_get_stockinfo_by_name(self, stockinfo_service):
        """测试按名称模糊查询"""
        result = stockinfo_service.get(name="平安")

        assert isinstance(result, ServiceResult)
        assert result.success is True

    def test_get_nonexistent_code(self, stockinfo_service):
        """测试查询不存在的股票代码"""
        result = stockinfo_service.get(code="NONEXISTENT.SZ")

        assert isinstance(result, ServiceResult)
        assert result.success is True


@pytest.mark.database
@pytest.mark.integration
class TestStockinfoServiceCount:
    """3. 股票信息统计测试"""

    def test_count_all_stockinfo(self, stockinfo_service):
        """测试统计所有股票信息数量"""
        result = stockinfo_service.count()

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None
        assert isinstance(result.data, int)
        assert result.data >= 0

    def test_count_stockinfo_by_code(self, stockinfo_service):
        """测试按代码统计股票数量"""
        result = stockinfo_service.count(code="000001.SZ")

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert isinstance(result.data, int)


@pytest.mark.database
@pytest.mark.integration
class TestStockinfoServiceHealthCheck:
    """4. 健康检查测试"""

    def test_health_check(self, stockinfo_service):
        """测试服务健康检查"""
        result = stockinfo_service.health_check()

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None

        # 健康检查返回的数据应包含服务名称和记录数
        assert "service_name" in result.data
        assert "total_records" in result.data


@pytest.mark.database
@pytest.mark.integration
class TestStockinfoServiceValidation:
    """5. 数据质量验证测试"""

    def test_validate_all_data(self, stockinfo_service):
        """测试验证所有股票信息数据质量"""
        result = stockinfo_service.validate()

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None

    def test_validate_with_filter(self, stockinfo_service):
        """测试带过滤条件的数据验证"""
        result = stockinfo_service.validate(filters={"code": "000001.SZ"})

        assert isinstance(result, ServiceResult)
        assert result.success is True


@pytest.mark.database
@pytest.mark.integration
class TestStockinfoServiceIntegrity:
    """6. 数据完整性检查测试"""

    def test_check_integrity_all(self, stockinfo_service):
        """测试检查所有股票信息数据完整性"""
        result = stockinfo_service.check_integrity()

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None

    def test_check_integrity_with_filter(self, stockinfo_service):
        """测试带过滤条件的完整性检查"""
        result = stockinfo_service.check_integrity(filters={"code": "000001.SZ"})

        assert isinstance(result, ServiceResult)
        assert result.success is True


@pytest.mark.database
@pytest.mark.integration
class TestStockinfoServiceWriteOperations:
    """7. 股票信息写入操作测试（使用TEST标记隔离）"""

    def test_add_and_get_test_stockinfo(self, stockinfo_service_with_cleanup):
        """测试写入测试股票信息后能正确查询"""
        from ginkgo.entities import StockInfo

        test_stock = StockInfo(
            code="999999.SZ",
            code_name="测试股票",
            industry="测试行业",
            market=MARKET_TYPES.CHINA,
            currency=CURRENCY_TYPES.CNY,
            list_date=datetime(2025, 1, 1),
            delist_date=datetime(2099, 12, 31),
            source=SOURCE_TYPES.TEST
        )
        test_stock._source = SOURCE_TYPES.TEST

        # 写入数据
        stockinfo_service_with_cleanup._crud_repo.add_batch([test_stock])

        # 验证查询
        result = stockinfo_service_with_cleanup.get(code="999999.SZ")
        assert result.success is True

        # 验证计数
        count_result = stockinfo_service_with_cleanup.count(code="999999.SZ")
        assert count_result.success is True
        assert count_result.data > 0

    def test_remove_test_stockinfo(self, stockinfo_service_with_cleanup):
        """测试删除测试股票信息"""
        from ginkgo.entities import StockInfo

        test_stock = StockInfo(
            code="999999.SZ",
            code_name="待删除股票",
            industry="测试行业",
            market=MARKET_TYPES.CHINA,
            currency=CURRENCY_TYPES.CNY,
            list_date=datetime(2025, 1, 1),
            delist_date=datetime(2099, 12, 31),
            source=SOURCE_TYPES.TEST
        )
        test_stock._source = SOURCE_TYPES.TEST

        # 写入
        stockinfo_service_with_cleanup._crud_repo.add_batch([test_stock])

        # 删除
        stockinfo_service_with_cleanup._crud_repo.remove(filters={"code": "999999.SZ"})

        # 验证已删除
        result = stockinfo_service_with_cleanup.exists(code="999999.SZ")
        assert result.success is True
        assert result.data is False


@pytest.mark.database
@pytest.mark.integration
class TestStockinfoServiceExists:
    """8. 股票存在性检查测试"""

    def test_exists_real_code(self, stockinfo_service):
        """测试检查已存在的股票代码"""
        # 假设数据库中可能有000001.SZ，也可能没有
        result = stockinfo_service.exists(code="000001.SZ")
        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert isinstance(result.data, bool)

    def test_exists_nonexistent_code(self, stockinfo_service):
        """测试检查不存在的股票代码"""
        result = stockinfo_service.exists(code="NONEXISTENT999.SZ")
        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is False
