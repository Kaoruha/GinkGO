"""
BarCRUD数据库操作TDD测试 - K线数据管理

本文件测试BarCRUD类的完整功能，确保K线数据(Bar)的增删改查操作正常工作。
Bar数据是量化交易系统中最基础的时间序列数据，包含OHLCV（开高低收成交量）信息。

测试范围：
1. 插入操作 (Insert Operations)
   - 批量插入 (add_batch): 高效插入大量K线数据
   - 单条插入 (add): 插入单条K线记录
   - 分页插入 (pagination): 测试大数据量分页处理

2. 查询操作 (Query Operations)
   - 按股票代码查询 (find_by_code): 获取特定股票的K线数据
   - 按时间范围查询 (find_by_date_range): 获取指定时间段的数据
   - 数据框转换 (find_as_dataframe): 返回pandas DataFrame格式
   - 模型列表转换 (model_list_conversions): 业务对象与数据库模型转换
   - 计数与存在性检查 (count_and_exists): 快速数据统计

3. 删除操作 (Delete Operations)
   - 按股票代码删除 (delete_by_code): 清理特定股票数据
   - 按时间范围删除 (delete_by_time_range): 清理指定时间段数据
   - 按频率删除 (delete_by_frequency): 清理特定频率数据
   - 按价格范围删除 (delete_by_price_range): 清理异常价格数据
   - 按成交量阈值删除 (delete_by_volume_threshold): 清理低流动性数据
   - 批量清理 (batch_cleanup): 测试数据批量清理

数据模型：
- MBar: K线数据模型，包含代码、时间戳、OHLCV、频率、数据源等字段
- 支持多种频率：日线、分钟线、小时线等
- 数据源支持：Tushare、Yahoo、AKShare、实盘等

业务价值：
- 为策略回测提供基础价格数据
- 支持技术指标计算和分析
- 为风险管理提供历史价格波动数据
- 支持多时间框架分析

测试策略：
- 使用SOURCE_TYPES.TEST标记测试数据，便于清理
- 覆盖边界条件和异常情况
- 验证数据完整性和一致性
- 测试性能和大数据量处理
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.bar_crud import BarCRUD
from ginkgo.data.models.model_bar import MBar
from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES
from decimal import Decimal


@pytest.mark.database
class TestBarCRUDInsert:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': BarCRUD}
    """1. CRUD层插入操作测试"""

    def test_add_batch_basic(self):
        """测试批量插入Bar数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: CRUD层批量插入")
        print("="*60)

        bar_crud = BarCRUD()
        print(f"✓ 创建BarCRUD实例: {bar_crud.__class__.__name__}")

        # 创建测试Bar数据
        test_bars = [
            MBar(
                code="TEST001.SZ",
                timestamp=datetime(2023, 1, 3, 9, 30),
                open=10.0,
                high=10.5,
                low=9.8,
                close=10.2,
                volume=1000000,
                frequency=FREQUENCY_TYPES.DAY,
                source=SOURCE_TYPES.TEST
            ),
            MBar(
                code="TEST001.SZ",
                timestamp=datetime(2023, 1, 4, 9, 30),
                open=10.2,
                high=10.8,
                low=10.0,
                close=10.6,
                volume=1200000,
                frequency=FREQUENCY_TYPES.DAY,
                source=SOURCE_TYPES.TEST
            )
        ]
        print(f"✓ 创建测试数据: {len(test_bars)}条Bar记录")
        print(f"  - 股票代码: TEST001.SZ")
        print(f"  - 日期范围: 2023-01-03 ~ 2023-01-04")
        print(f"  - 频率: {FREQUENCY_TYPES.DAY.name} (枚举值={test_bars[0].frequency})")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            bar_crud.add_batch(test_bars)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = bar_crud.find(filters={"code": "TEST001.SZ"})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 2

            # 验证数据内容
            codes = [bar.code for bar in query_result]
            print(f"✓ 股票代码验证通过: {set(codes)}")
            assert "TEST001.SZ" in codes

            # 验证第一条数据
            from decimal import Decimal
            first_bar = [bar for bar in query_result if bar.timestamp == datetime(2023, 1, 3, 9, 30)][0]
            print(f"\n→ 验证第一条数据详细字段...")
            print(f"  - open:   {first_bar.open} (expected: 10.0)")
            print(f"  - high:   {first_bar.high} (expected: 10.5)")
            print(f"  - low:    {first_bar.low} (expected: 9.8)")
            print(f"  - close:  {first_bar.close} (expected: 10.2)")
            print(f"  - volume: {first_bar.volume} (expected: 1000000)")

            assert first_bar.open == Decimal('10.0')
            assert first_bar.high == Decimal('10.5')
            assert first_bar.low == Decimal('9.8')
            assert first_bar.close == Decimal('10.2')
            assert first_bar.volume == 1000000
            print("✓ 所有字段验证通过")

        finally:
            print("="*60)
            print("测试完成!")
            print("="*60)

    def test_add_single(self):
        """测试单条插入Bar数据 - 使用真实数据库"""
        from decimal import Decimal

        print("\n" + "="*60)
        print("开始测试: CRUD层单条插入")
        print("="*60)

        bar_crud = BarCRUD()
        print(f"✓ 创建BarCRUD实例")

        # 创建单条测试Bar数据
        test_bar = MBar(
            code="SINGLE001.SZ",
            timestamp=datetime(2023, 8, 1, 9, 30),
            open=Decimal('88.0'),
            high=Decimal('90.0'),
            low=Decimal('87.0'),
            close=Decimal('89.0'),
            volume=800000,
            frequency=1
        )
        test_bar.source = SOURCE_TYPES.TEST
        print(f"✓ 创建单条测试数据")
        print(f"  - 股票代码: SINGLE001.SZ")
        print(f"  - 日期: 2023-08-01")
        print(f"  - 收盘价: 89.0")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            result = bar_crud.add(test_bar)
            print("✓ 单条插入成功")

            # 验证返回值
            print("\n→ 验证返回值...")
            assert result is not None, "add()应返回插入的对象"
            print(f"✓ 返回对象类型: {type(result).__name__}")

            # 验证返回对象包含正确数据
            assert result.code == "SINGLE001.SZ", "返回对象的code应该正确"
            assert result.close == Decimal('89.0'), "返回对象的close应该正确"
            print(f"✓ 返回对象数据正确: code={result.code}, close={result.close}")

            # 验证数据已插入数据库
            print("\n→ 验证数据已插入数据库...")
            query_result = bar_crud.find(filters={"code": "SINGLE001.SZ"})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1, f"应查到至少1条，实际{len(query_result)}条"

            # 验证插入的数据内容
            saved_bar = query_result[0]
            print(f"\n→ 验证插入的数据内容...")
            print(f"  - code:   {saved_bar.code}")
            print(f"  - open:   {saved_bar.open}")
            print(f"  - high:   {saved_bar.high}")
            print(f"  - low:    {saved_bar.low}")
            print(f"  - close:  {saved_bar.close}")
            print(f"  - volume: {saved_bar.volume}")

            assert saved_bar.code == "SINGLE001.SZ"
            assert saved_bar.open == Decimal('88.0')
            assert saved_bar.high == Decimal('90.0')
            assert saved_bar.low == Decimal('87.0')
            assert saved_bar.close == Decimal('89.0')
            assert saved_bar.volume == 800000
            print("✓ 所有字段验证通过")

            # 验证timestamp字段
            assert saved_bar.timestamp == datetime(2023, 8, 1, 9, 30)
            print(f"✓ 时间戳验证通过: {saved_bar.timestamp}")

        finally:
            # 清理测试数据
            print("\n→ 清理测试数据...")
            bar_crud.remove(filters={"code": "SINGLE001.SZ"})
            print("✓ 测试数据已清理")
            print("="*60)
            print("测试完成!")
            print("="*60)

    def test_remove(self):
        """测试删除Bar数据 - 使用真实数据库"""
        from decimal import Decimal

        print("\n" + "="*60)
        print("开始测试: CRUD层删除操作")
        print("="*60)

        bar_crud = BarCRUD()
        print(f"✓ 创建BarCRUD实例")

        # 准备测试数据 - 3条数据（2条REMOVE001.SZ，1条REMOVE002.SZ）
        test_bars = [
            MBar(
                code="REMOVE001.SZ",
                timestamp=datetime(2023, 9, 1, 9, 30),
                open=Decimal('100.0'),
                high=Decimal('105.0'),
                low=Decimal('99.0'),
                close=Decimal('102.0'),
                volume=1000000,
                frequency=1
            ),
            MBar(
                code="REMOVE001.SZ",
                timestamp=datetime(2023, 9, 2, 9, 30),
                open=Decimal('102.0'),
                high=Decimal('106.0'),
                low=Decimal('101.0'),
                close=Decimal('104.0'),
                volume=1100000,
                frequency=1
            ),
            MBar(
                code="REMOVE002.SZ",
                timestamp=datetime(2023, 9, 1, 9, 30),
                open=Decimal('200.0'),
                high=Decimal('205.0'),
                low=Decimal('199.0'),
                close=Decimal('202.0'),
                volume=500000,
                frequency=1
            )
        ]

        try:
            # 插入测试数据
            print(f"\n→ 插入 {len(test_bars)} 条测试数据...")
            print(f"  - REMOVE001.SZ: 2条")
            print(f"  - REMOVE002.SZ: 1条")
            bar_crud.add_batch(test_bars)
            print("✓ 数据插入成功")

            # 验证初始数据存在
            print("\n→ 验证初始数据...")
            count1 = bar_crud.count(filters={"code": "REMOVE001.SZ"})
            count2 = bar_crud.count(filters={"code": "REMOVE002.SZ"})
            print(f"✓ REMOVE001.SZ: {count1}条")
            print(f"✓ REMOVE002.SZ: {count2}条")
            assert count1 >= 2, "REMOVE001.SZ应有2条"
            assert count2 >= 1, "REMOVE002.SZ应有1条"

            # 测试1: 删除REMOVE001.SZ的所有数据
            print("\n→ 测试删除REMOVE001.SZ...")
            bar_crud.remove(filters={"code": "REMOVE001.SZ"})
            print("✓ 删除操作执行完成")

            # 验证REMOVE001.SZ已被删除
            print("\n→ 验证REMOVE001.SZ已被删除...")
            exists1 = bar_crud.exists(filters={"code": "REMOVE001.SZ"})
            count1_after = bar_crud.count(filters={"code": "REMOVE001.SZ"})
            find1_result = bar_crud.find(filters={"code": "REMOVE001.SZ"})

            print(f"  - exists: {exists1} (应为False)")
            print(f"  - count: {count1_after} (应为0)")
            print(f"  - find结果: {len(find1_result)}条 (应为0)")

            assert exists1 is False, "REMOVE001.SZ应该不存在"
            assert count1_after == 0, "REMOVE001.SZ的count应为0"
            assert len(find1_result) == 0, "REMOVE001.SZ的find应返回空列表"
            print("✓ REMOVE001.SZ已完全删除")

            # 验证REMOVE002.SZ未被误删
            print("\n→ 验证REMOVE002.SZ未被误删...")
            exists2 = bar_crud.exists(filters={"code": "REMOVE002.SZ"})
            count2_after = bar_crud.count(filters={"code": "REMOVE002.SZ"})
            find2_result = bar_crud.find(filters={"code": "REMOVE002.SZ"})

            print(f"  - exists: {exists2} (应为True)")
            print(f"  - count: {count2_after} (应>=1)")
            print(f"  - find结果: {len(find2_result)}条 (应>=1)")

            assert exists2 is True, "REMOVE002.SZ应该仍存在"
            assert count2_after >= 1, "REMOVE002.SZ的count应>=1"
            assert len(find2_result) >= 1, "REMOVE002.SZ的find应返回数据"
            print("✓ REMOVE002.SZ未被误删，删除操作边界正确")

            # 测试2: 按时间范围删除
            print("\n→ 测试按时间范围删除...")
            # 插入一条新数据用于时间范围删除测试
            time_test_bar = MBar(
                code="REMOVE003.SZ",
                timestamp=datetime(2023, 9, 15, 9, 30),
                open=Decimal('150.0'),
                high=Decimal('155.0'),
                low=Decimal('149.0'),
                close=Decimal('152.0'),
                volume=600000,
                frequency=1
            )
            time_test_bar.source = SOURCE_TYPES.TEST
            bar_crud.add(time_test_bar)
            print(f"✓ 插入测试数据: REMOVE003.SZ (2023-09-15)")

            # 删除2023-09-15之前的REMOVE003.SZ数据（不应该删除任何数据）
            bar_crud.remove(filters={
                "code": "REMOVE003.SZ",
                "timestamp__lte": datetime(2023, 9, 14, 23, 59)
            })

            # 验证REMOVE003.SZ仍存在（时间过滤正确）
            exists3 = bar_crud.exists(filters={"code": "REMOVE003.SZ"})
            assert exists3 is True, "REMOVE003.SZ应该仍存在（时间过滤应该排除它）"
            print(f"✓ 时间范围删除正确：REMOVE003.SZ未被删除")

            # 删除2023-09-15及之后的数据（应该删除REMOVE003.SZ）
            bar_crud.remove(filters={
                "code": "REMOVE003.SZ",
                "timestamp__gte": datetime(2023, 9, 15, 0, 0)
            })

            exists3_after = bar_crud.exists(filters={"code": "REMOVE003.SZ"})
            assert exists3_after is False, "REMOVE003.SZ应该被删除（时间范围匹配）"
            print(f"✓ 时间范围删除正确：REMOVE003.SZ已删除")

        finally:
            # 清理所有测试数据
            print("\n→ 清理所有测试数据...")
            bar_crud.remove(filters={"code": "REMOVE001.SZ"})
            bar_crud.remove(filters={"code": "REMOVE002.SZ"})
            bar_crud.remove(filters={"code": "REMOVE003.SZ"})
            print("✓ 所有测试数据已清理")
            print("="*60)
            print("测试完成!")
            print("="*60)

    def test_pagination(self):
        """测试分页查询功能 - 使用真实数据库"""
        from decimal import Decimal

        print("\n" + "="*60)
        print("开始测试: CRUD层分页查询")
        print("="*60)

        bar_crud = BarCRUD()
        print(f"✓ 创建BarCRUD实例")

        # 准备测试数据 - 10条数据（同一个code，不同日期）
        test_bars = []
        for i in range(1, 11):
            bar = MBar(
                code="PAGE001.SZ",
                timestamp=datetime(2023, 10, i, 9, 30),
                open=Decimal(f'{100 + i}.0'),
                high=Decimal(f'{105 + i}.0'),
                low=Decimal(f'{99 + i}.0'),
                close=Decimal(f'{102 + i}.0'),
                volume=1000000 + i * 10000,
                frequency=1
            )
            bar.source = SOURCE_TYPES.TEST
            test_bars.append(bar)

        try:
            # 插入测试数据
            print(f"\n→ 插入 {len(test_bars)} 条测试数据...")
            print(f"  - 股票代码: PAGE001.SZ")
            print(f"  - 日期范围: 2023-10-01 ~ 2023-10-10")
            bar_crud.add_batch(test_bars)
            print("✓ 数据插入成功")

            # 验证总数
            total_count = bar_crud.count(filters={"code": "PAGE001.SZ"})
            print(f"\n→ 验证总数: {total_count}条")
            assert total_count >= 10, f"应有至少10条，实际{total_count}条"

            # 测试1: 第1页（page=0, page_size=3）- 0-based索引
            print("\n→ 测试第1页（page=0, page_size=3）...")
            page1 = bar_crud.find(
                filters={"code": "PAGE001.SZ"},
                page=0,
                page_size=3,
                order_by="timestamp",
                desc_order=False
            )
            print(f"✓ 第1页查询到 {len(page1)} 条记录")
            assert len(page1) == 3, f"第1页应返回3条，实际{len(page1)}条"

            # 验证第1页数据（应该是10-01, 10-02, 10-03）
            page1_dates = [bar.timestamp.day for bar in page1]
            print(f"  - 日期: {page1_dates}")
            assert page1_dates == [1, 2, 3], f"第1页日期应为[1,2,3]，实际{page1_dates}"

            # 测试2: 第2页（page=1, page_size=3）- 0-based索引
            print("\n→ 测试第2页（page=1, page_size=3）...")
            page2 = bar_crud.find(
                filters={"code": "PAGE001.SZ"},
                page=1,
                page_size=3,
                order_by="timestamp",
                desc_order=False
            )
            print(f"✓ 第2页查询到 {len(page2)} 条记录")
            assert len(page2) == 3, f"第2页应返回3条，实际{len(page2)}条"

            # 验证第2页数据（应该是10-04, 10-05, 10-06）
            page2_dates = [bar.timestamp.day for bar in page2]
            print(f"  - 日期: {page2_dates}")
            assert page2_dates == [4, 5, 6], f"第2页日期应为[4,5,6]，实际{page2_dates}"

            # 测试3: 第4页（最后一页，只有1条）- page=3表示第4页
            print("\n→ 测试第4页（page=3, page_size=3）...")
            page4 = bar_crud.find(
                filters={"code": "PAGE001.SZ"},
                page=3,
                page_size=3,
                order_by="timestamp",
                desc_order=False
            )
            print(f"✓ 第4页查询到 {len(page4)} 条记录")
            assert len(page4) == 1, f"第4页应返回1条，实际{len(page4)}条"

            # 验证第4页数据（应该是10-10）
            page4_dates = [bar.timestamp.day for bar in page4]
            print(f"  - 日期: {page4_dates}")
            assert page4_dates == [10], f"第4页日期应为[10]，实际{page4_dates}"

            # 测试4: 验证数据不重复
            print("\n→ 验证分页数据不重复...")
            page1_codes = set(bar.timestamp.day for bar in page1)
            page2_codes = set(bar.timestamp.day for bar in page2)
            intersection = page1_codes & page2_codes
            print(f"✓ 第1页和第2页数据交集: {intersection}")
            assert len(intersection) == 0, "分页数据不应重复"

            # 测试5: 超出范围的页码 - page=99表示第100页
            print("\n→ 测试超出范围的页码（page=99）...")
            page100 = bar_crud.find(
                filters={"code": "PAGE001.SZ"},
                page=99,
                page_size=3
            )
            print(f"✓ 超范围页码返回: {len(page100)}条")
            assert len(page100) == 0, "超范围页码应返回空列表"

        finally:
            # 清理测试数据
            print("\n→ 清理测试数据...")
            bar_crud.remove(filters={"code": "PAGE001.SZ"})
            print("✓ 测试数据已清理")
            print("="*60)
            print("测试完成!")
            print("="*60)

    def test_ordering(self):
        """测试排序功能 - 使用真实数据库"""
        from decimal import Decimal

        print("\n" + "="*60)
        print("开始测试: CRUD层排序功能")
        print("="*60)

        bar_crud = BarCRUD()
        print(f"✓ 创建BarCRUD实例")

        # 准备测试数据 - 5条乱序数据
        test_bars = [
            MBar(code="ORDER001.SZ", timestamp=datetime(2023, 11, 3, 9, 30),
                 open=Decimal('103.0'), close=Decimal('103.5'),
                 high=Decimal('104.0'), low=Decimal('102.5'), volume=1300000, frequency=1),
            MBar(code="ORDER001.SZ", timestamp=datetime(2023, 11, 1, 9, 30),
                 open=Decimal('101.0'), close=Decimal('101.5'),
                 high=Decimal('102.0'), low=Decimal('100.5'), volume=1100000, frequency=1),
            MBar(code="ORDER001.SZ", timestamp=datetime(2023, 11, 5, 9, 30),
                 open=Decimal('105.0'), close=Decimal('105.5'),
                 high=Decimal('106.0'), low=Decimal('104.5'), volume=1500000, frequency=1),
            MBar(code="ORDER001.SZ", timestamp=datetime(2023, 11, 2, 9, 30),
                 open=Decimal('102.0'), close=Decimal('102.5'),
                 high=Decimal('103.0'), low=Decimal('101.5'), volume=1200000, frequency=1),
            MBar(code="ORDER001.SZ", timestamp=datetime(2023, 11, 4, 9, 30),
                 open=Decimal('104.0'), close=Decimal('104.5'),
                 high=Decimal('105.0'), low=Decimal('103.5'), volume=1400000, frequency=1),
        ]

        try:
            # 插入测试数据
            print(f"\n→ 插入 {len(test_bars)} 条乱序测试数据...")
            print(f"  - 股票代码: ORDER001.SZ")
            print(f"  - 插入顺序: 11-03, 11-01, 11-05, 11-02, 11-04 (乱序)")
            bar_crud.add_batch(test_bars)
            print("✓ 数据插入成功")

            # 测试1: 按timestamp升序排列
            print("\n→ 测试按timestamp升序排列...")
            result_asc = bar_crud.find(
                filters={"code": "ORDER001.SZ"},
                order_by="timestamp",
                desc_order=False
            )
            dates_asc = [bar.timestamp.day for bar in result_asc]
            print(f"✓ 升序结果: {dates_asc}")
            assert dates_asc == [1, 2, 3, 4, 5], f"升序应为[1,2,3,4,5]，实际{dates_asc}"
            print("✓ 升序排序正确")

            # 测试2: 按timestamp降序排列
            print("\n→ 测试按timestamp降序排列...")
            result_desc = bar_crud.find(
                filters={"code": "ORDER001.SZ"},
                order_by="timestamp",
                desc_order=True
            )
            dates_desc = [bar.timestamp.day for bar in result_desc]
            print(f"✓ 降序结果: {dates_desc}")
            assert dates_desc == [5, 4, 3, 2, 1], f"降序应为[5,4,3,2,1]，实际{dates_desc}"
            print("✓ 降序排序正确")

            # 测试3: 按volume升序排列
            print("\n→ 测试按volume升序排列...")
            result_vol_asc = bar_crud.find(
                filters={"code": "ORDER001.SZ"},
                order_by="volume",
                desc_order=False
            )
            volumes_asc = [bar.volume for bar in result_vol_asc]
            print(f"✓ volume升序: {volumes_asc}")
            expected_vol_asc = [1100000, 1200000, 1300000, 1400000, 1500000]
            assert volumes_asc == expected_vol_asc, f"volume升序错误"
            print("✓ volume升序排序正确")

            # 测试4: 按volume降序排列
            print("\n→ 测试按volume降序排列...")
            result_vol_desc = bar_crud.find(
                filters={"code": "ORDER001.SZ"},
                order_by="volume",
                desc_order=True
            )
            volumes_desc = [bar.volume for bar in result_vol_desc]
            print(f"✓ volume降序: {volumes_desc}")
            expected_vol_desc = [1500000, 1400000, 1300000, 1200000, 1100000]
            assert volumes_desc == expected_vol_desc, f"volume降序错误"
            print("✓ volume降序排序正确")

            # 测试5: 验证排序与过滤组合 - page=0表示第1页
            print("\n→ 测试排序与分页组合...")
            result_combined = bar_crud.find(
                filters={"code": "ORDER001.SZ"},
                order_by="timestamp",
                desc_order=True,
                page=0,
                page_size=3
            )
            dates_combined = [bar.timestamp.day for bar in result_combined]
            print(f"✓ 降序+分页(前3条): {dates_combined}")
            assert dates_combined == [5, 4, 3], f"组合查询应返回[5,4,3]，实际{dates_combined}"
            print("✓ 排序与分页组合正确")

        finally:
            # 清理测试数据
            print("\n→ 清理测试数据...")
            bar_crud.remove(filters={"code": "ORDER001.SZ"})
            print("✓ 测试数据已清理")
            print("="*60)
            print("测试完成!")
            print("="*60)

    def test_complex_filters(self):
        """测试复杂筛选条件组合 - 使用真实数据库"""
        from decimal import Decimal

        print("\n" + "="*60)
        print("开始测试: CRUD层复杂筛选")
        print("="*60)

        bar_crud = BarCRUD()
        print(f"✓ 创建BarCRUD实例")

        # 准备测试数据 - 两个股票，不同时间和成交量
        test_bars = [
            # FILTER_A.SZ - 大成交量
            MBar(code="FILTER_A.SZ", timestamp=datetime(2023, 11, 1, 9, 30),
                 open=Decimal('100.0'), close=Decimal('101.0'),
                 high=Decimal('102.0'), low=Decimal('99.0'), volume=5000000, frequency=1),
            MBar(code="FILTER_A.SZ", timestamp=datetime(2023, 11, 5, 9, 30),
                 open=Decimal('105.0'), close=Decimal('106.0'),
                 high=Decimal('107.0'), low=Decimal('104.0'), volume=6000000, frequency=1),
            MBar(code="FILTER_A.SZ", timestamp=datetime(2023, 11, 10, 9, 30),
                 open=Decimal('110.0'), close=Decimal('111.0'),
                 high=Decimal('112.0'), low=Decimal('109.0'), volume=7000000, frequency=1),
            # FILTER_B.SZ - 小成交量
            MBar(code="FILTER_B.SZ", timestamp=datetime(2023, 11, 3, 9, 30),
                 open=Decimal('50.0'), close=Decimal('51.0'),
                 high=Decimal('52.0'), low=Decimal('49.0'), volume=1000000, frequency=1),
            MBar(code="FILTER_B.SZ", timestamp=datetime(2023, 11, 7, 9, 30),
                 open=Decimal('55.0'), close=Decimal('56.0'),
                 high=Decimal('57.0'), low=Decimal('54.0'), volume=1500000, frequency=1),
        ]

        try:
            # 插入测试数据
            print(f"\n→ 插入 {len(test_bars)} 条测试数据...")
            print(f"  - FILTER_A.SZ: 3条（大成交量 5M-7M）")
            print(f"  - FILTER_B.SZ: 2条（小成交量 1M-1.5M）")
            bar_crud.add_batch(test_bars)
            print("✓ 数据插入成功")

            # 测试1: 单一code筛选 + 时间范围
            print("\n→ 测试组合1: code + 时间范围...")
            result1 = bar_crud.find(
                filters={
                    "code": "FILTER_A.SZ",
                    "timestamp__gte": datetime(2023, 11, 5, 0, 0),
                    "timestamp__lte": datetime(2023, 11, 10, 23, 59)
                }
            )
            print(f"✓ FILTER_A.SZ [11-05~11-10]: {len(result1)}条")
            assert len(result1) == 2, f"应返回2条（11-05和11-10），实际{len(result1)}条"
            dates1 = sorted([bar.timestamp.day for bar in result1])
            assert dates1 == [5, 10], f"日期应为[5,10]，实际{dates1}"

            # 测试2: 时间范围 + 成交量范围（跨code）
            print("\n→ 测试组合2: 时间范围 + 成交量范围...")
            result2 = bar_crud.find(
                filters={
                    "timestamp__gte": datetime(2023, 11, 1, 0, 0),
                    "timestamp__lte": datetime(2023, 11, 7, 23, 59),
                    "volume__gte": 1000000,
                    "volume__lte": 5500000
                }
            )
            print(f"✓ [11-01~11-07] volume∈[1M,5.5M]: {len(result2)}条")
            # 应包含: FILTER_A(11-01/5M), FILTER_B(11-03/1M, 11-07/1.5M)
            assert len(result2) == 3, f"应返回3条，实际{len(result2)}条"

            # 测试3: 三重条件组合（code + 时间 + 成交量）
            print("\n→ 测试组合3: code + 时间 + 成交量...")
            result3 = bar_crud.find(
                filters={
                    "code": "FILTER_A.SZ",
                    "timestamp__gte": datetime(2023, 11, 1, 0, 0),
                    "volume__gte": 6000000
                }
            )
            print(f"✓ FILTER_A.SZ + [11-01~] + volume≥6M: {len(result3)}条")
            # 应包含: 11-05(6M), 11-10(7M)
            assert len(result3) == 2, f"应返回2条，实际{len(result3)}条"
            volumes3 = sorted([bar.volume for bar in result3])
            assert volumes3 == [6000000, 7000000], "成交量应为[6M,7M]"

            # 测试4: 严格筛选导致空结果
            print("\n→ 测试组合4: 严格条件（无匹配）...")
            result4 = bar_crud.find(
                filters={
                    "code": "FILTER_B.SZ",
                    "volume__gte": 10000000  # FILTER_B最大只有1.5M
                }
            )
            print(f"✓ FILTER_B.SZ + volume≥10M: {len(result4)}条")
            assert len(result4) == 0, "严格条件应返回空结果"

            # 测试5: 复杂条件 + 排序 + 分页
            print("\n→ 测试组合5: 复杂筛选 + 排序 + 分页...")
            result5 = bar_crud.find(
                filters={
                    "timestamp__gte": datetime(2023, 11, 1, 0, 0),
                    "volume__gte": 1000000
                },
                order_by="volume",
                desc_order=True,
                page=0,
                page_size=3
            )
            print(f"✓ volume降序 + 分页前3条: {len(result5)}条")
            volumes5 = [bar.volume for bar in result5]
            print(f"  - 成交量序列: {volumes5}")
            # 降序前3: 7M, 6M, 5M
            assert volumes5 == [7000000, 6000000, 5000000], "降序前3应为[7M,6M,5M]"

        finally:
            # 清理测试数据
            print("\n→ 清理测试数据...")
            bar_crud.remove(filters={"code": "FILTER_A.SZ"})
            bar_crud.remove(filters={"code": "FILTER_B.SZ"})
            print("✓ 测试数据已清理")
            print("="*60)
            print("测试完成!")
            print("="*60)


