"""
Mock工具验证测试 - Pytest重构版本

验证MockBarCRUD和create_mock_bar_service()能正常工作。

重构要点：
- 使用pytest fixtures替代setup
- 使用parametrize进行参数化测试
- 使用pytest.mark.unit标记
- 清晰的测试类分组
"""

import pytest
from datetime import datetime
from decimal import Decimal

from test.fixtures.mock_crud_repo import MockBarCRUD
from test.fixtures.mock_data_service_factory import create_mock_bar_service
from ginkgo.enums import FREQUENCY_TYPES, ADJUSTMENT_TYPES


# ===== Fixtures =====

@pytest.fixture
def mock_bar_crud():
    """MockBarCRUD fixture"""
    return MockBarCRUD()


@pytest.fixture
def mock_bar_service():
    """Mock BarService fixture"""
    return create_mock_bar_service()


# ===== MockBarCRUD测试 =====

@pytest.mark.unit
class TestMockBarCRUD:
    """验证MockBarCRUD功能"""

    def test_mock_crud_initialization(self, mock_bar_crud):
        """测试MockBarCRUD初始化"""
        # 验证默认数据已加载
        all_data = mock_bar_crud.find()
        assert len(all_data) == 3  # 默认3条数据

        # 验证数据结构
        first_bar = all_data[0]
        assert hasattr(first_bar, 'code')
        assert hasattr(first_bar, 'open')
        assert hasattr(first_bar, 'close')

    def test_mock_crud_filter_by_code(self, mock_bar_crud):
        """测试按code过滤"""
        # 过滤000001.SZ
        result = mock_bar_crud.find(filters={"code": "000001.SZ"})
        assert len(result) == 2
        assert all(bar.code == "000001.SZ" for bar in result)

        # 过滤000002.SZ
        result = mock_bar_crud.find(filters={"code": "000002.SZ"})
        assert len(result) == 1

    @pytest.mark.parametrize("code,expected_count", [
        ("000001.SZ", 2),
        ("000002.SZ", 1),
        ("000003.SZ", 0),
    ])
    def test_mock_crud_filter_by_code_parametrized(self, mock_bar_crud, code, expected_count):
        """参数化测试按code过滤"""
        result = mock_bar_crud.find(filters={"code": code})
        assert len(result) == expected_count

    def test_mock_crud_filter_by_timestamp(self, mock_bar_crud):
        """测试按时间范围过滤"""
        # 过滤2023-01-03的数据
        result = mock_bar_crud.find(filters={
            "code": "000001.SZ",
            "timestamp__gte": datetime(2023, 1, 3, 0, 0),
            "timestamp__lte": datetime(2023, 1, 3, 23, 59)
        })
        assert len(result) == 1
        assert result[0].timestamp.date() == datetime(2023, 1, 3).date()


# ===== MockBarService测试 =====

