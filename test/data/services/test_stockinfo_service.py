"""
StockinfoService数据服务测试

测试股票信息服务的核心功能和业务逻辑
遵循pytest最佳实践，使用fixtures和参数化测试
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime
import random
import string

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.services.stockinfo_service import StockinfoService
from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.containers import container
from ginkgo.enums import SOURCE_TYPES, CURRENCY_TYPES, MARKET_TYPES
from ginkgo.libs import GCONF, datetime_normalize


# ============================================================================
# Fixtures - 共享测试资源
# ============================================================================

@pytest.fixture
def ginkgo_config():
    """配置调试模式"""
    GCONF.set_debug(True)
    yield GCONF
    GCONF.set_debug(False)


@pytest.fixture
def stockinfo_service():
    """获取StockinfoService实例"""
    return container.stockinfo_service()


@pytest.fixture
def unique_code():
    """生成唯一的测试代码"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"TEST_{timestamp}_{suffix}.SZ"


@pytest.fixture
def sample_stockinfo(stockinfo_service, unique_code):
    """创建示例股票信息"""
    try:
        record = stockinfo_service._crud_repo.create(
            code=unique_code,
            code_name=f"测试股票{unique_code}",
            industry="测试行业",
            currency=CURRENCY_TYPES.CNY,
            market=MARKET_TYPES.CHINA,
            list_date=datetime_normalize("19900101"),
            delist_date=datetime_normalize("20991231"),
            source=SOURCE_TYPES.TUSHARE
        )
        yield record
    except Exception:
        yield None
    finally:
        # 清理
        try:
            stockinfo_service._crud_repo.remove(filters={"code": unique_code})
        except Exception:
            pass


# ============================================================================
# 参数化测试数据
# ============================================================================

# 有效的市场类型
VALID_MARKETS = [
    MARKET_TYPES.CHINA,
    MARKET_TYPES.NASDAQ,
    MARKET_TYPES.OTHER,
]

# 有效的货币类型
VALID_CURRENCIES = [
    CURRENCY_TYPES.CNY,
    CURRENCY_TYPES.USD,
]

# 有效的来源类型
VALID_SOURCES = [
    SOURCE_TYPES.TUSHARE,
    SOURCE_TYPES.YAHOO,
    SOURCE_TYPES.AKSHARE,
]

# 无效的代码
INVALID_CODES = [
    ("", "空字符串"),
    ("   ", "纯空格"),
    ("123456", "缺少后缀"),
    ("ABCDEF", "缺少点号"),
]


# ============================================================================
# 测试类 - 服务初始化和构造
# ============================================================================

@pytest.mark.unit
class TestStockinfoServiceConstruction:
    """测试StockinfoService初始化和构造"""

    def test_service_initialization(self, stockinfo_service):
        """测试服务初始化"""
        assert stockinfo_service is not None
        assert isinstance(stockinfo_service, StockinfoService)

    def test_service_inherits_base_service(self, stockinfo_service):
        """测试继承BaseService"""
        assert isinstance(stockinfo_service, BaseService)

    def test_crud_repo_exists(self, stockinfo_service):
        """测试CRUD仓库存在"""
        assert hasattr(stockinfo_service, '_crud_repo')
        assert stockinfo_service._crud_repo is not None
        assert isinstance(stockinfo_service._crud_repo, StockInfoCRUD)

    def test_data_source_exists(self, stockinfo_service):
        """测试数据源存在"""
        assert hasattr(stockinfo_service, '_data_source')
        assert stockinfo_service._data_source is not None


# ============================================================================
# 测试类 - CRUD操作
# ============================================================================

