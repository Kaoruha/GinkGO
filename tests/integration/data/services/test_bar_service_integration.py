"""
BarService 集成测试 - 连接真实数据库通过CRUD操作

测试BarService与ClickHouse数据库的集成，验证K线数据的查询、统计等功能。
需要数据库环境可用，使用 SOURCE_TYPES.TEST 隔离测试数据。

运行方式:
    pytest tests/integration/data/services/test_bar_service_integration.py -v -m "database and integration"
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.enums import SOURCE_TYPES, FREQUENCY_TYPES, ADJUSTMENT_TYPES
from ginkgo.data.services.bar_service import BarService
from ginkgo.data.services.stockinfo_service import StockinfoService
from ginkgo.data.services.base_service import ServiceResult


def _skip_if_db_unavailable(exc):
    """数据库不可用时跳过测试的辅助函数"""
    pytest.skip(f"数据库不可用，跳过集成测试: {exc}")


def _create_bar_service():
    """创建连接真实数据库的BarService实例"""
    from ginkgo.data.crud.bar_crud import BarCRUD
    from ginkgo.data.crud.stock_info_crud import StockInfoCRUD
    from ginkgo.data.crud.adjustfactor_crud import AdjustfactorCRUD
    from ginkgo.data.services.adjustfactor_service import AdjustfactorService

    try:
        bar_crud = BarCRUD()
        stockinfo_crud = StockInfoCRUD()
        adjustfactor_crud = AdjustfactorCRUD()

        stockinfo_service = StockinfoService(
            crud_repo=stockinfo_crud,
            data_source=None
        )
        adjustfactor_service = AdjustfactorService(
            crud_repo=adjustfactor_crud,
            data_source=None,
            stockinfo_service=stockinfo_service
        )
        return BarService(
            crud_repo=bar_crud,
            data_source=None,
            stockinfo_service=stockinfo_service,
            adjustfactor_service=adjustfactor_service
        )
    except Exception as e:
        _skip_if_db_unavailable(e)


@pytest.fixture(scope="module")
def bar_service():
    """BarService fixture - 模块级别共享，减少数据库连接开销"""
    return _create_bar_service()


@pytest.fixture(scope="function")
def bar_service_with_cleanup(bar_service):
    """每次测试后清理测试数据的BarService fixture"""
    yield bar_service
    # 清理测试数据：删除测试创建的K线数据
    try:
        bar_service._crud_repo.remove(
            filters={"code": "999999.SZ"}
        )
    except Exception:
        pass


@pytest.mark.database
@pytest.mark.integration
class TestBarServiceConstruction:
    """1. BarService构造与数据库连接测试"""

    def test_service_construction(self, bar_service):
        """测试BarService使用真实CRUD成功构造"""
        assert bar_service is not None
        assert isinstance(bar_service, BarService)
        assert isinstance(bar_service, type(bar_service).__bases__[0])

    def test_service_crud_repo_connected(self, bar_service):
        """测试CRUD仓库已正确注入"""
        assert bar_service._crud_repo is not None

    def test_service_data_source_none(self, bar_service):
        """测试无数据源时服务仍可正常创建（仅查询模式）"""
        # data_source为None不影响构造
        assert bar_service._data_source is None

    def test_service_name(self, bar_service):
        """测试服务名称正确设置"""
        assert bar_service.service_name == "BarService"


@pytest.mark.database
@pytest.mark.integration
class TestBarServiceQuery:
    """2. K线数据查询测试"""

    def test_get_bars_with_code(self, bar_service):
        """测试按股票代码查询K线数据"""
        result = bar_service.get(code="000001.SZ")

        # 结果必须是ServiceResult且查询成功
        assert isinstance(result, ServiceResult)
        assert result.success is True
        # data可能是ModelList或空列表
        assert result.data is not None

    def test_get_bars_with_date_range(self, bar_service):
        """测试按日期范围查询K线数据"""
        start = datetime(2023, 1, 1)
        end = datetime(2023, 12, 31)
        result = bar_service.get(code="000001.SZ", start_date=start, end_date=end)

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None

    def test_get_bars_no_adjustment(self, bar_service):
        """测试查询不复权的K线数据"""
        result = bar_service.get(
            code="000001.SZ",
            adjustment_type=ADJUSTMENT_TYPES.NONE
        )

        assert isinstance(result, ServiceResult)
        assert result.success is True

    def test_get_bars_empty_params(self, bar_service):
        """测试无参数查询应返回错误"""
        result = bar_service.get()
        assert isinstance(result, ServiceResult)
        assert result.success is False
        assert result.error != ""

    def test_get_bars_nonexistent_code(self, bar_service):
        """测试查询不存在的股票代码"""
        result = bar_service.get(code="NONEXISTENT.SZ")
        assert isinstance(result, ServiceResult)
        # 可能成功但返回空数据
        assert result.success is True
        assert result.data is not None


@pytest.mark.database
@pytest.mark.integration
class TestBarServiceCount:
    """3. K线数据统计测试"""

    def test_count_all_bars(self, bar_service):
        """测试统计所有K线数据数量"""
        result = bar_service.count()

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None
        assert isinstance(result.data, int)
        assert result.data >= 0

    def test_count_bars_by_code(self, bar_service):
        """测试按股票代码统计K线数量"""
        result = bar_service.count(code="000001.SZ")

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert isinstance(result.data, int)

    def test_count_bars_by_date_range(self, bar_service):
        """测试按日期范围统计K线数量"""
        start = datetime(2023, 1, 1)
        end = datetime(2023, 6, 30)
        result = bar_service.count(start_date=start, end_date=end)

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert isinstance(result.data, int)


@pytest.mark.database
@pytest.mark.integration
class TestBarServiceCodes:
    """4. 可用股票代码查询测试"""

    def test_get_available_codes(self, bar_service):
        """测试获取可用股票代码列表"""
        result = bar_service.get_available_codes(frequency=FREQUENCY_TYPES.DAY)

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None
        assert isinstance(result.data, list)

    def test_get_available_codes_empty_db(self, bar_service):
        """测试数据库为空时获取代码列表"""
        # 查询不存在的频率
        from ginkgo.enums import FREQUENCY_TYPES
        result = bar_service.get_available_codes(frequency=FREQUENCY_TYPES.MINUTE)

        assert isinstance(result, ServiceResult)
        assert result.success is True
        # 可能为空列表
        assert result.data is not None


@pytest.mark.database
@pytest.mark.integration
class TestBarServiceWriteOperations:
    """5. K线数据写入操作测试（使用TEST标记隔离）"""

    def test_add_and_get_test_bars(self, bar_service_with_cleanup):
        """测试写入测试K线数据后能正确查询"""
        from ginkgo.entities import Bar

        # 创建测试K线数据
        base_time = datetime(2025, 1, 2)
        test_bar = Bar(
            code="999999.SZ",
            timestamp=base_time,
            open=Decimal("10.00"),
            high=Decimal("10.50"),
            low=Decimal("9.80"),
            close=Decimal("10.20"),
            volume=100000,
            frequency=FREQUENCY_TYPES.DAY,
            source=SOURCE_TYPES.TEST
        )

        # 写入数据
        bar_service_with_cleanup._crud_repo.add_batch([test_bar])

        # 验证查询
        result = bar_service_with_cleanup.get(code="999999.SZ")
        assert result.success is True
        assert result.data is not None

        # 验证计数
        count_result = bar_service_with_cleanup.count(code="999999.SZ")
        assert count_result.success is True
        assert count_result.data > 0

    def test_remove_test_bars(self, bar_service_with_cleanup):
        """测试删除测试K线数据"""
        from ginkgo.entities import Bar

        base_time = datetime(2025, 1, 3)
        test_bar = Bar(
            code="999999.SZ",
            timestamp=base_time,
            open=Decimal("11.00"),
            high=Decimal("11.50"),
            low=Decimal("10.80"),
            close=Decimal("11.20"),
            volume=200000,
            frequency=FREQUENCY_TYPES.DAY,
            source=SOURCE_TYPES.TEST
        )

        # 写入
        bar_service_with_cleanup._crud_repo.add_batch([test_bar])

        # 删除
        bar_service_with_cleanup._crud_repo.remove(filters={"code": "999999.SZ"})

        # 验证已删除
        count_result = bar_service_with_cleanup.count(code="999999.SZ")
        assert count_result.success is True
        assert count_result.data == 0


@pytest.mark.database
@pytest.mark.integration
class TestBarServiceEdgeCases:
    """6. 边界条件和异常处理测试"""

    def test_empty_database_count(self, bar_service):
        """测试空数据库时的计数操作"""
        result = bar_service.count(code="TESTEMPTY.SZ")
        assert result.success is True
        assert result.data == 0

    def test_get_with_future_date_range(self, bar_service):
        """测试查询未来日期范围应返回空结果"""
        future_start = datetime(2099, 1, 1)
        future_end = datetime(2099, 12, 31)
        result = bar_service.get(code="000001.SZ", start_date=future_start, end_date=future_end)

        assert isinstance(result, ServiceResult)
        assert result.success is True