@pytest.mark.unit
class TestMockBarService:
    """验证create_mock_bar_service()功能"""

    def test_create_mock_bar_service(self, mock_bar_service):
        """测试创建Mock BarService"""
        # 验证实例类型
        from ginkgo.data.services.bar_service import BarService
        assert isinstance(mock_bar_service, BarService)

        # 验证依赖注入
        assert hasattr(mock_bar_service, 'crud_repo')
        assert hasattr(mock_bar_service, 'data_source')
        assert hasattr(mock_bar_service, 'stockinfo_service')

    def test_mock_bar_service_get_bars(self, mock_bar_service):
        """测试Mock BarService的get_bars()方法"""
        # 调用get_bars
        result = mock_bar_service.get_bars(
            code="000001.SZ",
            start_date=datetime(2023, 1, 3),
            end_date=datetime(2023, 1, 4),
            as_dataframe=False,
            adjustment_type=ADJUSTMENT_TYPES.NONE
        )

        # 验证返回数据
        assert len(result) == 2

        # 验证数据内容
        first_bar = result[0]
        assert first_bar.code == "000001.SZ"
        assert first_bar.open == Decimal('10.0')
        assert first_bar.close == Decimal('10.2')

    @pytest.mark.parametrize("code,start_date,end_date,expected_count", [
        ("000001.SZ", datetime(2023, 1, 1), datetime(2023, 1, 3), 3),
        ("000002.SZ", datetime(2023, 1, 2), datetime(2023, 1, 2), 1),
        ("000001.SZ", datetime(2023, 1, 3), datetime(2023, 1, 3), 1),
    ])
    def test_mock_bar_service_get_bars_parametrized(
        self, mock_bar_service, code, start_date, end_date, expected_count
    ):
        """参数化测试get_bars方法"""
        result = mock_bar_service.get_bars(
            code=code,
            start_date=start_date,
            end_date=end_date,
            as_dataframe=False,
            adjustment_type=ADJUSTMENT_TYPES.NONE
        )

        assert len(result) == expected_count

    def test_mock_bar_service_get_bars_as_dataframe(self, mock_bar_service):
        """测试返回DataFrame格式"""
        # 请求DataFrame格式
        df = mock_bar_service.get_bars(
            code="000001.SZ",
            as_dataframe=True,
            adjustment_type=ADJUSTMENT_TYPES.NONE
        )

        # 验证DataFrame
        import pandas as pd
        assert isinstance(df, pd.DataFrame)

        # 验证包含必要列
        assert 'open' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns

    def test_mock_bar_service_empty_result(self, mock_bar_service):
        """测试空结果处理"""
        # 查询不存在的数据
        result = mock_bar_service.get_bars(
            code="999999.SZ",
            start_date=datetime(2020, 1, 1),
            end_date=datetime(2020, 1, 31),
            as_dataframe=False,
            adjustment_type=ADJUSTMENT_TYPES.NONE
        )

        # 应该返回空列表
        assert isinstance(result, list)
        assert len(result) == 0


# ===== 边界情况测试 =====

@pytest.mark.unit
class TestMockToolsEdgeCases:
    """Mock工具边界情况测试"""

    @pytest.mark.parametrize("invalid_filters", [
        {"nonexistent_field": "value"},
        {"code": None},
        {},
    ])
    def test_handle_invalid_filters(self, mock_bar_crud, invalid_filters):
        """测试处理无效过滤条件"""
        result = mock_bar_crud.find(filters=invalid_filters)
        # 应该能处理无效过滤器
        assert isinstance(result, list)

    @pytest.mark.parametrize("date_range,expected_count", [
        # (start_date, end_date), expected_count
        ((datetime(2023, 1, 1), datetime(2023, 1, 1)), 1),
        ((datetime(2023, 1, 1), datetime(2023, 1, 31)), 3),
        ((datetime(2099, 1, 1), datetime(2099, 12, 31)), 0),
    ])
    def test_various_date_ranges(self, mock_bar_crud, date_range, expected_count):
        """测试不同日期范围"""
        start_date, end_date = date_range
        result = mock_bar_crud.find(filters={
            "timestamp__gte": start_date,
            "timestamp__lte": end_date
        })
        assert len(result) == expected_count


# ===== 集成测试 =====

@pytest.mark.unit
class TestMockToolsIntegration:
    """Mock工具集成测试"""

    def test_crud_and_service_integration(self, mock_bar_crud, mock_bar_service):
        """测试CRUD和服务集成"""
        # 通过CRUD添加数据
        new_bar = {
            "code": "000003.SZ",
            "timestamp": datetime(2023, 1, 5),
            "open": Decimal('15.0'),
            "close": Decimal('15.5'),
            "high": Decimal('16.0'),
            "low": Decimal('14.5'),
            "volume": 500000
        }
        mock_bar_crud.add(new_bar)

        # 通过服务查询数据
        result = mock_bar_service.get_bars(
            code="000003.SZ",
            start_date=datetime(2023, 1, 5),
            end_date=datetime(2023, 1, 5),
            as_dataframe=False,
            adjustment_type=ADJUSTMENT_TYPES.NONE
        )

        # 验证集成
        assert len(result) >= 1

    def test_multiple_code_queries(self, mock_bar_service):
        """测试多代码查询"""
        codes = ["000001.SZ", "000002.SZ"]
        results = []

        for code in codes:
            result = mock_bar_service.get_bars(
                code=code,
                as_dataframe=False,
                adjustment_type=ADJUSTMENT_TYPES.NONE
            )
            results.extend(result)

        # 验证总结果
        assert len(results) >= 2
        assert all(isinstance(r, object) for r in results)
