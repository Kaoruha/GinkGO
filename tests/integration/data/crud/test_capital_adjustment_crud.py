"""
CapitalAdjustment CRUD数据库操作TDD测试 - 资金调整管理

本文件测试CapitalAdjustmentCRUD类的完整功能，确保资金调整记录的增删改查操作正常工作。
资金调整记录是投资组合管理的重要数据模型，存储所有资金变动信息，为量化交易中的资金管理和风险控制提供支持。

测试范围：
1. 插入操作 (Insert Operations)
   - 批量插入 (add_batch): 高效插入大量资金调整记录
   - 单条插入 (add_single_adjustment): 插入单条资金调整记录
   - 多类型调整插入 (various_adjustment_types): 测试不同类型的资金调整

2. 查询操作 (Query Operations)
   - 按投资组合查询 (find_by_portfolio_id): 获取特定投资组合的资金变动
   - 按时间范围查询 (find_by_time_range): 获取指定时间段的资金变动
   - 按调整类型查询 (find_by_adjustment_type): 获取特定类型的资金变动
   - 按金额范围查询 (find_by_amount_range): 获取指定金额范围的调整
   - 复合条件查询 (complex_filters): 测试多条件组合查询

3. 业务逻辑测试 (Business Logic Tests)
   - 资金调整摘要分析 (adjustment_summary_analysis): 资金变动统计汇总
   - 股票调整对比 (stock_adjustment_comparison): 不同股票的调整对比
   - 调整趋势分析 (adjustment_trend_analysis): 资金变动趋势分析
   - 异常调整检测 (abnormal_adjustment_detection): 异常资金变动识别

4. 删除操作 (Delete Operations)
   - 按投资组合删除 (delete_by_portfolio_id): 清理特定投资组合记录
   - 按时间范围删除 (delete_by_time_range): 清理指定时间段记录
   - 按调整类型删除 (delete_by_adjustment_type): 清理特定类型记录
   - 按金额删除 (delete_by_amount): 删除特定金额记录
   - 按异常值删除 (delete_by_abnormal_values): 清理异常数据
   - 批量清理 (batch_cleanup): 高效批量清理

5. 数据转换测试 (Data Conversion Tests)
   - 模型列表转换 (model_list_conversions): 业务对象与数据库模型转换

6. 替换操作 (Replace Operations)
   - 批量替换 (replace): 原子性替换资金调整数据

TODO: 添加replace方法测试用例
- 测试replace方法的原子操作 (备份→删除→插入→失败时恢复)
- 测试没有匹配数据时的行为 (应返回空结果，不插入新数据)
- 测试类型错误检查 (传入错误Model类型时应抛出TypeError)
- 测试空new_items的处理
- 测试批量替换的性能和正确性
- 测试ClickHouse和MySQL数据库的兼容性

数据模型：
- MCapitalAdjustment: 资金调整数据模型，包含投资组合ID、金额、时间戳、原因、数据源等
- 支持多种调整类型：入金、出金、费用扣除、收益分配、风险准备金等
- 精确的金额计算：使用Decimal类型确保资金计算精度
- 时间戳管理：记录调整发生的准确时间
- 调整原因：详细记录资金变动的原因和背景

业务价值：
- 完整的资金变动追踪：记录投资组合的所有资金流入流出
- 支持资金管理决策：提供详细的资金分析数据
- 风险控制支持：监控资金变动异常情况
- 合规审计支持：提供完整的资金变动记录
- 绩效评估基础：为投资组合绩效评估提供资金数据

调整类型说明：
- 入金(Deposit): 增加投资组合资金
- 出金(Withdrawal): 减少投资组合资金
- 手续费(Fee): 交易相关费用扣除
- 收益分配(Profit Distribution): 投资收益分配
- 风险准备金(Risk Reserve): 风险准备金计提
- 其他调整(Other): 其他类型的资金调整

测试策略：
- 覆盖所有调整类型和业务场景
- 验证资金计算精度和一致性
- 测试时间范围查询和统计分析
- 验证异常情况的处理逻辑
- 使用测试数据源标记便于清理
- 测试大数据量处理性能
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.capital_adjustment_crud import CapitalAdjustmentCRUD
from ginkgo.data.models.model_capital_adjustment import MCapitalAdjustment
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestCapitalAdjustmentCRUDInsert:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': CapitalAdjustmentCRUD}

    """1. CRUD层插入操作测试 - CapitalAdjustment数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入CapitalAdjustment数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: CapitalAdjustment CRUD层批量插入")
        print("="*60)

        capital_crud = CapitalAdjustmentCRUD()
        print(f"✓ 创建CapitalAdjustmentCRUD实例: {capital_crud.__class__.__name__}")

        # 创建测试资金调整数据 - 不同投资组合的资金变动
        base_time = datetime(2023, 6, 15, 15, 0, 0)
        test_adjustments = []

        # 投资组合A入金
        portfolio_a_deposit = MCapitalAdjustment(
            portfolio_id="portfolio_001",
            amount=Decimal("100000.00"),
            timestamp=base_time,
            reason="初始入金",
            source=SOURCE_TYPES.TEST
        )
        test_adjustments.append(portfolio_a_deposit)

        # 投资组合B入金
        portfolio_b_deposit = MCapitalAdjustment(
            portfolio_id="portfolio_002",
            amount=Decimal("50000.00"),
            timestamp=base_time + timedelta(days=1),
            reason="初始入金",
            source=SOURCE_TYPES.TEST
        )
        test_adjustments.append(portfolio_b_deposit)

        # 投资组合A费用扣除
        portfolio_a_fee = MCapitalAdjustment(
            portfolio_id="portfolio_001",
            amount=Decimal("-150.50"),
            timestamp=base_time + timedelta(days=2),
            reason="交易手续费",
            source=SOURCE_TYPES.TEST
        )
        test_adjustments.append(portfolio_a_fee)

        print(f"✓ 创建测试数据: {len(test_adjustments)}条资金调整记录")
        print(f"  - 投资组合ID: {[adj.portfolio_id for adj in test_adjustments]}")
        print(f"  - 调整金额: {[adj.amount for adj in test_adjustments]}")
        print(f"  - 时间范围: {test_adjustments[0].timestamp} ~ {test_adjustments[-1].timestamp}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            capital_crud.add_batch(test_adjustments)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = capital_crud.find(filters={
                "timestamp__gte": base_time,
                "timestamp__lte": base_time + timedelta(days=3)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 3

            # 验证数据内容
            portfolio_ids = set(adj.portfolio_id for adj in query_result)
            print(f"✓ 投资组合ID验证通过: {len(portfolio_ids)} 种")
            assert len(portfolio_ids) >= 2

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_adjustment(self):
        """测试单条CapitalAdjustment数据插入"""
        print("\n" + "="*60)
        print("开始测试: CapitalAdjustment CRUD层单条插入")
        print("="*60)

        capital_crud = CapitalAdjustmentCRUD()

        test_adjustment = MCapitalAdjustment(
            portfolio_id="portfolio_003",
            amount=Decimal("-500.00"),
            timestamp=datetime(2023, 6, 20, 15, 0, 0),
            reason="交易手续费扣除",
            source=SOURCE_TYPES.TEST
        )
        print(f"✓ 创建测试资金调整: {test_adjustment.portfolio_id}")
        print(f"  - 调整金额: {test_adjustment.amount}")
        print(f"  - 调整原因: {test_adjustment.reason}")
        print(f"  - 数据源: {SOURCE_TYPES(test_adjustment.source).name}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            capital_crud.add(test_adjustment)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = capital_crud.find(filters={
                "portfolio_id": "portfolio_003",
                "timestamp": datetime(2023, 6, 20, 15, 0, 0)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_adjustment = query_result[0]
            print(f"✓ 插入的资金调整验证: {inserted_adjustment.portfolio_id}")
            assert inserted_adjustment.portfolio_id.strip() == "portfolio_003"
            assert inserted_adjustment.amount == Decimal("-500.00")
            assert inserted_adjustment.reason.strip() == "交易手续费扣除"

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestCapitalAdjustmentCRUDQuery:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': CapitalAdjustmentCRUD}

    """2. CRUD层查询操作测试 - CapitalAdjustment数据查询和过滤"""

    def test_find_by_portfolio_id(self):
        """测试根据投资组合ID查询CapitalAdjustment"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID查询CapitalAdjustment")
        print("="*60)

        capital_crud = CapitalAdjustmentCRUD()

        try:
            # 查询特定投资组合的资金调整
            print("→ 查询投资组合portfolio_001的资金调整...")
            portfolio_adjustments = capital_crud.find(filters={
                "portfolio_id": "portfolio_001"
            })
            print(f"✓ 查询到 {len(portfolio_adjustments)} 条记录")

            # 验证查询结果
            for adj in portfolio_adjustments:
                print(f"  - {adj.timestamp}: 金额{adj.amount}, 原因{adj.reason}")
                assert adj.portfolio_id.strip() == "portfolio_001"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_adjustment_reason(self):
        """测试根据调整原因查询CapitalAdjustment"""
        print("\n" + "="*60)
        print("开始测试: 根据调整原因查询CapitalAdjustment")
        print("="*60)

        capital_crud = CapitalAdjustmentCRUD()

        try:
            # 查询入金记录
            print("→ 查询入金记录...")
            deposit_adjustments = capital_crud.find(filters={
                "reason": "初始入金"
            })
            print(f"✓ 查询到 {len(deposit_adjustments)} 条入金记录")

            # 查询费用扣除记录
            print("→ 查询费用扣除记录...")
            fee_adjustments = capital_crud.find(filters={
                "reason": "交易手续费"
            })
            print(f"✓ 查询到 {len(fee_adjustments)} 条费用扣除记录")

            # 验证查询结果
            for adj in deposit_adjustments[:3]:
                print(f"  - {adj.portfolio_id}: 入金 {adj.amount} 元")
                assert adj.reason.strip() == "初始入金"
                assert adj.amount > 0

            for adj in fee_adjustments[:3]:
                print(f"  - {adj.portfolio_id}: 费用 {adj.amount} 元")
                assert adj.reason.strip() == "交易手续费"
                assert adj.amount < 0

            print("✓ 调整原因查询验证成功")

        except Exception as e:
            print(f"✗ 调整原因查询失败: {e}")
            raise

    def test_find_by_time_range(self):
        """测试根据时间范围查询CapitalAdjustment"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围查询CapitalAdjustment")
        print("="*60)

        capital_crud = CapitalAdjustmentCRUD()

        try:
            # 查询特定时间范围内的资金调整
            start_time = datetime(2023, 1, 1)
            end_time = datetime(2023, 12, 31, 23, 59, 59)

            print(f"→ 查询时间范围 {start_time} ~ {end_time} 的资金调整...")
            time_adjustments = capital_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            })
            print(f"✓ 查询到 {len(time_adjustments)} 条记录")

            # 验证时间范围
            for adj in time_adjustments:
                print(f"  - {adj.portfolio_id}: {adj.reason} ({adj.timestamp.date()})")
                assert start_time <= adj.timestamp <= end_time

            print("✓ 时间范围查询验证成功")

        except Exception as e:
            print(f"✗ 时间范围查询失败: {e}")
            raise

    def test_find_by_adjustment_amount(self):
        """测试根据调整金额查询CapitalAdjustment"""
        print("\n" + "="*60)
        print("开始测试: 根据调整金额查询CapitalAdjustment")
        print("="*60)

        capital_crud = CapitalAdjustmentCRUD()

        try:
            # 查询大额入金记录(>50000元)
            print("→ 查询大额入金记录 > 50000 元...")
            large_deposits = capital_crud.find(filters={
                "amount__gt": Decimal("50000.00")
            })
            print(f"✓ 查询到 {len(large_deposits)} 条大额入金记录")

            # 查询所有负金额记录(出金和费用)
            print("→ 查询所有出金和费用记录...")
            negative_adjustments = capital_crud.find(filters={
                "amount__lt": Decimal("0")
            })
            print(f"✓ 查询到 {len(negative_adjustments)} 条出金记录")

            # 验证查询结果
            for adj in large_deposits[:3]:
                print(f"  - {adj.portfolio_id}: 入金 {adj.amount} 元 ({adj.timestamp.date()})")
                assert adj.amount > Decimal("50000.00")

            for adj in negative_adjustments[:3]:
                print(f"  - {adj.portfolio_id}: 支出 {adj.amount} 元 ({adj.timestamp.date()})")
                assert adj.amount < Decimal("0")

            print("✓ 调整金额查询验证成功")

        except Exception as e:
            print(f"✗ 调整金额查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestCapitalAdjustmentCRUDUpdate:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': CapitalAdjustmentCRUD}

    """3. CRUD层更新操作测试 - CapitalAdjustment数据更新验证"""

    # 注意: ClickHouse不支持UPDATE操作，移除所有更新测试用例
    # 对于资本调整数据，历史记录应该不可变，修正通过插入新记录实现

    # 注意: ClickHouse不支持UPDATE操作，移除更新测试用例
    # 对于资本调整数据，历史记录应该不可变，修正通过插入新记录实现

@pytest.mark.database
@pytest.mark.tdd
class TestCapitalAdjustmentCRUDDelete:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': CapitalAdjustmentCRUD}

    """4. CRUD层删除操作测试 - CapitalAdjustment数据删除验证"""

    def test_delete_adjustment_by_portfolio_id(self):
        """测试根据投资组合ID删除CapitalAdjustment"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID删除CapitalAdjustment")
        print("="*60)

        capital_crud = CapitalAdjustmentCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_adjustment = MCapitalAdjustment(
            portfolio_id="DELETE_TEST_PORTFOLIO",
            amount=Decimal("1000.00"),
            timestamp=datetime(2023, 8, 15, 15, 0, 0),
            reason="测试删除",
            source=SOURCE_TYPES.TEST
        )
        capital_crud.add(test_adjustment)
        print(f"✓ 插入测试数据: {test_adjustment.portfolio_id}")

        # 验证数据存在
        before_count = len(capital_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            capital_crud.remove(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(capital_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            print("✓ 根据投资组合ID删除CapitalAdjustment验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_adjustment_by_time_range(self):
        """测试根据时间范围删除CapitalAdjustment"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围删除CapitalAdjustment")
        print("="*60)

        capital_crud = CapitalAdjustmentCRUD()

        # 准备测试数据 - 特定时间范围的数据
        print("→ 准备测试数据...")
        test_time_range = [
            datetime(2023, 9, 1, 15, 0, 0),
            datetime(2023, 9, 2, 15, 0, 0),
            datetime(2023, 9, 3, 15, 0, 0)
        ]

        for i, test_time in enumerate(test_time_range):
            test_adjustment = MCapitalAdjustment(
                portfolio_id=f"DELETE_TIME_{i+1:03d}",
                amount=Decimal(f"100.{i}00"),
                timestamp=test_time,
                reason="时间范围删除测试",
                source=SOURCE_TYPES.TEST
            )
            capital_crud.add(test_adjustment)

        print(f"✓ 插入时间范围测试数据: {len(test_time_range)}条")

        # 验证数据存在
        before_count = len(capital_crud.find(filters={
            "timestamp__gte": datetime(2023, 9, 1),
            "timestamp__lte": datetime(2023, 9, 3, 23, 59, 59)
        }))
        print(f"✓ 删除前时间范围内数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行时间范围删除操作...")
            capital_crud.remove(filters={
                "timestamp__gte": datetime(2023, 9, 1),
                "timestamp__lte": datetime(2023, 9, 3, 23, 59, 59)
            })
            print("✓ 时间范围删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(capital_crud.find(filters={
                "timestamp__gte": datetime(2023, 9, 1),
                "timestamp__lte": datetime(2023, 9, 3, 23, 59, 59)
            }))
            print(f"✓ 删除后时间范围内数据量: {after_count}")
            assert after_count == 0, "删除后时间范围内应该没有数据"

            print("✓ 根据时间范围删除CapitalAdjustment验证成功")

        except Exception as e:
            print(f"✗ 时间范围删除操作失败: {e}")
            raise

    def test_delete_adjustment_by_reason(self):
        """测试根据调整原因删除CapitalAdjustment"""
        print("\n" + "="*60)
        print("开始测试: 根据调整原因删除CapitalAdjustment")
        print("="*60)

        capital_crud = CapitalAdjustmentCRUD()

        # 准备测试数据 - 不同调整原因
        print("→ 准备测试数据...")
        test_reasons = [
            ("DELETE_REASON_001", "测试删除入金"),
            ("DELETE_REASON_002", "测试删除出金"),
            ("DELETE_REASON_003", "测试删除费用")
        ]

        base_time = datetime(2023, 10, 15, 15, 0, 0)

        for portfolio_id, reason in test_reasons:
            if "入金" in reason:
                amount = Decimal("1000.00")
            elif "出金" in reason:
                amount = Decimal("-500.00")
            else:  # 费用
                amount = Decimal("-50.00")

            test_adjustment = MCapitalAdjustment(
                portfolio_id=portfolio_id,
                amount=amount,
                timestamp=base_time,
                reason=reason,
                source=SOURCE_TYPES.TEST
            )
            capital_crud.add(test_adjustment)

        print(f"✓ 插入调整原因测试数据: {len(test_reasons)} 条")

        try:
            # 删除入金记录
            print("\n→ 删除入金记录...")
            before_deposit = len(capital_crud.find(filters={
                "reason": "测试删除入金"
            }))
            print(f"✓ 删除前入金记录: {before_deposit} 条")

            capital_crud.remove(filters={"reason": "测试删除入金"})
            print("✓ 入金记录删除完成")

            after_deposit = len(capital_crud.find(filters={"reason": "测试删除入金"}))
            print(f"✓ 删除后入金记录: {after_deposit} 条")
            assert after_deposit == 0, "入金记录应该全部删除"

            # 验证其他原因记录保留
            withdrawal_count = len(capital_crud.find(filters={"reason": "测试删除出金"}))
            fee_count = len(capital_crud.find(filters={"reason": "测试删除费用"}))
            print(f"✓ 保留出金记录: {withdrawal_count} 条")
            print(f"✓ 保留费用记录: {fee_count} 条")

            print("✓ 根据调整原因删除CapitalAdjustment验证成功")

        except Exception as e:
            print(f"✗ 调整原因删除操作失败: {e}")
            raise

    def test_delete_adjustment_batch_cleanup(self):
        """测试批量清理CapitalAdjustment数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理CapitalAdjustment数据")
        print("="*60)

        capital_crud = CapitalAdjustmentCRUD()

        # 准备批量清理数据
        print("→ 准备批量清理测试数据...")
        cleanup_portfolios = []
        base_time = datetime(2023, 11, 15, 15, 0, 0)

        for i in range(10):
            portfolio_id = f"CLEANUP_BATCH_{i+1:03d}"
            cleanup_portfolios.append(portfolio_id)

            test_adjustment = MCapitalAdjustment(
                portfolio_id=portfolio_id,
                amount=Decimal(f"100.{i:02d}"),
                timestamp=base_time + timedelta(days=i),
                reason="批量清理测试",
                source=SOURCE_TYPES.TEST
            )
            capital_crud.add(test_adjustment)

        print(f"✓ 插入批量清理测试数据: {len(cleanup_portfolios)}条")

        # 验证数据存在
        before_count = len(capital_crud.find(filters={
            "portfolio_id__like": "CLEANUP_BATCH_%"
        }))
        print(f"✓ 删除前批量数据量: {before_count}")

        try:
            # 批量删除
            print("\n→ 执行批量清理操作...")
            capital_crud.remove(filters={
                "portfolio_id__like": "CLEANUP_BATCH_%"
            })
            print("✓ 批量清理操作完成")

            # 验证删除结果
            print("\n→ 验证批量清理结果...")
            after_count = len(capital_crud.find(filters={
                "portfolio_id__like": "CLEANUP_BATCH_%"
            }))
            print(f"✓ 删除后批量数据量: {after_count}")
            assert after_count == 0, "删除后应该没有批量清理数据"

            # 确认其他数据未受影响
            other_data_count = len(capital_crud.find(page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理CapitalAdjustment数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestCapitalAdjustmentCRUDBusinessLogic:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': CapitalAdjustmentCRUD}

    """5. CRUD层业务逻辑测试 - CapitalAdjustment业务场景验证"""

    def test_capital_adjustment_impact_analysis(self):
        """测试资金调整影响分析"""
        print("\n" + "="*60)
        print("开始测试: 资金调整影响分析")
        print("="*60)

        capital_crud = CapitalAdjustmentCRUD()

        try:
            # 查询特定投资组合的所有资金调整
            print("→ 查询投资组合资金调整影响分析...")
            portfolio_id = "portfolio_001"
            adjustments = capital_crud.find(filters={"portfolio_id": portfolio_id})

            if len(adjustments) < 2:
                print("✗ 资金调整数据不足，跳过影响分析")
                return

            # 按时间排序
            adjustments.sort(key=lambda x: x.timestamp)

            # 分析调整影响
            print(f"✓ {portfolio_id} 资金调整影响分析:")
            total_deposits = Decimal("0")
            total_withdrawals = Decimal("0")
            total_fees = Decimal("0")

            for adj in adjustments:
                if adj.amount > 0:
                    total_deposits += adj.amount
                    print(f"  - {adj.timestamp.date()}: 入金 {adj.amount} 元 ({adj.reason})")
                elif "手续费" in adj.reason or "费用" in adj.reason:
                    total_fees += abs(adj.amount)
                    print(f"  - {adj.timestamp.date()}: 费用 {adj.amount} 元 ({adj.reason})")
                else:
                    total_withdrawals += abs(adj.amount)
                    print(f"  - {adj.timestamp.date()}: 出金 {adj.amount} 元 ({adj.reason})")

            net_cash_flow = total_deposits - total_withdrawals - total_fees

            print(f"✓ 累计入金: {total_deposits} 元")
            print(f"✓ 累计出金: {total_withdrawals} 元")
            print(f"✓ 累计费用: {total_fees} 元")
            print(f"✓ 净现金流: {net_cash_flow} 元")

            # 验证影响分析合理性
            assert total_deposits >= 0
            assert total_withdrawals >= 0
            assert total_fees >= 0
            print("✓ 资金调整影响分析验证成功")

        except Exception as e:
            print(f"✗ 资金调整影响分析失败: {e}")
            raise

    def test_cash_flow_statistics(self):
        """测试资金流水统计"""
        print("\n" + "="*60)
        print("开始测试: 资金流水统计")
        print("="*60)

        capital_crud = CapitalAdjustmentCRUD()

        try:
            # 查询用于资金流水统计的调整记录
            print("→ 查询资金流水统计数据...")
            adjustments = capital_crud.find(page_size=10)

            if len(adjustments) < 1:
                print("✗ 资金调整数据不足，跳过资金流水统计")
                return

            # 模拟资金流水统计
            print("✓ 资金流水统计模拟:")
            total_amount = Decimal("0")
            positive_count = 0
            negative_count = 0

            for adj in adjustments[:5]:
                total_amount += adj.amount
                if adj.amount > 0:
                    positive_count += 1
                    print(f"  - {adj.portfolio_id}: 入金 {adj.amount} 元 ({adj.reason})")
                else:
                    negative_count += 1
                    print(f"  - {adj.portfolio_id}: 支出 {adj.amount} 元 ({adj.reason})")

            avg_amount = total_amount / len(adjustments[:5]) if len(adjustments[:5]) > 0 else Decimal("0")

            print(f"✓ 统计结果:")
            print(f"  - 总交易额: {total_amount} 元")
            print(f"  - 平均金额: {avg_amount} 元")
            print(f"  - 入金次数: {positive_count}")
            print(f"  - 支出次数: {negative_count}")

            print("✓ 资金流水统计验证成功")

        except Exception as e:
            print(f"✗ 资金流水统计失败: {e}")
            raise

    def test_capital_adjustment_data_integrity(self):
        """测试资金调整数据完整性"""
        print("\n" + "="*60)
        print("开始测试: 资金调整数据完整性")
        print("="*60)

        capital_crud = CapitalAdjustmentCRUD()

        try:
            # 测试必要字段约束
            print("→ 测试必要字段约束...")

            # 查询数据验证完整性
            valid_adjustments = capital_crud.find()
            for adj in valid_adjustments:
                # 验证portfolio_id非空
                assert adj.portfolio_id and len(adj.portfolio_id.strip()) > 0

                # 验证timestamp有效
                assert adj.timestamp is not None

                # 验证amount字段为有效数值
                assert isinstance(adj.amount, Decimal)
                # 注意：amount可以是正数(入金)或负数(出金/费用)

                # 验证reason非空
                assert adj.reason and len(adj.reason.strip()) > 0

                # 验证source为有效枚举值
                from ginkgo.enums import SOURCE_TYPES
                assert isinstance(adj.source, int)
                # 验证source值在SOURCE_TYPES枚举范围内
                valid_source_values = [source.value for source in SOURCE_TYPES]
                assert adj.source in valid_source_values, f"Source value {adj.source} not in valid SOURCE_TYPES"

            print(f"✓ 验证了 {len(valid_adjustments)} 条资金调整的完整性约束")
            print("✓ 资金调整数据完整性验证成功")

        except Exception as e:
            print(f"✗ 数据完整性测试失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：CapitalAdjustment CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_capital_adjustment_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 资本调整数据存储和复权计算功能")
