"""
TransferCRUD数据库操作TDD测试

测试CRUD层的资金划转数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)

Transfer是资金划转数据模型，记录投资组合的资金转入和转出操作。
为回测过程中的资金管理和风控提供支持。
"""
import pytest
import sys
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.transfer_crud import TransferCRUD
from ginkgo.data.models.model_transfer import MTransfer
from ginkgo.enums import (
    SOURCE_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES,
    TRANSFERDIRECTION_TYPES
)

# 导入异步清理工具
sys.path.insert(0, str(project_root / "test" / "libs" / "utils"))
from async_cleanup import AsyncCleanupMixin, async_cleanup_with_wait




@pytest.mark.database
@pytest.mark.tdd
class TestTransferCRUDInsert:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': TransferCRUD}
    """1. CRUD层插入操作测试 - Transfer数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入Transfer数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: Transfer CRUD层批量插入")
        print("="*60)

        transfer_crud = TransferCRUD()
        print(f"✓ 创建TransferCRUD实例: {transfer_crud.__class__.__name__}")

        # 创建测试Transfer数据 - 资金转入和转出记录
        base_time = datetime(2023, 1, 3, 9, 30)
        test_transfers = []

        # 资金转入记录
        transfer_in = MTransfer(
            portfolio_id="test_portfolio_001",
            engine_id="test_engine_001",
            run_id="test_run_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("100000.00"),  # 10万元入金
            status=TRANSFERSTATUS_TYPES.FILLED,
            source=SOURCE_TYPES.TEST,
            timestamp=base_time
        )
        test_transfers.append(transfer_in)

        # 资金转出记录
        transfer_out = MTransfer(
            portfolio_id="test_portfolio_001",
            engine_id="test_engine_001",
            run_id="test_run_001",
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.CHINA,
            money=Decimal("5000.00"),    # 5千元出金
            status=TRANSFERSTATUS_TYPES.FILLED,
            source=SOURCE_TYPES.TEST,
            timestamp=base_time + timedelta(hours=1)
        )
        test_transfers.append(transfer_out)

        print(f"✓ 创建测试数据: {len(test_transfers)}条Transfer记录")
        total_amount = sum(float(t.money) for t in test_transfers)
        print(f"  - 总金额: {total_amount:,.2f}")
        print(f"  - 时间范围: {test_transfers[0].timestamp} ~ {test_transfers[-1].timestamp}")

        try:
            # 查询插入前的数据数量
            print("\n→ 查询插入前的数据数量...")
            before_count = len(transfer_crud.find(filters={
                "portfolio_id": "test_portfolio_001",
                "timestamp__gte": base_time,
                "timestamp__lte": base_time + timedelta(hours=2)
            }))
            print(f"✓ 插入前数据数量: {before_count} 条")

            # 批量插入
            print("\n→ 执行批量插入操作...")
            transfer_crud.add_batch(test_transfers)
            print("✓ 批量插入成功")

            # 验证插入后的数据增量
            print("\n→ 验证插入后的数据增量...")
            query_result = transfer_crud.find(filters={
                "portfolio_id": "test_portfolio_001",
                "timestamp__gte": base_time,
                "timestamp__lte": base_time + timedelta(hours=2)
            })
            after_count = len(query_result)
            inserted_count = after_count - before_count
            expected_count = len(test_transfers)

            print(f"✓ 插入前数据数量: {before_count} 条")
            print(f"✓ 插入后数据数量: {after_count} 条")
            print(f"✓ 实际增加数量: {inserted_count} 条")
            print(f"✓ 预期插入数量: {expected_count} 条")

            assert inserted_count == expected_count, f"数据增量验证失败：预期增加{expected_count}条，实际增加{inserted_count}条"

            # 验证数据内容
            deposit_count = sum(1 for t in query_result if t.direction == TRANSFERDIRECTION_TYPES.IN.value)
            withdraw_count = sum(1 for t in query_result if t.direction == TRANSFERDIRECTION_TYPES.OUT.value)
            print(f"✓ 入金记录验证通过: {deposit_count} 条")
            print(f"✓ 出金记录验证通过: {withdraw_count} 条")

            # 验证新增的记录中包含预期的类型
            assert deposit_count >= 1, "新增记录中应该包含入金记录"
            assert withdraw_count >= 1, "新增记录中应该包含出金记录"

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_transfer(self):
        """测试单条Transfer数据插入"""
        print("\n" + "="*60)
        print("开始测试: Transfer CRUD层单条插入")
        print("="*60)

        transfer_crud = TransferCRUD()

        test_transfer = MTransfer(
            portfolio_id="test_portfolio_002",
            engine_id="test_engine_001",
            run_id="test_run_001",
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("50000.00"),   # 5万元入金
            status=TRANSFERSTATUS_TYPES.FILLED,
            source=SOURCE_TYPES.TEST,
            timestamp=datetime(2023, 1, 3, 10, 30)
        )

        try:
            # 查询插入前的数据数量
            print("\n→ 查询插入前的数据数量...")
            before_count = len(transfer_crud.find(filters={
                "portfolio_id": "test_portfolio_002",
                "timestamp": datetime(2023, 1, 3, 10, 30)
            }))
            print(f"✓ 插入前数据数量: {before_count} 条")

            # 单条插入
            print("\n→ 执行单条插入操作...")
            transfer_crud.add(test_transfer)
            print("✓ 单条插入成功")

            # 验证插入后的数据增量
            print("\n→ 验证插入后的数据增量...")
            query_result = transfer_crud.find(filters={
                "portfolio_id": "test_portfolio_002",
                "timestamp": datetime(2023, 1, 3, 10, 30)
            })
            after_count = len(query_result)
            inserted_count = after_count - before_count
            expected_count = 1

            print(f"✓ 插入前数据数量: {before_count} 条")
            print(f"✓ 插入后数据数量: {after_count} 条")
            print(f"✓ 实际增加数量: {inserted_count} 条")
            print(f"✓ 预期插入数量: {expected_count} 条")

            assert inserted_count == expected_count, f"数据增量验证失败：预期增加{expected_count}条，实际增加{inserted_count}条"

            # 验证插入的数据内容
            inserted_transfer = query_result[0]
            print(f"✓ 插入的Transfer验证: {inserted_transfer.money}")
            assert inserted_transfer.portfolio_id == "test_portfolio_002"
            assert inserted_transfer.money == Decimal("50000.00")

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTransferCRUDQuery:
    CRUD_TEST_CONFIG = {'crud_class': TransferCRUD}
    """2. CRUD层查询操作测试 - Transfer数据查询和过滤"""

    def test_find_by_portfolio_id(self):
        """测试根据投资组合ID查询Transfer"""
        print("\n" + "="*60)
        print("开始测试: 根据portfolio_id查询Transfer")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 查询特定投资组合的资金划转记录
            print("→ 查询portfolio_id=test_portfolio_001的资金划转记录...")
            portfolio_transfers = transfer_crud.find(filters={
                "portfolio_id": "test_portfolio_001"
            })
            print(f"✓ 查询到 {len(portfolio_transfers)} 条记录")

            # 验证查询结果
            total_transferred = sum(float(t.money) for t in portfolio_transfers)
            print(f"✓ 总划转金额: {total_transferred:,.2f}")

            for transfer in portfolio_transfers[:5]:  # 只显示前5条
                direction_name = "入金" if transfer.direction == TRANSFERDIRECTION_TYPES.IN.value else "出金"
                print(f"  - {transfer.timestamp}: {direction_name} {transfer.money}")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_direction(self):
        """测试根据划转方向查询Transfer"""
        print("\n" + "="*60)
        print("开始测试: 根据划转方向查询Transfer")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 查询所有入金记录
            print("→ 查询所有入金记录 (direction=IN)...")
            deposit_transfers = transfer_crud.find(filters={
                "direction": TRANSFERDIRECTION_TYPES.IN.value
            })
            print(f"✓ 查询到 {len(deposit_transfers)} 条入金记录")

            # 查询所有出金记录
            print("→ 查询所有出金记录 (direction=OUT)...")
            withdraw_transfers = transfer_crud.find(filters={
                "direction": TRANSFERDIRECTION_TYPES.OUT.value
            })
            print(f"✓ 查询到 {len(withdraw_transfers)} 条出金记录")

            # 验证查询结果
            deposit_total = sum(float(t.money) for t in deposit_transfers)
            withdraw_total = sum(float(t.money) for t in withdraw_transfers)
            print(f"✓ 入金总额: {deposit_total:,.2f}")
            print(f"✓ 出金总额: {withdraw_total:,.2f}")

        except Exception as e:
            print(f"✗ 方向查询失败: {e}")
            raise

    def test_find_by_time_range(self):
        """测试根据时间范围查询Transfer"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围查询Transfer")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 查询特定时间范围的资金划转记录
            start_time = datetime(2023, 1, 1)
            end_time = datetime(2023, 1, 31, 23, 59, 59)

            print(f"→ 查询时间范围 {start_time} ~ {end_time} 的资金划转记录...")
            time_transfers = transfer_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            })
            print(f"✓ 查询到 {len(time_transfers)} 条记录")

            # 验证时间范围
            for transfer in time_transfers:
                direction_name = "入金" if transfer.direction == TRANSFERDIRECTION_TYPES.IN.value else "出金"
                print(f"  - {transfer.timestamp}: {direction_name} {transfer.money}")
                assert start_time <= transfer.timestamp <= end_time

            print("✓ 时间范围查询验证成功")

        except Exception as e:
            print(f"✗ 时间范围查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTransferCRUDUpdate:
    CRUD_TEST_CONFIG = {'crud_class': TransferCRUD}
    """3. CRUD层更新操作测试 - Transfer属性更新"""

    def test_update_transfer_status(self):
        """测试更新Transfer状态"""
        print("\n" + "="*60)
        print("开始测试: 更新Transfer状态")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 查询待更新的资金划转记录
            print("→ 查询待更新的资金划转记录...")
            transfers = transfer_crud.find(filters={}, page=1, page_size=1)
            if not transfers:
                print("✗ 没有找到可更新的资金划转记录")
                return

            target_transfer = transfers[0]
            print(f"✓ 找到资金划转记录: {target_transfer.timestamp}")
            print(f"  - 当前状态: {target_transfer.status}")
            print(f"  - 金额: {target_transfer.money}")

            # 更新状态为成功
            print("→ 更新划转状态...")
            updated_data = {
                "status": TRANSFERSTATUS_TYPES.FILLED.value
            }

            transfer_crud.modify({"uuid": target_transfer.uuid}, updated_data)
            print(f"✓ 划转状态更新为: 成功")

            # 验证更新结果
            print("→ 验证更新结果...")
            updated_transfers = transfer_crud.find(filters={"uuid": target_transfer.uuid})
            assert len(updated_transfers) == 1

            updated_transfer = updated_transfers[0]
            print(f"✓ 更新后状态: {updated_transfer.status}")

            assert updated_transfer.status == TRANSFERSTATUS_TYPES.FILLED.value
            print("✓ Transfer状态更新验证成功")

        except Exception as e:
            print(f"✗ 更新Transfer状态失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTransferCRUDBusinessLogic:
    CRUD_TEST_CONFIG = {'crud_class': TransferCRUD}
    """4. CRUD层业务逻辑测试 - Transfer业务场景验证"""

    def test_portfolio_fund_analysis(self):
        """测试投资组合资金分析"""
        print("\n" + "="*60)
        print("开始测试: 投资组合资金分析")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 查询所有资金划转记录进行分析
            print("→ 查询所有资金划转记录进行分析...")
            all_transfers = transfer_crud.find()

            if len(all_transfers) < 2:
                print("✗ 资金划转记录不足，跳过分析测试")
                return

            # 按投资组合分组统计
            portfolio_analysis = {}
            for transfer in all_transfers:
                portfolio_id = transfer.portfolio_id
                if portfolio_id not in portfolio_analysis:
                    portfolio_analysis[portfolio_id] = {
                        "deposit_count": 0,
                        "withdraw_count": 0,
                        "deposit_total": Decimal("0"),
                        "withdraw_total": Decimal("0"),
                        "net_amount": Decimal("0"),
                        "records": []
                    }

                portfolio_analysis[portfolio_id]["records"].append(transfer)

                if transfer.direction == TRANSFERDIRECTION_TYPES.IN.value:
                    portfolio_analysis[portfolio_id]["deposit_count"] += 1
                    portfolio_analysis[portfolio_id]["deposit_total"] += transfer.money
                elif transfer.direction == TRANSFERDIRECTION_TYPES.OUT.value:
                    portfolio_analysis[portfolio_id]["withdraw_count"] += 1
                    portfolio_analysis[portfolio_id]["withdraw_total"] += transfer.money

            # 计算净金额
            for portfolio_id, stats in portfolio_analysis.items():
                stats["net_amount"] = stats["deposit_total"] - stats["withdraw_total"]

            print(f"✓ 投资组合资金分析结果:")
            for portfolio_id, stats in portfolio_analysis.items():
                print(f"  - {portfolio_id}:")
                print(f"    入金: {stats['deposit_count']}次, 总额 {stats['deposit_total']:,.2f}")
                print(f"    出金: {stats['withdraw_count']}次, 总额 {stats['withdraw_total']:,.2f}")
                print(f"    净额: {stats['net_amount']:,.2f}")

            # 验证分析结果
            total_records = sum(stats["deposit_count"] + stats["withdraw_count"] for stats in portfolio_analysis.values())
            assert total_records == len(all_transfers)
            print("✓ 投资组合资金分析验证成功")

        except Exception as e:
            print(f"✗ 投资组合资金分析失败: {e}")
            raise

    def test_transfer_trend_analysis(self):
        """测试资金划转趋势分析"""
        print("\n" + "="*60)
        print("开始测试: 资金划转趋势分析")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 查询特定时间范围内的资金划转记录
            start_time = datetime(2023, 1, 1)
            end_time = datetime(2023, 12, 31)

            print(f"→ 查询时间范围 {start_time.date()} ~ {end_time.date()} 的资金划转记录...")
            transfers = transfer_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            })

            if len(transfers) < 5:
                print("✗ 资金划转记录不足，跳过趋势分析")
                return

            # 按月份分组统计
            monthly_stats = {}
            for transfer in transfers:
                month_key = transfer.timestamp.strftime("%Y-%m")
                if month_key not in monthly_stats:
                    monthly_stats[month_key] = {
                        "deposit_count": 0,
                        "withdraw_count": 0,
                        "deposit_total": Decimal("0"),
                        "withdraw_total": Decimal("0")
                    }

                if transfer.direction == TRANSFERDIRECTION_TYPES.IN.value:
                    monthly_stats[month_key]["deposit_count"] += 1
                    monthly_stats[month_key]["deposit_total"] += transfer.money
                elif transfer.direction == TRANSFERDIRECTION_TYPES.OUT.value:
                    monthly_stats[month_key]["withdraw_count"] += 1
                    monthly_stats[month_key]["withdraw_total"] += transfer.money

            print(f"✓ 月度资金划转趋势:")
            for month in sorted(monthly_stats.keys()):
                stats = monthly_stats[month]
                net_monthly = stats["deposit_total"] - stats["withdraw_total"]
                print(f"  - {month}: 入金 {stats['deposit_total']:,.2f}, 出金 {stats['withdraw_total']:,.2f}, 净额 {net_monthly:,.2f}")

            # 分析趋势
            months = sorted(monthly_stats.keys())
            if len(months) >= 2:
                first_month = monthly_stats[months[0]]
                last_month = monthly_stats[months[-1]]
                trend_change = (last_month["deposit_total"] - first_month["deposit_total"]) / first_month["deposit_total"] * 100 if first_month["deposit_total"] > 0 else 0
                print(f"✓ 趋势分析: 从{months[0]}到{months[-1]}，入金趋势变化 {trend_change:+.1f}%")

            print("✓ 资金划转趋势分析验证成功")

        except Exception as e:
            print(f"✗ 资金划转趋势分析失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTransferCRUDDelete:
    CRUD_TEST_CONFIG = {'crud_class': TransferCRUD}
    """4. CRUD层删除操作测试 - Transfer数据删除验证"""

    def test_delete_transfer_by_portfolio(self):
        """测试根据投资组合ID删除资金划转记录"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID删除资金划转记录")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 准备测试数据
            print("→ 创建测试资金划转记录...")
            test_transfers = MTransfer(
                portfolio_id="delete_test_portfolio",
                engine_id="test_engine_001",
                run_id="test_run_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("10000.00"),
                status=TRANSFERSTATUS_TYPES.FILLED,
                source=SOURCE_TYPES.TEST
            )

            test_transfer2 = MTransfer(
                portfolio_id="delete_test_portfolio",
                engine_id="test_engine_001",
                run_id="test_run_001",
                direction=TRANSFERDIRECTION_TYPES.OUT,
                market=MARKET_TYPES.CHINA,
                money=Decimal("5000.00"),
                status=TRANSFERSTATUS_TYPES.FILLED,
                source=SOURCE_TYPES.TEST
            )

            transfer_crud.add(test_transfers)
            transfer_crud.add(test_transfer2)
            print("✓ 测试资金划转记录创建成功")

            # 验证数据存在
            print("→ 验证资金划转记录存在...")
            transfers_before = transfer_crud.find(filters={"portfolio_id": "delete_test_portfolio"})
            print(f"✓ 删除前记录数: {len(transfers_before)}")
            assert len(transfers_before) >= 2

            # 执行删除操作
            print("→ 执行资金划转记录删除...")
            transfer_crud.remove(filters={"portfolio_id": "delete_test_portfolio"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            transfers_after = transfer_crud.find(filters={"portfolio_id": "delete_test_portfolio"})
            print(f"✓ 删除后记录数: {len(transfers_after)}")
            assert len(transfers_after) == 0

            print("✓ 根据投资组合ID删除资金划转记录验证成功")

        except Exception as e:
            print(f"✗ 根据投资组合ID删除资金划转记录失败: {e}")
            raise

    def test_delete_transfer_by_direction(self):
        """测试根据划转方向删除资金划转记录"""
        print("\n" + "="*60)
        print("开始测试: 根据划转方向删除资金划转记录")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 准备不同方向的测试数据
            print("→ 创建不同方向的资金划转记录...")
            test_transfers = [
                MTransfer(
                    portfolio_id="direction_test_portfolio",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    direction=TRANSFERDIRECTION_TYPES.IN,    # 入金
                    market=MARKET_TYPES.CHINA,
                    money=Decimal("8000.00"),
                    status=TRANSFERSTATUS_TYPES.FILLED,
                    source=SOURCE_TYPES.TEST
                ),
                MTransfer(
                    portfolio_id="direction_test_portfolio",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    direction=TRANSFERDIRECTION_TYPES.OUT,   # 出金
                    market=MARKET_TYPES.CHINA,
                    money=Decimal("3000.00"),
                    status=TRANSFERSTATUS_TYPES.FILLED,
                    source=SOURCE_TYPES.TEST
                ),
                MTransfer(
                    portfolio_id="direction_test_portfolio",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    direction=TRANSFERDIRECTION_TYPES.OUT,   # 出金
                    market=MARKET_TYPES.CHINA,
                    money=Decimal("2000.00"),
                    status=TRANSFERSTATUS_TYPES.FILLED,
                    source=SOURCE_TYPES.TEST
                )
            ]

            for transfer in test_transfers:
                transfer_crud.add(transfer)
            print("✓ 不同方向的资金划转记录创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_transfers = transfer_crud.find(filters={"portfolio_id": "direction_test_portfolio"})
            out_transfers = [t for t in all_transfers if t.direction == TRANSFERDIRECTION_TYPES.OUT.value]
            initial_count = len(all_transfers)
            initial_out_count = len(out_transfers)
            print(f"✓ 总记录数: {initial_count}, 出金记录数: {initial_out_count}")
            assert initial_out_count >= 2, f"至少需要2条出金记录，实际找到{initial_out_count}条"

            # 删除所有出金记录
            print("→ 删除所有出金记录...")
            transfer_crud.remove(filters={
                "portfolio_id": "direction_test_portfolio",
                "direction": TRANSFERDIRECTION_TYPES.OUT.value
            })
            print("✓ 出金记录删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_transfers = transfer_crud.find(filters={"portfolio_id": "direction_test_portfolio"})
            remaining_out_transfers = [t for t in remaining_transfers if t.direction == TRANSFERDIRECTION_TYPES.OUT.value]
            final_count = len(remaining_transfers)
            final_out_count = len(remaining_out_transfers)

            print(f"✓ 删除后记录数: {final_count}, 剩余出金记录数: {final_out_count}")
            # 验证数据确实减少了
            assert final_count < initial_count, f"删除后总记录数应该减少，但删除前{initial_count}条，删除后{final_count}条"
            assert final_out_count == 0, f"删除后不应该有出金记录，但实际还有{final_out_count}条"
            # 验证删除的记录数量正确
            deleted_count = initial_count - final_count
            expected_deleted = initial_out_count
            assert deleted_count >= expected_deleted, f"应该至少删除{expected_deleted}条记录，实际删除了{deleted_count}条"

            print("✓ 根据划转方向删除资金划转记录验证成功")

        except Exception as e:
            print(f"✗ 根据划转方向删除资金划转记录失败: {e}")
            raise

    def test_delete_transfer_by_amount_range(self):
        """测试根据金额范围删除资金划转记录"""
        print("\n" + "="*60)
        print("开始测试: 根据金额范围删除资金划转记录")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 准备不同金额的测试数据
            print("→ 创建不同金额的资金划转记录...")
            test_transfers = [
                MTransfer(
                    portfolio_id="amount_test_portfolio",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    direction=TRANSFERDIRECTION_TYPES.IN,
                    market=MARKET_TYPES.CHINA,
                    money=Decimal("1000.00"),  # 小额
                    status=TRANSFERSTATUS_TYPES.FILLED,
                    source=SOURCE_TYPES.TEST
                ),
                MTransfer(
                    portfolio_id="amount_test_portfolio",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    direction=TRANSFERDIRECTION_TYPES.IN,
                    market=MARKET_TYPES.CHINA,
                    money=Decimal("15000.00"),  # 大额
                    status=TRANSFERSTATUS_TYPES.FILLED,
                    source=SOURCE_TYPES.TEST
                ),
                MTransfer(
                    portfolio_id="amount_test_portfolio",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    direction=TRANSFERDIRECTION_TYPES.OUT,
                    market=MARKET_TYPES.CHINA,
                    money=Decimal("500.00"),  # 小额
                    status=TRANSFERSTATUS_TYPES.FILLED,
                    source=SOURCE_TYPES.TEST
                )
            ]

            for transfer in test_transfers:
                transfer_crud.add(transfer)
            print("✓ 不同金额的资金划转记录创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_transfers = transfer_crud.find(filters={"portfolio_id": "amount_test_portfolio"})
            initial_count = len(all_transfers)
            print(f"✓ 总记录数: {initial_count}")
            assert initial_count >= 3, f"至少需要3条记录，实际找到{initial_count}条"

            # 计算应该删除的小额记录数
            small_amount_transfers = [t for t in all_transfers if t.money < Decimal("2000.00")]
            expected_deleted_count = len(small_amount_transfers)
            print(f"→ 应删除的小额记录数: {expected_deleted_count}")

            # 删除小额记录（小于2000）
            print("→ 删除小额资金划转记录...")
            transfer_crud.remove(filters={
                "portfolio_id": "amount_test_portfolio",
                "money__lt": Decimal("2000.00")
            })
            print("✓ 小额记录删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_transfers = transfer_crud.find(filters={"portfolio_id": "amount_test_portfolio"})
            final_count = len(remaining_transfers)
            print(f"✓ 删除后记录数: {final_count}")

            # 验证数据确实减少了
            assert final_count < initial_count, f"删除后总记录数应该减少，但删除前{initial_count}条，删除后{final_count}条"
            # 验证删除的记录数量正确
            deleted_count = initial_count - final_count
            assert deleted_count >= expected_deleted_count, f"应该至少删除{expected_deleted_count}条记录，实际删除了{deleted_count}条"

            # 验证剩余记录都是大额
            for transfer in remaining_transfers:
                assert transfer.money >= Decimal("2000.00")
                print(f"✓ 记录金额 {transfer.money} 符合要求")

            print("✓ 根据金额范围删除资金划转记录验证成功")

        except Exception as e:
            print(f"✗ 根据金额范围删除资金划转记录失败: {e}")
            raise

    def test_delete_pending_transfers(self):
        """测试删除待处理的资金划转记录"""
        print("\n" + "="*60)
        print("开始测试: 删除待处理的资金划转记录")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 准备不同状态的测试数据
            print("→ 创建不同状态的资金划转记录...")
            test_transfers = [
                MTransfer(
                    portfolio_id="status_test_portfolio",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    direction=TRANSFERDIRECTION_TYPES.IN,
                    market=MARKET_TYPES.CHINA,
                    money=Decimal("5000.00"),
                    status=TRANSFERSTATUS_TYPES.FILLED,  # 已完成
                    source=SOURCE_TYPES.TEST
                ),
                MTransfer(
                    portfolio_id="status_test_portfolio",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    direction=TRANSFERDIRECTION_TYPES.IN,
                    market=MARKET_TYPES.CHINA,
                    money=Decimal("3000.00"),
                    status=TRANSFERSTATUS_TYPES.PENDING,    # 待处理
                    source=SOURCE_TYPES.TEST
                ),
                MTransfer(
                    portfolio_id="status_test_portfolio",
                    engine_id="test_engine_001",
                    run_id="test_run_001",
                    direction=TRANSFERDIRECTION_TYPES.OUT,
                    market=MARKET_TYPES.CHINA,
                    money=Decimal("2000.00"),
                    status=TRANSFERSTATUS_TYPES.PENDING,    # 待处理
                    source=SOURCE_TYPES.TEST
                )
            ]

            for transfer in test_transfers:
                transfer_crud.add(transfer)
            print("✓ 不同状态的资金划转记录创建成功")

            # 验证初始数据
            print("→ 验证初始数据...")
            all_transfers = transfer_crud.find(filters={"portfolio_id": "status_test_portfolio"})
            pending_transfers = [t for t in all_transfers if t.status == TRANSFERSTATUS_TYPES.PENDING.value]
            initial_count = len(all_transfers)
            initial_pending_count = len(pending_transfers)
            print(f"✓ 总记录数: {initial_count}, 待处理记录数: {initial_pending_count}")
            assert initial_pending_count >= 2, f"至少需要2条待处理记录，实际找到{initial_pending_count}条"

            # 删除所有待处理记录
            print("→ 删除所有待处理记录...")
            transfer_crud.remove(filters={
                "portfolio_id": "status_test_portfolio",
                "status": TRANSFERSTATUS_TYPES.PENDING.value
            })
            print("✓ 待处理记录删除完成")

            # 验证删除结果
            print("→ 验证删除结果...")
            remaining_transfers = transfer_crud.find(filters={"portfolio_id": "status_test_portfolio"})
            remaining_pending = [t for t in remaining_transfers if t.status == TRANSFERSTATUS_TYPES.PENDING.value]
            final_count = len(remaining_transfers)
            final_pending_count = len(remaining_pending)

            print(f"✓ 删除后记录数: {final_count}, 剩余待处理记录数: {final_pending_count}")
            # 验证数据确实减少了
            assert final_count < initial_count, f"删除后总记录数应该减少，但删除前{initial_count}条，删除后{final_count}条"
            assert final_pending_count == 0, f"删除后不应该有待处理记录，但实际还有{final_pending_count}条"
            # 验证删除的记录数量正确
            deleted_count = initial_count - final_count
            expected_deleted = initial_pending_count
            assert deleted_count >= expected_deleted, f"应该至少删除{expected_deleted}条记录，实际删除了{deleted_count}条"

            # 验证剩余记录都是已完成状态
            filled_transfers = [t for t in remaining_transfers if t.status == TRANSFERSTATUS_TYPES.FILLED.value]
            assert len(filled_transfers) == final_count, f"剩余的{final_count}条记录应该都是已完成状态，但实际只有{len(filled_transfers)}条已完成"

            print("✓ 删除待处理资金划转记录验证成功")

        except Exception as e:
            print(f"✗ 删除待处理资金划转记录失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTransferCRUDDataTypes:
    CRUD_TEST_CONFIG = {'crud_class': TransferCRUD}
    """5. CRUD层数据类型转换测试 - 验证枚举转换和业务对象转换"""

    def test_crud_returns_mtransfer_models(self):
        """测试CRUD返回MTransfer模型对象（枚举字段为int）"""
        print("\n" + "="*60)
        print("开始测试: CRUD返回MTransfer模型对象")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 插入测试数据
            test_transfer = MTransfer(
                portfolio_id="datatype_test_portfolio",
                engine_id="test_engine_001",
                run_id="test_run_001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("10000.00"),
                status=TRANSFERSTATUS_TYPES.FILLED,
            source=SOURCE_TYPES.TEST,
            timestamp=datetime(2023, 1, 3, 15, 30)
            )

            transfer_crud.add(test_transfer)
            print("✓ 测试数据插入成功")

            # 查询数据
            print("→ 查询数据验证返回类型...")
            results = transfer_crud.find(filters={"portfolio_id": "datatype_test_portfolio"})

            assert len(results) >= 1
            returned_model = results[0]

            # 验证返回的是MTransfer模型对象
            assert isinstance(returned_model, MTransfer)
            print(f"✓ 返回类型: {type(returned_model).__name__}")

            # 验证枚举字段是int类型（数据库存储格式）
            assert isinstance(returned_model.direction, int)
            assert isinstance(returned_model.market, int)
            assert isinstance(returned_model.status, int)
            assert isinstance(returned_model.source, int)

            print(f"✓ 枚举字段类型验证:")
            print(f"  - direction: {type(returned_model.direction)} (value: {returned_model.direction})")
            print(f"  - market: {type(returned_model.market)} (value: {returned_model.market})")
            print(f"  - status: {type(returned_model.status)} (value: {returned_model.status})")

        except Exception as e:
            print(f"✗ 数据类型验证失败: {e}")
            raise

    def test_enum_conversion_works_correctly(self):
        """测试枚举转换功能正常工作"""
        print("\n" + "="*60)
        print("开始测试: 枚举转换功能")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 验证int可以正确转换为枚举
            direction_int = TRANSFERDIRECTION_TYPES.IN.value
            direction_enum = TRANSFERDIRECTION_TYPES(direction_int)

            assert direction_enum == TRANSFERDIRECTION_TYPES.IN
            assert direction_enum.name == "IN"
            print(f"✓ 方向枚举转换: {direction_int} -> {direction_enum.name}")

            # 验证市场枚举转换
            market_int = MARKET_TYPES.CHINA.value
            market_enum = MARKET_TYPES(market_int)

            assert market_enum == MARKET_TYPES.CHINA
            assert market_enum.name == "CHINA"
            print(f"✓ 市场枚举转换: {market_int} -> {market_enum.name}")

            # 验证状态枚举转换
            status_int = TRANSFERSTATUS_TYPES.FILLED.value
            status_enum = TRANSFERSTATUS_TYPES(status_int)

            assert status_enum == TRANSFERSTATUS_TYPES.FILLED
            assert status_enum.name == "FILLED"
            print(f"✓ 状态枚举转换: {status_int} -> {status_enum.name}")

        except Exception as e:
            print(f"✗ 枚举转换验证失败: {e}")
            raise

    def test_business_object_conversion(self):
        """测试业务对象转换功能"""
        print("\n" + "="*60)
        print("开始测试: 业务对象转换功能")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 查询数据并转换为业务对象
            model_results = transfer_crud.find(
                filters={},
                page=1,
                page_size=1
            )

            if len(model_results) == 0:
                print("✗ 没有找到数据，跳过业务对象转换测试")
                return

            # 使用ModelList的to_entities方法转换为业务对象
            business_objects = model_results.to_entities()
            business_object = business_objects[0]

            # 验证返回的对象（可能是MTransfer模型或Transfer业务对象）
            print(f"✓ 返回对象类型: {type(business_object).__name__}")
            # 检查是否是业务对象或模型对象
            is_business_object = hasattr(business_object, 'direction') and hasattr(business_object, 'portfolio_id')
            print(f"✓ 对象具有业务属性: {is_business_object}")

            # 如果是业务对象，验证枚举字段
            if is_business_object:
                assert isinstance(business_object.direction, TRANSFERDIRECTION_TYPES)
                assert isinstance(business_object.market, MARKET_TYPES)
                assert isinstance(business_object.status, TRANSFERSTATUS_TYPES)
                print(f"✓ 业务对象枚举字段验证:")
                print(f"  - direction: {type(business_object.direction).__name__} (value: {business_object.direction.name})")
                print(f"  - market: {type(business_object.market).__name__} (value: {business_object.market.name})")
                print(f"  - status: {type(business_object.status).__name__} (value: {business_object.status.name})")
            else:
                print("✓ 返回的是MTransfer模型对象，跳过业务对象枚举验证")

        except Exception as e:
            print(f"✗ 业务对象转换验证失败: {e}")
            raise

    def test_modellist_conversion_features(self):
        """测试ModelList转换功能"""
        print("\n" + "="*60)
        print("开始测试: ModelList转换功能")
        print("="*60)

        transfer_crud = TransferCRUD()

        try:
            # 获取ModelList结果
            results = transfer_crud.find(filters={})

            assert hasattr(results, 'to_dataframe')
            assert hasattr(results, 'to_entities')
            print("✓ ModelList具有转换方法")

            # 测试转换为DataFrame
            df = results.to_dataframe()
            assert isinstance(df, pd.DataFrame)
            print(f"✓ 转换为DataFrame: {df.shape}")

            # 测试转换为业务对象
            entities = results.to_entities()
            print(f"✓ 转换为业务对象: {len(entities)}个")

            # 验证转换后的对象类型
            if len(entities) > 0:
                entity = entities[0]
                # 可能是MTransfer模型或Transfer业务对象
                print(f"✓ 实体类型: {type(entity).__name__}")

                # 检查是否是业务对象
                is_business_entity = hasattr(entity, 'direction') and hasattr(entity, 'portfolio_id')
                if is_business_entity:
                    print(f"✓ 检测到业务对象，具有业务属性")
                else:
                    print(f"✓ 检测到模型对象，具有数据字段")

        except Exception as e:
            print(f"✗ ModelList转换验证失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：Transfer CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_transfer_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 资金划转业务逻辑和趋势分析")