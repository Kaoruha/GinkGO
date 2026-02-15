"""
TickService数据服务测试

测试TickService的核心功能和业务逻辑
遵循pytest最佳实践，使用fixtures和参数化测试
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.services.tick_service import TickService
from ginkgo.data.services.stockinfo_service import StockinfoService
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.containers import container
from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
from ginkgo.data.sources.ginkgo_tushare import GinkgoTushare
from ginkgo.data.sources.ginkgo_tdx import GinkgoTDX
from ginkgo.enums import ADJUSTMENT_TYPES, SOURCE_TYPES, MARKET_TYPES, CURRENCY_TYPES
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
def tick_service():
    """获取TickService实例"""
    return container.tick_service()


@pytest.fixture
def stockinfo_service():
    """获取StockinfoService实例"""
    return container.stockinfo_service()


@pytest.fixture
def unique_code():
    """生成唯一的测试股票代码"""
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    return f"TEST{timestamp[-6:]}.SZ"


@pytest.fixture
def test_stock_info(stockinfo_service, unique_code):
    """创建测试用股票信息"""
    try:
        stockinfo_service._crud_repo.create(
            code=unique_code,
            code_name=f"测试股票{unique_code}",
            industry="测试行业",
            currency=CURRENCY_TYPES.CNY,
            market=MARKET_TYPES.CHINA,
            list_date=datetime_normalize("19900101"),
            delist_date=datetime_normalize("20991231"),
            source=SOURCE_TYPES.TUSHARE
        )
    except Exception:
        pass  # 已存在
    yield unique_code
    # 清理
    try:
        stockinfo_service._crud_repo.remove(filters={"code": unique_code})
    except Exception:
        pass


@pytest.fixture
def sample_tick_data(tick_service, test_stock_info):
    """创建示例tick数据并返回代码"""
    test_date = datetime(2024, 1, 2)
    # 同步数据
    sync_result = tick_service.sync_date(test_stock_info, test_date)
    if sync_result.success:
        return test_stock_info
    return None


# ============================================================================
# 参数化测试数据
# ============================================================================

# 有效的调整类型
VALID_ADJUSTMENT_TYPES = [
    ADJUSTMENT_TYPES.NONE,
    ADJUSTMENT_TYPES.FORE,
    ADJUSTMENT_TYPES.BACK,
]

# 无效的股票代码
INVALID_CODES = [
    ("", "空字符串"),
    ("   ", "纯空格"),
    ("INVALID", "无效格式"),
    ("123456", "纯数字"),
]


# ============================================================================
# 测试类 - TickService 构造和初始化
# ============================================================================

@pytest.mark.unit
class TestTickServiceConstruction:
    """
    TickService构造和初始化测试
    测试服务实例化、依赖注入和基础配置
    """

    def test_tick_service_initialization(self, tick_service):
        """测试TickService基本初始化"""
        assert isinstance(tick_service, TickService)
        assert isinstance(tick_service, BaseService)

    def test_tick_service_has_crud_repo(self, tick_service):
        """测试CRUD仓储已设置"""
        assert hasattr(tick_service, '_crud_repo')
        assert tick_service._crud_repo is not None

    def test_tick_service_has_data_source(self, tick_service):
        """测试数据源已设置"""
        assert hasattr(tick_service, '_data_source')
        assert tick_service._data_source is not None

    def test_tick_service_has_stockinfo_service(self, tick_service):
        """测试股票信息服务已设置"""
        assert hasattr(tick_service, '_stockinfo_service')
        assert tick_service._stockinfo_service is not None

    def test_tick_service_has_logger(self, tick_service):
        """测试日志记录器已设置"""
        assert hasattr(tick_service, '_logger')


# ============================================================================
# 测试类 - Tick数据同步
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestTickServiceSync:
    """
    Tick数据同步测试
    测试单日同步、范围同步、批量同步和智能同步
    """

    CLEANUP_CONFIG = {'tick': {'code': '000001.SZ'}}

    def test_sync_date_success(self, tick_service, sample_tick_data):
        """测试单日同步成功"""
        if not sample_tick_data:
            pytest.skip("测试数据同步失败")

        # 验证同步后数据存在
        result = tick_service.get(code=sample_tick_data, start_date=datetime(2024, 1, 2))
        assert result.success
        assert len(result.data) > 0

    def test_sync_range_success(self, tick_service):
        """测试日期范围同步"""
        start_date = datetime(2024, 1, 2)
        end_date = datetime(2024, 1, 3)

        result = tick_service.sync_range("000001.SZ", start_date, end_date)
        assert result.success, f"范围同步失败: {result.message}"

    def test_sync_batch_multiple_codes(self, tick_service):
        """测试批量同步多个股票"""
        codes = ["000001.SZ", "000002.SZ"]
        test_date = datetime(2024, 1, 2)

        result = tick_service.sync_batch(
            codes=codes,
            start_date=test_date,
            end_date=test_date
        )
        assert result.success, f"批量同步失败: {result.message}"

    def test_sync_smart_functionality(self, tick_service):
        """测试智能同步功能"""
        result = tick_service.sync_smart("000001.SZ", max_backtrack_days=7)
        assert result.success, f"智能同步失败: {result.message}"

    def test_sync_date_increment(self, tick_service):
        """测试同步数据增量"""
        test_date = datetime(2024, 1, 2)

        # 同步前计数
        before_count = len(tick_service._crud_repo.find({
            "code": "000001.SZ",
            "timestamp__gte": test_date,
            "timestamp__lte": test_date.replace(hour=23, minute=59, second=59)
        }))

        # 执行同步
        result = tick_service.sync_date("000001.SZ", test_date)
        assert result.success, f"同步失败: {result.message}"

        # 同步后计数
        after_count = len(tick_service._crud_repo.find({
            "code": "000001.SZ",
            "timestamp__gte": test_date,
            "timestamp__lte": test_date.replace(hour=23, minute=59, second=59)
        }))

        # 验证数据增加
        increment = after_count - before_count
        assert increment > 0, f"应该新增数据，实际新增: {increment}"


# ============================================================================
# 测试类 - Tick数据查询
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestTickServiceQuery:
    """
    Tick数据查询测试
    测试基础查询、日期过滤、复权查询
    """

    CLEANUP_CONFIG = {'tick': {'code': '000001.SZ'}}

    def test_get_basic_query(self, tick_service, sample_tick_data):
        """测试基础get查询"""
        if not sample_tick_data:
            pytest.skip("测试数据同步失败")

        result = tick_service.get(
            code=sample_tick_data,
            start_date=datetime(2024, 1, 2),
            end_date=datetime(2024, 1, 2)
        )

        assert result.success
        assert result.data is not None
        assert len(result.data) > 0

    def test_get_empty_result(self, tick_service):
        """测试查询不存在的数据"""
        result = tick_service.get(
            code="999999.SZ",
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 1, 2)
        )

        assert result.success
        assert len(result.data) == 0

    def test_get_with_price_adjustment(self, tick_service):
        """测试价格调整查询"""
        # 先同步数据
        tick_service.sync_date("000001.SZ", datetime(2024, 1, 2))

        # 测试前复权
        result = tick_service.get(
            code="000001.SZ",
            start_date=datetime(2024, 1, 2),
            end_date=datetime(2024, 1, 2),
            adjustment_type=ADJUSTMENT_TYPES.FORE
        )

        assert result.success, f"价格调整查询失败: {result.message}"

    @pytest.mark.parametrize("adjustment_type", VALID_ADJUSTMENT_TYPES)
    def test_get_with_different_adjustments(self, tick_service, adjustment_type):
        """参数化测试：不同复权类型查询"""
        # 先同步数据
        tick_service.sync_date("000001.SZ", datetime(2024, 1, 2))

        result = tick_service.get(
            code="000001.SZ",
            start_date=datetime(2024, 1, 2),
            end_date=datetime(2024, 1, 2),
            adjustment_type=adjustment_type
        )

        assert result.success, f"复权类型{adjustment_type}查询失败"

    def test_get_model_list_functionality(self, tick_service, sample_tick_data):
        """测试ModelList功能"""
        if not sample_tick_data:
            pytest.skip("测试数据同步失败")

        result = tick_service.get(
            code=sample_tick_data,
            start_date=datetime(2024, 1, 2),
            end_date=datetime(2024, 1, 2)
        )

        assert result.success
        model_list = result.data

        # 验证to_dataframe方法
        df = model_list.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # 验证to_entities方法
        entities = model_list.to_entities()
        assert isinstance(entities, list)
        assert len(entities) > 0

        # 验证实体属性
        if entities:
            first_entity = entities[0]
            assert hasattr(first_entity, 'code')
            assert hasattr(first_entity, 'timestamp')
            assert hasattr(first_entity, 'price')


# ============================================================================
# 测试类 - Tick数据计数
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestTickServiceCount:
    """
    Tick数据计数测试
    测试计数功能和统计
    """

    CLEANUP_CONFIG = {'tick': {'code': '000001.SZ'}}

    def test_count_after_sync(self, tick_service):
        """测试同步后计数"""
        test_date = datetime(2024, 1, 2)

        # 同步前计数
        count_before = tick_service.count(code="000001.SZ", date=test_date)
        assert count_before.success
        before_records = count_before.data if count_before.data else 0

        # 同步数据
        tick_service.sync_date("000001.SZ", test_date)

        # 同步后计数
        count_after = tick_service.count(code="000001.SZ", date=test_date)
        assert count_after.success
        after_records = count_after.data

        # 验证计数增加
        assert after_records > before_records

    def test_count_nonexistent_code(self, tick_service):
        """测试不存在代码的计数"""
        result = tick_service.count(code="999999.SZ")
        assert result.success
        assert result.data == 0


# ============================================================================
# 测试类 - Tick数据验证
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestTickServiceValidation:
    """
    Tick数据验证测试
    测试数据质量验证和完整性检查
    """

    CLEANUP_CONFIG = {'tick': {'code': '000001.SZ'}}

    def test_validate_data_quality(self, tick_service):
        """测试数据质量验证"""
        # 同步数据
        tick_service.sync_date("000001.SZ", datetime(2024, 1, 2))

        # 获取数据
        tick_data = tick_service._crud_repo.find(filters={"code": "000001.SZ"})

        # 验证数据质量
        result = tick_service.validate(tick_data)
        assert result.success
        assert hasattr(result.data, 'is_valid')
        assert hasattr(result.data, 'data_quality_score')

    def test_check_integrity(self, tick_service):
        """测试完整性检查"""
        result = tick_service.check_integrity(
            "000001.SZ",
            datetime(2024, 1, 2),
            datetime(2024, 1, 2)
        )
        assert result.success
        assert hasattr(result.data, 'integrity_score')
        assert hasattr(result.data, 'is_healthy')


# ============================================================================
# 测试类 - Tick服务错误处理
# ============================================================================

@pytest.mark.unit
class TestTickServiceErrorHandling:
    """
    Tick服务错误处理测试
    测试边界条件和异常处理
    """

    @pytest.mark.parametrize("invalid_code, description", INVALID_CODES)
    def test_invalid_code_handling(self, tick_service, invalid_code, description):
        """参数化测试：无效股票代码处理"""
        result = tick_service.get(code=invalid_code)
        assert not result.success, f"应该拒绝{description}"

    def test_get_empty_code(self, tick_service):
        """测试空代码查询"""
        result = tick_service.get(code="")
        assert not result.success
        assert "required" in result.message.lower()

    def test_count_empty_code(self, tick_service):
        """测试空代码计数"""
        result = tick_service.count(code="")
        assert not result.success
        assert "required" in result.message.lower()


# ============================================================================
# 测试类 - Tick服务健康检查
# ============================================================================

@pytest.mark.unit
class TestTickServiceHealth:
    """TickService健康检查测试"""

    def test_health_check(self, tick_service):
        """测试健康检查返回正确信息"""
        result = tick_service.health_check()

        assert result.success
        health_data = result.data
        assert health_data["service_name"] == "TickService"
        assert health_data["status"] in ["healthy", "unhealthy", "degraded"]


# ============================================================================
# 测试类 - Tick服务集成测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.db_cleanup
class TestTickServiceIntegration:
    """
    TickService集成测试
    测试完整的业务流程
    """

    CLEANUP_CONFIG = {'tick': {'code': '000001.SZ'}}

    def test_full_sync_workflow(self, tick_service):
        """测试完整同步工作流：同步->查询->验证"""
        # 1. 同步数据
        sync_result = tick_service.sync_date("000001.SZ", datetime(2024, 1, 2))
        assert sync_result.success

        # 2. 查询数据
        get_result = tick_service.get(
            code="000001.SZ",
            start_date=datetime(2024, 1, 2),
            end_date=datetime(2024, 1, 2)
        )
        assert get_result.success
        assert len(get_result.data) > 0

        # 3. 验证数据
        tick_data = tick_service._crud_repo.find(filters={"code": "000001.SZ"})
        validate_result = tick_service.validate(tick_data)
        assert validate_result.success

    def test_sync_query_with_adjustment_workflow(self, tick_service):
        """测试同步-查询-复权工作流"""
        # 1. 同步数据
        tick_service.sync_date("000001.SZ", datetime(2024, 1, 2))

        # 2. 不复权查询
        none_adj = tick_service.get(
            code="000001.SZ",
            start_date=datetime(2024, 1, 2),
            end_date=datetime(2024, 1, 2),
            adjustment_type=ADJUSTMENT_TYPES.NONE
        )
        assert none_adj.success

        # 3. 前复权查询
        fore_adj = tick_service.get(
            code="000001.SZ",
            start_date=datetime(2024, 1, 2),
            end_date=datetime(2024, 1, 2),
            adjustment_type=ADJUSTMENT_TYPES.FORE
        )
        assert fore_adj.success