@pytest.mark.database
@pytest.mark.db_cleanup
class TestStockinfoServiceCRUD:
    """测试StockinfoService CRUD操作"""

    CLEANUP_CONFIG = {
        'stockinfo': {'code__like': 'TEST_%'}
    }

    def test_add_stockinfo_success(self, stockinfo_service, unique_code):
        """测试成功添加股票信息"""
        test_name = f"测试股票_{unique_code}"

        result = stockinfo_service._crud_repo.create(
            code=unique_code,
            code_name=test_name,
            industry="测试行业",
            market=MARKET_TYPES.CHINA,
            currency=CURRENCY_TYPES.CNY,
            list_date=datetime.now(),
            source=SOURCE_TYPES.TUSHARE
        )

        assert result is not None
        assert hasattr(result, 'uuid')
        assert result.code == unique_code

    @pytest.mark.parametrize("market", VALID_MARKETS)
    def test_add_various_markets(self, stockinfo_service, unique_code, market):
        """测试添加各种市场类型的股票信息"""
        result = stockinfo_service._crud_repo.create(
            code=unique_code,
            code_name=f"测试股票{unique_code}",
            industry="测试行业",
            market=market,
            currency=CURRENCY_TYPES.CNY,
            list_date=datetime.now(),
            source=SOURCE_TYPES.TUSHARE
        )

        assert result is not None
        assert result.market == market

    def test_get_stockinfo_by_code(self, stockinfo_service, sample_stockinfo):
        """测试按代码获取股票信息"""
        if sample_stockinfo is None:
            pytest.skip("无法创建测试数据")

        code = sample_stockinfo.code
        result = stockinfo_service.get(code=code)

        assert result.success
        assert result.data is not None
        assert len(result.data) > 0
        assert result.data[0].code == code

    def test_get_stockinfo_all(self, stockinfo_service):
        """测试获取所有股票信息"""
        result = stockinfo_service.get()

        assert result.success
        assert result.data is not None
        assert isinstance(result.data, list)

    def test_get_stockinfo_not_found(self, stockinfo_service):
        """测试获取不存在的股票信息"""
        result = stockinfo_service.get(code="NONEXISTENT_CODE_999999.SZ")

        assert result.success
        assert len(result.data) == 0

    def test_count_stockinfo(self, stockinfo_service, unique_code):
        """测试统计股票信息数量"""
        # 先添加测试数据
        stockinfo_service._crud_repo.create(
            code=unique_code,
            code_name=f"测试股票_{unique_code}",
            industry="测试行业",
            currency=CURRENCY_TYPES.CNY,
            market=MARKET_TYPES.CHINA,
            list_date=datetime.now(),
            source=SOURCE_TYPES.TUSHARE
        )

        result = stockinfo_service.count()

        assert result.success
        assert result.data >= 1


# ============================================================================
# 测试类 - 数据同步
# ============================================================================

@pytest.mark.database
@pytest.mark.db_cleanup
class TestStockinfoServiceSync:
    """测试股票信息同步功能"""

    CLEANUP_CONFIG = {
        'stockinfo': {'code__like': 'TEST_%'}
    }

    def test_sync_method_structure(self, stockinfo_service):
        """测试同步方法的ServiceResult返回结构"""
        result = stockinfo_service.sync()

        assert isinstance(result, ServiceResult)
        assert result.data is not None

        # 验证DataSyncResult基本字段
        assert hasattr(result.data, 'entity_type')
        assert result.data.entity_type == "stockinfo"

    def test_sync_result_handling(self, stockinfo_service):
        """测试同步结果处理"""
        result = stockinfo_service.sync()

        # 验证结果结构
        assert result is not None
        assert isinstance(result, ServiceResult)

        # 可能因为没有Tushare配置而失败，但结构应该正确
        if not result.success:
            assert result.error is not None


# ============================================================================
# 测试类 - 数据验证
# ============================================================================

@pytest.mark.database
@pytest.mark.db_cleanup
class TestStockinfoServiceValidation:
    """测试数据验证功能"""

    CLEANUP_CONFIG = {
        'stockinfo': {'code__like': 'TEST_%'}
    }

    def test_validate_method(self, stockinfo_service, sample_stockinfo):
        """测试数据验证方法"""
        if sample_stockinfo is None:
            pytest.skip("无法创建测试数据")

        result = stockinfo_service.validate()

        assert result.success
        assert result.data is not None

    def test_check_integrity_method(self, stockinfo_service, sample_stockinfo):
        """测试完整性检查方法"""
        result = stockinfo_service.check_integrity()

        assert result.success
        assert result.data is not None


# ============================================================================
# 测试类 - 健康检查
# ============================================================================

@pytest.mark.unit
class TestStockinfoServiceHealthCheck:
    """测试健康检查功能"""

    def test_health_check_success(self, stockinfo_service):
        """测试健康检查成功"""
        result = stockinfo_service.health_check()

        assert result.is_success()
        assert result.data is not None

        # 验证健康检查数据结构
        health_data = result.data
        assert "service_name" in health_data
        assert "status" in health_data
        assert "total_records" in health_data

        # 验证状态值
        assert health_data["service_name"] == "StockinfoService"
        assert health_data["status"] in ["healthy", "unhealthy", "degraded"]
        assert isinstance(health_data["total_records"], int)