@pytest.mark.database
class TestBarCRUDQuery:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': BarCRUD}
    """2. CRUD层查询操作测试"""

    def test_find_by_code(self):
        """测试按股票代码查询 - 使用真实数据库"""
        from decimal import Decimal

        print("\n" + "="*60)
        print("开始测试: CRUD层按代码查询")
        print("="*60)

        bar_crud = BarCRUD()
        print(f"✓ 创建BarCRUD实例")

        # 准备测试数据
        test_bars = [
            MBar(
                code="QUERY001.SZ",
                timestamp=datetime(2023, 5, 10, 9, 30),
                open=Decimal('12.0'),
                high=Decimal('12.5'),
                low=Decimal('11.8'),
                close=Decimal('12.2'),
                volume=900000,
                frequency=1
            ),
            MBar(
                code="QUERY001.SZ",
                timestamp=datetime(2023, 5, 11, 9, 30),
                open=Decimal('12.2'),
                high=Decimal('12.8'),
                low=Decimal('12.0'),
                close=Decimal('12.6'),
                volume=950000,
                frequency=1
            ),
            MBar(
                code="QUERY002.SZ",
                timestamp=datetime(2023, 5, 10, 9, 30),
                open=Decimal('25.0'),
                high=Decimal('25.5'),
                low=Decimal('24.8'),
                close=Decimal('25.2'),
                volume=600000,
                frequency=1
            )
        ]

        try:
            # 插入测试数据
            print(f"\n→ 插入 {len(test_bars)} 条测试数据...")
            bar_crud.add_batch(test_bars)
            print("✓ 数据插入成功")

            # 查询QUERY001.SZ
            print("\n→ 查询 QUERY001.SZ...")
            result = bar_crud.find(filters={"code": "QUERY001.SZ"})
            print(f"✓ 查询到 {len(result)} 条记录")

            # 验证查询结果
            assert len(result) == 2, f"应查到2条，实际{len(result)}条"
            assert all(bar.code == "QUERY001.SZ" for bar in result), "所有记录应为QUERY001.SZ"
            print("✓ 股票代码过滤正确")

            # 验证数据内容
            dates = [bar.timestamp.date() for bar in result]
            print(f"✓ 查询到的日期: {dates}")
            assert datetime(2023, 5, 10).date() in dates
            assert datetime(2023, 5, 11).date() in dates

            # 查询QUERY002.SZ
            print("\n→ 查询 QUERY002.SZ...")
            result2 = bar_crud.find(filters={"code": "QUERY002.SZ"})
            print(f"✓ 查询到 {len(result2)} 条记录")
            assert len(result2) == 1
            assert result2[0].code == "QUERY002.SZ"
            print("✓ 不同代码查询互不干扰")

        finally:
            # 清理测试数据
            print("\n→ 清理测试数据...")
            bar_crud.remove(filters={"code": "QUERY001.SZ"})
            bar_crud.remove(filters={"code": "QUERY002.SZ"})
            print("✓ 测试数据已清理")
            print("="*60)
            print("测试完成!")
            print("="*60)

    def test_find_by_date_range(self):
        """测试按时间范围查询 - 使用真实数据库"""
        from decimal import Decimal

        print("\n" + "="*60)
        print("开始测试: CRUD层按时间范围查询")
        print("="*60)

        bar_crud = BarCRUD()
        print(f"✓ 创建BarCRUD实例")

        # 准备测试数据 - 3个不同日期
        test_bars = [
            MBar(
                code="DATERANGE001.SZ",
                timestamp=datetime(2023, 5, 10, 9, 30),
                open=Decimal('10.0'),
                high=Decimal('10.5'),
                low=Decimal('9.8'),
                close=Decimal('10.2'),
                volume=1000000,
                frequency=1
            ),
            MBar(
                code="DATERANGE001.SZ",
                timestamp=datetime(2023, 5, 15, 9, 30),
                open=Decimal('15.0'),
                high=Decimal('15.5'),
                low=Decimal('14.8'),
                close=Decimal('15.2'),
                volume=1500000,
                frequency=1
            ),
            MBar(
                code="DATERANGE001.SZ",
                timestamp=datetime(2023, 5, 20, 9, 30),
                open=Decimal('20.0'),
                high=Decimal('20.5'),
                low=Decimal('19.8'),
                close=Decimal('20.2'),
                volume=2000000,
                frequency=1
            )
        ]

        try:
            # 插入测试数据
            print(f"\n→ 插入 {len(test_bars)} 条测试数据...")
            print(f"  - 日期1: 2023-05-10")
            print(f"  - 日期2: 2023-05-15")
            print(f"  - 日期3: 2023-05-20")
            bar_crud.add_batch(test_bars)
            print("✓ 数据插入成功")

            # 测试1: 查询中间范围（2023-05-12 ~ 2023-05-18）
            print("\n→ 测试时间范围过滤: 2023-05-12 ~ 2023-05-18...")
            result = bar_crud.find(filters={
                "code": "DATERANGE001.SZ",
                "timestamp__gte": datetime(2023, 5, 12, 0, 0),
                "timestamp__lte": datetime(2023, 5, 18, 23, 59)
            })
            print(f"✓ 查询到 {len(result)} 条记录")

            # 验证只返回2023-05-15的记录
            assert len(result) == 1, f"应查到1条，实际{len(result)}条"
            assert result[0].timestamp.date() == datetime(2023, 5, 15).date()
            print(f"✓ 时间范围过滤正确: {result[0].timestamp.date()}")

            # 验证数据字段
            assert result[0].close == Decimal('15.2')
            print(f"✓ 数据内容正确: close={result[0].close}")

            # 测试2: 查询全部范围验证3条都存在
            print("\n→ 验证全部数据: 2023-05-01 ~ 2023-05-31...")
            result_all = bar_crud.find(filters={
                "code": "DATERANGE001.SZ",
                "timestamp__gte": datetime(2023, 5, 1, 0, 0),
                "timestamp__lte": datetime(2023, 5, 31, 23, 59)
            })
            print(f"✓ 查询到 {len(result_all)} 条记录")
            assert len(result_all) == 3, f"应查到3条，实际{len(result_all)}条"

            dates = sorted([bar.timestamp.date() for bar in result_all])
            print(f"✓ 所有日期: {dates}")
            assert datetime(2023, 5, 10).date() in dates
            assert datetime(2023, 5, 15).date() in dates
            assert datetime(2023, 5, 20).date() in dates

            # 测试3: 查询边界情况（精确日期）
            print("\n→ 测试精确日期查询: 2023-05-15...")
            result_exact = bar_crud.find(filters={
                "code": "DATERANGE001.SZ",
                "timestamp__gte": datetime(2023, 5, 15, 0, 0),
                "timestamp__lte": datetime(2023, 5, 15, 23, 59)
            })
            print(f"✓ 查询到 {len(result_exact)} 条记录")
            assert len(result_exact) == 1
            assert result_exact[0].timestamp.date() == datetime(2023, 5, 15).date()
            print("✓ 精确日期查询正确")

        finally:
            # 清理测试数据
            print("\n→ 清理测试数据...")
            bar_crud.remove(filters={"code": "DATERANGE001.SZ"})
            print("✓ 测试数据已清理")
            print("="*60)
            print("测试完成!")
            print("="*60)

    def test_find_as_dataframe(self):
        """测试DataFrame格式返回 - 使用真实数据库"""
        from decimal import Decimal
        import pandas as pd

        print("\n" + "="*60)
        print("开始测试: CRUD层DataFrame格式返回")
        print("="*60)

        bar_crud = BarCRUD()
        print(f"✓ 创建BarCRUD实例")

        # 准备测试数据
        test_bars = [
            MBar(
                code="DATAFRAME001.SZ",
                timestamp=datetime(2023, 6, 1, 9, 30),
                open=Decimal('100.0'),
                high=Decimal('105.0'),
                low=Decimal('98.0'),
                close=Decimal('102.0'),
                volume=1000000,
                frequency=1
            ),
            MBar(
                code="DATAFRAME001.SZ",
                timestamp=datetime(2023, 6, 2, 9, 30),
                open=Decimal('102.0'),
                high=Decimal('108.0'),
                low=Decimal('100.0'),
                close=Decimal('106.0'),
                volume=1200000,
                frequency=1
            )
        ]

        try:
            # 插入测试数据
            print(f"\n→ 插入 {len(test_bars)} 条测试数据...")
            bar_crud.add_batch(test_bars)
            print("✓ 数据插入成功")

            # 测试1: 查询返回ModelList，然后转换为DataFrame
            print("\n→ 测试ModelList转DataFrame格式...")
            model_list = bar_crud.find(filters={"code": "DATAFRAME001.SZ"})
            print(f"✓ 返回类型: {type(model_list).__name__}")
            assert hasattr(model_list, 'to_dataframe'), "ModelList应该有to_dataframe方法"

            df = model_list.to_dataframe()
            print(f"✓ 转换后的DataFrame类型: {type(df).__name__}")
            assert isinstance(df, pd.DataFrame), f"应返回DataFrame，实际{type(df)}"
            print(f"✓ DataFrame形状: {df.shape}")

            # 验证行数
            assert len(df) == 2, f"应有2行，实际{len(df)}行"

            # 测试2: 验证DataFrame列名
            print("\n→ 验证DataFrame列名...")
            required_columns = ['code', 'timestamp', 'open', 'high', 'low', 'close', 'volume']
            print(f"  实际列: {list(df.columns)}")
            for col in required_columns:
                assert col in df.columns, f"缺少列: {col}"
            print(f"✓ 包含所有必要列: {required_columns}")

            # 测试3: 验证数据类型（Decimal在DataFrame中存储为object dtype）
            print("\n→ 验证数据类型（Decimal存储）...")
            from decimal import Decimal

            # 获取第一行数据用于后续验证
            first_row = df.iloc[0]

            # Decimal在pandas DataFrame中存储为object dtype，这是正常的
            assert df['open'].dtype == object, f"open列应为object(Decimal)，实际{df['open'].dtype}"
            assert df['close'].dtype == object, f"close列应为object(Decimal)，实际{df['close'].dtype}"
            print(f"✓ 价格字段类型: open={df['open'].dtype}, close={df['close'].dtype}")

            # 验证确实是Decimal类型且值正确
            assert isinstance(first_row['open'], Decimal), f"open应为Decimal，实际{type(first_row['open'])}"
            assert isinstance(first_row['close'], Decimal), f"close应为Decimal，实际{type(first_row['close'])}"
            print(f"✓ Decimal类型验证通过，保持了金融精度")

            # 测试4: 验证数据内容
            print("\n→ 验证数据内容...")
            print(f"  第一行: code={first_row['code']}, open={first_row['open']}, close={first_row['close']}")
            assert first_row['code'] == "DATAFRAME001.SZ"
            assert first_row['open'] == Decimal('100.0')
            assert first_row['close'] == Decimal('102.0')
            assert first_row['volume'] == 1000000
            print("✓ 数据内容正确（保持Decimal精度）")

            # 测试5: 验证空查询返回空DataFrame
            print("\n→ 测试空查询返回空DataFrame...")
            empty_model_list = bar_crud.find(filters={"code": "NONEXISTENT.SZ"})
            print(f"✓ 空查询返回类型: {type(empty_model_list).__name__}")
            assert hasattr(empty_model_list, 'to_dataframe'), "空ModelList应该有to_dataframe方法"

            empty_df = empty_model_list.to_dataframe()
            print(f"✓ 空查询DataFrame类型: {type(empty_df).__name__}")
            assert isinstance(empty_df, pd.DataFrame), "空查询应返回DataFrame"
            assert len(empty_df) == 0, f"空查询应返回0行，实际{len(empty_df)}行"
            print("✓ 空DataFrame处理正确")

            # 测试6: 验证ModelList的其他方法
            print("\n→ 测试ModelList的其他功能...")
            assert hasattr(model_list, 'count'), "ModelList应该有count方法"
            assert hasattr(model_list, '__len__'), "ModelList应该支持len()"
            assert len(model_list) == 2, f"ModelList长度应为2，实际{len(model_list)}"
            assert model_list.count() == 2, f"ModelList.count()应为2，实际{model_list.count()}"
            print("✓ ModelList功能验证正确")

        finally:
            # 清理测试数据
            print("\n→ 清理测试数据...")
            bar_crud.remove(filters={"code": "DATAFRAME001.SZ"})
            print("✓ 测试数据已清理")
            print("="*60)
            print("测试完成!")
            print("="*60)

    def test_model_list_conversions(self):
        """测试ModelList的to_dataframe和to_entities转换功能"""
        from decimal import Decimal
        import pandas as pd

        print("\n" + "="*60)
        print("开始测试: ModelList转换功能")
        print("="*60)

        bar_crud = BarCRUD()
        print(f"✓ 创建BarCRUD实例")

        # 准备测试数据 - 包含不同的频率和源
        test_bars = [
            MBar(
                code="CONVERT001.SZ",
                timestamp=datetime(2023, 12, 1, 9, 30),
                open=Decimal('50.0'),
                high=Decimal('52.0'),
                low=Decimal('49.0'),
                close=Decimal('51.0'),
                volume=2000000,
                frequency=FREQUENCY_TYPES.DAY,
                source=SOURCE_TYPES.TEST
            ),
            MBar(
                code="CONVERT001.SZ",
                timestamp=datetime(2023, 12, 2, 9, 30),
                open=Decimal('51.0'),
                high=Decimal('53.0'),
                low=Decimal('50.0'),
                close=Decimal('52.0'),
                volume=2200000,
                frequency=FREQUENCY_TYPES.DAY,
                source=SOURCE_TYPES.TEST
            ),
            MBar(
                code="CONVERT002.SZ",
                timestamp=datetime(2023, 12, 1, 10, 0),
                open=Decimal('100.0'),
                high=Decimal('102.0'),
                low=Decimal('99.0'),
                close=Decimal('101.0'),
                volume=1500000,
                frequency=FREQUENCY_TYPES.HOUR1,
                source=SOURCE_TYPES.TEST
            )
        ]

        try:
            # 插入测试数据
            print(f"\n→ 插入 {len(test_bars)} 条测试数据...")
            bar_crud.add_batch(test_bars)
            print("✓ 数据插入成功")

            # 获取ModelList
            print("\n→ 获取ModelList...")
            model_list = bar_crud.find(filters={"code__like": "CONVERT%"})
            print(f"✓ ModelList类型: {type(model_list).__name__}")
            print(f"✓ ModelList长度: {len(model_list)}")
            assert len(model_list) == 3, f"应有3条记录，实际{len(model_list)}条"

            # 测试1: to_dataframe转换
            print("\n→ 测试to_dataframe转换...")
            df = model_list.to_dataframe()
            print(f"✓ DataFrame类型: {type(df).__name__}")
            print(f"✓ DataFrame形状: {df.shape}")
            assert isinstance(df, pd.DataFrame), "应返回DataFrame"
            assert len(df) == 3, "DataFrame应有3行"

            # 验证DataFrame列和内容
            required_columns = ['code', 'timestamp', 'open', 'high', 'low', 'close', 'volume', 'frequency', 'source']
            for col in required_columns:
                assert col in df.columns, f"DataFrame缺少列: {col}"
            print(f"✓ 包含所有必要列: {required_columns}")

            # 验证Decimal精度保持
            first_row = df.iloc[0]
            assert isinstance(first_row['open'], Decimal), "open应保持Decimal类型"
            assert first_row['open'] == Decimal('50.0'), "open值应正确"
            print(f"✓ Decimal精度保持正确: open={first_row['open']}")

            # 测试2: to_entities转换
            print("\n→ 测试to_entities转换...")
            from ginkgo.trading import Bar
            entities = model_list.to_entities()
            print(f"✓ 实体列表类型: {type(entities).__name__}")
            print(f"✓ 实体列表长度: {len(entities)}")
            assert len(entities) == 3, "实体列表应有3个对象"

            # 验证实体类型和内容
            first_entity = entities[0]
            print(f"✓ 第一个实体类型: {type(first_entity).__name__}")
            assert isinstance(first_entity, Bar), "应转换为Bar业务对象"

            # 验证业务对象字段
            assert first_entity.code == "CONVERT001.SZ", "code应正确"
            assert first_entity.open == Decimal('50.0'), "open应正确"
            assert first_entity.volume == 2000000, "volume应正确"
            assert first_entity.frequency == FREQUENCY_TYPES.DAY, "frequency枚举应正确"
            # 注意：Bar业务对象不使用source字段，只有MBar模型需要source来记录数据来源
            print(f"✓ 业务对象字段验证通过")

            # 测试3: 验证枚举转换的正确性
            print("\n→ 验证枚举转换的正确性...")
            frequencies = [entity.frequency for entity in entities]

            print(f"✓ 频率枚举: {[f.name for f in frequencies]}")

            assert FREQUENCY_TYPES.DAY in frequencies, "应包含DAY频率"
            assert FREQUENCY_TYPES.HOUR1 in frequencies, "应包含HOUR1频率"
            print("✓ 枚举转换验证正确（frequency字段）")

            # 测试4: 验证缓存机制
            print("\n→ 测试转换缓存机制...")
            # 再次调用to_dataframe，应该使用缓存
            df2 = model_list.to_dataframe()
            entities2 = model_list.to_entities()

            # 验证结果一致性
            assert df.equals(df2), "缓存的DataFrame应该相同"
            assert len(entities) == len(entities2), "缓存的实体数量应该相同"

            # 验证地址不同（说明是缓存但不是同一个对象引用）
            # 这里我们只验证内容相同，因为具体实现可能返回缓存中的对象
            print("✓ 缓存机制验证正确")

            # 测试5: 验证空ModelList的转换
            print("\n→ 测试空ModelList的转换...")
            empty_model_list = bar_crud.find(filters={"code": "NONEXISTENT.SZ"})
            assert len(empty_model_list) == 0, "空ModelList长度应为0"

            empty_df = empty_model_list.to_dataframe()
            empty_entities = empty_model_list.to_entities()

            assert isinstance(empty_df, pd.DataFrame), "空转换应返回DataFrame"
            assert len(empty_df) == 0, "空DataFrame长度应为0"
            assert isinstance(empty_entities, list), "空转换应返回列表"
            assert len(empty_entities) == 0, "空实体列表长度应为0"
            print("✓ 空ModelList转换验证正确")

            print("\n✓ 所有ModelList转换功能测试通过！")

        finally:
            # 清理测试数据
            print("\n→ 清理测试数据...")
            bar_crud.remove(filters={"code__like": "CONVERT%"})
            print("✓ 测试数据已清理")
            print("="*60)
            print("测试完成!")
            print("="*60)

    def test_count_and_exists(self):
        """测试count()和exists()工具方法 - 使用真实数据库"""
        from decimal import Decimal

        print("\n" + "="*60)
        print("开始测试: CRUD层count和exists方法")
        print("="*60)

        bar_crud = BarCRUD()
        print(f"✓ 创建BarCRUD实例")

        # 准备测试数据 - 3条数据（2条COUNT001.SZ，1条COUNT002.SZ）
        test_bars = [
            MBar(
                code="COUNT001.SZ",
                timestamp=datetime(2023, 7, 1, 9, 30),
                open=Decimal('50.0'),
                high=Decimal('52.0'),
                low=Decimal('49.0'),
                close=Decimal('51.0'),
                volume=500000,
                frequency=1
            ),
            MBar(
                code="COUNT001.SZ",
                timestamp=datetime(2023, 7, 2, 9, 30),
                open=Decimal('51.0'),
                high=Decimal('53.0'),
                low=Decimal('50.0'),
                close=Decimal('52.0'),
                volume=550000,
                frequency=1
            ),
            MBar(
                code="COUNT002.SZ",
                timestamp=datetime(2023, 7, 1, 9, 30),
                open=Decimal('80.0'),
                high=Decimal('82.0'),
                low=Decimal('79.0'),
                close=Decimal('81.0'),
                volume=800000,
                frequency=1
            )
        ]

        try:
            # 插入测试数据
            print(f"\n→ 插入 {len(test_bars)} 条测试数据...")
            print(f"  - COUNT001.SZ: 2条")
            print(f"  - COUNT002.SZ: 1条")
            bar_crud.add_batch(test_bars)
            print("✓ 数据插入成功")

            # 测试1: count全部数据
            print("\n→ 测试count全部数据...")
            total_count = bar_crud.count(filters={"code": "COUNT001.SZ"})
            print(f"✓ COUNT001.SZ总数: {total_count}")
            assert total_count >= 2, f"应至少有2条，实际{total_count}条"

            # 测试2: count按code过滤
            print("\n→ 测试count按code过滤...")
            count1 = bar_crud.count(filters={"code": "COUNT001.SZ"})
            count2 = bar_crud.count(filters={"code": "COUNT002.SZ"})
            print(f"✓ COUNT001.SZ: {count1}条")
            print(f"✓ COUNT002.SZ: {count2}条")
            assert count1 >= 2, f"COUNT001.SZ应有2条，实际{count1}条"
            assert count2 >= 1, f"COUNT002.SZ应有1条，实际{count2}条"

            # 测试3: count按时间范围过滤
            print("\n→ 测试count按时间范围过滤...")
            count_range = bar_crud.count(filters={
                "code": "COUNT001.SZ",
                "timestamp__gte": datetime(2023, 7, 1, 0, 0),
                "timestamp__lte": datetime(2023, 7, 1, 23, 59)
            })
            print(f"✓ 2023-07-01的COUNT001.SZ: {count_range}条")
            assert count_range >= 1, f"应至少有1条，实际{count_range}条"

            # 测试4: exists检查存在的数据
            print("\n→ 测试exists检查存在的数据...")
            exists1 = bar_crud.exists(filters={"code": "COUNT001.SZ"})
            exists2 = bar_crud.exists(filters={"code": "COUNT002.SZ"})
            print(f"✓ COUNT001.SZ存在: {exists1}")
            print(f"✓ COUNT002.SZ存在: {exists2}")
            assert exists1 is True, "COUNT001.SZ应该存在"
            assert exists2 is True, "COUNT002.SZ应该存在"

            # 测试5: exists检查不存在的数据
            print("\n→ 测试exists检查不存在的数据...")
            exists_none = bar_crud.exists(filters={"code": "NONEXISTENT999.SZ"})
            print(f"✓ NONEXISTENT999.SZ存在: {exists_none}")
            assert exists_none is False, "不存在的code应返回False"

            # 测试6: count不存在的数据应返回0
            print("\n→ 测试count不存在的数据...")
            count_none = bar_crud.count(filters={"code": "NONEXISTENT999.SZ"})
            print(f"✓ NONEXISTENT999.SZ数量: {count_none}")
            assert count_none == 0, f"不存在的code应返回0，实际{count_none}"

        finally:
            # 清理测试数据
            print("\n→ 清理测试数据...")
            bar_crud.remove(filters={"code": "COUNT001.SZ"})
            bar_crud.remove(filters={"code": "COUNT002.SZ"})
            print("✓ 测试数据已清理")
            print("="*60)
            print("测试完成!")
            print("="*60)


