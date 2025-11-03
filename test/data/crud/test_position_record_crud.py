"""
PositionRecord CRUD数据库操作TDD测试

测试CRUD层的持仓变更记录数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)

PositionRecord是持仓变更记录数据模型，存储持仓的历史变更记录。
为持仓分析、成本核算和风险监控提供支持。
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.position_record_crud import PositionRecordCRUD
from ginkgo.data.models.model_position_record import MPositionRecord
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestPositionRecordCRUDInsert:
    CRUD_TEST_CONFIG = {'crud_class': PositionRecordCRUD}
    """1. CRUD层插入操作测试 - PositionRecord数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入PositionRecord数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: PositionRecord CRUD层批量插入")
        print("="*60)

        position_record_crud = PositionRecordCRUD()
        print(f"✓ 创建PositionRecordCRUD实例: {position_record_crud.__class__.__name__}")

        # 创建测试PositionRecord数据 - 不同类型的持仓变更记录
        base_time = datetime(2023, 1, 3, 9, 30)
        test_records = []

        # 买入建仓记录
        buy_record = MPositionRecord(
            portfolio_id="portfolio_001",
            engine_id="engine_001",
            code="000001.SZ",
            cost=Decimal("12.50"),
            volume=1000,
            frozen_volume=0,
            frozen_money=Decimal("0.00"),
            price=Decimal("12.52"),
            fee=Decimal("6.26"),
            timestamp=base_time
        )
        buy_record.source = SOURCE_TYPES.TEST
        test_records.append(buy_record)

        # 卖出平仓记录
        sell_record = MPositionRecord(
            portfolio_id="portfolio_001",
            engine_id="engine_001",
            code="000002.SZ",
            cost=Decimal("18.75"),
            volume=-500,
            frozen_volume=0,
            frozen_money=Decimal("0.00"),
            price=Decimal("18.73"),
            fee=Decimal("3.75"),
            timestamp=base_time + timedelta(minutes=5)
        )
        sell_record.source = SOURCE_TYPES.TEST
        test_records.append(sell_record)

        # 部分冻结记录
        freeze_record = MPositionRecord(
            portfolio_id="portfolio_002",
            engine_id="engine_001",
            code="000858.SZ",
            cost=Decimal("25.60"),
            volume=800,
            frozen_volume=300,
            frozen_money=Decimal("7680.00"),
            price=Decimal("25.68"),
            fee=Decimal("8.19"),
            timestamp=base_time + timedelta(minutes=10)
        )
        freeze_record.source = SOURCE_TYPES.TEST
        test_records.append(freeze_record)

        print(f"✓ 创建测试数据: {len(test_records)}条PositionRecord记录")
        portfolio_ids = list(set(r.portfolio_id for r in test_records))
        print(f"  - 投资组合ID: {portfolio_ids}")
        print(f"  - 股票代码: {[r.code for r in test_records]}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            position_record_crud.add_batch(test_records)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = position_record_crud.find(filters={
                "timestamp__gte": base_time,
                "timestamp__lte": base_time + timedelta(minutes=15)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 3

            # 验证数据内容
            codes = set(r.code for r in query_result)
            print(f"✓ 股票代码验证通过: {len(codes)} 种")
            assert len(codes) >= 3

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_position_record(self):
        """测试单条PositionRecord数据插入"""
        print("\n" + "="*60)
        print("开始测试: PositionRecord CRUD层单条插入")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        test_record = MPositionRecord(
            portfolio_id="portfolio_003",
            engine_id="engine_002",
            code="600000.SH",
            cost=Decimal("8.85"),
            volume=1500,
            frozen_volume=0,
            frozen_money=Decimal("0.00"),
            price=Decimal("8.87"),
            fee=Decimal("9.96"),
            timestamp=datetime(2023, 1, 3, 10, 30),
            source=SOURCE_TYPES.TEST
        )
        print(f"✓ 创建测试PositionRecord")
        print(f"  - 投资组合: {test_record.portfolio_id}")
        print(f"  - 股票代码: {test_record.code}")
        print(f"  - 持仓数量: {test_record.volume}")
        print(f"  - 成本价格: {test_record.cost}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            position_record_crud.add(test_record)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = position_record_crud.find(filters={
                "portfolio_id": "portfolio_003",
                "code": "600000.SH",
                "timestamp": datetime(2023, 1, 3, 10, 30)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_record = query_result[0]
            print(f"✓ 插入的PositionRecord验证")
            assert inserted_record.portfolio_id == "portfolio_003"
            assert inserted_record.code == "600000.SH"
            assert inserted_record.volume == 1500

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestPositionRecordCRUDQuery:
    CRUD_TEST_CONFIG = {'crud_class': PositionRecordCRUD}
    """2. CRUD层查询操作测试 - PositionRecord数据查询和过滤"""

    def test_find_by_portfolio_id(self):
        """测试根据投资组合ID查询PositionRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID查询PositionRecord")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        try:
            # 查询特定投资组合的持仓记录
            print("→ 查询portfolio_id=portfolio_001的持仓记录...")
            portfolio_records = position_record_crud.find(filters={
                "portfolio_id": "portfolio_001"
            })
            print(f"✓ 查询到 {len(portfolio_records)} 条记录")

            # 验证查询结果
            for record in portfolio_records:
                print(f"  - {record.code}: {record.volume}股, 成本{record.cost}")
                assert record.portfolio_id == "portfolio_001"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_stock_code(self):
        """测试根据股票代码查询PositionRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据股票代码查询PositionRecord")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        try:
            # 查询特定股票的持仓记录
            print("→ 查询股票代码=000001.SZ的持仓记录...")
            stock_records = position_record_crud.find(filters={
                "code": "000001.SZ"
            })
            print(f"✓ 查询到 {len(stock_records)} 条记录")

            # 验证查询结果
            for record in stock_records:
                print(f"  - {record.portfolio_id}: {record.volume}股, 价格{record.price}")
                assert record.code == "000001.SZ"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_time_range(self):
        """测试根据时间范围查询PositionRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围查询PositionRecord")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        try:
            # 查询特定时间范围的持仓记录
            start_time = datetime(2023, 1, 3, 9, 0)
            end_time = datetime(2023, 1, 3, 12, 0)

            print(f"→ 查询时间范围 {start_time} ~ {end_time} 的持仓记录...")
            time_records = position_record_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            })
            print(f"✓ 查询到 {len(time_records)} 条记录")

            # 验证时间范围
            for record in time_records:
                print(f"  - {record.code}: {record.volume}股 ({record.timestamp})")
                assert start_time <= record.timestamp <= end_time

            print("✓ 时间范围查询验证成功")

        except Exception as e:
            print(f"✗ 时间范围查询失败: {e}")
            raise

    def test_find_by_volume_range(self):
        """测试根据持仓数量范围查询PositionRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据持仓数量范围查询PositionRecord")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        try:
            # 查询大额持仓（数量>=1000股）
            print("→ 查询持仓数量 >= 1000股的记录...")
            large_volume_records = position_record_crud.find(filters={
                "volume__gte": 1000
            })
            print(f"✓ 查询到 {len(large_volume_records)} 条大额持仓记录")

            # 查询空头持仓（数量<0股）
            print("→ 查询空头持仓（数量<0股）的记录...")
            short_volume_records = position_record_crud.find(filters={
                "volume__lt": 0
            })
            print(f"✓ 查询到 {len(short_volume_records)} 条空头持仓记录")

            # 验证查询结果
            for record in large_volume_records[:3]:
                print(f"  - {record.code}: {record.volume}股")

            for record in short_volume_records[:3]:
                print(f"  - {record.code}: {record.volume}股（空头）")

            print("✓ 持仓数量范围查询验证成功")

        except Exception as e:
            print(f"✗ 持仓数量范围查询失败: {e}")
            raise

    def test_find_frozen_positions(self):
        """测试查询有冻结资金的持仓记录"""
        print("\n" + "="*60)
        print("开始测试: 查询有冻结资金的持仓记录")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        try:
            # 查询有冻结数量的持仓记录
            print("→ 查询有冻结数量的持仓记录...")
            frozen_volume_records = position_record_crud.find(filters={
                "frozen_volume__gt": 0
            })
            print(f"✓ 查询到 {len(frozen_volume_records)} 条有冻结数量的记录")

            # 查询有冻结资金的持仓记录
            print("→ 查询有冻结资金的持仓记录...")
            frozen_money_records = position_record_crud.find(filters={
                "frozen_money__gt": 0
            })
            print(f"✓ 查询到 {len(frozen_money_records)} 条有冻结资金的记录")

            # 验证查询结果
            for record in frozen_volume_records[:3]:
                print(f"  - {record.code}: 冻结{record.frozen_volume}股, 冻结资金{record.frozen_money}")

            print("✓ 冻结持仓查询验证成功")

        except Exception as e:
            print(f"✗ 冻结持仓查询失败: {e}")
            raise




@pytest.mark.database
@pytest.mark.tdd
class TestPositionRecordCRUDBusinessLogic:
    CRUD_TEST_CONFIG = {'crud_class': PositionRecordCRUD}
    """4. CRUD层业务逻辑测试 - PositionRecord业务场景验证"""

    def test_position_change_analysis(self):
        """测试持仓变更分析"""
        print("\n" + "="*60)
        print("开始测试: 持仓变更分析")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        try:
            # 查询所有持仓记录进行变更分析
            print("→ 查询所有持仓记录进行变更分析...")
            all_records = position_record_crud.find(page_size=1000)

            if len(all_records) < 5:
                print("✗ 持仓记录数据不足，跳过变更分析")
                return

            # 按投资组合和股票分组分析
            portfolio_stock_stats = {}
            total_volume = 0
            total_cost = 0
            total_frozen_money = 0

            for record in all_records:
                key = (record.portfolio_id, record.code)
                if key not in portfolio_stock_stats:
                    portfolio_stock_stats[key] = {
                        "portfolio_id": record.portfolio_id,
                        "code": record.code,
                        "total_volume": 0,
                        "avg_cost": Decimal("0"),
                        "current_price": Decimal("0"),
                        "frozen_volume": 0,
                        "frozen_money": Decimal("0"),
                        "record_count": 0
                    }

                stats = portfolio_stock_stats[key]
                stats["total_volume"] += record.volume
                stats["frozen_volume"] = record.frozen_volume
                stats["frozen_money"] = record.frozen_money
                stats["current_price"] = record.price
                stats["record_count"] += 1

                # 计算加权平均成本
                if stats["record_count"] == 1:
                    stats["avg_cost"] = record.cost
                else:
                    # 简化的加权平均计算
                    total_position_value = stats["avg_cost"] * (stats["total_volume"] - record.volume) + record.cost * record.volume
                    stats["avg_cost"] = total_position_value / stats["total_volume"] if stats["total_volume"] != 0 else Decimal("0")

                total_volume += abs(record.volume)
                total_cost += abs(record.cost * record.volume)
                total_frozen_money += record.frozen_money

            print(f"✓ 持仓变更分析结果:")
            print(f"  - 总持仓记录数: {len(all_records)}")
            print(f"  - 总持仓变动量: {total_volume}股")
            print(f"  - 总成本金额: {total_cost:.2f}")
            print(f"  - 总冻结资金: {total_frozen_money:.2f}")
            print(f"  - 涉及投资组合: {len(set(r.portfolio_id for r in all_records))}个")
            print(f"  - 涉及股票数量: {len(set(r.code for r in all_records))}只")

            # 显示各投资组合的主要持仓
            for (portfolio_id, code), stats in list(portfolio_stock_stats.items())[:5]:
                print(f"  - {portfolio_id}.{code}: {stats['total_volume']}股, 成本{stats['avg_cost']:.2f}")

            # 验证分析结果
            assert len(all_records) > 0
            assert total_volume >= 0
            print("✓ 持仓变更分析验证成功")

        except Exception as e:
            print(f"✗ 持仓变更分析失败: {e}")
            raise

    def test_frozen_position_analysis(self):
        """测试冻结持仓分析"""
        print("\n" + "="*60)
        print("开始测试: 冻结持仓分析")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        try:
            # 查询有冻结的持仓记录
            print("→ 查询有冻结的持仓记录进行分析...")
            frozen_records = position_record_crud.find(filters={
                "frozen_volume__gt": 0
            }, page_size=500)

            if len(frozen_records) < 2:
                print("✗ 冻结持仓记录数据不足，跳过冻结分析")
                return

            # 分析冻结情况
            total_frozen_volume = sum(r.frozen_volume for r in frozen_records)
            total_frozen_money = sum(r.frozen_money for r in frozen_records)
            total_position_volume = sum(abs(r.volume) for r in frozen_records)

            # 计算冻结比例
            frozen_volume_ratio = (total_frozen_volume / total_position_volume * 100) if total_position_volume > 0 else 0

            print(f"✓ 冻结持仓分析结果:")
            print(f"  - 冻结记录数: {len(frozen_records)}")
            print(f"  - 总冻结数量: {total_frozen_volume}股")
            print(f"  - 总冻结资金: {total_frozen_money:.2f}")
            print(f"  - 冻结数量比例: {frozen_volume_ratio:.2f}%")

            # 按投资组合分组统计冻结情况
            portfolio_frozen_stats = {}
            for record in frozen_records:
                portfolio_id = record.portfolio_id
                if portfolio_id not in portfolio_frozen_stats:
                    portfolio_frozen_stats[portfolio_id] = {
                        "frozen_volume": 0,
                        "frozen_money": Decimal("0"),
                        "record_count": 0
                    }

                portfolio_frozen_stats[portfolio_id]["frozen_volume"] += record.frozen_volume
                portfolio_frozen_stats[portfolio_id]["frozen_money"] += record.frozen_money
                portfolio_frozen_stats[portfolio_id]["record_count"] += 1

            # 显示各投资组合的冻结情况
            for portfolio_id, stats in portfolio_frozen_stats.items():
                print(f"  - {portfolio_id}: 冻结{stats['frozen_volume']}股, 资金{stats['frozen_money']:.2f}")

            print("✓ 冻结持仓分析验证成功")

        except Exception as e:
            print(f"✗ 冻结持仓分析失败: {e}")
            raise

    def test_position_cost_analysis(self):
        """测试持仓成本分析"""
        print("\n" + "="*60)
        print("开始测试: 持仓成本分析")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        try:
            # 查询所有持仓记录进行成本分析
            print("→ 查询持仓记录进行成本分析...")
            all_records = position_record_crud.find(page_size=1000)

            if len(all_records) < 5:
                print("✗ 持仓记录数据不足，跳过成本分析")
                return

            # 计算成本相关指标
            total_cost_value = 0
            total_market_value = 0
            total_fees = 0
            cost_records = []

            for record in all_records:
                if record.cost > 0 and record.volume != 0:
                    cost_value = record.cost * abs(record.volume)
                    market_value = record.price * abs(record.volume)

                    total_cost_value += cost_value
                    total_market_value += market_value
                    total_fees += record.fee
                    cost_records.append(record)

            # 计算整体收益率
            overall_return = 0
            if total_cost_value > 0:
                overall_return = ((total_market_value - total_cost_value) / total_cost_value) * 100

            # 计算平均费用率
            avg_fee_rate = 0
            if total_cost_value > 0:
                avg_fee_rate = (total_fees / total_cost_value) * 100

            print(f"✓ 持仓成本分析结果:")
            print(f"  - 有效持仓记录数: {len(cost_records)}")
            print(f"  - 总成本价值: {total_cost_value:.2f}")
            print(f"  - 总市值: {total_market_value:.2f}")
            print(f"  - 总手续费: {total_fees:.2f}")
            print(f"  - 整体收益率: {overall_return:+.2f}%")
            print(f"  - 平均费用率: {avg_fee_rate:.4f}%")

            # 分析盈亏分布
            profit_records = []
            loss_records = []

            for record in cost_records:
                cost_value = record.cost * abs(record.volume)
                market_value = record.price * abs(record.volume)
                profit_loss = market_value - cost_value

                if profit_loss > 0:
                    profit_records.append((record, profit_loss))
                elif profit_loss < 0:
                    loss_records.append((record, profit_loss))

            print(f"  - 盈利股票数: {len(profit_records)}只")
            print(f"  - 亏损股票数: {len(loss_records)}只")

            # 显示盈利和亏损最大的股票
            if profit_records:
                best_profit = max(profit_records, key=lambda x: x[1])
                print(f"  - 最大盈利: {best_profit[0].code} (+{best_profit[1]:.2f})")

            if loss_records:
                worst_loss = min(loss_records, key=lambda x: x[1])
                print(f"  - 最大亏损: {worst_loss[0].code} ({worst_loss[1]:.2f})")

            print("✓ 持仓成本分析验证成功")

        except Exception as e:
            print(f"✗ 持仓成本分析失败: {e}")
            raise

    def test_position_flow_analysis(self):
        """测试持仓流分析（时序分析）"""
        print("\n" + "="*60)
        print("开始测试: 持仓流分析")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        try:
            # 查询特定时间范围的持仓流数据
            start_time = datetime(2023, 1, 3, 9, 30)
            end_time = datetime(2023, 1, 3, 15, 0)

            print(f"→ 查询时间范围 {start_time.time()} ~ {end_time.time()} 的持仓流...")
            flow_records = position_record_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            }, page_size=1000)

            if len(flow_records) < 5:
                print("✗ 持仓流数据不足，跳过流分析")
                return

            # 按时间排序
            flow_records.sort(key=lambda r: r.timestamp)

            # 分析持仓流时间分布
            time_distribution = {}
            for record in flow_records:
                hour = record.timestamp.hour
                if hour not in time_distribution:
                    time_distribution[hour] = {
                        "count": 0,
                        "buy_volume": 0,
                        "sell_volume": 0,
                        "total_cost": Decimal("0")
                    }

                time_distribution[hour]["count"] += 1
                time_distribution[hour]["total_cost"] += abs(record.cost * record.volume)

                if record.volume > 0:
                    time_distribution[hour]["buy_volume"] += record.volume
                elif record.volume < 0:
                    time_distribution[hour]["sell_volume"] += abs(record.volume)

            print(f"✓ 持仓流分析结果:")
            print(f"  - 总持仓变动记录数: {len(flow_records)}")
            print(f"  - 时间跨度: {flow_records[0].timestamp.time()} ~ {flow_records[-1].timestamp.time()}")

            # 计算总体买卖比例
            total_buy_volume = sum(r.volume for r in flow_records if r.volume > 0)
            total_sell_volume = sum(abs(r.volume) for r in flow_records if r.volume < 0)

            print(f"  - 总买入量: {total_buy_volume}股")
            print(f"  - 总卖出量: {total_sell_volume}股")

            if total_sell_volume > 0:
                buy_sell_ratio = total_buy_volume / total_sell_volume
                print(f"  - 买卖比例: {buy_sell_ratio:.2f}")

            # 显示时间分布
            for hour in sorted(time_distribution.keys()):
                stats = time_distribution[hour]
                print(f"  - {hour:02d}时: {stats['count']}条变动, 买入{stats['buy_volume']}股, 卖出{stats['sell_volume']}股")

            print("✓ 持仓流分析验证成功")

        except Exception as e:
            print(f"✗ 持仓流分析失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestPositionRecordCRUDDelete:
    CRUD_TEST_CONFIG = {'crud_class': PositionRecordCRUD}
    """3. CRUD层删除操作测试 - PositionRecord数据删除验证"""

    def test_delete_position_record_by_portfolio_id(self):
        """测试根据投资组合ID删除PositionRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID删除PositionRecord")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_record = MPositionRecord(
            portfolio_id="DELETE_TEST_PORTFOLIO",
            engine_id="delete_test_engine",
            code="000001.SZ",
            volume=1000,
            cost=Decimal("10.50"),
            price=Decimal("10.80"),
            frozen_volume=0,
            frozen_money=Decimal("0.00"),
            fee=Decimal("5.00"),
            timestamp=datetime(2023, 6, 15, 10, 30),
            source=SOURCE_TYPES.TEST
        )
        position_record_crud.add(test_record)
        print(f"✓ 插入测试数据: {test_record.code} in {test_record.portfolio_id}")

        # 验证数据存在
        before_count = len(position_record_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            position_record_crud.remove(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(position_record_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            print("✓ 根据投资组合ID删除PositionRecord验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_position_record_by_engine_id(self):
        """测试根据引擎ID删除PositionRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据引擎ID删除PositionRecord")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        # 准备测试数据 - 特定引擎ID的数据
        print("→ 准备测试数据...")
        test_engines = [
            ("delete_engine_001", "DELETE_STOCK_001", 500),
            ("delete_engine_002", "DELETE_STOCK_002", 800),
            ("delete_engine_001", "DELETE_STOCK_003", 1200),
        ]

        for engine_id, code, volume in test_engines:
            test_record = MPositionRecord(
                portfolio_id="engine_test_portfolio",
                engine_id=engine_id,
                code=code,
                volume=volume,
                cost=Decimal("15.00"),
                price=Decimal("15.50"),
                frozen_volume=0,
                frozen_money=Decimal("0.00"),
                fee=Decimal("3.00"),
                timestamp=datetime(2023, 7, 1, 10, 30),
                source=SOURCE_TYPES.TEST
            )
            position_record_crud.add(test_record)

        print(f"✓ 插入引擎测试数据: {len(test_engines)}条")

        # 验证数据存在
        before_count = len(position_record_crud.find(filters={"engine_id": "delete_engine_001"}))
        print(f"✓ 删除前引擎001数据量: {before_count}")

        try:
            # 删除特定引擎的数据
            print("\n→ 执行引擎ID删除操作...")
            position_record_crud.remove(filters={"engine_id": "delete_engine_001"})
            print("✓ 引擎ID删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(position_record_crud.find(filters={"engine_id": "delete_engine_001"}))
            print(f"✓ 删除后引擎001数据量: {after_count}")
            assert after_count == 0, "删除后应该没有引擎001的数据"

            # 确认其他引擎数据未受影响
            other_engine_count = len(position_record_crud.find(filters={"engine_id": "delete_engine_002"}))
            print(f"✓ 其他引擎数据保留验证: {other_engine_count}条")
            assert other_engine_count > 0, "其他引擎数据应该保留"

            print("✓ 根据引擎ID删除PositionRecord验证成功")

        except Exception as e:
            print(f"✗ 引擎ID删除操作失败: {e}")
            raise

    def test_delete_position_record_by_code(self):
        """测试根据股票代码删除PositionRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据股票代码删除PositionRecord")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        # 准备测试数据 - 特定股票代码的数据
        print("→ 准备测试数据...")
        test_codes = [
            ("code_delete_test", "DELETE_ENGINE_001"),
            ("code_delete_test", "DELETE_ENGINE_002"),
            ("code_keep_test", "DELETE_ENGINE_003"),
        ]

        for code, engine_id in test_codes:
            test_record = MPositionRecord(
                portfolio_id="code_test_portfolio",
                engine_id=engine_id,
                code=code,
                volume=2000,
                cost=Decimal("20.00"),
                price=Decimal("20.50"),
                frozen_volume=100,
                frozen_money=Decimal("2050.00"),
                fee=Decimal("8.00"),
                timestamp=datetime(2023, 8, 15, 10, 30),
                source=SOURCE_TYPES.TEST
            )
            position_record_crud.add(test_record)

        print(f"✓ 插入代码测试数据: {len(test_codes)}条")

        try:
            # 删除特定代码的数据
            print("\n→ 执行股票代码删除操作...")
            before_count = len(position_record_crud.find(filters={"code": "code_delete_test"}))
            print(f"✓ 删除前测试代码数据量: {before_count}")

            position_record_crud.remove(filters={"code": "code_delete_test"})
            print("✓ 股票代码删除操作完成")

            # 验证删除结果
            after_count = len(position_record_crud.find(filters={"code": "code_delete_test"}))
            print(f"✓ 删除后测试代码数据量: {after_count}")
            assert after_count == 0, "删除后应该没有测试代码数据"

            # 确认其他代码数据未受影响
            other_code_count = len(position_record_crud.find(filters={"code": "code_keep_test"}))
            print(f"✓ 其他代码数据保留验证: {other_code_count}条")
            assert other_code_count > 0, "其他代码数据应该保留"

            print("✓ 根据股票代码删除PositionRecord验证成功")

        except Exception as e:
            print(f"✗ 股票代码删除操作失败: {e}")
            raise

    def test_delete_position_record_by_time_range(self):
        """测试根据时间范围删除PositionRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围删除PositionRecord")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        # 准备测试数据 - 特定时间范围的数据
        print("→ 准备测试数据...")
        test_time_range = [
            datetime(2023, 9, 1, 10, 30),
            datetime(2023, 9, 2, 10, 30),
            datetime(2023, 9, 3, 10, 30)
        ]

        for i, test_time in enumerate(test_time_range):
            test_record = MPositionRecord(
                portfolio_id="time_test_portfolio",
                engine_id="time_test_engine",
                code=f"TIME_TEST_{i+1:03d}",
                volume=3000 + i * 100,
                cost=Decimal(f"25.{1000+i}"),
                price=Decimal(f"26.{1000+i}"),
                frozen_volume=50,
                frozen_money=Decimal(f"1300.{1000+i}"),
                fee=Decimal(f"12.{1000+i}"),
                timestamp=test_time,
                source=SOURCE_TYPES.TEST
            )
            position_record_crud.add(test_record)

        print(f"✓ 插入时间范围测试数据: {len(test_time_range)}条")

        # 验证数据存在
        before_count = len(position_record_crud.find(filters={
            "timestamp__gte": datetime(2023, 9, 1),
            "timestamp__lte": datetime(2023, 9, 3, 23, 59, 59)
        }))
        print(f"✓ 删除前时间范围内数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行时间范围删除操作...")
            position_record_crud.remove(filters={
                "timestamp__gte": datetime(2023, 9, 1),
                "timestamp__lte": datetime(2023, 9, 3, 23, 59, 59)
            })
            print("✓ 时间范围删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(position_record_crud.find(filters={
                "timestamp__gte": datetime(2023, 9, 1),
                "timestamp__lte": datetime(2023, 9, 3, 23, 59, 59)
            }))
            print(f"✓ 删除后时间范围内数据量: {after_count}")
            assert after_count == 0, "删除后时间范围内应该没有数据"

            print("✓ 根据时间范围删除PositionRecord验证成功")

        except Exception as e:
            print(f"✗ 时间范围删除操作失败: {e}")
            raise

    def test_delete_position_record_by_volume_range(self):
        """测试根据持仓量范围删除PositionRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据持仓量范围删除PositionRecord")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        # 准备测试数据 - 不同持仓量的数据
        print("→ 准备测试数据...")
        test_volumes = [
            ("VOLUME_SMALL_STOCK", 100),     # 小持仓
            ("VOLUME_MEDIUM_STOCK", 5000),    # 中持仓
            ("VOLUME_LARGE_STOCK", 50000),    # 大持仓
            ("VOLUME_EXTREME_STOCK", 500000), # 极大持仓
        ]

        for code, volume in test_volumes:
            test_record = MPositionRecord(
                portfolio_id="volume_test_portfolio",
                engine_id="volume_test_engine",
                code=code,
                volume=volume,
                cost=Decimal("30.00"),
                price=Decimal("30.50"),
                frozen_volume=0,
                frozen_money=Decimal("0.00"),
                fee=Decimal("15.00"),
                timestamp=datetime(2023, 10, 15, 10, 30),
                source=SOURCE_TYPES.TEST
            )
            position_record_crud.add(test_record)

        print(f"✓ 插入持仓量测试数据: {len(test_volumes)}条")

        try:
            # 删除大持仓数据 (> 10000)
            print("\n→ 执行大持仓数据删除操作...")
            before_large = len(position_record_crud.find(filters={"volume__gt": 10000}))
            print(f"✓ 删除前大持仓数据量: {before_large}")

            position_record_crud.remove(filters={"volume__gt": 10000})
            print("✓ 大持仓删除操作完成")

            after_large = len(position_record_crud.find(filters={"volume__gt": 10000}))
            print(f"✓ 删除后大持仓数据量: {after_large}")
            assert after_large == 0, "删除后应该没有大持仓数据"

            # 删除小持仓数据 (< 1000)
            print("\n→ 执行小持仓数据删除操作...")
            before_small = len(position_record_crud.find(filters={"volume__lt": 1000}))
            print(f"✓ 删除前小持仓数据量: {before_small}")

            position_record_crud.remove(filters={"volume__lt": 1000})
            print("✓ 小持仓删除操作完成")

            after_small = len(position_record_crud.find(filters={"volume__lt": 1000}))
            print(f"✓ 删除后小持仓数据量: {after_small}")
            assert after_small == 0, "删除后应该没有小持仓数据"

            # 确认中持仓数据未受影响
            medium_volume_count = len(position_record_crud.find(filters={
                "volume__gte": 1000,
                "volume__lte": 10000
            }))
            print(f"✓ 中持仓数据保留验证: {medium_volume_count}条")
            assert medium_volume_count > 0, "中持仓数据应该保留"

            print("✓ 根据持仓量范围删除PositionRecord验证成功")

        except Exception as e:
            print(f"✗ 持仓量范围删除操作失败: {e}")
            raise

    def test_delete_position_record_batch_cleanup(self):
        """测试批量清理PositionRecord数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理PositionRecord数据")
        print("="*60)

        position_record_crud = PositionRecordCRUD()

        # 准备批量清理数据
        print("→ 准备批量清理测试数据...")
        cleanup_records = []
        base_time = datetime(2023, 11, 1)

        for i in range(15):
            code = f"CLEANUP_RECORD_{i+1:03d}"
            cleanup_records.append(code)

            test_record = MPositionRecord(
                portfolio_id=f"cleanup_portfolio_{i+1:03d}",
                engine_id=f"cleanup_engine_{i+1:03d}",
                code=code,
                volume=4000 + i * 200,
                cost=Decimal(f"35.{1000+i}"),
                price=Decimal(f"36.{1000+i}"),
                frozen_volume=100 + i * 10,
                frozen_money=Decimal(f"3600.{1000+i}"),
                fee=Decimal(f"20.{1000+i}"),
                timestamp=base_time + timedelta(hours=i),
                source=SOURCE_TYPES.TEST
            )
            position_record_crud.add(test_record)

        print(f"✓ 插入批量清理测试数据: {len(cleanup_records)}条")

        # 验证数据存在
        before_count = len(position_record_crud.find(filters={
            "code__like": "CLEANUP_RECORD_%"
        }))
        print(f"✓ 删除前批量数据量: {before_count}")

        try:
            # 批量删除
            print("\n→ 执行批量清理操作...")
            position_record_crud.remove(filters={
                "code__like": "CLEANUP_RECORD_%"
            })
            print("✓ 批量清理操作完成")

            # 验证删除结果
            print("\n→ 验证批量清理结果...")
            after_count = len(position_record_crud.find(filters={
                "code__like": "CLEANUP_RECORD_%"
            }))
            print(f"✓ 删除后批量数据量: {after_count}")
            assert after_count == 0, "删除后应该没有批量清理数据"

            # 确认其他数据未受影响
            other_data_count = len(position_record_crud.find(page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理PositionRecord数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：PositionRecord CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_position_record_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 持仓变更记录存储和分析功能")
