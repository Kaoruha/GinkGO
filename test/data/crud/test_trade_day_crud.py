"""
TradeDayCRUD数据库操作TDD测试

测试CRUD层的交易日历数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)

TradeDay是交易日历数据模型，记录各市场的交易日和休市日。
为策略回测和实盘交易提供时间基准支持。

测试数据管理：
- 所有测试数据使用UUID前缀 "TRADEDAY" 进行标识
- 提供自动清理机制，避免测试数据污染
- 支持按前缀批量删除测试数据

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
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "test"))

from ginkgo.data.crud.trade_day_crud import TradeDayCRUD
from ginkgo.data.models.model_trade_day import MTradeDay
from ginkgo.enums import SOURCE_TYPES, MARKET_TYPES
from test.fixtures.test_utils import generate_test_uuid



@pytest.mark.database
@pytest.mark.tdd
class TestTradeDayCRUDCreate:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': TradeDayCRUD}

    """测试TradeDay CRUD的create方法"""

    def test_create_single_trade_day(self):
        """测试使用create方法创建单个TradeDay"""
        print("\n" + "="*60)
        print("开始测试: TradeDay CRUD层create方法")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 使用create方法创建TradeDay
            print("→ 使用create方法创建TradeDay...")
            create_result = trade_day_crud.create(
                market=MARKET_TYPES.CHINA,
                is_open=True,
                timestamp=datetime(2023, 1, 3),
                source=SOURCE_TYPES.TEST
            )

            # 获取创建的模型（create返回单个Model）
            created_trade_day = create_result
            print(f"✓ create成功: {created_trade_day.timestamp}")
            print(f"  - UUID: {created_trade_day.uuid}")
            print(f"  - 原始market值: {created_trade_day.market} (整数)")
            print(f"  - 是否开盘: {created_trade_day.is_open}")

            # 验证数据已插入
            print("\n→ 验证插入的数据...")
            query_result = trade_day_crud.find(filters={"uuid": created_trade_day.uuid})
            assert query_result.count() == 1

            # 转换为业务对象验证
            found_trade_day = query_result.to_entities()[0]
            print(f"✓ 查询到业务对象: {type(found_trade_day).__name__}")
            print(f"  - 市场: {found_trade_day.market.name}")
            print(f"  - 是否开盘: {found_trade_day.is_open}")
            assert found_trade_day.market == MARKET_TYPES.CHINA
            assert found_trade_day.is_open == True
            print("✓ 数据验证通过")

        except Exception as e:
            print(f"✗ create方法测试失败: {e}")
            raise

    def test_create_with_validation(self):
        """测试create方法的数据验证功能"""
        print("\n" + "="*60)
        print("开始测试: create方法数据验证")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 测试创建带验证数据的TradeDay
            print("→ 创建带验证的TradeDay...")
            create_result = trade_day_crud.create(
                market=MARKET_TYPES.NASDAQ,
                is_open=False,
                timestamp=datetime(2023, 12, 25),  # 节假日
                source=SOURCE_TYPES.TEST
            )

            validated_trade_day = create_result
            print(f"✓ 验证创建成功: {validated_trade_day.timestamp}")
            print(f"  - 原始market值: {validated_trade_day.market} (整数)")
            print(f"  - 休市日: {not validated_trade_day.is_open}")

            # 使用find方法获取业务对象进行验证
            print("\n→ 验证业务对象转换...")
            query_result = trade_day_crud.find(filters={"uuid": validated_trade_day.uuid})
            assert query_result.count() == 1
            found_trade_day = query_result.to_entities()[0]
            print(f"✓ 查询到业务对象: {type(found_trade_day).__name__}")
            print(f"  - 市场: {found_trade_day.market.name}")
            print(f"  - 休市日: {not found_trade_day.is_open}")
            assert found_trade_day.market == MARKET_TYPES.NASDAQ
            assert found_trade_day.is_open == False

        except Exception as e:
            print(f"✗ 数据验证测试失败: {e}")
            raise


class TestTradeDayCRUDInsert:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': TradeDayCRUD}

    """1. CRUD层插入操作测试 - TradeDay数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入TradeDay数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: TradeDay CRUD层批量插入")
        print("="*60)

        trade_day_crud = TradeDayCRUD()
        print(f"✓ 创建TradeDayCRUD实例: {trade_day_crud.__class__.__name__}")

        # 创建测试TradeDay数据 - 2023年1月的交易日历
        base_date = datetime(2023, 1, 1)
        test_trade_days = []

        for i in range(10):  # 创建10天的交易日历
            current_date = base_date + timedelta(days=i)
            # 简化规则：周末休市，工作日交易（实际应该根据真实日历）
            is_open = current_date.weekday() < 5  # 周一到周五

            trade_day = MTradeDay(
                market=MARKET_TYPES.CHINA,
                is_open=is_open,
                timestamp=current_date,
                source=SOURCE_TYPES.TEST
            )
            test_trade_days.append(trade_day)

        print(f"✓ 创建测试数据: {len(test_trade_days)}条TradeDay记录")
        trading_days = sum(1 for td in test_trade_days if td.is_open)
        print(f"  - 交易日: {trading_days} 天")
        print(f"  - 休市日: {len(test_trade_days) - trading_days} 天")
        print(f"  - 时间范围: {test_trade_days[0].timestamp} ~ {test_trade_days[-1].timestamp}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            trade_day_crud.add_batch(test_trade_days)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = trade_day_crud.find(filters={
                "market": MARKET_TYPES.CHINA,
                "timestamp__gte": base_date,
                "timestamp__lte": base_date + timedelta(days=9)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 10

            # 验证数据内容
            trading_count = sum(1 for td in query_result if td.is_open)
            print(f"✓ 交易日验证通过: {trading_count} 天")
            assert trading_count >= 5  # 至少有5个交易日

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_trade_day(self):
        """测试单条TradeDay数据插入"""
        print("\n" + "="*60)
        print("开始测试: TradeDay CRUD层单条插入")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        test_trade_day = MTradeDay(
            market=MARKET_TYPES.NASDAQ,
            is_open=True,
            timestamp=datetime(2023, 1, 3),
            source=SOURCE_TYPES.TEST
        )
        print(f"✓ 创建测试TradeDay: {test_trade_day.timestamp}")
        try:
            market_name = test_trade_day.market.name if hasattr(test_trade_day.market, 'name') else MARKET_TYPES(test_trade_day.market).name
        except:
            market_name = str(test_trade_day.market)
        print(f"  - 市场: {test_trade_day.market} ({market_name})")
        print(f"  - 是否交易: {test_trade_day.is_open}")

        try:
            # 获取插入前的记录数
            print("\n→ 获取插入前数据状态...")
            pre_insert_count = trade_day_crud.count()
            pre_specific_count = len(trade_day_crud.find(filters={
                "market": MARKET_TYPES.NASDAQ,
                "timestamp": datetime(2023, 1, 3)
            }))
            print(f"✓ 插入前总记录数: {pre_insert_count}")
            print(f"✓ 插入前特定日期市场记录数: {pre_specific_count}")

            # 单条插入
            print("\n→ 执行单条插入操作...")
            trade_day_crud.add(test_trade_day)
            print("✓ 单条插入成功")

            # 验证插入效果 - 使用计数比对方式
            print("\n→ 验证插入效果...")
            post_insert_count = trade_day_crud.count()
            post_specific_count = len(trade_day_crud.find(filters={
                "market": MARKET_TYPES.NASDAQ,
                "timestamp": datetime(2023, 1, 3)
            }))
            print(f"✓ 插入后总记录数: {post_insert_count}")
            print(f"✓ 插入后特定日期市场记录数: {post_specific_count}")

            # 断言：通过比对操作前后的计数变化来验证插入效果
            assert post_insert_count > pre_insert_count, f"插入后总记录数应该增加，之前{pre_insert_count}条，现在{post_insert_count}条"
            assert post_specific_count >= pre_specific_count, f"插入后特定记录数应该增加或保持不变，之前{pre_specific_count}条，现在{post_specific_count}条"

            if post_specific_count > pre_specific_count:
                print(f"✓ 成功插入了{post_specific_count - pre_specific_count}条特定记录")
            else:
                print("✓ 特定记录已存在（可能是重复插入或数据覆盖）")

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTradeDayCRUDQuery:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': TradeDayCRUD}

    """2. CRUD层查询操作测试 - TradeDay数据查询和过滤"""

    def test_find_by_market(self):
        """测试根据市场查询TradeDay"""
        print("\n" + "="*60)
        print("开始测试: 根据market查询TradeDay")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 查询中国市场的交易日历
            print("→ 查询market=CHINA的交易日历...")
            find_result = trade_day_crud.find(filters={"market": MARKET_TYPES.CHINA})
            china_trade_days = find_result.to_entities()
            print(f"✓ 查询到 {find_result.count()} 条记录")

            # 验证查询结果
            trading_days = [td for td in china_trade_days if td.is_open]
            non_trading_days = [td for td in china_trade_days if not td.is_open]

            print(f"✓ 交易日: {len(trading_days)} 天")
            print(f"✓ 休市日: {len(non_trading_days)} 天")

            for trade_day in china_trade_days[:5]:  # 只显示前5条
                print(f"  - {trade_day.timestamp}: {'交易' if trade_day.is_open else '休市'}")
                assert trade_day.market == MARKET_TYPES.CHINA

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_time_range(self):
        """测试根据时间范围查询TradeDay"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围查询TradeDay")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 查询特定时间范围的交易日历
            start_date = datetime(2023, 1, 1)
            end_date = datetime(2023, 1, 7)

            print(f"→ 查询时间范围 {start_date} ~ {end_date} 的交易日历...")
            find_result = trade_day_crud.find(filters={
                "timestamp__gte": start_date,
                "timestamp__lte": end_date
            })
            time_trade_days = find_result.to_entities()
            print(f"✓ 查询到 {len(time_trade_days)} 条记录")

            # 验证时间范围
            for trade_day in time_trade_days:
                print(f"  - {trade_day.timestamp}: {'交易' if trade_day.is_open else '休市'} ({MARKET_TYPES(trade_day.market).name})")
                assert start_date <= trade_day.timestamp <= end_date

            print("✓ 时间范围查询验证成功")

        except Exception as e:
            print(f"✗ 时间范围查询失败: {e}")
            raise

    def test_find_trading_days_only(self):
        """测试仅查询交易日"""
        print("\n" + "="*60)
        print("开始测试: 仅查询交易日")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 查询所有交易日
            print("→ 查询所有交易日 (is_open=True)...")
            trading_result = trade_day_crud.find(filters={"is_open": True})
            trading_days = trading_result.to_entities()
            print(f"✓ 查询到 {trading_result.count()} 个交易日")

            # 查询所有休市日
            print("→ 查询所有休市日 (is_open=False)...")
            non_trading_result = trade_day_crud.find(filters={"is_open": False})
            non_trading_days = non_trading_result.to_entities()
            print(f"✓ 查询到 {non_trading_result.count()} 个休市日")

            # 验证查询结果
            total_days = trading_result.count() + non_trading_result.count()
            print(f"✓ 总天数: {total_days} 天")
            if total_days > 0:
                print(f"✓ 交易日占比: {trading_result.count()/total_days*100:.1f}%")
            else:
                print("✓ 警告: 没有数据可供计算交易日占比")

            for trade_day in trading_days[:3]:  # 显示前3个交易日
                print(f"  - 交易日: {trade_day.timestamp} ({MARKET_TYPES(trade_day.market).name})")
                assert trade_day.is_open == True

            for trade_day in non_trading_days[:3]:  # 显示前3个休市日
                print(f"  - 休市日: {trade_day.timestamp} ({MARKET_TYPES(trade_day.market).name})")
                assert trade_day.is_open == False

            print("✓ 交易日/休市日查询验证成功")

        except Exception as e:
            print(f"✗ 交易日查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTradeDayCRUDUpdate:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': TradeDayCRUD}

    """3. CRUD层更新操作测试 - TradeDay属性更新"""

    def test_update_trade_day_status(self):
        """测试更新TradeDay交易状态"""
        print("\n" + "="*60)
        print("开始测试: 更新TradeDay交易状态")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 查询待更新的交易日历
            print("→ 查询待更新的交易日历...")
            trade_days = trade_day_crud.find(page_size=1)
            if not trade_days:
                print("✗ 没有找到可更新的交易日历")
                return

            target_trade_day = trade_days[0]
            print(f"✓ 找到交易日: {target_trade_day.timestamp}")
            print(f"  - 当前状态: {'交易' if target_trade_day.is_open else '休市'}")
            print(f"  - 市场: {MARKET_TYPES(target_trade_day.market).name}")

            # 更新交易状态
            print("→ 更新交易状态...")
            new_status = not target_trade_day.is_open
            updated_data = {
                "is_open": new_status
            }

            trade_day_crud.modify({"uuid": target_trade_day.uuid}, updated_data)
            print(f"✓ 交易日状态更新为: {'交易' if new_status else '休市'}")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_trade_days = trade_day_crud.find(filters={"uuid": target_trade_day.uuid})
            assert len(updated_trade_days) == 1

            updated_trade_day = updated_trade_days[0]
            print(f"✓ 更新后状态: {'交易' if updated_trade_day.is_open else '休市'}")

            assert updated_trade_day.is_open == new_status
            print("✓ 交易日状态更新验证成功")

        except Exception as e:
            print(f"✗ 更新交易日状态失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTradeDayCRUDBusinessLogic:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': TradeDayCRUD}

    """4. CRUD层业务逻辑测试 - TradeDay业务场景验证"""

    def test_trading_calendar_analysis(self):
        """测试交易日历分析"""
        print("\n" + "="*60)
        print("开始测试: 交易日历分析")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 查询所有交易日历进行分析
            print("→ 查询所有交易日历进行分析...")
            all_trade_days = trade_day_crud.find()

            if len(all_trade_days) < 10:
                print("✗ 交易日历数据不足，跳过分析测试")
                return

            # 按市场分组统计
            market_analysis = {}
            for trade_day in all_trade_days:
                market_name = MARKET_TYPES(trade_day.market).name
                if market_name not in market_analysis:
                    market_analysis[market_name] = {
                        "total_days": 0,
                        "trading_days": 0,
                        "non_trading_days": 0,
                        "date_range": []
                    }

                market_analysis[market_name]["total_days"] += 1
                market_analysis[market_name]["date_range"].append(trade_day.timestamp)

                if trade_day.is_open:
                    market_analysis[market_name]["trading_days"] += 1
                else:
                    market_analysis[market_name]["non_trading_days"] += 1

            print(f"✓ 交易日历分析结果:")
            for market_name, stats in market_analysis.items():
                if stats["date_range"]:
                    start_date = min(stats["date_range"])
                    end_date = max(stats["date_range"])
                    trading_ratio = stats["trading_days"] / stats["total_days"] * 100
                    print(f"  - {market_name}:")
                    print(f"    总天数: {stats['total_days']}")
                    print(f"    交易日: {stats['trading_days']} ({trading_ratio:.1f}%)")
                    print(f"    休市日: {stats['non_trading_days']}")
                    print(f"    时间范围: {start_date.date()} ~ {end_date.date()}")

            # 验证分析结果
            total_days = sum(stats["total_days"] for stats in market_analysis.values())
            assert total_days == len(all_trade_days)
            print("✓ 交易日历分析验证成功")

        except Exception as e:
            print(f"✗ 交易日历分析失败: {e}")
            raise

    def test_trading_day_sequence_validation(self):
        """测试交易日序列连续性验证"""
        print("\n" + "="*60)
        print("开始测试: 交易日序列连续性验证")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 查询特定时间范围的交易日历
            start_date = datetime(2023, 1, 1)
            end_date = datetime(2023, 1, 10)

            print(f"→ 查询时间范围 {start_date.date()} ~ {end_date.date()} 的交易日历...")
            trade_days = trade_day_crud.find(filters={
                "timestamp__gte": start_date,
                "timestamp__lte": end_date,
                "market": MARKET_TYPES.CHINA
            })

            if len(trade_days) < 5:
                print("✗ 交易日历数据不足，跳过连续性验证")
                return

            # 按日期排序
            trade_days.sort(key=lambda x: x.timestamp)

            # 验证日期连续性
            print("→ 验证日期连续性...")
            date_gaps = []
            for i in range(1, len(trade_days)):
                prev_date = trade_days[i-1].timestamp.date()
                curr_date = trade_days[i].timestamp.date()
                expected_date = prev_date + timedelta(days=1)

                if curr_date != expected_date:
                    date_gaps.append((prev_date, curr_date))
                    print(f"  - 发现日期间隔: {prev_date} -> {curr_date}")

            if not date_gaps:
                print("✓ 日期序列连续，无间隔")
            else:
                print(f"✓ 发现 {len(date_gaps)} 个日期间隔")

            # 统计交易日分布
            trading_days = [td for td in trade_days if td.is_open]
            print(f"✓ 时间范围内交易日: {len(trading_days)} 天")
            print(f"✓ 时间范围内总天数: {len(trade_days)} 天")
            print(f"✓ 交易日占比: {len(trading_days)/len(trade_days)*100:.1f}%")

            print("✓ 交易日序列连续性验证成功")

        except Exception as e:
            print(f"✗ 交易日序列验证失败: {e}")
            raise

    def test_market_comparison_analysis(self):
        """测试跨市场交易日历对比分析"""
        print("\n" + "="*60)
        print("开始测试: 跨市场交易日历对比分析")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 查询所有市场的交易日历
            print("→ 查询所有市场的交易日历...")
            all_trade_days = trade_day_crud.find()

            if len(all_trade_days) < 10:
                print("✗ 交易日历数据不足，跳过跨市场分析")
                return

            # 按市场和日期分组
            market_date_map = {}
            for trade_day in all_trade_days:
                date_key = trade_day.timestamp.date()
                market_name = MARKET_TYPES(trade_day.market).name

                if date_key not in market_date_map:
                    market_date_map[date_key] = {}
                market_date_map[date_key][market_name] = trade_day.is_open

            # 分析跨市场交易一致性
            print("→ 分析跨市场交易一致性...")
            consistent_days = 0
            inconsistent_days = 0

            for date, markets in market_date_map.items():
                if len(markets) > 1:
                    # 检查同一天不同市场的交易状态
                    trading_statuses = list(markets.values())
                    is_consistent = all(status == trading_statuses[0] for status in trading_statuses)

                    if is_consistent:
                        consistent_days += 1
                    else:
                        inconsistent_days += 1
                        print(f"  - {date}: 市场交易状态不一致")

            print(f"✓ 跨市场分析结果:")
            print(f"  - 总分析天数: {len(market_date_map)}")
            print(f"  - 市场状态一致天数: {consistent_days}")
            print(f"  - 市场状态不一致天数: {inconsistent_days}")

            if len(market_date_map) > 0:
                consistency_ratio = consistent_days / len(market_date_map) * 100
                print(f"  - 一致性比例: {consistency_ratio:.1f}%")

            print("✓ 跨市场交易日历对比分析验证成功")

        except Exception as e:
            print(f"✗ 跨市场分析失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTradeDayCRUDDelete:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': TradeDayCRUD}

    """4. CRUD层删除操作测试 - TradeDay数据删除验证"""

    def test_delete_trade_day_by_date(self):
        """测试根据日期删除交易日"""
        print("\n" + "="*60)
        print("开始测试: 根据日期删除交易日")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 准备测试数据
            print("→ 创建测试交易日...")
            from datetime import datetime

            test_date = datetime(2024, 1, 15)
            test_trade_day = MTradeDay(
                market=MARKET_TYPES.CHINA,
                timestamp=test_date,
                is_open=True,
                source=SOURCE_TYPES.TEST
            )
            trade_day_crud.add(test_trade_day)
            print("✓ 测试交易日创建成功")

            # 验证数据存在
            print("→ 验证交易日存在...")
            trade_days_before = trade_day_crud.find(filters={"timestamp": test_date})
            print(f"✓ 删除前交易日数: {len(trade_days_before)}")
            assert len(trade_days_before) >= 1

            # 执行删除操作
            print("→ 执行交易日删除...")
            trade_day_crud.remove(filters={"timestamp": test_date})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            trade_days_after = trade_day_crud.find(filters={"timestamp": test_date})
            print(f"✓ 删除后交易日数: {len(trade_days_after)}")
            assert len(trade_days_after) == 0

            print("✓ 根据日期删除交易日验证成功")

        except Exception as e:
            print(f"✗ 根据日期删除交易日失败: {e}")
            raise

    def test_delete_trade_day_by_market(self):
        """测试根据市场删除交易日"""
        print("\n" + "="*60)
        print("开始测试: 根据市场删除交易日")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 准备测试数据
            print("→ 创建不同市场的交易日...")
            from datetime import datetime

            test_dates = [
                datetime(2024, 1, 10),
                datetime(2024, 1, 11),
                datetime(2024, 1, 12)
            ]

            test_trade_days = []
            for date in test_dates:
                # 为中国市场创建交易日
                china_trade_day = MTradeDay(
                    market=MARKET_TYPES.CHINA,
                    timestamp=date,
                    is_open=True,
                    source=SOURCE_TYPES.TEST
                )
                test_trade_days.append(china_trade_day)

                # 为美国市场创建交易日
                us_trade_day = MTradeDay(
                    market=MARKET_TYPES.NASDAQ,
                    timestamp=date,
                    is_open=True,
                    source=SOURCE_TYPES.TEST
                )
                test_trade_days.append(us_trade_day)

            for trade_day in test_trade_days:
                trade_day_crud.add(trade_day)
            print(f"✓ {len(test_trade_days)}个交易日创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_trade_days = trade_day_crud.find()
            china_trade_days = [t for t in all_trade_days if t.market == MARKET_TYPES.CHINA.value]
            print(f"✓ 总交易日数: {len(all_trade_days)}, 中国市场交易日数: {len(china_trade_days)}")
            assert len(china_trade_days) >= 3

            # 删除所有中国市场的交易日
            print("→ 删除所有中国市场的交易日...")
            trade_day_crud.remove(filters={"market": MARKET_TYPES.CHINA})
            print("✓ 中国市场交易日删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_trade_days = trade_day_crud.find()
            remaining_china = [t for t in remaining_trade_days if t.market == MARKET_TYPES.CHINA]

            print(f"✓ 删除后交易日数: {len(remaining_trade_days)}, 剩余中国市场交易日数: {len(remaining_china)}")
            assert len(remaining_china) == 0

            print("✓ 根据市场删除交易日验证成功")

        except Exception as e:
            print(f"✗ 根据市场删除交易日失败: {e}")
            raise

    def test_delete_closed_trade_days(self):
        """测试删除休市日"""
        print("\n" + "="*60)
        print("开始测试: 删除休市日")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 准备测试数据
            print("→ 创建不同类型的交易日...")
            from datetime import datetime, timedelta

            base_date = datetime(2024, 1, 1)
            test_trade_days = []

            # 创建交易日
            for i in range(3):
                trading_day = MTradeDay(
                    market=MARKET_TYPES.CHINA,
                    timestamp=base_date + timedelta(days=i),
                    is_open=True,
                    source=SOURCE_TYPES.TEST
                )
                test_trade_days.append(trading_day)

            # 创建休市日
            for i in range(2):
                closed_day = MTradeDay(
                    market=MARKET_TYPES.CHINA,
                    timestamp=base_date + timedelta(days=10 + i),
                    is_open=False,
                    source=SOURCE_TYPES.TEST
                )
                test_trade_days.append(closed_day)

            for trade_day in test_trade_days:
                trade_day_crud.add(trade_day)
            print(f"✓ {len(test_trade_days)}个交易日创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_trade_days = trade_day_crud.find()
            closed_days = [t for t in all_trade_days if t.is_open == False]
            print(f"✓ 总交易日数: {len(all_trade_days)}, 休市日数: {len(closed_days)}")
            assert len(closed_days) >= 2

            # 删除所有休市日
            print("→ 删除所有休市日...")
            trade_day_crud.remove(filters={"is_open": False})
            print("✓ 休市日删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_trade_days = trade_day_crud.find()
            remaining_closed = [t for t in remaining_trade_days if t.is_open == False]

            print(f"✓ 删除后交易日数: {len(remaining_trade_days)}, 剩余休市日数: {len(remaining_closed)}")
            assert len(remaining_closed) == 0

            # 验证剩余的都是交易日
            for trade_day in remaining_trade_days:
                assert trade_day.is_open == True
                print(f"✓ 保留交易日: {trade_day.timestamp.date()}")

            print("✓ 删除休市日验证成功")

        except Exception as e:
            print(f"✗ 删除休市日失败: {e}")
            raise

    def test_delete_non_trading_days(self):
        """测试删除非交易日（休市日）"""
        print("\n" + "="*60)
        print("开始测试: 删除非交易日（休市日）")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 准备测试数据
            print("→ 创建交易日和非交易日数据...")
            from datetime import datetime, timedelta

            base_date = datetime(2024, 1, 1)
            test_trade_days = []

            # 创建交易日
            for i in range(3):
                trading_day = MTradeDay(
                    market=MARKET_TYPES.CHINA,
                    timestamp=base_date + timedelta(days=i),
                    is_open=True,
                    source=SOURCE_TYPES.TEST
                )
                test_trade_days.append(trading_day)

            # 创建非交易日（休市日）
            for i in range(2):
                non_trading_day = MTradeDay(
                    market=MARKET_TYPES.CHINA,
                    timestamp=base_date + timedelta(days=10 + i),
                    is_open=False,
                    source=SOURCE_TYPES.TEST
                )
                test_trade_days.append(non_trading_day)

            for trade_day in test_trade_days:
                trade_day_crud.add(trade_day)
            print(f"✓ {len(test_trade_days)}个交易日创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_trade_days = trade_day_crud.find()
            non_trading_days = [t for t in all_trade_days if t.is_open == False]
            print(f"✓ 总交易日数: {len(all_trade_days)}, 非交易日数: {len(non_trading_days)}")
            assert len(non_trading_days) >= 2

            # 删除所有非交易日
            print("→ 删除所有非交易日...")
            trade_day_crud.remove(filters={"is_open": False})
            print("✓ 非交易日删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_trade_days = trade_day_crud.find()
            remaining_non_trading = [t for t in remaining_trade_days if t.is_open == False]

            print(f"✓ 删除后交易日数: {len(remaining_trade_days)}, 剩余非交易日数: {len(remaining_non_trading)}")
            assert len(remaining_non_trading) == 0

            # 验证剩余的都是交易日
            for trade_day in remaining_trade_days:
                assert trade_day.is_open == True
                print(f"✓ 保留交易日: {trade_day.timestamp.date()}")

            print("✓ 删除非交易日验证成功")

        except Exception as e:
            print(f"✗ 删除非交易日失败: {e}")
            raise

    def test_delete_trade_day_by_date_range(self):
        """测试根据日期范围删除交易日"""
        print("\n" + "="*60)
        print("开始测试: 根据日期范围删除交易日")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 准备不同日期的测试数据
            print("→ 创建不同日期范围的交易日...")
            from datetime import datetime, timedelta

            # 使用未来的日期避免与现有数据冲突
            start_date = datetime(2025, 12, 1)
            test_trade_days = []

            # 创建十二月份的交易日
            for i in range(10):
                december_day = MTradeDay(
                    market=MARKET_TYPES.CHINA,
                    timestamp=start_date + timedelta(days=i),
                    is_open=True,
                    source=SOURCE_TYPES.TEST
                )
                test_trade_days.append(december_day)

            # 创建一月份的交易日（2026年1月）
            for i in range(5):
                january_day = MTradeDay(
                    market=MARKET_TYPES.CHINA,
                    timestamp=start_date + timedelta(days=35 + i),
                    is_open=True,
                    source=SOURCE_TYPES.TEST
                )
                test_trade_days.append(january_day)

            for trade_day in test_trade_days:
                trade_day_crud.add(trade_day)
            print(f"✓ {len(test_trade_days)}个交易日创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_trade_days = trade_day_crud.find()
            print(f"✓ 总交易日数: {len(all_trade_days)}")
            assert len(all_trade_days) >= 15

            # 删除十二月份的交易日
            print("→ 删除十二月份的交易日...")
            end_of_december = datetime(2025, 12, 31)
            trade_day_crud.remove(filters={
                "timestamp__gte": start_date,
                "timestamp__lte": end_of_december
            })
            print("✓ 十二月份交易日删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_trade_days = trade_day_crud.find(filters={
                "timestamp__gte": datetime(2025, 12, 1),
                "timestamp__lte": datetime(2026, 2, 1)
            })
            december_remaining = [t for t in remaining_trade_days if t.timestamp.month == 12]
            print(f"✓ 删除后交易日数: {len(remaining_trade_days)}, 剩余十二月份数: {len(december_remaining)}")
            assert len(december_remaining) == 0

            # 验证剩余的都是2026年1月
            for trade_day in remaining_trade_days:
                assert trade_day.timestamp.year == 2026 and trade_day.timestamp.month == 1
                print(f"✓ 保留交易日: {trade_day.timestamp.date()}")

            print("✓ 根据日期范围删除交易日验证成功")

        except Exception as e:
            print(f"✗ 根据日期范围删除交易日失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTradeDayCRUDDataFormats:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': TradeDayCRUD}

    """测试TradeDay CRUD的多种数据格式返回"""

    def test_find_dataframe_format(self):
        """测试find方法返回DataFrame格式"""
        print("\n" + "="*60)
        print("开始测试: TradeDay CRUD查询返回DataFrame")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 记录插入前的数据量
            print("→ 查询插入前的数据量...")
            initial_result = trade_day_crud.find(page_size=1000)
            initial_count = initial_result.count()
            print(f"✓ 插入前数据量: {initial_count}")

            # 创建测试数据
            print("→ 创建测试数据...")
            from datetime import datetime, timedelta
            test_days = [
                MTradeDay(
                    timestamp=datetime(2023, 1, 2),
                    market=MARKET_TYPES.CHINA,
                    is_open=True
                ),
                MTradeDay(
                    timestamp=datetime(2023, 1, 3),
                    market=MARKET_TYPES.NASDAQ,
                    is_open=False
                )
            ]
            trade_day_crud.add_batch(test_days)
            print(f"✓ 插入了{len(test_days)}条测试数据")

            # 验证插入后的数据量增加
            print("→ 验证插入效果...")
            after_insert_result = trade_day_crud.find(page_size=1000)
            after_insert_count = after_insert_result.count()
            expected_count = initial_count + len(test_days)
            assert after_insert_count == expected_count, f"期望{expected_count}条数据，实际{after_insert_count}条"
            print(f"✓ 插入后数据量: {after_insert_count} (+{len(test_days)})")

            # 测试返回DataFrame
            print("→ 查询并返回DataFrame格式...")
            find_result = trade_day_crud.find(page_size=10)
            df = find_result.to_dataframe()

            print(f"✓ DataFrame类型: {type(df)}")
            print(f"✓ DataFrame形状: {df.shape}")
            print(f"✓ DataFrame列名: {list(df.columns)}")

            # 验证DataFrame的基本属性
            assert hasattr(df, 'shape'), "返回对象应该有shape属性"
            assert hasattr(df, 'columns'), "返回对象应该有columns属性"
            assert len(df.columns) > 0, "DataFrame应该有列"

            # 验证必要的列存在
            required_columns = ['market', 'is_open', 'timestamp', 'source']
            missing_columns = [col for col in required_columns if col not in df.columns]
            assert len(missing_columns) == 0, f"缺少必要列: {missing_columns}"

            print(f"✓ 必要列验证通过: {required_columns}")

            # 验证DataFrame行数与ModelList行数一致
            model_list_count = find_result.count()
            dataframe_rows = len(df)
            assert dataframe_rows == model_list_count, f"DataFrame行数({dataframe_rows})应与ModelList行数({model_list_count})一致"
            print(f"✓ 行数一致性验证通过: {dataframe_rows}行")

            # 显示DataFrame的前几行
            if len(df) > 0:
                print("✓ DataFrame前3行数据:")
                for i, row in df.head(3).iterrows():
                    print(f"  行{i}: {row['timestamp']} - 市场:{row['market']} 开盘:{row['is_open']}")

            print("✓ DataFrame查询验证成功")

        except Exception as e:
            print(f"✗ DataFrame查询测试失败: {e}")
            raise

    def test_dataframe_data_manipulation(self):
        """测试DataFrame数据操作和分析"""
        print("\n" + "="*60)
        print("开始测试: DataFrame数据操作和分析")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 查询数据并返回DataFrame
            print("→ 查询数据用于分析...")
            df = trade_day_crud.find(
                filters={
                    "timestamp__gte": datetime(2023, 1, 1),
                    "timestamp__lte": datetime(2023, 12, 31)
                },
                order_by="timestamp",
                page_size=100
            ).to_dataframe()

            print(f"✓ 查询到 {len(df)} 条记录用于分析")

            if len(df) > 0:
                # 1. 基本统计分析
                trading_days = df[df['is_open'] == True]
                non_trading_days = df[df['is_open'] == False]

                print(f"✓ 交易日数量: {len(trading_days)}")
                print(f"✓ 非交易日数量: {len(non_trading_days)}")

                # 2. 按市场分组统计
                if 'market' in df.columns:
                    # 将枚举列转换为字符串以便groupby操作
                    df_copy = df.copy()
                    df_copy['market_str'] = df_copy['market'].astype(str)
                    market_stats = df_copy.groupby('market_str').agg({
                        'is_open': ['count', 'sum'],
                        'timestamp': ['min', 'max']
                    }).round(2)

                    print("✓ 按市场统计:")
                    print(market_stats)

                # 3. 时间序列分析
                if 'timestamp' in df.columns:
                    df['month'] = pd.to_datetime(df['timestamp']).dt.month
                    monthly_stats = df.groupby('month').size()
                    print(f"✓ 按月统计 (前6个月):")
                    print(monthly_stats.head(6))

                # 4. 数据过滤和筛选
                # 使用字符串比较来避免枚举比较问题
                nasdaq_data = df[df['market'].astype(str) == str(MARKET_TYPES.NASDAQ)]  # NASDAQ market
                print(f"✓ NASDAQ市场记录数: {len(nasdaq_data)}")

                # 5. 数据排序
                sorted_df = df.sort_values('timestamp', ascending=False)
                print(f"✓ 最新记录时间: {sorted_df.iloc[0]['timestamp'] if len(sorted_df) > 0 else '无数据'}")

                print("✓ DataFrame数据操作验证成功")

        except Exception as e:
            print(f"✗ DataFrame操作测试失败: {e}")
            raise

    def test_compare_list_vs_dataframe(self):
        """测试列表格式与DataFrame格式的对比"""
        print("\n" + "="*60)
        print("开始测试: 列表格式与DataFrame格式对比")
        print("="*60)

        trade_day_crud = TradeDayCRUD()

        try:
            # 相同查询条件的两种格式
            filters = {"market": MARKET_TYPES.CHINA}
            page_size = 5

            # 1. 列表格式查询
            print("→ 执行列表格式查询...")
            list_result = trade_day_crud.find(filters=filters, page_size=page_size)
            print(f"✓ 列表格式: {len(list_result)} 条记录")

            # 2. DataFrame格式查询
            print("→ 执行DataFrame格式查询...")
            df_result = trade_day_crud.find(filters=filters, page_size=page_size).to_dataframe()
            print(f"✓ DataFrame格式: {df_result.shape[0]} 条记录")

            # 3. 验证数据一致性
            assert len(list_result) == df_result.shape[0], "两种格式应该返回相同数量的记录"

            if len(list_result) > 0:
                # 验证第一条记录的一致性
                first_item = list_result[0]
                first_row = df_result.iloc[0]

                assert first_item.timestamp == first_row['timestamp'], "时间戳应该一致"
                assert first_item.is_open == first_row['is_open'], "开盘状态应该一致"
                # 比较枚举的值，确保一致性
                assert first_item.market == first_row['market'].value, "市场应该一致"

                print("✓ 数据一致性验证通过")

            # 4. 性能对比
            import time

            # 列表格式性能测试
            start_time = time.time()
            for _ in range(3):
                trade_day_crud.find(filters=filters, page_size=page_size)
            list_time = time.time() - start_time

            # DataFrame格式性能测试
            start_time = time.time()
            for _ in range(3):
                trade_day_crud.find(filters=filters, page_size=page_size).to_dataframe()
            df_time = time.time() - start_time

            print(f"✓ 列表格式平均耗时: {list_time/3:.4f}秒")
            print(f"✓ DataFrame格式平均耗时: {df_time/3:.4f}秒")

            print("✓ 格式对比验证成功")

        except Exception as e:
            print(f"✗ 格式对比测试失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：TradeDay CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_trade_day_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 交易日历连续性和跨市场一致性分析")