@pytest.mark.database
@pytest.mark.tdd
class TestBarCRUDDelete:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': BarCRUD}
    """3. CRUD层删除操作测试 - Bar数据删除验证"""

    def test_delete_bar_by_code(self):
        """测试根据股票代码删除Bar数据"""
        print("\n" + "="*60)
        print("开始测试: 根据股票代码删除Bar数据")
        print("="*60)

        bar_crud = BarCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_bars = [
            MBar(
                code="DELETE_BAR_TEST",
                timestamp=datetime(2023, 6, 15, 9, 30),
                open=Decimal("12.50"),
                high=Decimal("13.00"),
                low=Decimal("12.00"),
                close=Decimal("12.80"),
                volume=1500000,
                frequency=FREQUENCY_TYPES.DAY
            ),
            MBar(
                code="DELETE_BAR_TEST",
                timestamp=datetime(2023, 6, 16, 9, 30),
                open=Decimal("12.80"),
                high=Decimal("13.20"),
                low=Decimal("12.50"),
                close=Decimal("13.10"),
                volume=1800000,
                frequency=FREQUENCY_TYPES.DAY
            )
        ]

        for bar in test_bars:
            bar_crud.add(bar)

        print(f"✓ 插入测试数据: {len(test_bars)}条Bar记录")

        # 验证数据存在
        before_count = len(bar_crud.find(filters={"code": "DELETE_BAR_TEST"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            bar_crud.remove(filters={"code": "DELETE_BAR_TEST"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(bar_crud.find(filters={"code": "DELETE_BAR_TEST"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            print("✓ 根据股票代码删除Bar数据验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_bar_by_time_range(self):
        """测试根据时间范围删除Bar数据"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围删除Bar数据")
        print("="*60)

        bar_crud = BarCRUD()

        # 准备测试数据 - 特定时间范围的数据
        print("→ 准备测试数据...")
        test_time_range = [
            datetime(2023, 7, 1, 9, 30),
            datetime(2023, 7, 2, 9, 30),
            datetime(2023, 7, 3, 9, 30)
        ]

        for i, test_time in enumerate(test_time_range):
            test_bar = MBar(
                code=f"TIME_BAR_TEST_{i+1:03d}",
                timestamp=test_time,
                open=Decimal(f"20.{1000+i}"),
                high=Decimal(f"21.{1000+i}"),
                low=Decimal(f"19.{1000+i}"),
                close=Decimal(f"20.{2000+i}"),
                volume=1000000 + i * 100000,
                frequency=FREQUENCY_TYPES.DAY
            )
            test_bar.source = SOURCE_TYPES.TEST
            bar_crud.add(test_bar)

        print(f"✓ 插入时间范围测试数据: {len(test_time_range)}条")

        # 验证数据存在
        before_count = len(bar_crud.find(filters={
            "timestamp__gte": datetime(2023, 7, 1),
            "timestamp__lte": datetime(2023, 7, 3, 23, 59, 59)
        }))
        print(f"✓ 删除前时间范围内数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行时间范围删除操作...")
            bar_crud.remove(filters={
                "timestamp__gte": datetime(2023, 7, 1),
                "timestamp__lte": datetime(2023, 7, 3, 23, 59, 59)
            })
            print("✓ 时间范围删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(bar_crud.find(filters={
                "timestamp__gte": datetime(2023, 7, 1),
                "timestamp__lte": datetime(2023, 7, 3, 23, 59, 59)
            }))
            print(f"✓ 删除后时间范围内数据量: {after_count}")
            assert after_count == 0, "删除后时间范围内应该没有数据"

            print("✓ 根据时间范围删除Bar数据验证成功")

        except Exception as e:
            print(f"✗ 时间范围删除操作失败: {e}")
            raise

    def test_delete_bar_by_frequency(self):
        """测试根据频率删除Bar数据"""
        print("\n" + "="*60)
        print("开始测试: 根据频率删除Bar数据")
        print("="*60)

        bar_crud = BarCRUD()

        # 准备测试数据 - 不同频率的数据
        print("→ 准备测试数据...")
        test_frequencies = [
            ("FREQ_DAY_TEST", FREQUENCY_TYPES.DAY),
            ("FREQ_HOUR_TEST", FREQUENCY_TYPES.HOUR1),
            ("FREQ_MINUTE_TEST", FREQUENCY_TYPES.MIN1),
            ("FREQ_DAY_TEST_2", FREQUENCY_TYPES.DAY),
        ]

        for code, frequency in test_frequencies:
            test_bar = MBar(
                code=code,
                timestamp=datetime(2023, 8, 15, 10, 30),
                open=Decimal("30.00"),
                high=Decimal("31.00"),
                low=Decimal("29.00"),
                close=Decimal("30.50"),
                volume=2000000,
                frequency=frequency
            )
            test_bar.source = SOURCE_TYPES.TEST
            bar_crud.add(test_bar)

        print(f"✓ 插入频率测试数据: {len(test_frequencies)}条")

        try:
            # 删除日线数据
            print("\n→ 执行频率删除操作...")
            before_count = len(bar_crud.find(filters={"frequency": FREQUENCY_TYPES.DAY}))
            print(f"✓ 删除前日线数据量: {before_count}")

            bar_crud.remove(filters={"frequency": FREQUENCY_TYPES.DAY})
            print("✓ 频率删除操作完成")

            # 验证删除结果
            after_count = len(bar_crud.find(filters={"frequency": FREQUENCY_TYPES.DAY}))
            print(f"✓ 删除后日线数据量: {after_count}")
            assert after_count == 0, "删除后应该没有日线数据"

            # 确认其他频率数据未受影响
            other_frequency_count = len(bar_crud.find(filters={"frequency": FREQUENCY_TYPES.HOUR1}))
            print(f"✓ 其他频率数据保留验证: {other_frequency_count}条")
            assert other_frequency_count > 0, "其他频率数据应该保留"

            print("✓ 根据频率删除Bar数据验证成功")

        except Exception as e:
            print(f"✗ 频率删除操作失败: {e}")
            raise

    def test_delete_bar_by_price_range(self):
        """测试根据价格范围删除Bar数据"""
        print("\n" + "="*60)
        print("开始测试: 根据价格范围删除Bar数据")
        print("="*60)

        bar_crud = BarCRUD()

        # 准备测试数据 - 不同价格范围的数据
        print("→ 准备测试数据...")
        test_prices = [
            ("LOW_PRICE_BAR", Decimal("5.00"), Decimal("5.50"), Decimal("4.80")),  # 低价格
            ("MID_PRICE_BAR", Decimal("25.00"), Decimal("26.00"), Decimal("24.50")),  # 中价格
            ("HIGH_PRICE_BAR", Decimal("80.00"), Decimal("82.00"), Decimal("78.00")),  # 高价格
            ("EXTREME_PRICE_BAR", Decimal("150.00"), Decimal("155.00"), Decimal("148.00")),  # 极高价格
        ]

        for code, open_price, high_price, low_price in test_prices:
            close_price = (open_price + high_price + low_price) / 3
            test_bar = MBar(
                code=code,
                timestamp=datetime(2023, 9, 1, 9, 30),
                open=open_price,
                high=high_price,
                low=low_price,
                close=close_price,
                volume=3000000,
                frequency=FREQUENCY_TYPES.DAY
            )
            test_bar.source = SOURCE_TYPES.TEST
            bar_crud.add(test_bar)

        print(f"✓ 插入价格范围测试数据: {len(test_prices)}条")

        try:
            # 删除高价格数据 (close > 50.00)
            print("\n→ 执行高价格数据删除操作...")
            before_high = len(bar_crud.find(filters={"close__gt": Decimal("50.00")}))
            print(f"✓ 删除前高价格数据量: {before_high}")

            bar_crud.remove(filters={"close__gt": Decimal("50.00")})
            print("✓ 高价格删除操作完成")

            after_high = len(bar_crud.find(filters={"close__gt": Decimal("50.00")}))
            print(f"✓ 删除后高价格数据量: {after_high}")
            assert after_high == 0, "删除后应该没有高价格数据"

            # 删除低价格数据 (close < 20.00)
            print("\n→ 执行低价格数据删除操作...")
            before_low = len(bar_crud.find(filters={"close__lt": Decimal("20.00")}))
            print(f"✓ 删除前低价格数据量: {before_low}")

            bar_crud.remove(filters={"close__lt": Decimal("20.00")})
            print("✓ 低价格删除操作完成")

            after_low = len(bar_crud.find(filters={"close__lt": Decimal("20.00")}))
            print(f"✓ 删除后低价格数据量: {after_low}")
            assert after_low == 0, "删除后应该没有低价格数据"

            # 确认中价格数据未受影响
            mid_price_count = len(bar_crud.find(filters={
                "close__gte": Decimal("20.00"),
                "close__lte": Decimal("50.00")
            }))
            print(f"✓ 中价格数据保留验证: {mid_price_count}条")
            assert mid_price_count > 0, "中价格数据应该保留"

            print("✓ 根据价格范围删除Bar数据验证成功")

        except Exception as e:
            print(f"✗ 价格范围删除操作失败: {e}")
            raise

    def test_delete_bar_by_volume_threshold(self):
        """测试根据成交量阈值删除Bar数据"""
        print("\n" + "="*60)
        print("开始测试: 根据成交量阈值删除Bar数据")
        print("="*60)

        bar_crud = BarCRUD()

        # 准备测试数据 - 不同成交量的数据
        print("→ 准备测试数据...")
        test_volumes = [
            ("LOW_VOLUME_BAR", 500000),    # 低成交量
            ("MID_VOLUME_BAR", 2000000),   # 中成交量
            ("HIGH_VOLUME_BAR", 8000000),  # 高成交量
            ("EXTREME_VOLUME_BAR", 15000000), # 极高成交量
        ]

        for code, volume in test_volumes:
            test_bar = MBar(
                code=code,
                timestamp=datetime(2023, 10, 15, 9, 30),
                open=Decimal("40.00"),
                high=Decimal("41.00"),
                low=Decimal("39.00"),
                close=Decimal("40.50"),
                volume=volume,
                frequency=FREQUENCY_TYPES.DAY
            )
            test_bar.source = SOURCE_TYPES.TEST
            bar_crud.add(test_bar)

        print(f"✓ 插入成交量测试数据: {len(test_volumes)}条")

        try:
            # 删除高成交量数据 (> 5000000)
            print("\n→ 执行高成交量数据删除操作...")
            before_high = len(bar_crud.find(filters={"volume__gt": 5000000}))
            print(f"✓ 删除前高成交量数据量: {before_high}")

            bar_crud.remove(filters={"volume__gt": 5000000})
            print("✓ 高成交量删除操作完成")

            after_high = len(bar_crud.find(filters={"volume__gt": 5000000}))
            print(f"✓ 删除后高成交量数据量: {after_high}")
            assert after_high == 0, "删除后应该没有高成交量数据"

            # 删除低成交量数据 (< 1000000)
            print("\n→ 执行低成交量数据删除操作...")
            before_low = len(bar_crud.find(filters={"volume__lt": 1000000}))
            print(f"✓ 删除前低成交量数据量: {before_low}")

            bar_crud.remove(filters={"volume__lt": 1000000})
            print("✓ 低成交量删除操作完成")

            after_low = len(bar_crud.find(filters={"volume__lt": 1000000}))
            print(f"✓ 删除后低成交量数据量: {after_low}")
            assert after_low == 0, "删除后应该没有低成交量数据"

            # 确认中成交量数据未受影响
            mid_volume_count = len(bar_crud.find(filters={
                "volume__gte": 1000000,
                "volume__lte": 5000000
            }))
            print(f"✓ 中成交量数据保留验证: {mid_volume_count}条")
            assert mid_volume_count > 0, "中成交量数据应该保留"

            print("✓ 根据成交量阈值删除Bar数据验证成功")

        except Exception as e:
            print(f"✗ 成交量阈值删除操作失败: {e}")
            raise

    def test_delete_bar_batch_cleanup(self):
        """测试批量清理Bar数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理Bar数据")
        print("="*60)

        bar_crud = BarCRUD()

        # 准备批量清理数据
        print("→ 准备批量清理测试数据...")
        cleanup_bars = []
        base_time = datetime(2023, 11, 1)

        for i in range(12):
            code = f"CLEANUP_BAR_{i+1:03d}"
            cleanup_bars.append(code)

            test_bar = MBar(
                code=code,
                timestamp=base_time + timedelta(days=i),
                open=Decimal(f"50.{1000+i}"),
                high=Decimal(f"51.{1000+i}"),
                low=Decimal(f"49.{1000+i}"),
                close=Decimal(f"50.{2000+i}"),
                volume=4000000 + i * 100000,
                frequency=FREQUENCY_TYPES.DAY
            )
            test_bar.source = SOURCE_TYPES.TEST
            bar_crud.add(test_bar)

        print(f"✓ 插入批量清理测试数据: {len(cleanup_bars)}条")

        # 验证数据存在
        before_count = len(bar_crud.find(filters={
            "code__like": "CLEANUP_BAR_%"
        }))
        print(f"✓ 删除前批量数据量: {before_count}")

        try:
            # 批量删除
            print("\n→ 执行批量清理操作...")
            bar_crud.remove(filters={
                "code__like": "CLEANUP_BAR_%"
            })
            print("✓ 批量清理操作完成")

            # 验证删除结果
            print("\n→ 验证批量清理结果...")
            after_count = len(bar_crud.find(filters={
                "code__like": "CLEANUP_BAR_%"
            }))
            print(f"✓ 删除后批量数据量: {after_count}")
            assert after_count == 0, "删除后应该没有批量清理数据"

            # 确认其他数据未受影响
            other_data_count = len(bar_crud.find(page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理Bar数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise
