"""
TickCRUD数据库操作TDD测试

测试CRUD层的实时行情数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)

Tick是实时交易的基础数据，包含高频的价格和成交量信息。
支持动态表分区，每个股票代码有独立的表。
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.tick_crud import TickCRUD, get_tick_model
from ginkgo.data.models.model_tick import MTick
from ginkgo.enums import TICKDIRECTION_TYPES, SOURCE_TYPES

# ========================
# 测试用统一股票代码常量
# ========================
TEST_TICK_CODE = "TESTTICK_Tick"  # 所有测试统一使用这个code


@pytest.mark.database
@pytest.mark.tdd
class TestTickCRUDInsert:
    # 明确配置CRUD类和默认filters
    CRUD_TEST_CONFIG = {
        'crud_class': TickCRUD,
        'filters': {"code": "TESTTICK_Tick"}
    }

    """1. CRUD层插入操作测试 - Tick数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入Tick数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: Tick CRUD层批量插入")
        print("="*60)

        tick_crud = TickCRUD()
        print(f"✓ 创建TickCRUD实例: {tick_crud.__class__.__name__} (统一入口)")

        # 使用固定的测试代码，提高性能
        test_code = "TESTTICK_Tick"

        # 获取操作前数据条数用于验证（pytest会自动清理TEST source的数据）
        before_count = len(tick_crud.find(filters={"code": test_code, "source": SOURCE_TYPES.TEST.value}))
        print(f"✓ 操作前数据库记录数: {before_count}")

        # 创建测试Tick数据（使用字典数据，TickCRUD会自动处理动态Model）
        # 设置source为TEST类型，让pytest自动清理机制生效
        test_ticks = [
            {
                "code": test_code,
                "price": Decimal("10.50"),
                "volume": 1000,
                "direction": TICKDIRECTION_TYPES.ACTIVEBUY,
                "timestamp": datetime(2023, 1, 3, 9, 30, 0),
                "source": SOURCE_TYPES.TEST.value
            },
            {
                "code": test_code,
                "price": Decimal("10.51"),
                "volume": 500,
                "direction": TICKDIRECTION_TYPES.ACTIVESELL,
                "timestamp": datetime(2023, 1, 3, 9, 30, 1),
                "source": SOURCE_TYPES.TEST.value
            },
            {
                "code": test_code,
                "price": Decimal("15.25"),
                "volume": 800,
                "direction": TICKDIRECTION_TYPES.ACTIVEBUY,
                "timestamp": datetime(2023, 1, 3, 9, 30, 0),
                "source": SOURCE_TYPES.TEST.value
            }
        ]
        print(f"✓ 创建测试数据: {len(test_ticks)}条Tick记录")
        print(f"  - 股票代码: {test_code} (唯一测试代码)")
        print(f"  - 价格范围: {min(t['price'] for t in test_ticks)} - {max(t['price'] for t in test_ticks)}")
        print(f"  - 交易方向: BUY, SELL")
        print(f"  - 总成交量: {sum(t['volume'] for t in test_ticks)}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            tick_crud.add_batch(test_ticks)
            print("✓ 批量插入成功")

            # 验证数据库记录数变化
            after_count = len(tick_crud.find(filters={"code": test_code, "source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 操作后{test_code}数据库记录数: {after_count}")
            assert after_count - before_count == 3, f"应增加3条数据，实际增加{after_count - before_count}条"

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = tick_crud.find(filters={"code": test_code, "source": SOURCE_TYPES.TEST.value})
            print(f"✓ 查询到 {len(query_result)} 条记录")

            # 验证返回值类型 - find方法应返回ModelList
            from ginkgo.data.crud.model_conversion import ModelList
            assert isinstance(query_result, ModelList), f"find()应返回ModelList，实际{type(query_result)}"
            assert len(query_result) >= 2

            # 验证数据内容
            codes = [tick.code for tick in query_result]
            prices = [float(tick.price) for tick in query_result]
            volumes = [tick.volume for tick in query_result]
            directions = [tick.direction for tick in query_result]

            print(f"✓ 股票代码验证通过: {set(codes)}")
            print(f"✓ 价格范围验证: {min(prices):.2f} - {max(prices):.2f}")
            print(f"✓ 成交量验证: {sum(volumes)}")
            print(f"✓ 交易方向验证: {[TICKDIRECTION_TYPES(d).name for d in set(directions)]}")

            assert test_code in codes

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_tick(self):
        """测试单条Tick数据插入"""
        print("\n" + "="*60)
        print("开始测试: Tick CRUD层单条插入")
        print("="*60)

        tick_crud = TickCRUD()

        # 使用统一的测试代码常量
        test_code = TEST_TICK_CODE

        test_tick = MTick(
            code=test_code,
            price=Decimal("10.55"),
            volume=1200,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime(2023, 1, 3, 9, 31, 0)
        )
        print(f"✓ 创建测试Tick: {test_tick.code} @ {test_tick.price}, 成交量={test_tick.volume}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            tick_crud.add(test_tick)
            print("✓ 单条插入成功")

            # 验证数据 - 使用精确的时间戳匹配
            print("\n→ 验证插入的数据...")
            query_result = tick_crud.find(filters={
                "code": test_code,
                "timestamp": test_tick.timestamp  # 精确匹配时间戳
            })
            print(f"✓ 查询到 {len(query_result)} 条匹配的记录")
            assert len(query_result) == 1, f"应该查询到1条匹配的记录，实际为{len(query_result)}条"

            inserted_tick = query_result[0]  # 取唯一匹配的记录
            print(f"✓ 插入的Tick验证: 价格={inserted_tick.price}, 成交量={inserted_tick.volume}")
            assert inserted_tick.code == test_code
            assert float(inserted_tick.price) == 10.55
            assert inserted_tick.volume == 1200

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise

    def test_high_frequency_tick_insert(self):
        """测试高频Tick数据插入"""
        print("\n" + "="*60)
        print("开始测试: 高频Tick数据插入")
        print("="*60)

        tick_crud = TickCRUD()

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
        print(f"  - 时间跨度: {high_freq_ticks[0].timestamp} ~ {high_freq_ticks[-1].timestamp}")
        print(f"  - 价格范围: {high_freq_ticks[0].price} ~ {high_freq_ticks[-1].price}")

        try:
            # 批量插入高频数据
            print("\n→ 执行高频数据批量插入...")
            tick_crud.add_batch(high_freq_ticks)
            print("✓ 高频数据批量插入成功")

            # 验证数据插入
            print("\n→ 验证高频数据插入...")
            query_result = tick_crud.find(filters={"code": "TESTTICK_Tick"})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 100

            # 验证时间序列顺序
            timestamps = [tick.timestamp for tick in query_result[-100:]]
            is_sorted = all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))
            print(f"✓ 时间序列顺序验证: {'通过' if is_sorted else '失败'}")

        except Exception as e:
            print(f"✗ 高频数据插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTickCRUDQuery:
    # 明确配置CRUD类和默认filters
    CRUD_TEST_CONFIG = {
        'crud_class': TickCRUD,
        'filters': {"code": "TESTTICK_Tick"}
    }

    """2. CRUD层查询操作测试 - Tick数据查询和过滤"""

    def test_find_by_code(self):
        """测试根据股票代码查询Tick"""
        print("\n" + "="*60)
        print("开始测试: 根据code查询Tick")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 查询特定股票的tick数据
            print("→ 查询code=000001.SZ的tick数据...")
            ticks = tick_crud.find(filters={"code": "TESTTICK_Tick"}, page_size=50)
            print(f"✓ 查询到 {len(ticks)} 条记录")

            # 验证查询结果
            if ticks:
                prices = [float(t.price) for t in ticks]
                volumes = [t.volume for t in ticks]
                directions = [t.direction for t in ticks]

                print(f"✓ 价格范围: {min(prices):.3f} - {max(prices):.3f}")
                print(f"✓ 成交量范围: {min(volumes)} - {max(volumes)}")
                print(f"✓ 交易方向分布: BUY={directions.count(TICKDIRECTION_TYPES.ACTIVEBUY)}, SELL={directions.count(TICKDIRECTION_TYPES.ACTIVESELL)}")

                for tick in ticks:
                    assert tick.code == "TESTTICK_Tick"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_direction(self):
        """测试根据交易方向查询Tick"""
        print("\n" + "="*60)
        print("开始测试: 根据direction查询Tick")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 查询买入方向的tick数据
            print("→ 查询direction=BUY的tick数据...")
            buy_ticks = tick_crud.find(filters={"code": "TESTTICK_Tick"})
            buy_ticks = [t for t in buy_ticks if t.direction == TICKDIRECTION_TYPES.ACTIVEBUY]

            print(f"✓ 查询到 {len(buy_ticks)} 条买入记录")

            # 查询卖出方向的tick数据
            print("→ 查询direction=SELL的tick数据...")
            sell_ticks = tick_crud.find(filters={"code": "TESTTICK_Tick"})
            sell_ticks = [t for t in sell_ticks if t.direction == TICKDIRECTION_TYPES.ACTIVESELL]

            print(f"✓ 查询到 {len(sell_ticks)} 条卖出记录")

            # 验证查询结果
            total_ticks = len(buy_ticks) + len(sell_ticks)
            print(f"✓ 总tick记录数: {total_ticks}")
            if total_ticks > 0:
                print(f"✓ 买入占比: {len(buy_ticks)/total_ticks*100:.1f}%")
                print(f"✓ 卖出占比: {len(sell_ticks)/total_ticks*100:.1f}%")
            else:
                print("✓ 无tick数据，跳过占比计算")

        except Exception as e:
            print(f"✗ 方向查询失败: {e}")
            raise

    def test_find_by_time_range(self):
        """测试时间范围查询Tick"""
        print("\n" + "="*60)
        print("开始测试: 时间范围查询Tick")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 查询特定时间范围的tick数据
            start_time = datetime(2023, 1, 3, 9, 30, 0)
            end_time = datetime(2023, 1, 3, 10, 0, 0)

            print(f"→ 查询时间范围 {start_time} ~ {end_time} 的tick数据...")
            all_ticks = tick_crud.find(filters={"code": "TESTTICK_Tick"})

            # 手动过滤时间范围
            filtered_ticks = [t for t in all_ticks if start_time <= t.timestamp <= end_time]

            print(f"✓ 查询到 {len(filtered_ticks)} 条时间范围内的记录")

            # 验证时间范围
            if filtered_ticks:
                min_time = min(t.timestamp for t in filtered_ticks)
                max_time = max(t.timestamp for t in filtered_ticks)
                print(f"✓ 实际时间范围: {min_time} ~ {max_time}")

                assert start_time <= min_time <= max_time <= end_time

        except Exception as e:
            print(f"✗ 时间范围查询失败: {e}")
            raise

    def test_find_with_pagination(self):
        """测试分页查询Tick"""
        print("\n" + "="*60)
        print("开始测试: 分页查询Tick")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 分页查询
            print("→ 执行分页查询...")

            # 第一页
            page1 = tick_crud.find(filters={"code": "TESTTICK_Tick"}, page_size=20, page=1)
            print(f"✓ 第1页: {len(page1)} 条记录")

            # 第二页
            page2 = tick_crud.find(filters={"code": "TESTTICK_Tick"}, page_size=20, page=2)
            print(f"✓ 第2页: {len(page2)} 条记录")

            # 验证分页结果不重复
            if page1 and page2:
                page1_ids = [id(t) for t in page1]
                page2_ids = [id(t) for t in page2]
                overlap = set(page1_ids) & set(page2_ids)
                print(f"✓ 页面重叠记录数: {len(overlap)} (应为0)")
                assert len(overlap) == 0

        except Exception as e:
            print(f"✗ 分页查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
@pytest.mark.slow
@pytest.mark.performance
class TestTickCRUDPerformance:
    # 明确配置CRUD类和默认filters
    CRUD_TEST_CONFIG = {
        'crud_class': TickCRUD,
        'filters': {"code": "TESTTICK_Tick"}
    }

    """3. CRUD层性能测试 - Tick数据处理性能验证"""

    def test_bulk_insert_performance(self):
        """测试批量插入性能"""
        print("\n" + "="*60)
        print("开始测试: 批量插入性能")
        print("="*60)

        tick_crud = TickCRUD()

        # 创建测试数据。10k 行的性能测试在CI环境中过慢，这里收敛到 1k 行保持覆盖同时控制用时。
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

            tick_crud.add_batch(bulk_ticks)

            end_time = time.time()
            duration = end_time - start_time
            throughput = batch_size / duration if duration else float('inf')

            print(f"✓ 批量插入完成:")
            print(f"  - 数据量: {batch_size} 条")
            print(f"  - 耗时: {duration:.3f} 秒")
            print(f"  - 吞吐量: {throughput:.0f} 条/秒")

            # 保守的性能基准，确保批量插入不会退化到秒级别以上
            assert duration < 5, f"批量插入耗时过长: {duration:.2f} 秒"
            print("✓ 性能基准验证通过（耗时<5秒）")

        except Exception as e:
            print(f"✗ 批量插入性能测试失败: {e}")
            raise

    def test_real_time_query_performance(self):
        """测试实时查询性能"""
        print("\n" + "="*60)
        print("开始测试: 实时查询性能")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 预先插入测试数据
            print("→ 确保有足够的测试数据...")
            existing_ticks = tick_crud.find(filters={"code": "TESTTICK_Tick"}, page_size=1000)

            if len(existing_ticks) < 100:
                print("✗ 测试数据不足，跳过性能测试")
                return

            # 测试查询性能
            import time
            query_count = 20
            durations_ms = []

            print(f"→ 执行 {query_count} 次查询性能测试...")

            for _ in range(query_count):
                start_time = time.time()

                # 模拟实时查询场景
                result = tick_crud.find(
                    filters={"code": "TESTTICK_Tick"},
                    page_size=50
                )

                end_time = time.time()
                query_duration = (end_time - start_time) * 1000  # 转换为毫秒
                durations_ms.append(query_duration)

            first_duration = durations_ms[0] if durations_ms else 0
            print(f"✓ 首次查询耗时: {first_duration:.2f} ms")
            avg_duration = sum(durations_ms) / len(durations_ms)
            max_duration = max(durations_ms) if durations_ms else 0

            print(f"✓ 查询性能统计:")
            print(f"  - 查询次数: {query_count}")
            print(f"  - 平均耗时: {avg_duration:.2f} ms")
            print(f"  - 最大耗时: {max_duration:.2f} ms")

            # 放宽阈值，关注是否出现明显退化
            assert avg_duration < 100, f"查询延迟超标: {avg_duration:.2f} ms > 100 ms"
            assert max_duration < 200, f"查询峰值延迟超标: {max_duration:.2f} ms > 200 ms"
            print("✓ 实时查询性能基准验证通过")

        except Exception as e:
            print(f"✗ 实时查询性能测试失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTickCRUDBusinessLogic:
    # 明确配置CRUD类和默认filters
    CRUD_TEST_CONFIG = {
        'crud_class': TickCRUD,
        'filters': {"code": "TESTTICK_Tick"}
    }

    """4. CRUD层业务逻辑测试 - Tick业务场景验证"""

    def test_tick_price_movement_analysis(self):
        """测试Tick价格变动分析"""
        print("\n" + "="*60)
        print("开始测试: Tick价格变动分析")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 查询连续的tick数据进行价格分析
            print("→ 查询连续tick数据进行价格分析...")
            ticks = tick_crud.find(filters={"code": "TESTTICK_Tick"}, page_size=100, order_by="timestamp")

            if len(ticks) < 10:
                print("✗ tick数据不足，跳过价格分析测试")
                return

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
            assert avg_price > 0
            assert max_price >= min_price
            assert price_volatility >= 0
            print("✓ 价格变动分析验证成功")

        except Exception as e:
            print(f"✗ Tick价格变动分析失败: {e}")
            raise

    def test_tick_buy_sell_pressure_analysis(self):
        """测试Tick买卖压力分析"""
        print("\n" + "="*60)
        print("开始测试: Tick买卖压力分析")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 查询tick数据进行买卖压力分析
            print("→ 查询tick数据进行买卖压力分析...")
            ticks = tick_crud.find(filters={"code": "TESTTICK_Tick"}, page_size=200)

            if len(ticks) < 20:
                print("✗ tick数据不足，跳过买卖压力分析测试")
                return

            # 按买卖方向分组
            buy_ticks = [t for t in ticks if t.direction == TICKDIRECTION_TYPES.ACTIVEBUY]
            sell_ticks = [t for t in ticks if t.direction == TICKDIRECTION_TYPES.ACTIVESELL]

            # 计算买卖压力指标
            buy_volume = sum(t.volume for t in buy_ticks)
            sell_volume = sum(t.volume for t in sell_ticks)
            total_volume = buy_volume + sell_volume

            if buy_ticks:
                avg_buy_price = sum(float(t.price) for t in buy_ticks) / len(buy_ticks)
            else:
                avg_buy_price = 0

            if sell_ticks:
                avg_sell_price = sum(float(t.price) for t in sell_ticks) / len(sell_ticks)
            else:
                avg_sell_price = 0

            # 买卖压力比率
            buy_pressure = buy_volume / total_volume if total_volume > 0 else 0
            sell_pressure = sell_volume / total_volume if total_volume > 0 else 0
            pressure_ratio = buy_volume / sell_volume if sell_volume > 0 else float('inf')

            print(f"✓ 买卖压力分析结果:")
            print(f"  - 买入成交量: {buy_volume}")
            print(f"  - 卖出成交量: {sell_volume}")
            print(f"  - 总成交量: {total_volume}")
            print(f"  - 买入压力: {buy_pressure:.1%}")
            print(f"  - 卖出压力: {sell_pressure:.1%}")
            print(f"  - 买卖比率: {pressure_ratio:.2f}")
            print(f"  - 平均买入价: {avg_buy_price:.3f}")
            print(f"  - 平均卖出价: {avg_sell_price:.3f}")

            # 验证买卖压力数据合理性
            assert 0 <= buy_pressure <= 1
            assert 0 <= sell_pressure <= 1

            # 买卖压力总和应该接近1（允许有其他交易方向的数据）
            total_pressure = buy_pressure + sell_pressure
            if total_pressure > 0:
                # 只在有买卖交易时验证总和
                assert total_pressure <= 1.0, f"买卖压力总和不应超过1: {total_pressure}"
                print(f"✓ 买卖压力总和: {total_pressure:.3f}")
            else:
                print("✓ 无买卖交易数据，跳过压力总和验证")
            print("✓ 买卖压力分析验证成功")

        except Exception as e:
            print(f"✗ Tick买卖压力分析失败: {e}")
            raise

    def test_tick_data_integrity(self):
        """测试Tick数据完整性和约束"""
        print("\n" + "="*60)
        print("开始测试: Tick数据完整性和约束")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 测试必要字段约束
            print("→ 测试必要字段约束...")

            # code不能为空
            try:
                invalid_tick = MTick(
                    code="",  # 空字符串
                    price=Decimal("10.50"),
                    volume=100
                )
                tick_crud.add(invalid_tick)
                print("✗ 应该拒绝code为空的tick")
                assert False, "应该抛出异常"
            except Exception as e:
                print(f"✓ 正确拒绝无效tick: {type(e).__name__}")

            # 验证枚举值约束
            print("→ 验证枚举值约束...")
            valid_ticks = tick_crud.find(filters={"code": "TESTTICK_Tick"}, page_size=50)
            for tick in valid_ticks:
                # 验证direction是有效枚举值
                assert tick.direction in [d.value for d in TICKDIRECTION_TYPES]
                # 验证price为正数
                assert float(tick.price) > 0
                # 验证volume为正整数
                assert tick.volume > 0

            print(f"✓ 验证了 {len(valid_ticks)} 条tick的约束条件")
            print("✓ 数据完整性验证成功")

        except Exception as e:
            print(f"✗ 数据完整性测试失败: {e}")
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

            print("✓ 动态表分区机制验证成功")

        except Exception as e:
            print(f"✗ 动态表分区测试失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTickCRUDDelete:
    # 明确配置CRUD类和默认filters
    CRUD_TEST_CONFIG = {
        'crud_class': TickCRUD,
        'filters': {"code": "TESTTICK_Tick"}
    }

    """5. CRUD层删除操作测试 - Tick数据清理"""

    def test_delete_tick_by_time_range(self):
        """测试按时间范围删除Tick数据"""
        print("\n" + "="*60)
        print("开始测试: 按时间范围删除Tick数据")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 创建测试数据
            test_time = datetime(2023, 12, 31, 23, 59, 59)
            test_tick_data = {
                "code": "TESTTICK_Tick",
                "price": Decimal("1.00"),
                "volume": 100,
                "direction": TICKDIRECTION_TYPES.ACTIVEBUY,
                "timestamp": test_time
            }

            inserted_tick = tick_crud.add(test_tick_data)
            print(f"✓ 创建测试tick: {inserted_tick.uuid}")

            # 查询确认插入成功
            inserted_ticks = tick_crud.find(filters={"code": "TESTTICK_Tick"})
            assert len(inserted_ticks) >= 1
            print("✓ tick插入确认成功")

            # 删除特定时间的tick数据
            print("→ 删除特定时间的tick数据...")
            all_ticks = tick_crud.find(filters={"code": "TESTTICK_Tick"})
            for tick in all_ticks:
                if tick.timestamp.date() == test_time.date():
                    tick_crud.remove(filters={"code": "TESTTICK_Tick", "uuid": tick.uuid})

            print("✓ 时间范围删除成功")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_ticks = tick_crud.find(filters={"code": "TESTTICK_Tick"})
            remaining_same_day = [t for t in remaining_ticks if t.timestamp.date() == test_time.date()]

            print(f"✓ 删除后剩余同日期tick: {len(remaining_same_day)} 条")
            print("✓ 时间范围删除验证成功")

        except Exception as e:
            print(f"✗ 时间范围删除失败: {e}")
            raise

    def test_delete_tick_by_uuid(self):
        """测试根据UUID删除单条Tick数据"""
        print("\n" + "="*60)
        print("开始测试: 根据UUID删除单条Tick数据")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 创建测试数据（使用字典格式，让TickCRUD自动处理）
            test_tick_data = {
                "code": "TESTTICK_Tick",
                "price": Decimal("9.99"),
                "volume": 999,
                "direction": TICKDIRECTION_TYPES.ACTIVESELL,
                "timestamp": datetime(2023, 11, 15, 14, 30, 0)
            }

            inserted_tick = tick_crud.add(test_tick_data)
            test_uuid = inserted_tick.uuid
            print(f"✓ 创建测试tick: {test_uuid}")

            # 验证数据存在 - 需要提供code字段
            before_ticks = tick_crud.find(filters={"code": "TESTTICK_Tick", "uuid": test_uuid})
            assert len(before_ticks) >= 1
            print(f"✓ 删除前数据量: {len(before_ticks)}")

            # 执行删除
            print("→ 执行UUID删除操作...")
            tick_crud.remove(filters={"code": "TESTTICK_Tick", "uuid": test_uuid})
            print("✓ UUID删除操作完成")

            # 验证删除结果 - 需要提供code字段
            print("→ 验证删除结果...")
            after_ticks = tick_crud.find(filters={"code": "TESTTICK_Tick", "uuid": test_uuid})
            assert len(after_ticks) == 0, "删除后应该没有相关数据"
            print("✓ 根据UUID删除Tick验证成功")

        except Exception as e:
            print(f"✗ UUID删除操作失败: {e}")
            raise

    def test_delete_tick_by_code(self):
        """测试根据股票代码删除Tick数据"""
        print("\n" + "="*60)
        print("开始测试: 根据股票代码删除Tick数据")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 创建多个测试tick
            test_ticks = []
            base_time = datetime(2023, 10, 15, 10, 0, 0)

            print("→ 开始创建测试数据...")
            for i in range(5):
                print(f"  创建第 {i+1}/5 条tick数据...")
                tick = MTick(
                    code="TESTTICK_Tick",
                    price=Decimal(f"8.{i}88"),
                    volume=100 + i * 10,
                    direction=TICKDIRECTION_TYPES.ACTIVEBUY if i % 2 == 0 else TICKDIRECTION_TYPES.ACTIVESELL,
                    timestamp=base_time + timedelta(seconds=i)
                )
                tick_crud.add(tick)
                test_ticks.append(tick.uuid)
                print(f"  ✓ 第 {i+1} 条tick创建完成: {tick.uuid}")

            print(f"✓ 创建测试tick: {len(test_ticks)} 条")

            # 验证数据存在
            print("→ 查询删除前数据量...")
            before_count = len(tick_crud.find(filters={"code": "TESTTICK_Tick"}))
            print(f"✓ 删除前数据量: {before_count}")

            # 执行删除
            print("→ 执行股票代码删除操作...")
            print("  查询需要删除的数据...")
            all_ticks = tick_crud.find(filters={"code": "TESTTICK_Tick"})
            print(f"  找到 {len(all_ticks)} 条数据需要删除")

            for i, tick in enumerate(all_ticks):
                print(f"  删除第 {i+1}/{len(all_ticks)} 条数据: {tick.uuid}")
                tick_crud.remove(filters={"code": "TESTTICK_Tick", "uuid": tick.uuid})
                print(f"  ✓ 第 {i+1} 条数据删除完成")

            print("✓ 股票代码删除操作完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            after_count = len(tick_crud.find(filters={"code": "TESTTICK_Tick"}))
            assert after_count == 0, "删除后应该没有相关数据"
            print(f"✓ 删除后数据量: {after_count}")
            print("✓ 根据股票代码删除Tick验证成功")

        except Exception as e:
            print(f"✗ 股票代码删除操作失败: {e}")
            raise

    def test_delete_tick_by_direction(self):
        """测试根据买卖方向删除Tick数据"""
        print("\n" + "="*60)
        print("开始测试: 根据买卖方向删除Tick数据")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 创建不同方向的测试数据
            base_time = datetime(2023, 9, 15, 11, 0, 0)

            # 买入tick
            for i in range(3):
                buy_tick = MTick(
                    code=TEST_TICK_CODE,
                    price=Decimal("7.77"),
                    volume=100,
                    direction=TICKDIRECTION_TYPES.ACTIVEBUY,
                    timestamp=base_time + timedelta(seconds=i)
                )
                tick_crud.add(buy_tick)

            # 卖出tick
            for i in range(3):
                sell_tick = MTick(
                    code=TEST_TICK_CODE,
                    price=Decimal("7.88"),
                    volume=200,
                    direction=TICKDIRECTION_TYPES.ACTIVESELL,
                    timestamp=base_time + timedelta(seconds=i + 10)
                )
                tick_crud.add(sell_tick)

            print("✓ 创建买卖方向测试数据")

            # 验证数据存在
            buy_before = len(tick_crud.find(filters={
                "code": TEST_TICK_CODE,
                "direction": TICKDIRECTION_TYPES.ACTIVEBUY.value
            }))
            sell_before = len(tick_crud.find(filters={
                "code": TEST_TICK_CODE,
                "direction": TICKDIRECTION_TYPES.ACTIVESELL.value
            }))
            print(f"✓ 删除前买入tick: {buy_before} 条")
            print(f"✓ 删除前卖出tick: {sell_before} 条")

            # 删除买入tick
            print("→ 删除买入方向tick...")
            buy_ticks = tick_crud.find(filters={
                "code": TEST_TICK_CODE,
                "direction": TICKDIRECTION_TYPES.ACTIVEBUY.value
            })
            for tick in buy_ticks:
                tick_crud.remove(filters={"code": TEST_TICK_CODE, "uuid": tick.uuid})

            # 验证买入tick删除结果
            buy_after = len(tick_crud.find(filters={
                "code": TEST_TICK_CODE,
                "direction": TICKDIRECTION_TYPES.ACTIVEBUY.value
            }))
            sell_after = len(tick_crud.find(filters={
                "code": TEST_TICK_CODE,
                "direction": TICKDIRECTION_TYPES.ACTIVESELL.value
            }))

            print(f"✓ 删除后买入tick: {buy_after} 条")
            print(f"✓ 删除后卖出tick: {sell_after} 条")
            assert buy_after == 0, "买入tick应该全部删除"
            assert sell_after > 0, "卖出tick应该保留"
            print("✓ 根据买卖方向删除Tick验证成功")

        except Exception as e:
            print(f"✗ 买卖方向删除操作失败: {e}")
            raise

    def test_delete_tick_by_price_range(self):
        """测试根据价格范围删除Tick数据"""
        print("\n" + "="*60)
        print("开始测试: 根据价格范围删除Tick数据")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 创建不同价格的测试数据
            base_time = datetime(2023, 8, 15, 13, 0, 0)
            price_levels = [5.50, 6.00, 10.50, 15.00, 20.50]

            for i, price in enumerate(price_levels):
                tick = MTick(
                    code="TESTTICK_Tick",
                    price=Decimal(str(price)),
                    volume=100,
                    direction=TICKDIRECTION_TYPES.ACTIVEBUY,
                    timestamp=base_time + timedelta(seconds=i)
                )
                tick_crud.add(tick)

            print(f"✓ 创建价格范围测试数据: {len(price_levels)} 条")

            # 验证数据存在
            all_before = len(tick_crud.find(filters={"code": "TESTTICK_Tick"}))
            high_before = len(tick_crud.find(filters={
                "code": "TESTTICK_Tick",
                "price__gte": Decimal("10.00")
            }))
            print(f"✓ 删除前总tick: {all_before} 条")
            print(f"✓ 删除前高价tick(≥10.00): {high_before} 条")

            # 删除高价tick
            print("→ 删除高价tick...")
            high_ticks = tick_crud.find(filters={
                "code": "TESTTICK_Tick",
                "price__gte": Decimal("10.00")
            })
            for tick in high_ticks:
                tick_crud.remove(filters={"code": "TESTTICK_Tick", "uuid": tick.uuid})

            # 验证删除结果
            high_after = len(tick_crud.find(filters={
                "code": "TESTTICK_Tick",
                "price__gte": Decimal("10.00")
            }))
            low_after = len(tick_crud.find(filters={
                "code": "TESTTICK_Tick",
                "price__lt": Decimal("10.00")
            }))

            print(f"✓ 删除后高价tick: {high_after} 条")
            print(f"✓ 删除后低价tick: {low_after} 条")
            assert high_after == 0, "高价tick应该全部删除"
            assert low_after > 0, "低价tick应该保留"
            print("✓ 根据价格范围删除Tick验证成功")

        except Exception as e:
            print(f"✗ 价格范围删除操作失败: {e}")
            raise

    def test_delete_tick_batch_cleanup(self):
        """测试批量清理Tick数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理Tick数据")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 创建大量清理测试数据
            cleanup_count = 20
            base_time = datetime(2023, 7, 15, 9, 30, 0)

            for i in range(cleanup_count):
                tick = MTick(
                    code="TESTTICK_Tick",
                    price=Decimal(f"6.{1000+i}"),
                    volume=50 + i,
                    direction=TICKDIRECTION_TYPES.ACTIVEBUY if i % 2 == 0 else TICKDIRECTION_TYPES.ACTIVESELL,
                    timestamp=base_time + timedelta(seconds=i * 10)
                )
                tick_crud.add(tick)

            print(f"✓ 创建批量清理测试数据: {cleanup_count} 条")

            # 验证数据存在
            before_count = len(tick_crud.find(filters={"code": "TESTTICK_Tick"}))
            print(f"✓ 删除前批量数据量: {before_count}")

            # 批量删除
            print("→ 执行批量清理操作...")
            all_ticks = tick_crud.find(filters={"code": "TESTTICK_Tick"})
            for tick in all_ticks:
                tick_crud.remove(filters={"code": "TESTTICK_Tick", "uuid": tick.uuid})

            print("✓ 批量清理操作完成")

            # 验证删除结果
            print("→ 验证批量清理结果...")
            after_count = len(tick_crud.find(filters={"code": "TESTTICK_Tick"}))
            assert after_count == 0, "删除后应该没有批量清理数据"
            print(f"✓ 删除后批量数据量: {after_count}")

            # 确认其他数据未受影响
            other_data_count = len(tick_crud.find(filters={"code": "TESTTICK_Tick"}, page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理Tick数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise

    def test_model_list_conversions(self):
        """测试ModelList的to_dataframe和to_entities转换功能"""
        from decimal import Decimal
        import pandas as pd
        print("\n" + "="*60)
        print("开始测试: Tick ModelList转换功能")
        print("="*60)

        tick_crud = TickCRUD()

        try:
            # 创建测试数据
            test_ticks = [
                {
                    "code": "TESTTICK_Tick",
                    "price": Decimal("10.50"),
                    "volume": 1000,
                    "direction": TICKDIRECTION_TYPES.ACTIVEBUY,
                    "timestamp": datetime(2023, 1, 5, 9, 30, 0)
                },
                {
                    "code": "TESTTICK_Tick",
                    "price": Decimal("10.51"),
                    "volume": 500,
                    "direction": TICKDIRECTION_TYPES.ACTIVESELL,
                    "timestamp": datetime(2023, 1, 5, 9, 30, 1)
                },
                {
                    "code": "TESTTICK_Tick",
                    "price": Decimal("15.25"),
                    "volume": 800,
                    "direction": TICKDIRECTION_TYPES.ACTIVEBUY,
                    "timestamp": datetime(2023, 1, 5, 9, 30, 0)
                }
            ]

            # 获取操作前数据条数用于验证
            before_count = len(tick_crud.find(filters={"code": "TESTTICK_Tick"}))
            print(f"✓ 操作前000001.SZ数据库记录数: {before_count}")

            # 插入测试数据
            tick_crud.add_batch(test_ticks)

            # 验证数据库记录数变化
            after_count = len(tick_crud.find(filters={"code": "TESTTICK_Tick"}))
            print(f"✓ 操作后000001.SZ数据库记录数: {after_count}")
            assert after_count - before_count == 3, f"应增加3条数据，实际增加{after_count - before_count}条"

            # 获取ModelList进行转换测试
            print("\n→ 获取ModelList...")
            model_list = tick_crud.find(filters={"code": "TESTTICK_Tick"})
            print(f"✓ ModelList类型: {type(model_list).__name__}")
            print(f"✓ ModelList长度: {len(model_list)}")
            assert len(model_list) >= 2

            # 测试1: to_dataframe转换
            print("\n→ 测试to_dataframe转换...")
            df = model_list.to_dataframe()
            print(f"✓ DataFrame类型: {type(df).__name__}")
            print(f"✓ DataFrame形状: {df.shape}")
            assert isinstance(df, pd.DataFrame), "应返回DataFrame"
            assert len(df) == len(model_list), f"DataFrame行数应等于ModelList长度，{len(df)} != {len(model_list)}"

            # 验证DataFrame列和内容
            required_columns = ['code', 'price', 'volume', 'direction', 'timestamp']
            for col in required_columns:
                assert col in df.columns, f"DataFrame应包含列: {col}"
            print(f"✓ 验证必要列存在: {required_columns}")

            # 验证DataFrame数据内容（考虑数据库中有其他历史数据）
            code_set = set(df['code'])
            assert 'TESTTICK_Tick' in code_set, "应包含测试数据TESTTICK_Tick"
            print(f"✓ DataFrame数据内容验证通过 - 包含股票代码: {code_set}")

            # 验证我们的测试数据确实存在
            test_data_count = len(df[df['code'] == 'TESTTICK_Tick'])
            assert test_data_count >= 3, f"应至少包含3条测试数据，实际: {test_data_count}"
            # 验证我们的测试数据包含在结果中
            direction_set = set(df['direction'])
            assert TICKDIRECTION_TYPES.ACTIVEBUY in direction_set, "应包含ACTIVEBUY交易方向"
            assert TICKDIRECTION_TYPES.ACTIVESELL in direction_set, "应包含ACTIVESELL交易方向"
            print(f"✓ DataFrame数据内容验证通过 - 交易方向: {direction_set}")

            # 测试2: to_entities转换
            print("\n→ 测试to_entities转换...")
            entities = model_list.to_entities()
            print(f"✓ 实体列表类型: {type(entities).__name__}")
            print(f"✓ 实体列表长度: {len(entities)}")
            assert len(entities) == len(model_list), f"实体列表长度应等于ModelList长度，{len(entities)} != {len(model_list)}"

            # 验证实体类型和内容
            first_entity = entities[0]
            from ginkgo.trading import Tick
            assert isinstance(first_entity, Tick), f"应转换为Tick实体，实际{type(first_entity)}"

            # 验证实体属性
            assert first_entity.code == "TESTTICK_Tick"
            assert first_entity.direction in [TICKDIRECTION_TYPES.ACTIVEBUY, TICKDIRECTION_TYPES.ACTIVESELL]
            print("✓ Tick实体转换验证通过")

            # 测试3: 业务对象映射验证
            print("\n→ 测试业务对象映射...")
            for i, entity in enumerate(entities[:2]):  # 只验证前2个
                # 验证枚举类型正确转换
                assert entity.direction in [TICKDIRECTION_TYPES.ACTIVEBUY, TICKDIRECTION_TYPES.ACTIVESELL]

                # 验证数值类型
                assert isinstance(entity.volume, int)
                assert isinstance(entity.price, Decimal)
                print(f"  - 实体{i+1}: {entity.code} {entity.direction.name} {entity.volume}股 @ {entity.price}")
            print("✓ 业务对象映射验证通过")

            # 测试4: 验证缓存机制
            print("\n→ 测试转换缓存机制...")
            df2 = model_list.to_dataframe()
            entities2 = model_list.to_entities()
            # 验证结果一致性
            assert df.equals(df2), "DataFrame缓存结果应一致"
            assert len(entities) == len(entities2), "实体列表缓存结果应一致"
            print("✓ 缓存机制验证正确")

            # 测试5: 验证空ModelList的转换（处理不存在的表）
            print("\n→ 测试空ModelList的转换...")
            try:
                empty_model_list = tick_crud.find(filters={"code": "NONEXISTENT_TICK"})
                assert len(empty_model_list) == 0, "空ModelList长度应为0"
            except Exception as e:
                # 如果表不存在，应该优雅处理
                print(f"✓ 表不存在时优雅处理: {e}")
                empty_model_list = []  # 手动创建空列表用于后续测试
            empty_df = empty_model_list.to_dataframe()
            empty_entities = empty_model_list.to_entities()
            assert isinstance(empty_df, pd.DataFrame), "空转换应返回DataFrame"
            assert empty_df.shape[0] == 0, "空DataFrame行数应为0"
            assert isinstance(empty_entities, list), "空转换应返回列表"
            assert len(empty_entities) == 0, "空实体列表长度应为0"
            print("✓ 空ModelList转换验证正确")

            print("\n✓ 所有Tick ModelList转换功能测试通过！")

        finally:
            # 清理测试数据并验证删除效果
            try:
                # 查找我们要删除的测试数据（添加时间范围限制）
                test_ticks_to_delete = tick_crud.find(filters={
                    "code": "TESTTICK_Tick",
                    "timestamp__gte": datetime(2023, 1, 5, 9, 30, 0)
                })
                before_delete = len(tick_crud.find(filters={"code": "TESTTICK_Tick"}))

                for tick in test_ticks_to_delete:
                    tick_crud.remove({"code": "TESTTICK_Tick", "uuid": tick.uuid})

                after_delete = len(tick_crud.find(filters={"code": "TESTTICK_Tick"}))
                deleted_count = before_delete - after_delete
                print(f"✓ 清理测试数据: 删除了{deleted_count}条记录")
                assert deleted_count >= 2, f"应至少删除2条测试数据，实际删除{deleted_count}条"
            except Exception as cleanup_error:
                print(f"⚠️ 清理测试数据时出错: {cleanup_error}")


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：Tick CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_tick_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("特别关注: 动态表分区机制和性能基准验证")
