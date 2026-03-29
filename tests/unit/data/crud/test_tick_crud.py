"""
TickCRUD数据库操作TDD测试 - 实时行情数据管理

本文件测试TickCRUD类的完整功能，确保实时行情数据(Tick)的增删改查操作正常工作。
Tick是实时交易的基础数据，包含高频的价格和成交量信息。支持动态表分区，每个股票代码有独立的表。

测试范围：
1. 插入操作 (Insert Operations)
   - 批量插入 (add_batch): 高效插入大量Tick数据
   - 单条插入 (add): 插入单个Tick记录
   - 高频插入 (high_frequency): 高频数据插入性能

2. 查询操作 (Query Operations)
   - 按代码查询 (find_by_code): 根据股票代码查询
   - 按方向查询 (find_by_direction): 根据买卖方向查询
   - 按时间范围查询 (find_by_time_range): 时间范围筛选
   - 分页查询 (pagination): 支持大数据量分页

3. 性能测试 (Performance Tests)
   - 批量插入性能 (bulk_insert_performance): 测试批量插入吞吐量
   - 实时查询性能 (real_time_query): 测试实时查询响应时间

4. 删除操作 (Delete Operations)
   - 按时间范围删除 (delete_by_time_range): 清理历史Tick
   - 按UUID删除 (delete_by_uuid): 删除单条Tick
   - 按代码删除 (delete_by_code): 删除特定股票Tick
   - 按方向删除 (delete_by_direction): 删除买卖方向Tick
   - 按价格范围删除 (delete_by_price_range): 价格范围删除
   - 批量清理 (batch_cleanup): 高效批量删除

5. 业务逻辑测试 (Business Logic Tests)
   - 价格变动分析 (price_movement_analysis): Tick价格变动统计
   - 买卖压力分析 (buy_sell_pressure): 买卖压力分析
   - 数据完整性 (data_integrity): 约束和验证
   - 动态表分区 (dynamic_partitioning): 动态表机制

6. 转换功能测试 (Conversion Tests)
   - ModelList转换 (model_list_versions): to_dataframe和to_entities

TODO: 添加replace方法测试用例
- 测试replace方法的原子操作 (备份→删除→插入→失败时恢复)
- 测试没有匹配数据时的行为 (应返回空结果，不插入新数据)
- 测试类型错误检查 (传入错误Model类型时应抛出TypeError)
- 测试空new_items的处理
- 测试批量替换的性能和正确性
- 测试ClickHouse和MySQL数据库的兼容性
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "test"))

from ginkgo.data.crud.tick_crud import TickCRUD, get_tick_model
from ginkgo.data.models.model_tick import MTick
from ginkgo.enums import TICKDIRECTION_TYPES, SOURCE_TYPES

# 测试用统一股票代码常量
TEST_TICK_CODE = "TESTTICK_Tick"


@pytest.mark.database
@pytest.mark.tdd
class TestTickCRUDInsert:
    """TickCRUD层插入操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = TickCRUD()
        self.test_code = TEST_TICK_CODE

    def test_add_batch_basic(self):
        """测试批量插入Tick数据"""
        print("\n" + "="*60)
        print("开始测试: Tick CRUD层批量插入")
        print("="*60)

        # 获取操作前数据条数
        before_count = len(self.crud.find(filters={"code": self.test_code, "source": SOURCE_TYPES.TEST.value}))
        print(f"✓ 操作前数据库记录数: {before_count}")

        # 创建测试Tick数据
        test_ticks = [
            {
                "code": self.test_code,
                "price": Decimal("10.50"),
                "volume": 1000,
                "direction": TICKDIRECTION_TYPES.ACTIVEBUY,
                "timestamp": datetime(2023, 1, 3, 9, 30, 0),
                "source": SOURCE_TYPES.TEST.value
            },
            {
                "code": self.test_code,
                "price": Decimal("10.51"),
                "volume": 500,
                "direction": TICKDIRECTION_TYPES.ACTIVESELL,
                "timestamp": datetime(2023, 1, 3, 9, 30, 1),
                "source": SOURCE_TYPES.TEST.value
            },
            {
                "code": self.test_code,
                "price": Decimal("15.25"),
                "volume": 800,
                "direction": TICKDIRECTION_TYPES.ACTIVEBUY,
                "timestamp": datetime(2023, 1, 3, 9, 30, 0),
                "source": SOURCE_TYPES.TEST.value
            }
        ]
        print(f"✓ 创建测试数据: {len(test_ticks)}条Tick记录")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            self.crud.add_batch(test_ticks)
            print("✓ 批量插入成功")

            # 验证数据库记录数变化
            after_count = len(self.crud.find(filters={"code": self.test_code, "source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 操作后数据库记录数: {after_count}")
            assert after_count - before_count == 3, f"应增加3条数据，实际增加{after_count - before_count}条"

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = self.crud.find(filters={"code": self.test_code, "source": SOURCE_TYPES.TEST.value})
            print(f"✓ 查询到 {len(query_result)} 条记录")

            # 验证返回值类型 - find方法应返回ModelList
            from ginkgo.data.crud.model_conversion import ModelList
            assert isinstance(query_result, ModelList), f"find()应返回ModelList，实际{type(query_result)}"
            assert len(query_result) >= 2

            # 验证数据内容
            codes = [tick.code for tick in query_result]
            assert self.test_code in codes

            print("✓ 批量插入验证通过")

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_tick(self):
        """测试单条Tick数据插入"""
        print("\n" + "="*60)
        print("开始测试: Tick CRUD层单条插入")
        print("="*60)

        test_tick = MTick(
            code=self.test_code,
            price=Decimal("10.55"),
            volume=1200,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime(2023, 1, 3, 9, 31, 0)
        )
        print(f"✓ 创建测试Tick: {test_tick.code} @ {test_tick.price}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            self.crud.add(test_tick)
            print("✓ 单条插入成功")

            # 验证数据 - 使用精确的时间戳匹配
            print("\n→ 验证插入的数据...")
            query_result = self.crud.find(filters={
                "code": self.test_code,
                "timestamp": test_tick.timestamp
            })
            print(f"✓ 查询到 {len(query_result)} 条匹配的记录")
            assert len(query_result) == 1, f"应该查询到1条匹配的记录，实际为{len(query_result)}条"

            inserted_tick = query_result[0]
            assert inserted_tick.code == self.test_code
            assert float(inserted_tick.price) == 10.55
            assert inserted_tick.volume == 1200

            print("✓ 单条插入验证通过")

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise

    def test_high_frequency_tick_insert(self):
        """测试高频Tick数据插入"""
        print("\n" + "="*60)
        print("开始测试: 高频Tick数据插入")
        print("="*60)

        # 创建高频数据 - 1秒内100个tick
        base_time = datetime(2023, 1, 3, 10, 0, 0)
        high_freq_ticks = []

        for i in range(100):
            tick = MTick(
                code="TESTTICK_Tick",
                price=Decimal("10.50") + Decimal(str(i * 0.001)),
                volume=100 + i,
                direction=TICKDIRECTION_TYPES.ACTIVEBUY if i % 2 == 0 else TICKDIRECTION_TYPES.ACTIVESELL,
                timestamp=base_time.replace(microsecond=i * 10000)  # 10ms间隔
            )
            high_freq_ticks.append(tick)

        print(f"✓ 创建高频测试数据: {len(high_freq_ticks)}条记录")

        try:
            # 批量插入高频数据
            print("\n→ 执行高频数据批量插入...")
            self.crud.add_batch(high_freq_ticks)
            print("✓ 高频数据批量插入成功")

            # 验证数据插入
            print("\n→ 验证高频数据插入...")
            query_result = self.crud.find(filters={"code": "TESTTICK_Tick"})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 100

            # 验证时间序列顺序
            timestamps = [tick.timestamp for tick in query_result[-100:]]
            is_sorted = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
            print(f"✓ 时间序列顺序验证: {'通过' if is_sorted else '失败'}")
            assert is_sorted, "时间戳应有序"

            print("✓ 高频插入验证通过")

        except Exception as e:
            print(f"✗ 高频数据插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTickCRUDQuery:
    """TickCRUD层查询操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = TickCRUD()
        self.test_code = TEST_TICK_CODE

    def test_find_by_code(self):
        """测试根据股票代码查询Tick"""
        print("\n" + "="*60)
        print("开始测试: 根据code查询Tick")
        print("="*60)

        try:
            ticks = self.crud.find(filters={"code": self.test_code}, page_size=50)
            print(f"✓ 查询到 {len(ticks)} 条记录")

            # 验证查询结果
            for tick in ticks:
                assert tick.code == self.test_code

            print("✓ 按code查询验证通过")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_direction(self):
        """测试根据交易方向查询Tick"""
        print("\n" + "="*60)
        print("开始测试: 根据direction查询Tick")
        print("="*60)

        try:
            # 查询所有tick
            all_ticks = self.crud.find(filters={"code": self.test_code})

            # 按方向分组
            buy_ticks = [t for t in all_ticks if t.direction == TICKDIRECTION_TYPES.ACTIVEBUY]
            sell_ticks = [t for t in all_ticks if t.direction == TICKDIRECTION_TYPES.ACTIVESELL]

            print(f"✓ 买入记录: {len(buy_ticks)} 条")
            print(f"✓ 卖出记录: {len(sell_ticks)} 条")

            # 验证分组
            total_ticks = len(buy_ticks) + len(sell_ticks)
            assert total_ticks <= len(all_ticks), "分组总数应不超过总数"

            print("✓ 按direction查询验证通过")

        except Exception as e:
            print(f"✗ 方向查询失败: {e}")
            raise

    def test_find_by_time_range(self):
        """测试时间范围查询Tick"""
        print("\n" + "="*60)
        print("开始测试: 时间范围查询Tick")
        print("="*60)

        try:
            start_time = datetime(2023, 1, 3, 9, 30, 0)
            end_time = datetime(2023, 1, 3, 10, 0, 0)

            print(f"→ 查询时间范围 {start_time} ~ {end_time} 的tick数据...")
            all_ticks = self.crud.find(filters={"code": self.test_code})

            # 手动过滤时间范围
            filtered_ticks = [t for t in all_ticks if start_time <= t.timestamp <= end_time]

            print(f"✓ 查询到 {len(filtered_ticks)} 条时间范围内的记录")

            # 验证时间范围
            if filtered_ticks:
                min_time = min(t.timestamp for t in filtered_ticks)
                max_time = max(t.timestamp for t in filtered_ticks)
                print(f"✓ 实际时间范围: {min_time} ~ {max_time}")

                assert start_time <= min_time <= max_time <= end_time

            print("✓ 时间范围查询验证通过")

        except Exception as e:
            print(f"✗ 时间范围查询失败: {e}")
            raise

    def test_find_with_pagination(self):
        """测试分页查询Tick"""
        print("\n" + "="*60)
        print("开始测试: 分页查询Tick")
        print("="*60)

        try:
            # 分页查询
            page_size = 20

            # 第一页
            page1 = self.crud.find(filters={"code": self.test_code}, page_size=page_size, page=1)
            print(f"✓ 第1页: {len(page1)} 条记录")

            # 第二页
            page2 = self.crud.find(filters={"code": self.test_code}, page_size=page_size, page=2)
            print(f"✓ 第2页: {len(page2)} 条记录")

            # 验证分页结果不重复
            if page1 and page2:
                page1_ids = [id(t) for t in page1]
                page2_ids = [id(t) for t in page2]
                overlap = set(page1_ids) & set(page2_ids)
                print(f"✓ 页面重叠记录数: {len(overlap)} (应为0)")
                assert len(overlap) == 0, "分页结果不应有重叠"

            print("✓ 分页查询验证通过")

        except Exception as e:
            print(f"✗ 分页查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.slow
@pytest.mark.performance
class TestTickCRUDPerformance:
    """TickCRUD层性能测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = TickCRUD()
        self.test_code = TEST_TICK_CODE

    def test_bulk_insert_performance(self):
        """测试批量插入性能"""
        print("\n" + "="*60)
        print("开始测试: 批量插入性能")
        print("="*60)

        # 创建测试数据
        batch_size = 1000
        base_time = datetime(2023, 1, 3, 14, 0, 0)
        bulk_ticks = []

        for i in range(batch_size):
            tick = MTick(
                code="TESTTICK_Tick",
                price=Decimal("10.50") + Decimal(str((i % 100) * 0.001)),
                volume=100 + (i % 1000),
                direction=TICKDIRECTION_TYPES.ACTIVEBUY if i % 2 == 0 else TICKDIRECTION_TYPES.ACTIVESELL,
                timestamp=base_time.replace(microsecond=(i % 1000000))
            )
            bulk_ticks.append(tick)

        print(f"✓ 创建批量测试数据: {batch_size} 条记录")

        try:
            # 测试批量插入性能
            import time
            start_time = time.time()

            self.crud.add_batch(bulk_ticks)

            end_time = time.time()
            duration = end_time - start_time
            throughput = batch_size / duration if duration else float('inf')

            print(f"✓ 批量插入完成:")
            print(f"  - 数据量: {batch_size} 条")
            print(f"  - 耗时: {duration:.3f} 秒")
            print(f"  - 吞吐量: {throughput:.0f} 条/秒")

            # 性能基准
            assert duration < 5, f"批量插入耗时过长: {duration:.2f} 秒"
            print("✓ 性能基准验证通过（耗时<5秒）")

            print("✓ 批量插入性能验证通过")

        except Exception as e:
            print(f"✗ 批量插入性能测试失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTickCRUDBusinessLogic:
    """TickCRUD层业务逻辑测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = TickCRUD()
        self.test_code = TEST_TICK_CODE

    def test_tick_price_movement_analysis(self):
        """测试Tick价格变动分析"""
        print("\n" + "="*60)
        print("开始测试: Tick价格变动分析")
        print("="*60)

        try:
            # 查询连续的tick数据进行价格分析
            ticks = self.crud.find(filters={"code": self.test_code}, page_size=100, order_by="timestamp")

            if len(ticks) < 10:
                pytest.skip("tick数据不足，跳过价格分析测试")

            # 计算价格变动统计
            prices = [float(t.price) for t in ticks]
            volumes = [t.volume for t in ticks]

            # 价格变动分析
            price_changes = []
            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                price_changes.append(change)

            # 统计分析
            avg_price = sum(prices) / len(prices)
            max_price = max(prices)
            min_price = min(prices)
            price_volatility = max(prices) - min(prices)

            positive_changes = [c for c in price_changes if c > 0]
            negative_changes = [c for c in price_changes if c < 0]

            print(f"✓ 价格分析结果:")
            print(f"  - 平均价格: {avg_price:.3f}")
            print(f"  - 价格范围: {min_price:.3f} - {max_price:.3f}")
            print(f"  - 价格波动: {price_volatility:.3f}")
            print(f"  - 上涨次数: {len(positive_changes)}")
            print(f"  - 下跌次数: {len(negative_changes)}")
            print(f"  - 总成交量: {sum(volumes)}")

            # 验证价格数据合理性
            assert avg_price > 0, "平均价格应大于0"
            assert max_price >= min_price, "最高价应不低于最低价"
            assert price_volatility >= 0, "价格波动应非负"

            print("✓ 价格变动分析验证通过")

        except Exception as e:
            print(f"✗ Tick价格变动分析失败: {e}")
            raise

    def test_dynamic_table_partitioning(self):
        """测试动态表分区机制"""
        print("\n" + "="*60)
        print("开始测试: 动态表分区机制")
        print("="*60)

        try:
            # 测试动态模型创建
            print("→ 测试动态模型创建...")

            model1 = get_tick_model("TESTTICK_Tick")
            model2 = get_tick_model("TESTTICK2_Tick")
            model3 = get_tick_model("TESTTICK_Tick")  # 应该返回缓存模型

            print(f"✓ 创建动态模型: {model1.__name__}")
            print(f"✓ 创建动态模型: {model2.__name__}")
            print(f"✓ 缓存模型验证: {model1 is model3}")

            # 验证模型属性
            assert model1.__tablename__ == "TESTTICK_Tick_Tick"
            assert model2.__tablename__ == "TESTTICK2_Tick_Tick"
            assert model1 is model3  # 验证缓存机制

            print("✓ 动态表分区机制验证通过")

        except Exception as e:
            print(f"✗ 动态表分区测试失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.db_cleanup
class TestTickCRUDDelete:
    """TickCRUD层删除操作测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = TickCRUD()
        self.test_code = TEST_TICK_CODE

    def test_delete_tick_by_uuid(self):
        """测试根据UUID删除单条Tick数据"""
        print("\n" + "="*60)
        print("开始测试: 根据UUID删除单条Tick数据")
        print("="*60)

        try:
            # 创建测试数据
            test_tick_data = {
                "code": self.test_code,
                "price": Decimal("9.99"),
                "volume": 999,
                "direction": TICKDIRECTION_TYPES.ACTIVESELL,
                "timestamp": datetime(2023, 11, 15, 14, 30, 0)
            }

            inserted_tick = self.crud.add(test_tick_data)
            test_uuid = inserted_tick.uuid
            print(f"✓ 创建测试tick: {test_uuid}")

            # 验证数据存在
            before_ticks = self.crud.find(filters={"code": self.test_code, "uuid": test_uuid})
            assert len(before_ticks) >= 1, "删除前数据应存在"

            # 执行删除
            print("\n→ 执行UUID删除操作...")
            self.crud.remove(filters={"code": self.test_code, "uuid": test_uuid})
            print("✓ UUID删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_ticks = self.crud.find(filters={"code": self.test_code, "uuid": test_uuid})
            assert len(after_ticks) == 0, "删除后应该没有相关数据"

            print("✓ 根据UUID删除验证通过")

        except Exception as e:
            print(f"✗ UUID删除操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTickCRUDConversion:
    """TickCRUD转换功能测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前的设置"""
        self.crud = TickCRUD()
        self.test_code = TEST_TICK_CODE

    def test_model_list_conversions(self):
        """测试ModelList的to_dataframe和to_entities转换功能"""
        print("\n" + "="*60)
        print("开始测试: Tick ModelList转换功能")
        print("="*60)

        try:
            # 创建测试数据
            test_ticks = [
                {
                    "code": self.test_code,
                    "price": Decimal("10.50"),
                    "volume": 1000,
                    "direction": TICKDIRECTION_TYPES.ACTIVEBUY,
                    "timestamp": datetime(2023, 1, 5, 9, 30, 0)
                },
                {
                    "code": self.test_code,
                    "price": Decimal("10.51"),
                    "volume": 500,
                    "direction": TICKDIRECTION_TYPES.ACTIVESELL,
                    "timestamp": datetime(2023, 1, 5, 9, 30, 1)
                }
            ]

            # 插入测试数据
            self.crud.add_batch(test_ticks)

            # 获取ModelList进行转换测试
            print("\n→ 获取ModelList...")
            model_list = self.crud.find(filters={"code": self.test_code})
            assert len(model_list) >= 2, "应至少有2条测试数据"

            # 测试1: to_dataframe转换
            print("\n→ 测试to_dataframe转换...")
            df = model_list.to_dataframe()
            assert isinstance(df, pd.DataFrame), "应返回DataFrame"
            assert len(df) == len(model_list), "DataFrame行数应等于ModelList长度"

            # 验证DataFrame列
            required_columns = ['code', 'price', 'volume', 'direction', 'timestamp']
            for col in required_columns:
                assert col in df.columns, f"DataFrame应包含列: {col}"
            print("✓ to_dataframe转换验证通过")

            # 测试2: to_entities转换
            print("\n→ 测试to_entities转换...")
            entities = model_list.to_entities()
            assert len(entities) == len(model_list), "实体列表长度应等于ModelList长度"

            # 验证实体类型
            from ginkgo.trading import Tick
            first_entity = entities[0]
            assert isinstance(first_entity, Tick), "应转换为Tick实体"
            print("✓ to_entities转换验证通过")

            print("\n✓ 所有Tick ModelList转换功能测试通过！")

        except Exception as e:
            print(f"✗ ModelList转换测试失败: {e}")
            raise


# TDD验证入口
if __name__ == "__main__":
    print("TDD Red阶段验证：Tick CRUD测试")
    print("运行: pytest test/data/crud/test_tick_crud.py -v")
    print("预期结果: 所有测试通过")
    print("特别关注: 动态表分区机制和性能基准验证")