# ============================================================================
# 测试类 - 错误处理
# ============================================================================

@pytest.mark.unit
class TestStockinfoServiceErrorHandling:
    """测试错误处理"""

    @pytest.mark.parametrize("invalid_code,description", INVALID_CODES)
    def test_get_with_invalid_code(self, stockinfo_service, invalid_code, description):
        """测试使用无效代码获取股票信息"""
        result = stockinfo_service.get(code=invalid_code)

        # 应该返回成功但数据为空
        assert result.success
        assert len(result.data) == 0

    def test_count_with_invalid_filter(self, stockinfo_service):
        """测试使用无效过滤条件统计"""
        result = stockinfo_service.count(code="NONEXISTENT_CODE_999999.SZ")

        assert result.success
        assert result.data >= 0


# ============================================================================
# 测试类 - 业务逻辑
# ============================================================================

@pytest.mark.database
@pytest.mark.db_cleanup
class TestStockinfoServiceBusinessLogic:
    """测试业务逻辑"""

    CLEANUP_CONFIG = {
        'stockinfo': {'code__like': 'TEST_%'}
    }

    def test_stockinfo_lifecycle(self, stockinfo_service, unique_code):
        """测试股票信息完整生命周期"""
        # 1. 创建
        test_name = f"生命周期测试_{unique_code}"
        record = stockinfo_service._crud_repo.create(
            code=unique_code,
            code_name=test_name,
            industry="测试行业",
            currency=CURRENCY_TYPES.CNY,
            market=MARKET_TYPES.CHINA,
            list_date=datetime.now(),
            source=SOURCE_TYPES.TUSHARE
        )
        assert record is not None

        # 2. 读取
        get_result = stockinfo_service.get(code=unique_code)
        assert get_result.success
        assert len(get_result.data) > 0

        # 3. 计数
        count_result = stockinfo_service.count()
        assert count_result.success
        assert count_result.data >= 1

        # 4. 验证
        validate_result = stockinfo_service.validate()
        assert validate_result.success

        # 5. 删除
        stockinfo_service._crud_repo.remove(filters={"code": unique_code})

        # 6. 验证已删除
        final_get = stockinfo_service.get(code=unique_code)
        assert len(final_get.data) == 0


# ============================================================================
# 测试类 - 边界测试
# ============================================================================

@pytest.mark.database
@pytest.mark.db_cleanup
class TestStockinfoServiceEdgeCases:
    """测试边界情况"""

    CLEANUP_CONFIG = {
        'stockinfo': {'code__like': 'TEST_%'}
    }

    @pytest.mark.parametrize("market", VALID_MARKETS)
    def test_different_markets(self, stockinfo_service, unique_code, market):
        """测试不同市场类型"""
        result = stockinfo_service._crud_repo.create(
            code=unique_code,
            code_name=f"测试股票_{unique_code}",
            industry="测试行业",
            market=market,
            currency=CURRENCY_TYPES.CNY,
            list_date=datetime.now(),
            source=SOURCE_TYPES.TUSHARE
        )

        assert result is not None
        assert result.market == market

    @pytest.mark.parametrize("currency", VALID_CURRENCIES)
    def test_different_currencies(self, stockinfo_service, unique_code, currency):
        """测试不同货币类型"""
        result = stockinfo_service._crud_repo.create(
            code=unique_code,
            code_name=f"测试股票_{unique_code}",
            industry="测试行业",
            market=MARKET_TYPES.CHINA,
            currency=currency,
            list_date=datetime.now(),
            source=SOURCE_TYPES.TUSHARE
        )

        assert result is not None
        assert result.currency == currency

    @pytest.mark.parametrize("source", VALID_SOURCES)
    def test_different_sources(self, stockinfo_service, unique_code, source):
        """测试不同来源类型"""
        result = stockinfo_service._crud_repo.create(
            code=unique_code,
            code_name=f"测试股票_{unique_code}",
            industry="测试行业",
            market=MARKET_TYPES.CHINA,
            currency=CURRENCY_TYPES.CNY,
            list_date=datetime.now(),
            source=source
        )

        assert result is not None
        assert result.source == source
