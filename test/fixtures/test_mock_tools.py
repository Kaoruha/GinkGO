"""
Mock工具验证测试

验证MockBarCRUD和create_mock_bar_service()能正常工作。
"""

import pytest
from datetime import datetime
from decimal import Decimal

from test.fixtures.mock_crud_repo import MockBarCRUD
from test.fixtures.mock_data_service_factory import create_mock_bar_service
from ginkgo.enums import FREQUENCY_TYPES, ADJUSTMENT_TYPES


@pytest.mark.unit
class TestMockBarCRUD:
    """验证MockBarCRUD功能"""

    def test_mock_crud_initialization(self):
        """测试MockBarCRUD初始化"""
        print("\n=== 测试MockBarCRUD初始化 ===")

        crud = MockBarCRUD()

        # 验证默认数据已加载
        all_data = crud.find()
        print(f"✓ 默认数据数量: {len(all_data)} 条")
        assert len(all_data) == 3  # 默认3条数据

        # 验证数据结构
        first_bar = all_data[0]
        print(f"✓ 第一条数据: code={first_bar.code}, timestamp={first_bar.timestamp}")
        assert hasattr(first_bar, 'code')
        assert hasattr(first_bar, 'open')
        assert hasattr(first_bar, 'close')

    def test_mock_crud_filter_by_code(self):
        """测试按code过滤"""
        print("\n=== 测试按code过滤 ===")

        crud = MockBarCRUD()

        # 过滤000001.SZ
        result = crud.find(filters={"code": "000001.SZ"})
        print(f"✓ 000001.SZ数据: {len(result)} 条")
        assert len(result) == 2
        assert all(bar.code == "000001.SZ" for bar in result)

        # 过滤000002.SZ
        result = crud.find(filters={"code": "000002.SZ"})
        print(f"✓ 000002.SZ数据: {len(result)} 条")
        assert len(result) == 1

    def test_mock_crud_filter_by_timestamp(self):
        """测试按时间范围过滤"""
        print("\n=== 测试按时间范围过滤 ===")

        crud = MockBarCRUD()

        # 过滤2023-01-03的数据
        result = crud.find(filters={
            "code": "000001.SZ",
            "timestamp__gte": datetime(2023, 1, 3, 0, 0),
            "timestamp__lte": datetime(2023, 1, 3, 23, 59)
        })
        print(f"✓ 2023-01-03数据: {len(result)} 条")
        assert len(result) == 1
        assert result[0].timestamp.date() == datetime(2023, 1, 3).date()


@pytest.mark.unit
class TestMockBarService:
    """验证create_mock_bar_service()功能"""

    def test_create_mock_bar_service(self):
        """测试创建Mock BarService"""
        print("\n=== 测试创建Mock BarService ===")

        bar_service = create_mock_bar_service()

        # 验证实例类型
        from ginkgo.data.services.bar_service import BarService
        assert isinstance(bar_service, BarService)
        print(f"✓ BarService实例创建成功: {type(bar_service).__name__}")

        # 验证依赖注入
        assert hasattr(bar_service, 'crud_repo')
        assert hasattr(bar_service, 'data_source')
        assert hasattr(bar_service, 'stockinfo_service')
        print(f"✓ 依赖注入成功")

    def test_mock_bar_service_get_bars(self):
        """测试Mock BarService的get_bars()方法"""
        print("\n=== 测试Mock BarService.get_bars() ===")

        bar_service = create_mock_bar_service()

        # 调用get_bars
        result = bar_service.get_bars(
            code="000001.SZ",
            start_date=datetime(2023, 1, 3),
            end_date=datetime(2023, 1, 4),
            as_dataframe=False,
            adjustment_type=ADJUSTMENT_TYPES.NONE  # 不使用复权
        )

        # 验证返回数据
        print(f"✓ 查询到 {len(result)} 条数据")
        assert len(result) == 2

        # 验证数据内容
        first_bar = result[0]
        print(f"✓ 第一条: open={first_bar.open}, close={first_bar.close}")
        assert first_bar.code == "000001.SZ"
        assert first_bar.open == Decimal('10.0')
        assert first_bar.close == Decimal('10.2')

    def test_mock_bar_service_get_bars_as_dataframe(self):
        """测试返回DataFrame格式"""
        print("\n=== 测试返回DataFrame格式 ===")

        bar_service = create_mock_bar_service()

        # 请求DataFrame格式
        df = bar_service.get_bars(
            code="000001.SZ",
            as_dataframe=True,
            adjustment_type=ADJUSTMENT_TYPES.NONE
        )

        # 验证DataFrame
        import pandas as pd
        assert isinstance(df, pd.DataFrame)
        print(f"✓ DataFrame形状: {df.shape}")
        print(f"✓ 列名: {list(df.columns)}")

        # 验证包含必要列
        assert 'open' in df.columns
        assert 'close' in df.columns
        assert 'volume' in df.columns


if __name__ == "__main__":
    # 可以直接运行此文件进行快速验证
    pytest.main([__file__, "-v", "-s"])
