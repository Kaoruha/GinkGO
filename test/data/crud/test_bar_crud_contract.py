"""
BarCRUD契约测试 - 验证Mock与真实CRUD行为一致性

目的：确保MockBarCRUD在单元测试中能准确模拟BarCRUD行为
"""

import pytest
from datetime import datetime
from decimal import Decimal

from ginkgo.enums import SOURCE_TYPES

from ginkgo.data.crud import BarCRUD
from ginkgo.data.models import MBar
from test.fixtures.mock_crud_repo import MockBarCRUD


@pytest.mark.database
class TestBarCRUDContract:
    CRUD_TEST_CONFIG = {'crud_class': BarCRUD}
    """契约测试 - 验证Mock行为准确性"""

    @pytest.fixture
    def test_data(self):
        """共同测试数据 - 模拟真实数据库NOT NULL约束"""
        return [
            MBar(code="CTR.SZ", timestamp=datetime(2023, 11, 1, 9, 30),
                 open=Decimal('100.0'), close=Decimal('101.0'),
                 high=Decimal('102.0'), low=Decimal('99.0'),
                 volume=5000000, amount=Decimal('505000000.0'), frequency=1),
            MBar(code="CTR.SZ", timestamp=datetime(2023, 11, 5, 9, 30),
                 open=Decimal('105.0'), close=Decimal('106.0'),
                 high=Decimal('107.0'), low=Decimal('104.0'),
                 volume=6000000, amount=Decimal('636000000.0'), frequency=1),
            MBar(code="CTR.SZ", timestamp=datetime(2023, 11, 10, 9, 30),
                 open=Decimal('110.0'), close=Decimal('111.0'),
                 high=Decimal('112.0'), low=Decimal('109.0'),
                 volume=7000000, amount=Decimal('777000000.0'), frequency=1),
        ]

    def test_contract_basic_find(self, test_data):
        """契约1: 基础查询返回类型和数量一致"""
        print("\n" + "="*60)
        print("契约1: 基础查询")
        print("="*60)

        real = BarCRUD()
        mock = MockBarCRUD()

        try:
            # 准备数据
            real.remove(filters={"code": "CTR.SZ"})
            real.add_batch(test_data)
            mock.clear()
            mock.add_batch(test_data)

            # 执行查询
            real_result = real.find(filters={"code": "CTR.SZ"})
            mock_result = mock.find(filters={"code": "CTR.SZ"})

            # 验证
            print(f"\n✓ 真实CRUD: {len(real_result)}条, 类型={type(real_result).__name__}")
            print(f"✓ Mock CRUD: {len(mock_result)}条, 类型={type(mock_result).__name__}")

            assert isinstance(real_result, list) and isinstance(mock_result, list)
            assert len(real_result) == len(mock_result) == 3
            assert all(isinstance(b, MBar) for b in real_result + mock_result)

            print("✅ 契约验证通过")

        finally:
            real.remove(filters={"code": "CTR.SZ"})

    def test_contract_filtering(self, test_data):
        """契约2: 复杂筛选结果一致"""
        print("\n" + "="*60)
        print("契约2: 筛选条件")
        print("="*60)

        real = BarCRUD()
        mock = MockBarCRUD()

        try:
            real.remove(filters={"code": "CTR.SZ"})
            real.add_batch(test_data)
            mock.clear()
            mock.add_batch(test_data)

            # 场景1: 时间范围
            filters1 = {
                "code": "CTR.SZ",
                "timestamp__gte": datetime(2023, 11, 5, 0, 0),
                "timestamp__lte": datetime(2023, 11, 10, 23, 59)
            }
            real_r1 = real.find(filters=filters1)
            mock_r1 = mock.find(filters=filters1)
            print(f"\n✓ 时间范围筛选: 真实={len(real_r1)} Mock={len(mock_r1)}")
            assert len(real_r1) == len(mock_r1) == 2

            # 场景2: 成交量范围
            filters2 = {"code": "CTR.SZ", "volume__gte": 5500000, "volume__lte": 6500000}
            real_r2 = real.find(filters=filters2)
            mock_r2 = mock.find(filters=filters2)
            print(f"✓ 成交量筛选: 真实={len(real_r2)} Mock={len(mock_r2)}")
            assert len(real_r2) == len(mock_r2) == 1

            print("✅ 契约验证通过")

        finally:
            real.remove(filters={"code": "CTR.SZ"})

    def test_contract_ordering(self, test_data):
        """契约3: 排序结果一致"""
        print("\n" + "="*60)
        print("契约3: 排序功能")
        print("="*60)

        real = BarCRUD()
        mock = MockBarCRUD()

        try:
            real.remove(filters={"code": "CTR.SZ"})
            real.add_batch(test_data)
            mock.clear()
            mock.add_batch(test_data)

            # 升序
            real_asc = real.find(filters={"code": "CTR.SZ"}, order_by="timestamp", desc_order=False)
            mock_asc = mock.find(filters={"code": "CTR.SZ"}, order_by="timestamp", desc_order=False)
            real_dates_asc = [b.timestamp.day for b in real_asc]
            mock_dates_asc = [b.timestamp.day for b in mock_asc]
            print(f"\n✓ 升序: 真实={real_dates_asc} Mock={mock_dates_asc}")
            assert real_dates_asc == mock_dates_asc == [1, 5, 10]

            # 降序
            real_desc = real.find(filters={"code": "CTR.SZ"}, order_by="volume", desc_order=True)
            mock_desc = mock.find(filters={"code": "CTR.SZ"}, order_by="volume", desc_order=True)
            real_vols = [b.volume for b in real_desc]
            mock_vols = [b.volume for b in mock_desc]
            print(f"✓ 降序: 真实={real_vols} Mock={mock_vols}")
            assert real_vols == mock_vols == [7000000, 6000000, 5000000]

            print("✅ 契约验证通过")

        finally:
            real.remove(filters={"code": "CTR.SZ"})

    def test_contract_pagination(self, test_data):
        """契约4: 分页结果一致"""
        print("\n" + "="*60)
        print("契约4: 分页功能")
        print("="*60)

        real = BarCRUD()
        mock = MockBarCRUD()

        try:
            real.remove(filters={"code": "CTR.SZ"})
            real.add_batch(test_data)
            mock.clear()
            mock.add_batch(test_data)

            # page=0, page_size=2
            real_p0 = real.find(filters={"code": "CTR.SZ"}, order_by="timestamp", page=0, page_size=2)
            mock_p0 = mock.find(filters={"code": "CTR.SZ"}, order_by="timestamp", page=0, page_size=2)
            real_dates_p0 = [b.timestamp.day for b in real_p0]
            mock_dates_p0 = [b.timestamp.day for b in mock_p0]
            print(f"\n✓ 第1页(page=0): 真实={real_dates_p0} Mock={mock_dates_p0}")
            assert real_dates_p0 == mock_dates_p0 == [1, 5]

            # page=1, page_size=2
            real_p1 = real.find(filters={"code": "CTR.SZ"}, order_by="timestamp", page=1, page_size=2)
            mock_p1 = mock.find(filters={"code": "CTR.SZ"}, order_by="timestamp", page=1, page_size=2)
            print(f"✓ 第2页(page=1): 真实={len(real_p1)}条 Mock={len(mock_p1)}条")
            assert len(real_p1) == len(mock_p1) == 1

            print("✅ 契约验证通过")

        finally:
            real.remove(filters={"code": "CTR.SZ"})

    def test_contract_dataframe(self, test_data):
        """契约5: DataFrame格式一致"""
        print("\n" + "="*60)
        print("契约5: DataFrame格式")
        print("="*60)

        real = BarCRUD()
        mock = MockBarCRUD()

        try:
            real.remove(filters={"code": "CTR.SZ"})
            real.add_batch(test_data)
            mock.clear()
            mock.add_batch(test_data)

            # 查询DataFrame - 区分处理真实CRUD和Mock CRUD
            # 真实CRUD: 返回ModelList，需要to_dataframe()转换
            real_models = real.find(filters={"code": "CTR.SZ"})
            real_df = real_models.to_dataframe()

            # Mock CRUD: as_dataframe=True直接返回DataFrame
            mock_df = mock.find(filters={"code": "CTR.SZ"}, as_dataframe=True)

            import pandas as pd
            print(f"\n✓ 真实CRUD: {type(real_df).__name__}, shape={real_df.shape}")
            print(f"✓ Mock CRUD: {type(mock_df).__name__}, shape={mock_df.shape}")

            assert isinstance(real_df, pd.DataFrame) and isinstance(mock_df, pd.DataFrame)
            assert real_df.shape[0] == mock_df.shape[0] == 3

            # 验证关键列
            key_cols = ['code', 'timestamp', 'volume']
            for col in key_cols:
                assert col in real_df.columns and col in mock_df.columns

            assert list(real_df['volume']) == list(mock_df['volume'])

            print("✅ 契约验证通过")

        finally:
            real.remove(filters={"code": "CTR.SZ"})
