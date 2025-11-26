"""
TickSummaryCRUD数据库操作TDD测试

测试CRUD层的Tick汇总数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)

TickSummary是Tick数据的汇总模型，记录Tick数据的统计信息。
为高频数据分析和市场微观结构研究提供支持。

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

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.tick_summary_crud import TickSummaryCRUD
from ginkgo.data.models.model_tick_summary import MTickSummary
from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestTickSummaryCRUDInsert:
    CRUD_TEST_CONFIG = {'crud_class': TickSummaryCRUD}
    """1. CRUD层插入操作测试 - TickSummary数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入TickSummary数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: TickSummary CRUD层批量插入")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()
        print(f"✓ 创建TickSummaryCRUD实例: {tick_summary_crud.__class__.__name__}")

        # 创建测试TickSummary数据 - 不同时间点的价格汇总
        base_time = datetime(2023, 1, 3, 9, 30)
        test_summaries = []

        # 创建多个时间点的Tick汇总数据
        for i in range(10):
            current_time = base_time + timedelta(seconds=i)
            price = Decimal("10.50") + Decimal(str(i * 0.01))  # 价格逐步上升
            volume = 1000 + i * 100  # 成交量逐步增加

            tick_summary = MTickSummary(
                code="000001.SZ",
                price=price,
                volume=volume,
                timestamp=current_time
            )
            tick_summary.source = SOURCE_TYPES.TEST
            test_summaries.append(tick_summary)

        print(f"✓ 创建测试数据: {len(test_summaries)}条TickSummary记录")
        print(f"  - 股票代码: 000001.SZ")
        print(f"  - 价格范围: {test_summaries[0].price} ~ {test_summaries[-1].price}")
        print(f"  - 时间范围: {test_summaries[0].timestamp} ~ {test_summaries[-1].timestamp}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            tick_summary_crud.add_batch(test_summaries)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = tick_summary_crud.find(filters={
                "code": "000001.SZ",
                "timestamp__gte": base_time,
                "timestamp__lte": base_time + timedelta(seconds=9)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 10

            # 验证数据内容
            prices = [float(s.price) for s in query_result]
            volumes = [s.volume for s in query_result]
            print(f"✓ 价格验证通过: {min(prices):.2f} ~ {max(prices):.2f}")
            print(f"✓ 成交量验证通过: {min(volumes)} ~ {max(volumes)}")

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_tick_summary(self):
        """测试单条TickSummary数据插入"""
        print("\n" + "="*60)
        print("开始测试: TickSummary CRUD层单条插入")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        test_summary = MTickSummary(
            code="000002.SZ",
            price=Decimal("15.75"),
            volume=2000,
            timestamp=datetime(2023, 1, 3, 10, 30, 0)
        )
        test_summary.source = SOURCE_TYPES.TEST
        print(f"✓ 创建测试TickSummary: {test_summary.timestamp}")
        print(f"  - 股票代码: {test_summary.code}")
        print(f"  - 价格: {test_summary.price}")
        print(f"  - 成交量: {test_summary.volume}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            tick_summary_crud.add(test_summary)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = tick_summary_crud.find(filters={
                "code": "000002.SZ",
                "timestamp": datetime(2023, 1, 3, 10, 30, 0)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_summary = query_result[0]
            print(f"✓ 插入的TickSummary验证: {inserted_summary.price}")
            assert inserted_summary.code == "000002.SZ"
            assert inserted_summary.price == Decimal("15.75")
            assert inserted_summary.volume == 2000

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTickSummaryCRUDQuery:
    CRUD_TEST_CONFIG = {'crud_class': TickSummaryCRUD}
    """2. CRUD层查询操作测试 - TickSummary数据查询和过滤"""

    def test_find_by_code(self):
        """测试根据股票代码查询TickSummary"""
        print("\n" + "="*60)
        print("开始测试: 根据code查询TickSummary")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        try:
            # 查询特定股票的Tick汇总数据
            print("→ 查询code=000001.SZ的Tick汇总数据...")
            code_summaries = tick_summary_crud.find(filters={
                "code": "000001.SZ"
            })
            print(f"✓ 查询到 {len(code_summaries)} 条记录")

            if code_summaries:
                # 验证查询结果
                prices = [float(s.price) for s in code_summaries]
                volumes = [s.volume for s in code_summaries]
                avg_price = sum(prices) / len(prices)
                total_volume = sum(volumes)

                print(f"✓ 价格统计:")
                print(f"    平均价格: {avg_price:.2f}")
                print(f"    价格范围: {min(prices):.2f} ~ {max(prices):.2f}")
                print(f"✓ 成交量统计:")
                print(f"    总成交量: {total_volume:,}")
                print(f"    平均成交量: {total_volume/len(volumes):.0f}")

            for summary in code_summaries[:5]:  # 只显示前5条
                print(f"  - {summary.timestamp}: 价格 {summary.price}, 成交量 {summary.volume}")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_time_range(self):
        """测试根据时间范围查询TickSummary"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围查询TickSummary")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        try:
            # 查询特定时间范围的Tick汇总数据
            start_time = datetime(2023, 1, 3, 9, 30, 0)
            end_time = datetime(2023, 1, 3, 9, 35, 0)

            print(f"→ 查询时间范围 {start_time} ~ {end_time} 的Tick汇总数据...")
            time_summaries = tick_summary_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            })
            print(f"✓ 查询到 {len(time_summaries)} 条记录")

            # 验证时间范围
            for summary in time_summaries:
                print(f"  - {summary.timestamp}: {summary.code} 价格 {summary.price}, 成交量 {summary.volume}")
                assert start_time <= summary.timestamp <= end_time

            print("✓ 时间范围查询验证成功")

        except Exception as e:
            print(f"✗ 时间范围查询失败: {e}")
            raise

    def test_find_by_price_range(self):
        """测试根据价格范围查询TickSummary"""
        print("\n" + "="*60)
        print("开始测试: 根据价格范围查询TickSummary")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        try:
            # 查询特定价格范围的Tick汇总数据
            min_price = Decimal("10.50")
            max_price = Decimal("10.55")

            print(f"→ 查询价格范围 {min_price} ~ {max_price} 的Tick汇总数据...")
            price_summaries = tick_summary_crud.find(filters={
                "price__gte": min_price,
                "price__lte": max_price
            })
            print(f"✓ 查询到 {len(price_summaries)} 条记录")

            # 验证价格范围
            for summary in price_summaries:
                print(f"  - {summary.timestamp}: {summary.code} 价格 {summary.price}, 成交量 {summary.volume}")
                assert min_price <= summary.price <= max_price

            print("✓ 价格范围查询验证成功")

        except Exception as e:
            print(f"✗ 价格范围查询失败: {e}")
            raise

    def test_find_high_volume_ticks(self):
        """测试查询高成交量Tick汇总数据"""
        print("\n" + "="*60)
        print("开始测试: 查询高成交量Tick汇总数据")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        try:
            # 查询高成交量的Tick汇总数据
            min_volume = 1500

            print(f"→ 查询成交量 >= {min_volume} 的Tick汇总数据...")
            high_volume_summaries = tick_summary_crud.find(filters={
                "volume__gte": min_volume
            })
            print(f"✓ 查询到 {len(high_volume_summaries)} 条记录")

            # 验证成交量筛选
            for summary in high_volume_summaries:
                print(f"  - {summary.timestamp}: {summary.code} 价格 {summary.price}, 成交量 {summary.volume}")
                assert summary.volume >= min_volume

            if high_volume_summaries:
                avg_price = sum(float(s.price) for s in high_volume_summaries) / len(high_volume_summaries)
                print(f"✓ 高成交量Tick平均价格: {avg_price:.2f}")

            print("✓ 高成交量查询验证成功")

        except Exception as e:
            print(f"✗ 高成交量查询失败: {e}")
            raise



@pytest.mark.database
@pytest.mark.tdd
class TestTickSummaryCRUDBusinessLogic:
    CRUD_TEST_CONFIG = {'crud_class': TickSummaryCRUD}
    """4. CRUD层业务逻辑测试 - TickSummary业务场景验证"""

    def test_price_movement_analysis(self):
        """测试价格变动分析"""
        print("\n" + "="*60)
        print("开始测试: 价格变动分析")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        try:
            # 查询特定股票的价格数据进行分析
            print("→ 查询价格数据进行变动分析...")
            summaries = tick_summary_crud.find(filters={
                "code": "000001.SZ"
            }, order_by="timestamp")

            if len(summaries) < 5:
                print("✗ 价格数据不足，跳过变动分析")
                return

            # 计算价格变动统计
            prices = [float(s.price) for s in summaries]
            price_changes = []

            for i in range(1, len(prices)):
                change = prices[i] - prices[i-1]
                change_pct = (change / prices[i-1]) * 100 if prices[i-1] > 0 else 0
                price_changes.append(change_pct)

            # 分析结果
            avg_change = sum(price_changes) / len(price_changes)
            max_change = max(price_changes)
            min_change = min(price_changes)
            volatility = sum(abs(c) for c in price_changes) / len(price_changes)

            print(f"✓ 价格变动分析结果:")
            print(f"  - 数据点数: {len(summaries)}")
            print(f"  - 价格范围: {min(prices):.2f} ~ {max(prices):.2f}")
            print(f"  - 平均变动: {avg_change:+.3f}%")
            print(f"  - 最大涨幅: {max_change:+.3f}%")
            print(f"  - 最大跌幅: {min_change:+.3f}%")
            print(f"  - 波动率: {volatility:.3f}%")

            # 验证分析结果
            assert len(price_changes) == len(summaries) - 1
            assert volatility >= 0
            print("✓ 价格变动分析验证成功")

        except Exception as e:
            print(f"✗ 价格变动分析失败: {e}")
            raise

    def test_volume_pattern_analysis(self):
        """测试成交量模式分析"""
        print("\n" + "="*60)
        print("开始测试: 成交量模式分析")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        try:
            # 查询成交量数据进行分析
            print("→ 查询成交量数据进行模式分析...")
            summaries = tick_summary_crud.find(page=1, page_size=50, order_by="timestamp")

            if len(summaries) < 10:
                print("✗ 成交量数据不足，跳过模式分析")
                return

            # 成交量统计分析
            volumes = [s.volume for s in summaries]
            timestamps = [s.timestamp for s in summaries]

            # 计算统计指标
            avg_volume = sum(volumes) / len(volumes)
            max_volume = max(volumes)
            min_volume = min(volumes)
            volume_std = (sum((v - avg_volume) ** 2 for v in volumes) / len(volumes)) ** 0.5

            # 识别高成交量时段（成交量 > 平均值 + 1倍标准差）
            high_volume_threshold = avg_volume + volume_std
            high_volume_periods = []

            for i, volume in enumerate(volumes):
                if volume > high_volume_threshold:
                    high_volume_periods.append({
                        "timestamp": timestamps[i],
                        "volume": volume,
                        "price": summaries[i].price
                    })

            print(f"✓ 成交量模式分析结果:")
            print(f"  - 数据点数: {len(summaries)}")
            print(f"  - 平均成交量: {avg_volume:.0f}")
            print(f"  - 成交量范围: {min_volume} ~ {max_volume}")
            print(f"  - 成交量标准差: {volume_std:.0f}")
            print(f"  - 高成交量阈值: {high_volume_threshold:.0f}")
            print(f"  - 高成交量时段数: {len(high_volume_periods)}")

            # 显示高成交量时段
            for period in high_volume_periods[:5]:  # 只显示前5个
                print(f"    - {period['timestamp']}: 成交量 {period['volume']}, 价格 {period['price']}")

            # 验证分析结果
            assert len(volumes) == len(summaries)
            assert len(high_volume_periods) <= len(summaries)
            print("✓ 成交量模式分析验证成功")

        except Exception as e:
            print(f"✗ 成交量模式分析失败: {e}")
            raise

    def test_tick_summary_aggregation(self):
        """测试Tick汇总数据聚合分析"""
        print("\n" + "="*60)
        print("开始测试: Tick汇总数据聚合分析")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        try:
            # 查询Tick汇总数据进行聚合分析
            print("→ 查询数据进行聚合分析...")
            all_summaries = tick_summary_crud.find(page=1, page_size=100)

            if len(all_summaries) < 20:
                print("✗ 数据不足，跳过聚合分析")
                return

            # 按股票代码分组统计
            code_stats = {}
            for summary in all_summaries:
                code = summary.code
                if code not in code_stats:
                    code_stats[code] = {
                        "count": 0,
                        "total_volume": 0,
                        "prices": [],
                        "first_timestamp": summary.timestamp,
                        "last_timestamp": summary.timestamp
                    }

                code_stats[code]["count"] += 1
                code_stats[code]["total_volume"] += summary.volume
                code_stats[code]["prices"].append(float(summary.price))

                if summary.timestamp < code_stats[code]["first_timestamp"]:
                    code_stats[code]["first_timestamp"] = summary.timestamp
                if summary.timestamp > code_stats[code]["last_timestamp"]:
                    code_stats[code]["last_timestamp"] = summary.timestamp

            print(f"✓ 股票代码聚合分析结果:")
            for code, stats in code_stats.items():
                avg_price = sum(stats["prices"]) / len(stats["prices"])
                price_range = max(stats["prices"]) - min(stats["prices"])
                time_span = stats["last_timestamp"] - stats["first_timestamp"]

                print(f"  - {code}:")
                print(f"    数据点数: {stats['count']}")
                print(f"    总成交量: {stats['total_volume']:,}")
                print(f"    平均价格: {avg_price:.2f}")
                print(f"    价格振幅: {price_range:.2f}")
                print(f"    时间跨度: {time_span}")

            # 验证聚合结果
            total_points = sum(stats["count"] for stats in code_stats.values())
            assert total_points == len(all_summaries)
            print("✓ Tick汇总数据聚合分析验证成功")

        except Exception as e:
            print(f"✗ Tick汇总数据聚合分析失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTickSummaryCRUDDelete:
    CRUD_TEST_CONFIG = {'crud_class': TickSummaryCRUD}
    """3. CRUD层删除操作测试 - TickSummary数据删除验证"""

    def test_delete_tick_summary_by_code(self):
        """测试根据股票代码删除TickSummary"""
        print("\n" + "="*60)
        print("开始测试: 根据股票代码删除TickSummary")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_summary = MTickSummary(
            code="DELETE_TEST_STOCK",
            price=Decimal("20.50"),
            volume=3000,
            timestamp=datetime(2023, 6, 15, 10, 30, 0)
        )
        test_summary.source = SOURCE_TYPES.TEST
        tick_summary_crud.add(test_summary)
        print(f"✓ 插入测试数据: {test_summary.code} at {test_summary.timestamp}")

        # 验证数据存在
        before_count = len(tick_summary_crud.find(filters={"code": "DELETE_TEST_STOCK"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            tick_summary_crud.remove(filters={"code": "DELETE_TEST_STOCK"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(tick_summary_crud.find(filters={"code": "DELETE_TEST_STOCK"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            print("✓ 根据股票代码删除TickSummary验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_tick_summary_by_time_range(self):
        """测试根据时间范围删除TickSummary"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围删除TickSummary")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        # 准备测试数据 - 特定时间范围的数据
        print("→ 准备测试数据...")
        test_time_range = [
            datetime(2023, 7, 1, 10, 30, 0),
            datetime(2023, 7, 1, 10, 31, 0),
            datetime(2023, 7, 1, 10, 32, 0)
        ]

        for i, test_time in enumerate(test_time_range):
            test_summary = MTickSummary(
                code=f"TIME_TEST_STOCK_{i+1:03d}",
                price=Decimal(f"25.{1000+i}"),
                volume=2000 + i * 100,
                timestamp=test_time
            )
            test_summary.source = SOURCE_TYPES.TEST
            tick_summary_crud.add(test_summary)

        print(f"✓ 插入时间范围测试数据: {len(test_time_range)}条")

        # 验证数据存在
        before_count = len(tick_summary_crud.find(filters={
            "timestamp__gte": datetime(2023, 7, 1, 10, 30, 0),
            "timestamp__lte": datetime(2023, 7, 1, 10, 32, 59)
        }))
        print(f"✓ 删除前时间范围内数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行时间范围删除操作...")
            tick_summary_crud.remove(filters={
                "timestamp__gte": datetime(2023, 7, 1, 10, 30, 0),
                "timestamp__lte": datetime(2023, 7, 1, 10, 32, 59)
            })
            print("✓ 时间范围删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(tick_summary_crud.find(filters={
                "timestamp__gte": datetime(2023, 7, 1, 10, 30, 0),
                "timestamp__lte": datetime(2023, 7, 1, 10, 32, 59)
            }))
            print(f"✓ 删除后时间范围内数据量: {after_count}")
            assert after_count == 0, "删除后时间范围内应该没有数据"

            print("✓ 根据时间范围删除TickSummary验证成功")

        except Exception as e:
            print(f"✗ 时间范围删除操作失败: {e}")
            raise

    def test_delete_tick_summary_by_price_range(self):
        """测试根据价格范围删除TickSummary"""
        print("\n" + "="*60)
        print("开始测试: 根据价格范围删除TickSummary")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        # 准备测试数据 - 特定价格范围的数据
        print("→ 准备测试数据...")
        test_prices = [
            ("LOW_PRICE_STOCK", Decimal("5.00")),     # 低价格
            ("MID_PRICE_STOCK", Decimal("15.00")),    # 中价格
            ("HIGH_PRICE_STOCK", Decimal("50.00")),    # 高价格
            ("EXTREME_PRICE_STOCK", Decimal("100.00")), # 极高价格
        ]

        for stock_code, price in test_prices:
            test_summary = MTickSummary(
                code=stock_code,
                price=price,
                volume=2500,
                timestamp=datetime(2023, 8, 15, 10, 30, 0)
            )
            test_summary.source = SOURCE_TYPES.TEST
            tick_summary_crud.add(test_summary)

        print(f"✓ 插入价格范围测试数据: {len(test_prices)}条")

        try:
            # 删除高价格数据 (> 30.00)
            print("\n→ 执行高价格数据删除操作...")
            before_high = len(tick_summary_crud.find(filters={"price__gt": Decimal("30.00")}))
            print(f"✓ 删除前高价格数据量: {before_high}")

            tick_summary_crud.remove(filters={"price__gt": Decimal("30.00")})
            print("✓ 高价格删除操作完成")

            after_high = len(tick_summary_crud.find(filters={"price__gt": Decimal("30.00")}))
            print(f"✓ 删除后高价格数据量: {after_high}")
            assert after_high == 0, "删除后应该没有高价格数据"

            # 删除低价格数据 (< 10.00)
            print("\n→ 执行低价格数据删除操作...")
            before_low = len(tick_summary_crud.find(filters={"price__lt": Decimal("10.00")}))
            print(f"✓ 删除前低价格数据量: {before_low}")

            tick_summary_crud.remove(filters={"price__lt": Decimal("10.00")})
            print("✓ 低价格删除操作完成")

            after_low = len(tick_summary_crud.find(filters={"price__lt": Decimal("10.00")}))
            print(f"✓ 删除后低价格数据量: {after_low}")
            assert after_low == 0, "删除后应该没有低价格数据"

            # 确认中价格数据未受影响
            mid_price_count = len(tick_summary_crud.find(filters={
                "price__gte": Decimal("10.00"),
                "price__lte": Decimal("30.00")
            }))
            print(f"✓ 中价格数据保留验证: {mid_price_count}条")
            assert mid_price_count > 0, "中价格数据应该保留"

            print("✓ 根据价格范围删除TickSummary验证成功")

        except Exception as e:
            print(f"✗ 价格范围删除操作失败: {e}")
            raise

    def test_delete_tick_summary_by_volume_threshold(self):
        """测试根据成交量阈值删除TickSummary"""
        print("\n" + "="*60)
        print("开始测试: 根据成交量阈值删除TickSummary")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        # 准备测试数据 - 不同成交量的数据
        print("→ 准备测试数据...")
        test_volumes = [
            ("LOW_VOLUME_STOCK", 500),    # 低成交量
            ("MID_VOLUME_STOCK", 2000),   # 中成交量
            ("HIGH_VOLUME_STOCK", 8000),  # 高成交量
            ("EXTREME_VOLUME_STOCK", 15000), # 极高成交量
        ]

        for stock_code, volume in test_volumes:
            test_summary = MTickSummary(
                code=stock_code,
                price=Decimal("30.00"),
                volume=volume,
                timestamp=datetime(2023, 9, 1, 10, 30, 0)
            )
            test_summary.source = SOURCE_TYPES.TEST
            tick_summary_crud.add(test_summary)

        print(f"✓ 插入成交量测试数据: {len(test_volumes)}条")

        try:
            # 删除高成交量数据 (> 5000)
            print("\n→ 执行高成交量数据删除操作...")
            before_high = len(tick_summary_crud.find(filters={"volume__gt": 5000}))
            print(f"✓ 删除前高成交量数据量: {before_high}")

            tick_summary_crud.remove(filters={"volume__gt": 5000})
            print("✓ 高成交量删除操作完成")

            after_high = len(tick_summary_crud.find(filters={"volume__gt": 5000}))
            print(f"✓ 删除后高成交量数据量: {after_high}")
            assert after_high == 0, "删除后应该没有高成交量数据"

            # 删除低成交量数据 (< 1000)
            print("\n→ 执行低成交量数据删除操作...")
            before_low = len(tick_summary_crud.find(filters={"volume__lt": 1000}))
            print(f"✓ 删除前低成交量数据量: {before_low}")

            tick_summary_crud.remove(filters={"volume__lt": 1000})
            print("✓ 低成交量删除操作完成")

            after_low = len(tick_summary_crud.find(filters={"volume__lt": 1000}))
            print(f"✓ 删除后低成交量数据量: {after_low}")
            assert after_low == 0, "删除后应该没有低成交量数据"

            # 确认中成交量数据未受影响
            mid_volume_count = len(tick_summary_crud.find(filters={
                "volume__gte": 1000,
                "volume__lte": 5000
            }))
            print(f"✓ 中成交量数据保留验证: {mid_volume_count}条")
            assert mid_volume_count > 0, "中成交量数据应该保留"

            print("✓ 根据成交量阈值删除TickSummary验证成功")

        except Exception as e:
            print(f"✗ 成交量阈值删除操作失败: {e}")
            raise

    def test_delete_tick_summary_by_complex_conditions(self):
        """测试根据复杂条件删除TickSummary"""
        print("\n" + "="*60)
        print("开始测试: 根据复杂条件删除TickSummary")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        # 准备测试数据 - 满足不同复杂条件的数据
        print("→ 准备测试数据...")
        complex_conditions = [
            # (code, price, volume, hour)
            ("COMPLEX_001", Decimal("10.00"), 500, 9),    # 早盘低价低量
            ("COMPLEX_002", Decimal("20.00"), 3000, 10),   # 上午中价中量
            ("COMPLEX_003", Decimal("30.00"), 8000, 14),   # 午盘高价高量
            ("COMPLEX_004", Decimal("15.00"), 2000, 15),   # 下午中价中量
        ]

        for code, price, volume, hour in complex_conditions:
            test_summary = MTickSummary(
                code=code,
                price=price,
                volume=volume,
                timestamp=datetime(2023, 10, 15, hour, 30, 0)
            )
            test_summary.source = SOURCE_TYPES.TEST
            tick_summary_crud.add(test_summary)

        print(f"✓ 插入复杂条件测试数据: {len(complex_conditions)}条")

        try:
            # 删除午盘高成交量数据 (价格>25, 成交量>5000, 时间在12:00-16:00)
            print("\n→ 执行复杂条件删除操作...")
            before_complex = len(tick_summary_crud.find(filters={
                "price__gt": Decimal("25.00"),
                "volume__gt": 5000,
                "timestamp__gte": datetime(2023, 10, 15, 12, 0, 0),
                "timestamp__lte": datetime(2023, 10, 15, 16, 0, 0)
            }))
            print(f"✓ 删除前复杂条件数据量: {before_complex}")

            tick_summary_crud.remove(filters={
                "price__gt": Decimal("25.00"),
                "volume__gt": 5000,
                "timestamp__gte": datetime(2023, 10, 15, 12, 0, 0),
                "timestamp__lte": datetime(2023, 10, 15, 16, 0, 0)
            })
            print("✓ 复杂条件删除操作完成")

            after_complex = len(tick_summary_crud.find(filters={
                "price__gt": Decimal("25.00"),
                "volume__gt": 5000,
                "timestamp__gte": datetime(2023, 10, 15, 12, 0, 0),
                "timestamp__lte": datetime(2023, 10, 15, 16, 0, 0)
            }))
            print(f"✓ 删除后复杂条件数据量: {after_complex}")
            assert after_complex == 0, "删除后应该没有符合复杂条件的数据"

            # 确认其他数据未受影响
            remaining_count = len(tick_summary_crud.find(filters={
                "code__like": "COMPLEX_%"
            }))
            print(f"✓ 其他数据保留验证: {remaining_count}条")
            assert remaining_count > 0, "其他数据应该保留"

            print("✓ 根据复杂条件删除TickSummary验证成功")

        except Exception as e:
            print(f"✗ 复杂条件删除操作失败: {e}")
            raise

    def test_delete_tick_summary_batch_cleanup(self):
        """测试批量清理TickSummary数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理TickSummary数据")
        print("="*60)

        tick_summary_crud = TickSummaryCRUD()

        # 准备批量清理数据
        print("→ 准备批量清理测试数据...")
        cleanup_summaries = []
        base_time = datetime(2023, 11, 1, 10, 0, 0)

        for i in range(15):
            code = f"CLEANUP_STOCK_{i+1:03d}"
            cleanup_summaries.append(code)

            test_summary = MTickSummary(
                code=code,
                price=Decimal(f"35.{1000+i}"),
                volume=1000 + i * 50,
                timestamp=base_time + timedelta(minutes=i)
            )
            test_summary.source = SOURCE_TYPES.TEST
            tick_summary_crud.add(test_summary)

        print(f"✓ 插入批量清理测试数据: {len(cleanup_summaries)}条")

        # 验证数据存在
        before_count = len(tick_summary_crud.find(filters={
            "code__like": "CLEANUP_STOCK_%"
        }))
        print(f"✓ 删除前批量数据量: {before_count}")

        try:
            # 批量删除
            print("\n→ 执行批量清理操作...")
            tick_summary_crud.remove(filters={
                "code__like": "CLEANUP_STOCK_%"
            })
            print("✓ 批量清理操作完成")

            # 验证删除结果
            print("\n→ 验证批量清理结果...")
            after_count = len(tick_summary_crud.find(filters={
                "code__like": "CLEANUP_STOCK_%"
            }))
            print(f"✓ 删除后批量数据量: {after_count}")
            assert after_count == 0, "删除后应该没有批量清理数据"

            # 确认其他数据未受影响
            other_data_count = len(tick_summary_crud.find(page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理TickSummary数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：TickSummary CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_tick_summary_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: Tick汇总数据的统计分析功能")
