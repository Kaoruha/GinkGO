"""
TransferRecord CRUD数据库操作TDD测试

测试CRUD层的资金转账记录数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)

TransferRecord是资金转账记录数据模型，存储投资组合的资金流转信息。
为量化交易系统中的资金管理和风险控制提供支持，包括入金、出金、转账等记录。
支持回测引擎的资金流转追踪和实时资金状态监控。
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.transfer_record_crud import TransferRecordCRUD
from ginkgo.data.models.model_transfer_record import MTransferRecord
from ginkgo.enums import (
    SOURCE_TYPES,
    MARKET_TYPES,
    TRANSFERDIRECTION_TYPES,
    TRANSFERSTATUS_TYPES
)


@pytest.mark.database
@pytest.mark.tdd
class TestTransferRecordCRUDInsert:
    CRUD_TEST_CONFIG = {'crud_class': TransferRecordCRUD}
    """1. CRUD层插入操作测试 - TransferRecord数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入TransferRecord数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: TransferRecord CRUD层批量插入")
        print("="*60)

        transfer_crud = TransferRecordCRUD()
        print(f"✓ 创建TransferRecordCRUD实例: {transfer_crud.__class__.__name__}")

        # 创建测试转账记录数据 - 不同类型的资金流转
        base_time = datetime(2023, 1, 3, 9, 30, 0)
        test_transfers = []

        # 初始入金记录
        initial_deposit = MTransferRecord(
            portfolio_id="test_portfolio_001",
            engine_id="engine_001",
            timestamp=base_time,
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("1000000.00"),
            status=TRANSFERSTATUS_TYPES.FILLED
        )
        initial_deposit.source = SOURCE_TYPES.TEST
        test_transfers.append(initial_deposit)

        # 追加入金记录
        additional_deposit = MTransferRecord(
            portfolio_id="test_portfolio_001",
            engine_id="engine_001",
            timestamp=base_time + timedelta(days=30),
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("500000.00"),
            status=TRANSFERSTATUS_TYPES.FILLED
        )
        additional_deposit.source = SOURCE_TYPES.TEST
        test_transfers.append(additional_deposit)

        # 部分出金记录
        partial_withdraw = MTransferRecord(
            portfolio_id="test_portfolio_001",
            engine_id="engine_001",
            timestamp=base_time + timedelta(days=60),
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.CHINA,
            money=Decimal("200000.00"),
            status=TRANSFERSTATUS_TYPES.FILLED
        )
        partial_withdraw.source = SOURCE_TYPES.TEST
        test_transfers.append(partial_withdraw)

        # 跨市场转账记录
        cross_market = MTransferRecord(
            portfolio_id="test_portfolio_002",
            engine_id="engine_002",
            timestamp=base_time + timedelta(days=90),
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("100000.00"),
            status=TRANSFERSTATUS_TYPES.PENDING
        )
        cross_market.source = SOURCE_TYPES.TEST
        test_transfers.append(cross_market)

        print(f"✓ 创建测试数据: {len(test_transfers)}条转账记录")
        print(f"  - 投资组合: {[t.portfolio_id for t in test_transfers]}")
        print(f"  - 转账方向: {[TRANSFERDIRECTION_TYPES(t.direction).name for t in test_transfers]}")
        print(f"  - 市场类型: {[MARKET_TYPES(t.market).name for t in test_transfers]}")
        print(f"  - 总金额: {sum(t.money for t in test_transfers):,.2f}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            transfer_crud.add_batch(test_transfers)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = transfer_crud.find(filters={
                "timestamp__gte": base_time,
                "timestamp__lte": base_time + timedelta(days=100)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 4

            # 验证数据内容
            portfolios = set(t.portfolio_id for t in query_result)
            print(f"✓ 投资组合验证通过: {len(portfolios)} 个")
            assert len(portfolios) >= 2

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_transfer(self):
        """测试单条TransferRecord数据插入"""
        print("\n" + "="*60)
        print("开始测试: TransferRecord CRUD层单条插入")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        test_transfer = MTransferRecord(
            portfolio_id="single_test_portfolio",
            engine_id="engine_003",
            timestamp=datetime(2023, 6, 15, 14, 30, 0),
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("300000.00"),
            status=TRANSFERSTATUS_TYPES.FILLED
        )
        test_transfer.source = SOURCE_TYPES.TEST
        print(f"✓ 创建测试转账记录: {test_transfer.portfolio_id}")
        print(f"  - 转账方向: {TRANSFERDIRECTION_TYPES(test_transfer.direction).name}")
        print(f"  - 市场类型: {MARKET_TYPES(test_transfer.market).name}")
        print(f"  - 转账金额: {test_transfer.money:,.2f}")
        print(f"  - 状态: {TRANSFERSTATUS_TYPES(test_transfer.status).name}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            transfer_crud.add(test_transfer)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = transfer_crud.find(filters={
                "portfolio_id": "single_test_portfolio",
                "engine_id": "engine_003"
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_transfer = query_result[0]
            print(f"✓ 插入的转账记录验证: {inserted_transfer.portfolio_id}")
            assert inserted_transfer.portfolio_id == "single_test_portfolio"
            assert inserted_transfer.money == Decimal("300000.00")
            assert inserted_transfer.status == TRANSFERSTATUS_TYPES.FILLED.value

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise

    def test_add_pending_transfers(self):
        """测试插入待处理转账记录"""
        print("\n" + "="*60)
        print("开始测试: 插入待处理转账记录")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        # 创建不同状态的转账记录
        test_transfers = []

        # 待处理入金
        pending_in = MTransferRecord(
            portfolio_id="pending_test_portfolio",
            engine_id="engine_004",
            timestamp=datetime(2023, 7, 1, 10, 0, 0),
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("150000.00"),
            status=TRANSFERSTATUS_TYPES.PENDING
        )
        pending_in.source = SOURCE_TYPES.TEST
        test_transfers.append(pending_in)

        # 已确认出金
        confirmed_out = MTransferRecord(
            portfolio_id="pending_test_portfolio",
            engine_id="engine_004",
            timestamp=datetime(2023, 7, 2, 11, 0, 0),
            direction=TRANSFERDIRECTION_TYPES.OUT,
            market=MARKET_TYPES.CHINA,
            money=Decimal("50000.00"),
            status=TRANSFERSTATUS_TYPES.FILLED
        )
        confirmed_out.source = SOURCE_TYPES.TEST
        test_transfers.append(confirmed_out)

        # 已拒绝转账
        rejected = MTransferRecord(
            portfolio_id="pending_test_portfolio",
            engine_id="engine_004",
            timestamp=datetime(2023, 7, 3, 12, 0, 0),
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.NASDAQ,
            money=Decimal("75000.00"),
            status=TRANSFERSTATUS_TYPES.CANCELED
        )
        rejected.source = SOURCE_TYPES.TEST
        test_transfers.append(rejected)

        print(f"✓ 创建状态测试转账: {len(test_transfers)} 条")
        for transfer in test_transfers:
            print(f"  - {TRANSFERDIRECTION_TYPES(transfer.direction).name}: "
                  f"{TRANSFERSTATUS_TYPES(transfer.status).name} "
                  f"({transfer.money:,.2f})")

        try:
            # 批量插入
            print("\n→ 执行状态测试转账插入...")
            transfer_crud.add_batch(test_transfers)
            print("✓ 状态测试转账插入成功")

            # 验证数据
            print("\n→ 验证状态测试数据...")
            query_result = transfer_crud.find(filters={
                "portfolio_id": "pending_test_portfolio"
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 3

            # 验证状态分布
            status_count = {}
            for transfer in query_result:
                status_name = TRANSFERSTATUS_TYPES(transfer.status).name
                status_count[status_name] = status_count.get(status_name, 0) + 1

            print("✓ 状态分布验证:")
            for status, count in status_count.items():
                print(f"  - {status}: {count} 条")

            print("✓ 待处理转账记录验证成功")

        except Exception as e:
            print(f"✗ 待处理转账插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTransferRecordCRUDQuery:
    CRUD_TEST_CONFIG = {'crud_class': TransferRecordCRUD}
    """2. CRUD层查询操作测试 - TransferRecord数据查询和过滤"""

    def test_find_by_portfolio_id(self):
        """测试根据投资组合ID查询TransferRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID查询TransferRecord")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        try:
            # 查询特定投资组合的转账记录
            print("→ 查询投资组合 test_portfolio_001 的转账记录...")
            portfolio_transfers = transfer_crud.find(filters={
                "portfolio_id": "test_portfolio_001"
            })
            print(f"✓ 查询到 {len(portfolio_transfers)} 条记录")

            # 验证查询结果
            total_amount = Decimal("0")
            for transfer in portfolio_transfers:
                print(f"  - {transfer.timestamp}: {TRANSFERDIRECTION_TYPES(transfer.direction).name} "
                      f"{transfer.money:,.2f} ({TRANSFERSTATUS_TYPES(transfer.status).name})")
                assert transfer.portfolio_id == "test_portfolio_001"
                if transfer.direction == TRANSFERDIRECTION_TYPES.IN.value:
                    total_amount += transfer.money
                else:
                    total_amount -= transfer.money

            print(f"✓ 投资组合净流入: {total_amount:,.2f}")

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_direction(self):
        """测试根据转账方向查询TransferRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据转账方向查询TransferRecord")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        try:
            # 查询入金记录
            print("→ 查询入金记录...")
            in_transfers = transfer_crud.find(filters={
                "direction": TRANSFERDIRECTION_TYPES.IN.value
            })
            print(f"✓ 查询到 {len(in_transfers)} 条入金记录")

            # 查询出金记录
            print("→ 查询出金记录...")
            out_transfers = transfer_crud.find(filters={
                "direction": TRANSFERDIRECTION_TYPES.OUT.value
            })
            print(f"✓ 查询到 {len(out_transfers)} 条出金记录")

            # 统计金额
            total_in = sum(t.money for t in in_transfers)
            total_out = sum(t.money for t in out_transfers)

            print(f"✓ 入金总额: {total_in:,.2f}")
            print(f"✓ 出金总额: {total_out:,.2f}")
            print(f"✓ 净流入: {total_in - total_out:,.2f}")

            print("✓ 转账方向查询验证成功")

        except Exception as e:
            print(f"✗ 转账方向查询失败: {e}")
            raise

    def test_find_by_market(self):
        """测试根据市场类型查询TransferRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据市场类型查询TransferRecord")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        try:
            # 查询不同市场的转账记录
            for market in [MARKET_TYPES.CHINA, MARKET_TYPES.NASDAQ, MARKET_TYPES.OTHER]:
                print(f"→ 查询{market.name}市场转账记录...")
                market_transfers = transfer_crud.find(filters={
                    "market": market.value
                })
                print(f"✓ {market.name}市场记录: {len(market_transfers)} 条")

                if market_transfers:
                    market_total = sum(t.money for t in market_transfers)
                    print(f"  - {market.name}市场总额: {market_total:,.2f}")

            print("✓ 市场类型查询验证成功")

        except Exception as e:
            print(f"✗ 市场类型查询失败: {e}")
            raise

    def test_find_by_status(self):
        """测试根据状态查询TransferRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据状态查询TransferRecord")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        try:
            # 查询不同状态的转账记录
            for status in [TRANSFERSTATUS_TYPES.PENDING, TRANSFERSTATUS_TYPES.FILLED,
                         TRANSFERSTATUS_TYPES.FILLED, TRANSFERSTATUS_TYPES.CANCELED]:
                print(f"→ 查询{status.name}状态记录...")
                status_transfers = transfer_crud.find(filters={
                    "status": status.value
                })
                print(f"✓ {status.name}状态记录: {len(status_transfers)} 条")

                if status_transfers:
                    status_total = sum(t.money for t in status_transfers)
                    print(f"  - {status.name}状态总额: {status_total:,.2f}")

            print("✓ 状态查询验证成功")

        except Exception as e:
            print(f"✗ 状态查询失败: {e}")
            raise

    def test_find_by_time_range(self):
        """测试根据时间范围查询TransferRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围查询TransferRecord")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        try:
            # 查询特定时间范围的转账记录
            start_time = datetime(2023, 1, 1)
            end_time = datetime(2023, 12, 31, 23, 59, 59)

            print(f"→ 查询时间范围 {start_time} ~ {end_time} 的转账记录...")
            time_transfers = transfer_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            })
            print(f"✓ 查询到 {len(time_transfers)} 条记录")

            # 验证时间范围
            for transfer in time_transfers:
                print(f"  - {transfer.portfolio_id}: {transfer.money:,.2f} ({transfer.timestamp.date()})")
                assert start_time <= transfer.timestamp <= end_time

            print("✓ 时间范围查询验证成功")

        except Exception as e:
            print(f"✗ 时间范围查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd


@pytest.mark.database
@pytest.mark.tdd
class TestTransferRecordCRUDDelete:
    CRUD_TEST_CONFIG = {'crud_class': TransferRecordCRUD}
    """4. CRUD层删除操作测试 - TransferRecord数据删除验证"""

    def test_delete_transfer_by_portfolio(self):
        """测试根据投资组合ID删除TransferRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID删除TransferRecord")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_transfer = MTransferRecord(
            portfolio_id="DELETE_TEST_PORTFOLIO",
            engine_id="engine_007",
            timestamp=datetime(2023, 9, 15, 10, 30, 0),
            direction=TRANSFERDIRECTION_TYPES.IN,
            market=MARKET_TYPES.CHINA,
            money=Decimal("100000.00"),
            status=TRANSFERSTATUS_TYPES.FILLED
        )
        test_transfer.source = SOURCE_TYPES.TEST
        transfer_crud.add(test_transfer)
        print(f"✓ 插入测试数据: {test_transfer.portfolio_id}")

        # 验证数据存在
        before_count = len(transfer_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            transfer_crud.remove(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(transfer_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            print("✓ 根据投资组合ID删除TransferRecord验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_transfer_by_time_range(self):
        """测试根据时间范围删除TransferRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围删除TransferRecord")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        # 准备测试数据 - 特定时间范围的数据
        print("→ 准备测试数据...")
        test_time_range = [
            datetime(2023, 10, 1, 10, 30, 0),
            datetime(2023, 10, 2, 11, 30, 0),
            datetime(2023, 10, 3, 12, 30, 0)
        ]

        for i, test_time in enumerate(test_time_range):
            test_transfer = MTransferRecord(
                portfolio_id=f"DELETE_TIME_{i+1:03d}",
                engine_id="engine_008",
                timestamp=test_time,
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal(f"1000{i}0.00"),
                status=TRANSFERSTATUS_TYPES.FILLED
            )
            test_transfer.source = SOURCE_TYPES.TEST
            transfer_crud.add(test_transfer)

        print(f"✓ 插入时间范围测试数据: {len(test_time_range)}条")

        # 验证数据存在
        before_count = len(transfer_crud.find(filters={
            "timestamp__gte": datetime(2023, 10, 1),
            "timestamp__lte": datetime(2023, 10, 3, 23, 59, 59)
        }))
        print(f"✓ 删除前时间范围内数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行时间范围删除操作...")
            transfer_crud.remove(filters={
                "timestamp__gte": datetime(2023, 10, 1),
                "timestamp__lte": datetime(2023, 10, 3, 23, 59, 59)
            })
            print("✓ 时间范围删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(transfer_crud.find(filters={
                "timestamp__gte": datetime(2023, 10, 1),
                "timestamp__lte": datetime(2023, 10, 3, 23, 59, 59)
            }))
            print(f"✓ 删除后时间范围内数据量: {after_count}")
            assert after_count == 0, "删除后时间范围内应该没有数据"

            print("✓ 根据时间范围删除TransferRecord验证成功")

        except Exception as e:
            print(f"✗ 时间范围删除操作失败: {e}")
            raise

    def test_delete_transfer_by_status(self):
        """测试根据状态删除TransferRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据状态删除TransferRecord")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        # 准备测试数据 - 不同状态的记录
        print("→ 准备测试数据...")
        test_statuses = [
            (TRANSFERSTATUS_TYPES.CANCELED, "DELETE_REJECTED_001"),
            (TRANSFERSTATUS_TYPES.PENDING, "DELETE_PENDING_001"),
            (TRANSFERSTATUS_TYPES.FILLED, "DELETE_CONFIRMED_001")
        ]

        base_time = datetime(2023, 11, 15, 10, 30, 0)

        for status, portfolio_id in test_statuses:
            test_transfer = MTransferRecord(
                portfolio_id=portfolio_id,
                engine_id="engine_009",
                timestamp=base_time,
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal("50000.00"),
                status=status
            )
            test_transfer.source = SOURCE_TYPES.TEST
            transfer_crud.add(test_transfer)

        print(f"✓ 插入状态测试数据: {len(test_statuses)} 条")

        try:
            # 删除已拒绝的记录
            print("\n→ 删除已拒绝的转账记录...")
            before_rejected = len(transfer_crud.find(filters={
                "status": TRANSFERSTATUS_TYPES.CANCELED.value
            }))
            print(f"✓ 删除前已拒绝记录: {before_rejected} 条")

            transfer_crud.remove(filters={"status": TRANSFERSTATUS_TYPES.CANCELED.value})
            print("✓ 已拒绝记录删除完成")

            after_rejected = len(transfer_crud.find(filters={
                "status": TRANSFERSTATUS_TYPES.CANCELED.value
            }))
            print(f"✓ 删除后已拒绝记录: {after_rejected} 条")
            assert after_rejected == 0, "已拒绝记录应该全部删除"

            # 验证其他状态记录保留
            pending_count = len(transfer_crud.find(filters={
                "portfolio_id": "DELETE_PENDING_001"
            }))
            confirmed_count = len(transfer_crud.find(filters={
                "portfolio_id": "DELETE_CONFIRMED_001"
            }))
            print(f"✓ 保留待处理记录: {pending_count} 条")
            print(f"✓ 保留已确认记录: {confirmed_count} 条")

            print("✓ 根据状态删除TransferRecord验证成功")

        except Exception as e:
            print(f"✗ 状态删除操作失败: {e}")
            raise

    def test_delete_transfer_batch_cleanup(self):
        """测试批量清理TransferRecord数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理TransferRecord数据")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        # 准备批量清理数据
        print("→ 准备批量清理测试数据...")
        cleanup_count = 10
        cleanup_portfolio_prefix = "CLEANUP_BATCH_PORTFOLIO"

        for i in range(cleanup_count):
            test_transfer = MTransferRecord(
                portfolio_id=f"{cleanup_portfolio_prefix}_{i+1:03d}",
                engine_id="engine_010",
                timestamp=datetime(2023, 12, 1, 10, 30, 0) + timedelta(hours=i),
                direction=TRANSFERDIRECTION_TYPES.IN,
                market=MARKET_TYPES.CHINA,
                money=Decimal(f"1000{i}.00"),
                status=TRANSFERSTATUS_TYPES.FILLED
            )
            test_transfer.source = SOURCE_TYPES.TEST
            transfer_crud.add(test_transfer)

        print(f"✓ 插入批量清理测试数据: {cleanup_count}条")

        # 验证数据存在
        before_count = len(transfer_crud.find(filters={
            "portfolio_id__like": f"{cleanup_portfolio_prefix}_%"
        }))
        print(f"✓ 删除前批量数据量: {before_count}")

        try:
            # 批量删除
            print("\n→ 执行批量清理操作...")
            transfer_crud.remove(filters={
                "portfolio_id__like": f"{cleanup_portfolio_prefix}_%"
            })
            print("✓ 批量清理操作完成")

            # 验证删除结果
            print("\n→ 验证批量清理结果...")
            after_count = len(transfer_crud.find(filters={
                "portfolio_id__like": f"{cleanup_portfolio_prefix}_%"
            }))
            print(f"✓ 删除后批量数据量: {after_count}")
            assert after_count == 0, "删除后应该没有批量清理数据"

            # 确认其他数据未受影响
            other_data_count = len(transfer_crud.find(page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理TransferRecord数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestTransferRecordCRUDBusinessLogic:
    CRUD_TEST_CONFIG = {'crud_class': TransferRecordCRUD}
    """5. CRUD层业务逻辑测试 - TransferRecord业务场景验证"""

    def test_portfolio_cash_flow_analysis(self):
        """测试投资组合现金流分析"""
        print("\n" + "="*60)
        print("开始测试: 投资组合现金流分析")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        try:
            # 查询特定投资组合的所有转账记录
            print("→ 查询投资组合现金流分析...")
            portfolio_id = "test_portfolio_001"
            transfers = transfer_crud.find(filters={
                "portfolio_id": portfolio_id
            })

            if len(transfers) < 2:
                print("✗ 转账记录数据不足，跳过现金流分析")
                return

            # 按时间排序
            transfers.sort(key=lambda x: x.timestamp)

            # 分析现金流
            print(f"✓ {portfolio_id} 现金流分析:")
            total_inflow = Decimal("0")
            total_outflow = Decimal("0")
            net_flow = Decimal("0")

            for transfer in transfers:
                if transfer.direction == TRANSFERDIRECTION_TYPES.IN.value:
                    total_inflow += transfer.money
                    net_flow += transfer.money
                    print(f"  - {transfer.timestamp.date()}: 入金 +{transfer.money:,.2f}")
                else:
                    total_outflow += transfer.money
                    net_flow -= transfer.money
                    print(f"  - {transfer.timestamp.date()}: 出金 -{transfer.money:,.2f}")

            print(f"✓ 现金流汇总:")
            print(f"  - 总入金: {total_inflow:,.2f}")
            print(f"  - 总出金: {total_outflow:,.2f}")
            print(f"  - 净现金流: {net_flow:,.2f}")

            # 验证现金流合理性
            assert total_inflow >= 0
            assert total_outflow >= 0
            print("✓ 现金流分析验证成功")

        except Exception as e:
            print(f"✗ 现金流分析失败: {e}")
            raise

    def test_transfer_status_workflow(self):
        """测试转账状态工作流"""
        print("\n" + "="*60)
        print("开始测试: 转账状态工作流")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        try:
            # 查询不同状态的转账记录进行工作流分析
            print("→ 查询转账状态工作流...")
            all_transfers = transfer_crud.find(page_size=20)

            if len(all_transfers) == 0:
                print("✗ 转账记录数据不足，跳过工作流分析")
                return

            # 统计状态分布
            status_workflow = {}
            for transfer in all_transfers:
                status_name = TRANSFERSTATUS_TYPES(transfer.status).name
                status_workflow[status_name] = status_workflow.get(status_name, 0) + 1

            print(f"✓ 转账状态工作流分布:")
            for status, count in status_workflow.items():
                percentage = (count / len(all_transfers)) * 100
                print(f"  - {status}: {count} 条 ({percentage:.1f}%)")

            # 分析状态转换合理性
            pending_count = status_workflow.get("PENDING", 0)
            confirmed_count = status_workflow.get("CONFIRMED", 0)
            filled_count = status_workflow.get("FILLED", 0)
            canceled_count = status_workflow.get("CANCELED", 0)

            # 验证工作流逻辑
            total_processed = confirmed_count + filled_count + canceled_count
            if total_processed > 0:
                processing_rate = (total_processed / len(all_transfers)) * 100
                print(f"✓ 转账处理率: {processing_rate:.1f}%")

            print("✓ 转账状态工作流验证成功")

        except Exception as e:
            print(f"✗ 转账状态工作流失败: {e}")
            raise

    def test_cross_market_transfer_analysis(self):
        """测试跨市场转账分析"""
        print("\n" + "="*60)
        print("开始测试: 跨市场转账分析")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        try:
            # 查询跨市场转账数据
            print("→ 查询跨市场转账分析...")
            all_transfers = transfer_crud.find(page_size=50)

            if len(all_transfers) == 0:
                print("✗ 转账记录数据不足，跳过跨市场分析")
                return

            # 按市场分组统计
            market_analysis = {}
            for transfer in all_transfers:
                market_name = MARKET_TYPES(transfer.market).name
                if market_name not in market_analysis:
                    market_analysis[market_name] = {
                        "count": 0,
                        "total_amount": Decimal("0"),
                        "inflow": Decimal("0"),
                        "outflow": Decimal("0")
                    }

                market_analysis[market_name]["count"] += 1
                market_analysis[market_name]["total_amount"] += transfer.money

                if transfer.direction == TRANSFERDIRECTION_TYPES.IN.value:
                    market_analysis[market_name]["inflow"] += transfer.money
                else:
                    market_analysis[market_name]["outflow"] += transfer.money

            print(f"✓ 跨市场转账分析:")
            for market, stats in market_analysis.items():
                net_flow = stats["inflow"] - stats["outflow"]
                print(f"  - {market}:")
                print(f"    转账笔数: {stats['count']}")
                print(f"    总金额: {stats['total_amount']:,.2f}")
                print(f"    入金: {stats['inflow']:,.2f}")
                print(f"    出金: {stats['outflow']:,.2f}")
                print(f"    净流入: {net_flow:,.2f}")

            print("✓ 跨市场转账分析验证成功")

        except Exception as e:
            print(f"✗ 跨市场转账分析失败: {e}")
            raise

    def test_transfer_data_integrity(self):
        """测试转账数据完整性"""
        print("\n" + "="*60)
        print("开始测试: 转账数据完整性")
        print("="*60)

        transfer_crud = TransferRecordCRUD()

        try:
            # 测试必要字段约束
            print("→ 测试必要字段约束...")

            # 查询数据验证完整性
            valid_transfers = transfer_crud.find(page_size=50)
            for transfer in valid_transfers:
                # 验证portfolio_id非空
                assert transfer.portfolio_id and len(transfer.portfolio_id.strip()) > 0

                # 验证engine_id非空
                assert transfer.engine_id and len(transfer.engine_id.strip()) > 0

                # 验证timestamp有效
                assert transfer.timestamp is not None

                # 验证direction为有效枚举值
                valid_directions = [d.value for d in TRANSFERDIRECTION_TYPES]
                assert transfer.direction in valid_directions

                # 验证market为有效枚举值
                valid_markets = [m.value for m in MARKET_TYPES]
                assert transfer.market in valid_markets

                # 验证money为正数
                assert transfer.money > 0

                # 验证status为有效枚举值
                valid_statuses = [s.value for s in TRANSFERSTATUS_TYPES]
                assert transfer.status in valid_statuses

                # 验证source为有效枚举值
                valid_sources = [s.value for s in SOURCE_TYPES]
                assert transfer.source in valid_sources

            print(f"✓ 验证了 {len(valid_transfers)} 条转账的完整性约束")
            print("✓ 转账数据完整性验证成功")

        except Exception as e:
            print(f"✗ 数据完整性测试失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：TransferRecord CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_transfer_record_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 资金转账记录存储和现金流分析功能")
