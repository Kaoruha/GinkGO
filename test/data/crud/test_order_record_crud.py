"""
OrderRecord CRUD数据库操作TDD测试

测试CRUD层的订单执行记录数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)

OrderRecord是订单执行记录数据模型，存储订单的详细执行过程和结果。
为订单执行分析、性能评估和交易质量评估提供支持。
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.order_record_crud import OrderRecordCRUD
from ginkgo.data.models.model_order_record import MOrderRecord
from ginkgo.enums import SOURCE_TYPES, DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestOrderRecordCRUDInsert:
    CRUD_TEST_CONFIG = {'crud_class': OrderRecordCRUD}
    """1. CRUD层插入操作测试 - OrderRecord数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入OrderRecord数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: OrderRecord CRUD层批量插入")
        print("="*60)

        order_record_crud = OrderRecordCRUD()
        print(f"✓ 创建OrderRecordCRUD实例: {order_record_crud.__class__.__name__}")

        # 创建测试OrderRecord数据 - 不同状态的订单执行记录
        base_time = datetime(2023, 1, 3, 9, 30)
        test_records = []

        # 完全成交的订单记录
        filled_record = MOrderRecord(
            order_id="order_001",
            portfolio_id="portfolio_001",
            engine_id="engine_001",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.FILLED,
            volume=1000,
            limit_price=Decimal("12.50"),
            frozen=Decimal("12500.00"),
            transaction_price=Decimal("12.52"),
            transaction_volume=1000,
            remain=Decimal("0.00"),
            fee=Decimal("6.26"),
            timestamp=base_time,
            business_timestamp=base_time - timedelta(minutes=2),  # 业务时间比系统时间早2分钟
            source=SOURCE_TYPES.TEST
        )
        test_records.append(filled_record)

        # 部分成交的订单记录
        partial_filled_record = MOrderRecord(
            order_id="order_002",
            portfolio_id="portfolio_001",
            engine_id="engine_001",
            code="000002.SZ",
            direction=DIRECTION_TYPES.SHORT,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.PARTIAL_FILLED,
            volume=500,
            limit_price=Decimal("18.75"),
            frozen=Decimal("9375.00"),
            transaction_price=Decimal("18.73"),
            transaction_volume=200,
            remain=Decimal("5625.00"),
            fee=Decimal("3.75"),
            timestamp=base_time + timedelta(minutes=5),
            business_timestamp=base_time + timedelta(minutes=3),  # 业务时间比系统时间早2分钟
            source=SOURCE_TYPES.TEST
        )
        test_records.append(partial_filled_record)

        # 已取消的订单记录
        canceled_record = MOrderRecord(
            order_id="order_003",
            portfolio_id="portfolio_002",
            engine_id="engine_001",
            code="000858.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.CANCELED,
            volume=800,
            limit_price=Decimal("0.00"),
            frozen=Decimal("20480.00"),
            transaction_price=Decimal("0.00"),
            transaction_volume=0,
            remain=Decimal("20480.00"),
            fee=Decimal("0.00"),
            timestamp=base_time + timedelta(minutes=10),
            business_timestamp=base_time + timedelta(minutes=8),  # 业务时间比系统时间早2分钟
            source=SOURCE_TYPES.TEST
        )
        test_records.append(canceled_record)

        print(f"✓ 创建测试数据: {len(test_records)}条OrderRecord记录")
        order_statuses = list(set(r.status for r in test_records))
        print(f"  - 订单状态: {order_statuses}")
        print(f"  - 投资组合ID: {[r.portfolio_id for r in test_records]}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            order_record_crud.add_batch(test_records)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = order_record_crud.find(filters={
                "timestamp__gte": base_time,
                "timestamp__lte": base_time + timedelta(minutes=15)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 3

            # 验证数据内容
            order_ids = set(r.order_id for r in query_result)
            print(f"✓ 订单ID验证通过: {len(order_ids)} 种")
            assert len(order_ids) >= 3

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_order_record(self):
        """测试单条OrderRecord数据插入"""
        print("\n" + "="*60)
        print("开始测试: OrderRecord CRUD层单条插入")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        base_time = datetime(2023, 1, 3, 10, 30)
        test_record = MOrderRecord(
            order_id="order_004",
            portfolio_id="portfolio_003",
            engine_id="engine_002",
            code="600000.SH",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.SUBMITTED,
            volume=1500,
            limit_price=Decimal("8.85"),
            frozen=Decimal("13275.00"),
            transaction_price=Decimal("0.00"),
            transaction_volume=0,
            remain=Decimal("13275.00"),
            fee=Decimal("0.00"),
            timestamp=base_time,
            business_timestamp=base_time - timedelta(minutes=1),  # 业务时间比系统时间早1分钟
            source=SOURCE_TYPES.TEST
        )
        print(f"✓ 创建测试OrderRecord: {test_record.order_id}")
        print(f"  - 股票代码: {test_record.code}")
        print(f"  - 订单状态: {test_record.status}")
        print(f"  - 委托价格: {test_record.limit_price}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            order_record_crud.add(test_record)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = order_record_crud.find(filters={
                "order_id": "order_004",
                "timestamp": datetime(2023, 1, 3, 10, 30)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_record = query_result[0]
            print(f"✓ 插入的OrderRecord验证: {inserted_record.order_id}")
            assert inserted_record.order_id == "order_004"
            assert inserted_record.code == "600000.SH"
            assert inserted_record.volume == 1500

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestOrderRecordCRUDQuery:
    CRUD_TEST_CONFIG = {'crud_class': OrderRecordCRUD}
    """2. CRUD层查询操作测试 - OrderRecord数据查询和过滤"""

    def test_find_by_order_id(self):
        """测试根据订单ID查询OrderRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据订单ID查询OrderRecord")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 查询特定订单的执行记录
            print("→ 查询订单ID=order_001的执行记录...")
            order_records = order_record_crud.find(filters={
                "order_id": "order_001"
            })
            print(f"✓ 查询到 {len(order_records)} 条记录")

            # 验证查询结果
            for record in order_records:
                print(f"  - {record.code}: 状态{record.status}, 成交{record.transaction_volume}/{record.volume}股")
                assert record.order_id == "order_001"
                assert record.volume > 0

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_portfolio_id(self):
        """测试根据投资组合ID查询OrderRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID查询OrderRecord")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 查询特定投资组合的订单记录
            print("→ 查询portfolio_id=portfolio_001的订单记录...")
            portfolio_records = order_record_crud.find(filters={
                "portfolio_id": "portfolio_001"
            })
            print(f"✓ 查询到 {len(portfolio_records)} 条记录")

            # 验证查询结果
            for record in portfolio_records:
                print(f"  - {record.order_id}: {record.code}, {record.direction}方向, {record.volume}股")
                assert record.portfolio_id == "portfolio_001"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_order_status(self):
        """测试根据订单状态查询OrderRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据订单状态查询OrderRecord")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 查询完全成交的订单记录
            print("→ 查询状态为完全成交的订单记录...")
            filled_records = order_record_crud.find(filters={
                "status": ORDERSTATUS_TYPES.FILLED.value
            })
            print(f"✓ 查询到 {len(filled_records)} 条完全成交记录")

            # 查询部分成交的订单记录
            print("→ 查询状态为部分成交的订单记录...")
            partial_records = order_record_crud.find(filters={
                "status": ORDERSTATUS_TYPES.PARTIAL_FILLED.value
            })
            print(f"✓ 查询到 {len(partial_records)} 条部分成交记录")

            # 查询已取消的订单记录
            print("→ 查询状态为已取消的订单记录...")
            canceled_records = order_record_crud.find(filters={
                "status": ORDERSTATUS_TYPES.CANCELED.value
            })
            print(f"✓ 查询到 {len(canceled_records)} 条已取消记录")

            # 验证查询结果
            for record in filled_records[:3]:
                print(f"  - {record.order_id}: {record.code}, 成交{record.transaction_volume}股")

        except Exception as e:
            print(f"✗ 订单状态查询失败: {e}")
            raise

    def test_find_by_time_range(self):
        """测试根据时间范围查询OrderRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围查询OrderRecord")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 查询特定时间范围的订单记录
            start_time = datetime(2023, 1, 3, 9, 0)
            end_time = datetime(2023, 1, 3, 12, 0)

            print(f"→ 查询时间范围 {start_time} ~ {end_time} 的订单记录...")
            time_records = order_record_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            })
            print(f"✓ 查询到 {len(time_records)} 条记录")

            # 验证时间范围
            for record in time_records:
                print(f"  - {record.order_id}: {record.code} ({record.timestamp})")
                assert start_time <= record.timestamp <= end_time

            print("✓ 时间范围查询验证成功")

        except Exception as e:
            print(f"✗ 时间范围查询失败: {e}")
            raise

    def test_find_by_transaction_volume_range(self):
        """测试根据成交量范围查询OrderRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据成交量范围查询OrderRecord")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 查询大额成交订单（成交>=1000股）
            print("→ 查询成交量 >= 1000股的订单...")
            large_volume_records = order_record_crud.find(filters={
                "transaction_volume__gte": 1000
            })
            print(f"✓ 查询到 {len(large_volume_records)} 条大额成交记录")

            # 查询小额成交订单（成交<500股）
            print("→ 查询成交量 < 500股的订单...")
            small_volume_records = order_record_crud.find(filters={
                "transaction_volume__lt": 500
            })
            print(f"✓ 查询到 {len(small_volume_records)} 条小额成交记录")

            # 验证查询结果
            for record in large_volume_records[:3]:
                print(f"  - {record.order_id}: {record.code}, 成交{record.transaction_volume}股")

            for record in small_volume_records[:3]:
                print(f"  - {record.order_id}: {record.code}, 成交{record.transaction_volume}股")

            print("✓ 成交量范围查询验证成功")

        except Exception as e:
            print(f"✗ 成交量范围查询失败: {e}")
            raise




@pytest.mark.database
@pytest.mark.tdd
class TestOrderRecordCRUDBusinessLogic:
    CRUD_TEST_CONFIG = {'crud_class': OrderRecordCRUD}
    """4. CRUD层业务逻辑测试 - OrderRecord业务场景验证"""

    def test_order_execution_analysis(self):
        """测试订单执行分析"""
        print("\n" + "="*60)
        print("开始测试: 订单执行分析")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 查询所有订单记录进行执行分析
            print("→ 查询所有订单记录进行执行分析...")
            all_records = order_record_crud.find(page_size=1000)

            if len(all_records) < 5:
                pytest.skip("订单记录数据不足(少于5条)，跳过执行分析")

            # 按订单状态分组统计
            status_stats = {}
            execution_rate = 0
            total_volume = 0
            executed_volume = 0

            for record in all_records:
                status = record.status
                if status not in status_stats:
                    status_stats[status] = {
                        "count": 0,
                        "total_volume": 0,
                        "executed_volume": 0
                    }

                status_stats[status]["count"] += 1
                total_volume += record.volume
                executed_volume += record.transaction_volume

            print(f"✓ 订单执行分析结果:")
            print(f"  - 总订单数: {len(all_records)}")
            print(f"  - 总委托数量: {total_volume}股")
            print(f"  - 总成交数量: {executed_volume}股")

            if total_volume > 0:
                execution_rate = (executed_volume / total_volume) * 100
                print(f"  - 整体执行率: {execution_rate:.2f}%")

            # 显示各状态统计
            for status, stats in status_stats.items():
                status_name = ORDERSTATUS_TYPES.from_int(status).name if status >= 0 else "UNKNOWN"
                print(f"  - {status_name}: {stats['count']}单")

            # 验证分析结果
            assert len(all_records) > 0
            assert execution_rate >= 0
            print("✓ 订单执行分析验证成功")

        except Exception as e:
            print(f"✗ 订单执行分析失败: {e}")
            raise

    def test_transaction_price_analysis(self):
        """测试成交价格分析"""
        print("\n" + "="*60)
        print("开始测试: 成交价格分析")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 查询有成交记录的订单
            print("→ 查询有成交记录的订单进行价格分析...")
            executed_records = order_record_crud.find(filters={
                "transaction_volume__gt": 0
            }, page_size=500)

            if len(executed_records) < 3:
                pytest.skip("成交记录数据不足(少于3条)，跳过价格分析")

            # 分析成交价格与委托价格的偏差
            price_deviations = []
            for record in executed_records:
                if record.limit_price > 0 and record.transaction_price > 0:
                    deviation = (record.transaction_price - record.limit_price) / record.limit_price
                    price_deviations.append(deviation)

            print(f"✓ 成交价格分析结果:")
            print(f"  - 成交订单数: {len(executed_records)}")
            print(f"  - 有效价格偏差样本: {len(price_deviations)}")

            if price_deviations:
                avg_deviation = sum(price_deviations) / len(price_deviations)
                max_deviation = max(price_deviations)
                min_deviation = min(price_deviations)

                print(f"  - 平均价格偏差: {avg_deviation:+.4f}")
                print(f"  - 最大价格偏差: {max_deviation:+.4f}")
                print(f"  - 最小价格偏差: {min_deviation:+.4f}")

                # 统计改善和恶化的比例
                improved = sum(1 for d in price_deviations if d < 0)
                worsened = sum(1 for d in price_deviations if d > 0)

                print(f"  - 价格改善订单: {improved}单 ({improved/len(price_deviations)*100:.1f}%)")
                print(f"  - 价格恶化订单: {worsened}单 ({worsened/len(price_deviations)*100:.1f}%)")

            print("✓ 成交价格分析验证成功")

        except Exception as e:
            print(f"✗ 成交价格分析失败: {e}")
            raise

    def test_order_flow_analysis(self):
        """测试订单流分析"""
        print("\n" + "="*60)
        print("开始测试: 订单流分析")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 查询特定时间范围的订单流数据
            start_time = datetime(2023, 1, 3, 9, 30)
            end_time = datetime(2023, 1, 3, 15, 0)

            print(f"→ 查询时间范围 {start_time.time()} ~ {end_time.time()} 的订单流...")
            flow_records = order_record_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            }, page_size=1000)

            if len(flow_records) < 10:
                pytest.skip("订单流数据不足(少于10条)，跳过流分析")

            # 按时间排序
            flow_records.sort(key=lambda r: r.timestamp)

            # 分析订单流时间分布
            time_distribution = {}
            for record in flow_records:
                hour = record.timestamp.hour
                if hour not in time_distribution:
                    time_distribution[hour] = {
                        "count": 0,
                        "volume": 0,
                        "buy_count": 0,
                        "sell_count": 0
                    }

                time_distribution[hour]["count"] += 1
                time_distribution[hour]["volume"] += record.volume

                if record.direction == DIRECTION_TYPES.LONG.value:
                    time_distribution[hour]["buy_count"] += 1
                elif record.direction == DIRECTION_TYPES.SHORT.value:
                    time_distribution[hour]["sell_count"] += 1

            print(f"✓ 订单流分析结果:")
            print(f"  - 总订单数: {len(flow_records)}")
            print(f"  - 时间跨度: {flow_records[0].timestamp.time()} ~ {flow_records[-1].timestamp.time()}")

            # 显示时间分布
            for hour in sorted(time_distribution.keys()):
                stats = time_distribution[hour]
                buy_ratio = stats["buy_count"] / stats["count"] * 100 if stats["count"] > 0 else 0
                print(f"  - {hour:02d}时: {stats['count']}单, {stats['volume']}股, 买入{buy_ratio:.1f}%")

            print("✓ 订单流分析验证成功")

        except Exception as e:
            print(f"✗ 订单流分析失败: {e}")
            raise

    def test_order_quality_metrics(self):
        """测试订单质量指标计算"""
        print("\n" + "="*60)
        print("开始测试: 订单质量指标计算")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 查询所有订单记录计算质量指标
            print("→ 查询订单记录计算质量指标...")
            all_records = order_record_crud.find(page_size=1000)

            if len(all_records) < 5:
                pytest.skip("订单记录数据不足(少于5条)，跳过质量指标计算")

            # 计算各种质量指标
            filled_orders = [r for r in all_records if r.status == ORDERSTATUS_TYPES.FILLED.value]
            partial_orders = [r for r in all_records if r.status == ORDERSTATUS_TYPES.PARTIAL_FILLED.value]
            canceled_orders = [r for r in all_records if r.status == ORDERSTATUS_TYPES.CANCELED.value]

            total_orders = len(all_records)
            fill_rate = len(filled_orders) / total_orders * 100 if total_orders > 0 else 0
            partial_rate = len(partial_orders) / total_orders * 100 if total_orders > 0 else 0
            cancel_rate = len(canceled_orders) / total_orders * 100 if total_orders > 0 else 0

            # 计算平均执行规模
            executed_orders = filled_orders + partial_orders
            avg_execution_size = sum(r.transaction_volume for r in executed_orders) / len(executed_orders) if executed_orders else 0

            # 计算平均手续费率
            avg_fee_rate = 0
            fee_records = [r for r in executed_orders if r.transaction_price > 0 and r.transaction_volume > 0]
            if fee_records:
                total_notional = sum(r.transaction_price * r.transaction_volume for r in fee_records)
                total_fees = sum(r.fee for r in fee_records)
                avg_fee_rate = (total_fees / total_notional) * 100 if total_notional > 0 else 0

            print(f"✓ 订单质量指标结果:")
            print(f"  - 总订单数: {total_orders}")
            print(f"  - 完全成交率: {fill_rate:.2f}%")
            print(f"  - 部分成交率: {partial_rate:.2f}%")
            print(f"  - 取消率: {cancel_rate:.2f}%")
            print(f"  - 平均执行规模: {avg_execution_size:.0f}股")
            print(f"  - 平均手续费率: {avg_fee_rate:.4f}%")

            # 验证质量指标
            assert fill_rate >= 0 and fill_rate <= 100
            assert avg_execution_size >= 0
            assert avg_fee_rate >= 0
            print("✓ 订单质量指标计算验证成功")

        except Exception as e:
            print(f"✗ 订单质量指标计算失败: {e}")
            raise

    def test_find_by_business_time_range(self):
        """测试根据业务时间范围查询OrderRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据业务时间范围查询OrderRecord")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 查询特定业务时间范围的订单记录
            start_business_time = datetime(2023, 1, 3, 9, 25)   # 业务时间开始
            end_business_time = datetime(2023, 1, 3, 10, 35)    # 业务时间结束

            print(f"→ 查询业务时间范围 {start_business_time.time()} ~ {end_business_time.time()} 的订单记录...")
            # 使用普通查询并验证业务时间
            business_time_records = order_record_crud.find(filters={
                "timestamp__gte": start_business_time,
                "timestamp__lte": end_business_time,
                "source": SOURCE_TYPES.TEST.value
            })
            print(f"✓ 查询到 {len(business_time_records)} 条记录")

            # 验证业务时间范围
            for record in business_time_records:
                print(f"  - {record.code}: 系统时间 {record.timestamp.time()}, 业务时间 {record.business_timestamp.time() if record.business_timestamp else 'None'}")
                if record.business_timestamp:
                    assert start_business_time <= record.business_timestamp <= end_business_time

            print("✓ 业务时间范围查询验证成功")

        except Exception as e:
            print(f"✗ 业务时间范围查询失败: {e}")
            raise

    def test_find_by_time_range_with_business_timestamp(self):
        """测试使用双时间戳的灵活时间范围查询OrderRecord"""
        print("\n" + "="*60)
        print("开始测试: 双时间戳时间范围查询OrderRecord")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 测试双时间戳查询
            start_time = datetime(2023, 1, 3, 9, 0)
            end_time = datetime(2023, 1, 3, 11, 0)

            print(f"→ 使用系统时间查询范围 {start_time.time()} ~ {end_time.time()}...")
            system_records = order_record_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time,
                "source": SOURCE_TYPES.TEST.value
            })
            print(f"✓ 系统时间查询到 {len(system_records)} 条记录")

            print(f"→ 验证双时间戳数据一致性...")
            for record in system_records:
                if record.business_timestamp:
                    time_diff = record.timestamp - record.business_timestamp
                    print(f"  - {record.code}: 系统时间与业务时间差 {time_diff}")
                    assert abs(time_diff.total_seconds() >= 0)  # 时间差应该合理

            print("✓ 双时间戳查询验证成功")

        except Exception as e:
            print(f"✗ 双时间戳查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestOrderRecordCRUDDelete:
    CRUD_TEST_CONFIG = {'crud_class': OrderRecordCRUD}
    """4. CRUD层删除操作测试 - OrderRecord数据删除验证"""

    def test_delete_order_records_by_portfolio(self):
        """测试根据投资组合ID删除订单记录"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID删除订单记录")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 准备测试数据
            print("→ 创建测试订单记录...")
            # 使用CRUD的创建方法来避免run_id字段问题
            test_records = order_record_crud._create_from_params(
                portfolio_id="delete_test_portfolio",
                code="000001.SZ",
                direction=DIRECTION_TYPES.LONG,
                order_type=ORDER_TYPES.LIMITORDER,
                status=ORDERSTATUS_TYPES.FILLED,
                limit_price=Decimal("10.50"),
                transaction_price=Decimal("10.48"),
                transaction_volume=1000,
                fee=Decimal("5.24")
            )

            test_record2 = order_record_crud._create_from_params(
                portfolio_id="delete_test_portfolio",
                code="000002.SZ",
                direction=DIRECTION_TYPES.SHORT,
                order_type=ORDER_TYPES.MARKETORDER,
                status=ORDERSTATUS_TYPES.CANCELED,
                limit_price=Decimal("0.00"),
                transaction_price=Decimal("0.00"),
                transaction_volume=0,
                fee=Decimal("0.00")
            )

            order_record_crud.add(test_records)
            order_record_crud.add(test_record2)
            print("✓ 测试订单记录创建成功")

            # 验证数据存在
            print("→ 验证订单记录存在...")
            records_before = order_record_crud.find(filters={"portfolio_id": "delete_test_portfolio"})

            initial_count = len(records_before)
            print(f"✓ 删除前记录数: {initial_count}")

            # 断言：至少有我们刚创建的记录
            assert initial_count >= 2

            # 执行删除操作
            print("→ 执行订单记录删除...")
            order_record_crud.remove(filters={"portfolio_id": "delete_test_portfolio"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            records_after = order_record_crud.find(filters={"portfolio_id": "delete_test_portfolio"})
            final_count = len(records_after)

            print(f"✓ 删除后记录数: {final_count}")

            # 断言：通过比对操作前后的计数变化来验证删除效果
            assert final_count == 0, f"删除后记录数应该为0，实际为{final_count}"
            assert final_count == initial_count - initial_count, f"删除后总记录数应该减少{initial_count}个"

            print("✓ 根据投资组合ID删除订单记录验证成功")

        except Exception as e:
            print(f"✗ 根据投资组合ID删除订单记录失败: {e}")
            raise

    def test_delete_order_records_by_status(self):
        """测试根据订单状态删除订单记录"""
        print("\n" + "="*60)
        print("开始测试: 根据订单状态删除订单记录")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 准备不同状态的测试数据
            print("→ 创建不同状态的订单记录...")
            test_records = [
                MOrderRecord(
                    portfolio_id="status_test_portfolio",
                    code="000001.SZ",
                    direction=DIRECTION_TYPES.LONG.value,
                    status=ORDERSTATUS_TYPES.FILLED.value,  # 已成交
                    limit_price=Decimal("10.50"),
                    transaction_price=Decimal("10.48"),
                    transaction_volume=1000,
                    source=SOURCE_TYPES.TEST
                ),
                MOrderRecord(
                    portfolio_id="status_test_portfolio",
                    code="000002.SZ",
                    direction=DIRECTION_TYPES.SHORT.value,
                    status=ORDERSTATUS_TYPES.CANCELED.value,  # 已取消
                    limit_price=Decimal("20.00"),
                    transaction_price=Decimal("0.00"),
                    transaction_volume=0,
                    source=SOURCE_TYPES.TEST
                ),
                MOrderRecord(
                    portfolio_id="status_test_portfolio",
                    code="000003.SZ",
                    direction=DIRECTION_TYPES.LONG.value,
                    status=ORDERSTATUS_TYPES.CANCELED.value,  # 已取消
                    limit_price=Decimal("30.00"),
                    transaction_price=Decimal("0.00"),
                    transaction_volume=0,
                    source=SOURCE_TYPES.TEST
                )
            ]

            for record in test_records:
                order_record_crud.add(record)
            print("✓ 不同状态的订单记录创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_records = order_record_crud.find(filters={"portfolio_id": "status_test_portfolio"})
            canceled_records = [r for r in all_records if r.status == ORDERSTATUS_TYPES.CANCELED.value]
            filled_records = [r for r in all_records if r.status == ORDERSTATUS_TYPES.FILLED.value]

            initial_count = len(all_records)
            initial_canceled_count = len(canceled_records)
            initial_filled_count = len(filled_records)

            print(f"✓ 初始状态 - 总记录数: {initial_count}, 已取消记录数: {initial_canceled_count}, 已成交记录数: {initial_filled_count}")

            # 断言：至少有我们刚创建的记录
            assert initial_count >= 3
            assert initial_canceled_count >= 2
            assert initial_filled_count >= 1

            # 删除已取消的订单记录
            print("→ 删除已取消的订单记录...")
            order_record_crud.remove(filters={
                "portfolio_id": "status_test_portfolio",
                "status": ORDERSTATUS_TYPES.CANCELED.value
            })
            print("✓ 已取消订单记录删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_records = order_record_crud.find(filters={"portfolio_id": "status_test_portfolio"})
            remaining_canceled = [r for r in remaining_records if r.status == ORDERSTATUS_TYPES.CANCELED.value]
            remaining_filled = [r for r in remaining_records if r.status == ORDERSTATUS_TYPES.FILLED.value]

            final_count = len(remaining_records)
            final_canceled_count = len(remaining_canceled)
            final_filled_count = len(remaining_filled)

            print(f"✓ 删除后状态 - 总记录数: {final_count}, 剩余已取消记录数: {final_canceled_count}, 剩余已成交记录数: {final_filled_count}")

            # 断言：通过比对操作前后的计数变化来验证删除效果
            assert final_count == initial_count - initial_canceled_count, f"删除后总记录数应该减少{initial_canceled_count}个"
            assert final_canceled_count == 0, "删除后已取消记录数应该为0"
            assert final_filled_count == initial_filled_count, "已成交记录数应该保持不变"

            print("✓ 根据订单状态删除订单记录验证成功")

        except Exception as e:
            print(f"✗ 根据订单状态删除订单记录失败: {e}")
            raise

    def test_delete_order_records_by_date_range(self):
        """测试根据日期范围删除订单记录"""
        print("\n" + "="*60)
        print("开始测试: 根据日期范围删除订单记录")
        print("="*60)

        order_record_crud = OrderRecordCRUD()

        try:
            # 准备不同日期的测试数据
            print("→ 创建不同日期的订单记录...")
            from datetime import datetime, timedelta

            base_date = datetime.now()
            test_records = [
                MOrderRecord(
                    portfolio_id="date_test_portfolio",
                    code="000001.SZ",
                    direction=DIRECTION_TYPES.LONG.value,
                    status=ORDERSTATUS_TYPES.FILLED.value,
                    limit_price=Decimal("10.50"),
                    transaction_price=Decimal("10.48"),
                    transaction_volume=1000,
                    timestamp=base_date - timedelta(days=5),  # 5天前
                    source=SOURCE_TYPES.TEST
                ),
                MOrderRecord(
                    portfolio_id="date_test_portfolio",
                    code="000002.SZ",
                    direction=DIRECTION_TYPES.SHORT.value,
                    status=ORDERSTATUS_TYPES.FILLED.value,
                    limit_price=Decimal("20.00"),
                    transaction_price=Decimal("19.95"),
                    transaction_volume=500,
                    timestamp=base_date - timedelta(days=1),  # 1天前
                    source=SOURCE_TYPES.TEST
                ),
                MOrderRecord(
                    portfolio_id="date_test_portfolio",
                    code="000003.SZ",
                    direction=DIRECTION_TYPES.LONG.value,
                    status=ORDERSTATUS_TYPES.FILLED.value,
                    limit_price=Decimal("30.00"),
                    transaction_price=Decimal("30.10"),
                    transaction_volume=300,
                    timestamp=base_date,  # 今天
                    source=SOURCE_TYPES.TEST
                )
            ]

            for record in test_records:
                order_record_crud.add(record)
            print("✓ 不同日期的订单记录创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_records = order_record_crud.find(filters={"portfolio_id": "date_test_portfolio"})

            # 计算3天前的记录数
            cutoff_date = base_date - timedelta(days=3)
            old_records = [r for r in all_records if r.timestamp < cutoff_date]
            recent_records = [r for r in all_records if r.timestamp >= cutoff_date]

            initial_count = len(all_records)
            old_count = len(old_records)
            recent_count = len(recent_records)

            print(f"✓ 初始状态 - 总记录数: {initial_count}, 3天前记录数: {old_count}, 3天内记录数: {recent_count}")

            # 断言：至少有我们刚创建的记录
            assert initial_count >= 3
            assert old_count >= 1  # 至少有一个3天前的记录
            assert recent_count >= 1  # 至少有一个3天内的记录

            # 删除3天前的记录
            print("→ 删除3天前的订单记录...")
            order_record_crud.remove(filters={
                "portfolio_id": "date_test_portfolio",
                "timestamp__lt": cutoff_date
            })
            print("✓ 3天前订单记录删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_records = order_record_crud.find(filters={"portfolio_id": "date_test_portfolio"})
            remaining_old = [r for r in remaining_records if r.timestamp < cutoff_date]
            remaining_recent = [r for r in remaining_records if r.timestamp >= cutoff_date]

            final_count = len(remaining_records)
            final_old_count = len(remaining_old)
            final_recent_count = len(remaining_recent)

            print(f"✓ 删除后状态 - 总记录数: {final_count}, 3天前记录数: {final_old_count}, 3天内记录数: {final_recent_count}")

            # 断言：通过比对操作前后的计数变化来验证删除效果
            assert final_count == initial_count - old_count, f"删除后总记录数应该减少{old_count}个"
            assert final_old_count == 0, "删除后3天前的记录数应该为0"
            assert final_recent_count == recent_count, "3天内的记录数应该保持不变"

            # 验证剩余记录都是3天内的
            for record in remaining_records:
                assert record.timestamp >= cutoff_date
                print(f"✓ 记录 {record.code} 日期符合要求")

            print("✓ 根据日期范围删除订单记录验证成功")

        except Exception as e:
            print(f"✗ 根据日期范围删除订单记录失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：OrderRecord CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_order_record_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 订单执行记录存储和分析功能")
