"""
AnalyzerRecordCRUD数据库操作TDD测试

测试CRUD层的分析器记录数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)

AnalyzerRecord是分析器记录数据模型，存储回测过程中各种分析器的计算结果。
为策略分析、性能评估和回测报告生成提供支持。
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.analyzer_record_crud import AnalyzerRecordCRUD
from ginkgo.data.models.model_analyzer_record import MAnalyzerRecord
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestAnalyzerRecordCRUDInsert:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': AnalyzerRecordCRUD}

    """1. CRUD层插入操作测试 - AnalyzerRecord数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入AnalyzerRecord数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: AnalyzerRecord CRUD层批量插入")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()
        print(f"✓ 创建AnalyzerRecordCRUD实例: {analyzer_record_crud.__class__.__name__}")

        # 创建测试AnalyzerRecord数据 - 不同类型的分析器记录
        base_time = datetime(2023, 1, 3, 9, 30)
        test_records = []

        # 收益率分析器记录
        return_record = MAnalyzerRecord(
            portfolio_id="test_portfolio_001",
            engine_id="test_engine_001",
            analyzer_id="sharpe_ratio_analyzer",
            name="Sharpe Ratio Analyzer",
            value=Decimal("1.25"),
            timestamp=base_time,
            business_timestamp=base_time - timedelta(minutes=30)  # 业务时间比系统时间早30分钟
        )
        return_record.source = SOURCE_TYPES.TEST
        test_records.append(return_record)

        # 最大回撤分析器记录
        drawdown_record = MAnalyzerRecord(
            portfolio_id="test_portfolio_001",
            engine_id="test_engine_001",
            analyzer_id="max_drawdown_analyzer",
            name="Maximum Drawdown Analyzer",
            value=Decimal("0.085"),
            timestamp=base_time + timedelta(hours=1),
            business_timestamp=base_time + timedelta(hours=1, minutes=-30)  # 业务时间比系统时间早30分钟
        )
        drawdown_record.source = SOURCE_TYPES.TEST
        test_records.append(drawdown_record)

        # 胜率分析器记录
        winrate_record = MAnalyzerRecord(
            portfolio_id="test_portfolio_001",
            engine_id="test_engine_001",
            analyzer_id="win_rate_analyzer",
            name="Win Rate Analyzer",
            value=Decimal("0.65"),
            timestamp=base_time + timedelta(hours=2),
            business_timestamp=base_time + timedelta(hours=2, minutes=-30)  # 业务时间比系统时间早30分钟
        )
        winrate_record.source = SOURCE_TYPES.TEST
        test_records.append(winrate_record)

        # 夏普比率分析器记录
        calmar_record = MAnalyzerRecord(
            portfolio_id="test_portfolio_001",
            engine_id="test_engine_001",
            analyzer_id="calmar_ratio_analyzer",
            name="Calmar Ratio Analyzer",
            value=Decimal("2.8"),
            timestamp=base_time + timedelta(hours=3),
            business_timestamp=base_time + timedelta(hours=3, minutes=-30)  # 业务时间比系统时间早30分钟
        )
        calmar_record.source = SOURCE_TYPES.TEST
        test_records.append(calmar_record)

        print(f"✓ 创建测试数据: {len(test_records)}条AnalyzerRecord记录")
        analyzer_types = list(set(r.analyzer_id for r in test_records))
        print(f"  - 分析器类型: {analyzer_types}")
        print(f"  - 投资组合ID: {test_records[0].portfolio_id}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            result = analyzer_record_crud.add_batch(test_records)

            # 验证返回类型
            from ginkgo.data.crud.model_conversion import ModelList
            assert isinstance(result, ModelList), f"add_batch应返回ModelList对象，实际返回: {type(result)}"
            assert isinstance(result.count(), int), f"ModelList.count()应返回int类型，实际: {type(result.count())}"
            assert len(result) == result.count(), f"len(ModelList)应与count()一致，len={len(result)}, count={result.count()}"
            print(f"✓ 批量插入成功，返回ModelList(count={result.count()}, 包含{len(result)}个MAnalyzerRecord对象)")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = analyzer_record_crud.find(filters={"portfolio_id": "test_portfolio_001",
                "engine_id": "test_engine_001",
                "timestamp__gte": base_time,
                "timestamp__lte": base_time + timedelta(hours=4), "source": SOURCE_TYPES.TEST.value})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 4

            # 验证数据内容
            analyzer_count = len(set(r.analyzer_id for r in query_result))
            print(f"✓ 分析器类型验证通过: {analyzer_count} 种")
            assert analyzer_count >= 4

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_analyzer_record(self):
        """测试单条AnalyzerRecord数据插入"""
        print("\n" + "="*60)
        print("开始测试: AnalyzerRecord CRUD层单条插入")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        test_record = MAnalyzerRecord(
            portfolio_id="test_portfolio_002",
            engine_id="test_engine_002",
            analyzer_id="volatility_analyzer",
            name="Portfolio Volatility Analyzer",
            value=Decimal("0.023"),
            timestamp=datetime(2023, 1, 3, 10, 30),
            source=SOURCE_TYPES.TEST
        )
        print(f"✓ 创建测试AnalyzerRecord: {test_record.name}")
        print(f"  - 分析器ID: {test_record.analyzer_id}")
        print(f"  - 分析值: {test_record.value}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            result = analyzer_record_crud.add(test_record)

            # 验证返回类型
            assert isinstance(result, MAnalyzerRecord), f"add应返回MAnalyzerRecord对象，实际返回: {type(result)}"
            assert hasattr(result, 'uuid'), f"MAnalyzerRecord应有uuid属性"
            assert hasattr(result, 'analyzer_id'), f"MAnalyzerRecord应有analyzer_id属性"
            assert hasattr(result, 'value'), f"MAnalyzerRecord应有value属性"
            print(f"✓ 单条插入成功，返回MAnalyzerRecord(uuid={result.uuid[:8]}..., analyzer_id={result.analyzer_id}, value={result.value})")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = analyzer_record_crud.find(filters={"analyzer_id": "volatility_analyzer",
                "portfolio_id": "test_portfolio_002",
                "timestamp": datetime(2023, 1, 3, 10, 30), "source": SOURCE_TYPES.TEST.value})
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_record = query_result[0]
            print(f"✓ 插入的AnalyzerRecord验证: {inserted_record.name}")
            assert inserted_record.analyzer_id == "volatility_analyzer"
            assert inserted_record.value == Decimal("0.023")

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestAnalyzerRecordCRUDQuery:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': AnalyzerRecordCRUD}

    """2. CRUD层查询操作测试 - AnalyzerRecord数据查询和过滤"""

    def test_find_by_portfolio_id(self):
        """测试根据投资组合ID查询AnalyzerRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据portfolio_id查询AnalyzerRecord")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        try:
            # 查询特定投资组合的分析器记录
            print("→ 查询portfolio_id=test_portfolio_001的分析器记录...")
            portfolio_records = analyzer_record_crud.find(filters={"portfolio_id": "test_portfolio_001", "source": SOURCE_TYPES.TEST.value})

            # 验证返回类型
            from ginkgo.data.crud.model_conversion import ModelList
            assert isinstance(portfolio_records, ModelList), f"find应返回ModelList对象，实际返回: {type(portfolio_records)}"
            assert isinstance(portfolio_records.count(), int), f"ModelList.count()应返回int类型，实际: {type(portfolio_records.count())}"
            assert len(portfolio_records) == portfolio_records.count(), f"len(ModelList)应与count()一致，len={len(portfolio_records)}, count={portfolio_records.count()}"
            print(f"✓ 查询到 {len(portfolio_records)} 条记录，返回ModelList(count={portfolio_records.count()})")

            # 验证查询结果
            for record in portfolio_records:
                print(f"  - {record.name}: {record.value} ({record.timestamp})")
                assert record.portfolio_id == "test_portfolio_001"

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_analyzer_id(self):
        """测试根据分析器ID查询AnalyzerRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据analyzer_id查询AnalyzerRecord")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        try:
            # 查询特定分析器的记录
            print("→ 查询analyzer_id=sharpe_ratio_analyzer的记录...")
            analyzer_records = analyzer_record_crud.find(filters={
                "analyzer_id": "sharpe_ratio_analyzer"
            })
            print(f"✓ 查询到 {len(analyzer_records)} 条记录")

            # 验证查询结果
            for record in analyzer_records:
                print(f"  - 投资组合: {record.portfolio_id}, 夏普比率: {record.value}")
                assert record.analyzer_id == "sharpe_ratio_analyzer"

        except Exception as e:
            print(f"✗ 分析器ID查询失败: {e}")
            raise

    def test_find_by_time_range(self):
        """测试根据时间范围查询AnalyzerRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围查询AnalyzerRecord")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        try:
            # 查询特定时间范围的分析器记录
            start_time = datetime(2023, 1, 1)
            end_time = datetime(2023, 12, 31)

            print(f"→ 查询时间范围 {start_time.date()} ~ {end_time.date()} 的分析器记录...")
            time_records = analyzer_record_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            })
            print(f"✓ 查询到 {len(time_records)} 条记录")

            # 验证时间范围
            for record in time_records:
                print(f"  - {record.name}: {record.value} ({record.timestamp.date()})")
                assert start_time <= record.timestamp <= end_time

            print("✓ 时间范围查询验证成功")

        except Exception as e:
            print(f"✗ 时间范围查询失败: {e}")
            raise

    def test_find_by_business_time_range(self):
        """测试根据业务时间范围查询AnalyzerRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据业务时间范围查询AnalyzerRecord")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        try:
            # 查询特定业务时间范围的分析器记录
            start_business_time = datetime(2023, 1, 3, 9, 0)  # 业务时间开始
            end_business_time = datetime(2023, 1, 3, 12, 0)   # 业务时间结束

            print(f"→ 查询业务时间范围 {start_business_time.time()} ~ {end_business_time.time()} 的分析器记录...")
            business_time_records = analyzer_record_crud.find_by_business_time(
                portfolio_id="test_portfolio_001",
                start_business_time=start_business_time,
                end_business_time=end_business_time
            )
            print(f"✓ 查询到 {len(business_time_records)} 条记录")

            # 验证业务时间范围
            for record in business_time_records:
                print(f"  - {record.name}: {record.value} (系统时间: {record.timestamp.time()}, 业务时间: {record.business_timestamp.time() if record.business_timestamp else 'None'})")
                if record.business_timestamp:
                    assert start_business_time <= record.business_timestamp <= end_business_time

            print("✓ 业务时间范围查询验证成功")

        except Exception as e:
            print(f"✗ 业务时间范围查询失败: {e}")
            raise

    def test_find_by_time_range_with_business_timestamp(self):
        """测试使用双时间戳的灵活时间范围查询AnalyzerRecord"""
        print("\n" + "="*60)
        print("开始测试: 双时间戳时间范围查询AnalyzerRecord")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        try:
            # 测试业务时间查询
            start_time = datetime(2023, 1, 3, 9, 0)
            end_time = datetime(2023, 1, 3, 12, 0)

            print(f"→ 使用业务时间查询范围 {start_time.time()} ~ {end_time.time()}...")
            business_records = analyzer_record_crud.find_by_time_range(
                portfolio_id="test_portfolio_001",
                start_time=start_time,
                end_time=end_time,
                use_business_time=True
            )
            print(f"✓ 业务时间查询到 {len(business_records)} 条记录")

            print(f"→ 使用系统时间查询相同范围...")
            system_records = analyzer_record_crud.find_by_time_range(
                portfolio_id="test_portfolio_001",
                start_time=start_time,
                end_time=end_time,
                use_business_time=False
            )
            print(f"✓ 系统时间查询到 {len(system_records)} 条记录")

            # 验证双时间戳差异
            print("→ 验证双时间戳数据一致性...")
            for record in business_records:
                if record.business_timestamp:
                    time_diff = record.timestamp - record.business_timestamp
                    print(f"  - {record.name}: 系统时间与业务时间差 {time_diff}")
                    assert abs(time_diff.total_seconds()) == 30 * 60  # 应该是30分钟差异

            print("✓ 双时间戳查询验证成功")

        except Exception as e:
            print(f"✗ 双时间戳查询失败: {e}")
            raise

    def test_find_by_value_range(self):
        """测试根据分析器值范围查询AnalyzerRecord - 统一测试流程"""
        print("\n" + "="*60)
        print("开始测试: 根据分析器值范围查询AnalyzerRecord")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        try:
            # 1. 确认当前数据库为空（仅测试数据）
            print("→ 步骤1: 确认数据库中测试相关数据为空...")
            initial_count = analyzer_record_crud.count(filters={"source": SOURCE_TYPES.TEST.value})
            print(f"✓ 初始测试数据记录数: {initial_count}")

            # 2. 插入测试数据
            print("→ 步骤2: 插入测试数据...")

            # 插入高夏普比率测试数据
            test_sharpe_high = MAnalyzerRecord(
                portfolio_id="TEST_HIGH_001",
                engine_id="TEST_ENGINE_001",
                analyzer_id="sharpe_ratio_analyzer",
                value=Decimal("2.5"),  # > 2.0
                timestamp=datetime(2023, 1, 1),
                source=SOURCE_TYPES.TEST.value
            )
            analyzer_record_crud.add(test_sharpe_high)
            print("✓ 插入高夏普比率测试数据 (2.5)")

            test_sharpe_high2 = MAnalyzerRecord(
                portfolio_id="TEST_HIGH_002",
                engine_id="TEST_ENGINE_001",
                analyzer_id="sharpe_ratio_analyzer",
                value=Decimal("3.0"),  # > 2.0
                timestamp=datetime(2023, 1, 2),
                source=SOURCE_TYPES.TEST.value
            )
            analyzer_record_crud.add(test_sharpe_high2)
            print("✓ 插入高夏普比率测试数据 (3.0)")

            # 插入低夏普比率测试数据（应该不被查询到）
            test_sharpe_low = MAnalyzerRecord(
                portfolio_id="TEST_LOW_001",
                engine_id="TEST_ENGINE_001",
                analyzer_id="sharpe_ratio_analyzer",
                value=Decimal("1.5"),  # < 2.0，不应被查询到
                timestamp=datetime(2023, 1, 1),
                source=SOURCE_TYPES.TEST.value
            )
            analyzer_record_crud.add(test_sharpe_low)
            print("✓ 插入低夏普比率测试数据 (1.5，用于边界测试)")

            # 插入低回撤测试数据
            test_drawdown_low = MAnalyzerRecord(
                portfolio_id="TEST_DRAWDOWN_001",
                engine_id="TEST_ENGINE_001",
                analyzer_id="max_drawdown_analyzer",
                value=Decimal("0.05"),  # < 0.1
                timestamp=datetime(2023, 1, 1),
                source=SOURCE_TYPES.TEST.value
            )
            analyzer_record_crud.add(test_drawdown_low)
            print("✓ 插入低回撤测试数据 (0.05)")

            # 插入高回撤测试数据（应该不被查询到）
            test_drawdown_high = MAnalyzerRecord(
                portfolio_id="TEST_DRAWDOWN_002",
                engine_id="TEST_ENGINE_001",
                analyzer_id="max_drawdown_analyzer",
                value=Decimal("0.15"),  # > 0.1，不应被查询到
                timestamp=datetime(2023, 1, 2),
                source=SOURCE_TYPES.TEST.value
            )
            analyzer_record_crud.add(test_drawdown_high)
            print("✓ 插入高回撤测试数据 (0.15，用于边界测试)")

            # 3. 查询测试
            print("→ 步骤3: 执行查询操作...")

            # 查询夏普比率 > 2.0 的记录
            high_sharpe_records = analyzer_record_crud.find(filters={
                "analyzer_id": "sharpe_ratio_analyzer",
                "value__gt": Decimal("2.0"),
                "source": SOURCE_TYPES.TEST.value
            })
            print(f"✓ 查询到 {len(high_sharpe_records)} 条高夏普比率记录")

            # 查询回撤率 < 0.1 的记录
            low_drawdown_records = analyzer_record_crud.find(filters={
                "analyzer_id": "max_drawdown_analyzer",
                "value__lt": Decimal("0.1"),
                "source": SOURCE_TYPES.TEST.value
            })
            print(f"✓ 查询到 {len(low_drawdown_records)} 条低回撤记录")

            # 4. 精确断言：根据插入数据预期查询结果
            print("→ 步骤4: 验证查询结果...")
            assert len(high_sharpe_records) == 2, f"夏普比率>2.0的记录应为2条，实际为{len(high_sharpe_records)}条"
            assert len(low_drawdown_records) == 1, f"最大回撤<0.1的记录应为1条，实际为{len(low_drawdown_records)}条"

            for record in high_sharpe_records[:3]:
                assert record.analyzer_id == "sharpe_ratio_analyzer", f"分析器ID应该为sharpe_ratio_analyzer，实际: {record.analyzer_id}"
                assert float(record.value) > 2.0, f"夏普比率应该大于2.0，实际: {record.value}"
                print(f"  - {record.portfolio_id}: 夏普比率 {record.value}")

            for record in low_drawdown_records[:3]:
                assert record.analyzer_id == "max_drawdown_analyzer", f"分析器ID应该为max_drawdown_analyzer，实际: {record.analyzer_id}"
                assert float(record.value) < 0.1, f"最大回撤应该小于0.1，实际: {record.value}"
                print(f"  - {record.portfolio_id}: 最大回撤 {record.value}")

            print("✓ 分析器值范围查询验证成功")

        except Exception as e:
            print(f"✗ 分析器值范围查询失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.database
@pytest.mark.tdd
class TestAnalyzerRecordCRUDBusinessLogic:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': AnalyzerRecordCRUD}

    """4. CRUD层业务逻辑测试 - AnalyzerRecord业务场景验证"""

    def test_analyzer_performance_summary(self):
        """测试分析器性能汇总分析"""
        print("\n" + "="*60)
        print("开始测试: 分析器性能汇总分析")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        try:
            # 查询所有分析器记录进行分析
            print("→ 查询所有分析器记录进行分析...")
            all_records = analyzer_record_crud.find(page_size=1000)

            if len(all_records) < 5:
                print("✗ 分析器记录数据不足，跳过汇总分析")
                return

            # 按分析器类型分组统计
            analyzer_stats = {}
            for record in all_records:
                analyzer_id = record.analyzer_id
                if analyzer_id not in analyzer_stats:
                    analyzer_stats[analyzer_id] = {
                        "count": 0,
                        "values": [],
                        "portfolio_ids": set(),
                        "latest_timestamp": None
                    }

                analyzer_stats[analyzer_id]["count"] += 1
                analyzer_stats[analyzer_id]["values"].append(float(record.value))
                analyzer_stats[analyzer_id]["portfolio_ids"].add(record.portfolio_id)

                if (analyzer_stats[analyzer_id]["latest_timestamp"] is None or
                    record.timestamp > analyzer_stats[analyzer_id]["latest_timestamp"]):
                    analyzer_stats[analyzer_id]["latest_timestamp"] = record.timestamp

            print(f"✓ 分析器性能汇总结果:")
            print(f"  - 总分析器记录数: {len(all_records)}")
            print(f"  - 分析器类型数: {len(analyzer_stats)}")

            for analyzer_id, stats in analyzer_stats.items():
                avg_value = sum(stats["values"]) / len(stats["values"])
                min_value = min(stats["values"])
                max_value = max(stats["values"])
                print(f"    {analyzer_id}:")
                print(f"      记录数: {stats['count']}")
                print(f"      覆盖投资组合: {len(stats['portfolio_ids'])}")
                print(f"      平均值: {avg_value:.4f}")
                print(f"      值范围: {min_value:.4f} ~ {max_value:.4f}")

            # 验证分析结果
            assert len(analyzer_stats) > 0, "应该有分析器数据"
            assert all(stats["count"] > 0 for stats in analyzer_stats.values()), "每个分析器都应该有记录"
            assert all(len(stats["values"]) == stats["count"] for stats in analyzer_stats.values()), "每个分析器的值列表长度应该等于记录数"

            total_records = sum(stats["count"] for stats in analyzer_stats.values())
            assert total_records == len(all_records), "汇总记录数应该等于原始记录数"

            # 验证统计数据的合理性
            for analyzer_id, stats in analyzer_stats.items():
                assert len(stats["portfolio_ids"]) > 0, f"分析器 {analyzer_id} 应该覆盖至少1个投资组合"
                assert stats["latest_timestamp"] is not None, f"分析器 {analyzer_id} 应该有最新时间戳"
                assert avg_value >= min_value, f"平均值应该大于等于最小值，分析器: {analyzer_id}"
                assert avg_value <= max_value, f"平均值应该小于等于最大值，分析器: {analyzer_id}"

            print("✓ 分析器性能汇总分析验证成功")

        except Exception as e:
            print(f"✗ 分析器性能汇总分析失败: {e}")
            raise

    def test_portfolio_performance_ranking(self):
        """测试投资组合表现排名分析"""
        print("\n" + "="*60)
        print("开始测试: 投资组合表现排名分析")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        try:
            # 查询夏普比率数据进行排名分析
            print("→ 查询夏普比率数据进行投资组合排名...")
            sharpe_records = analyzer_record_crud.find(filters={
                "analyzer_id": "sharpe_ratio_analyzer"
            })

            if len(sharpe_records) < 3:
                print("✗ 夏普比率数据不足，跳过排名分析")
                return

            # 按投资组合分组计算最新夏普比率
            portfolio_latest = {}
            for record in sharpe_records:
                portfolio_id = record.portfolio_id
                if (portfolio_id not in portfolio_latest or
                    record.timestamp > portfolio_latest[portfolio_id].timestamp):
                    portfolio_latest[portfolio_id] = record

            # 按夏普比率排序
            sorted_portfolios = sorted(
                portfolio_latest.items(),
                key=lambda x: x[1].value,
                reverse=True
            )

            print(f"✓ 投资组合夏普比率排名:")
            for rank, (portfolio_id, record) in enumerate(sorted_portfolios, 1):
                print(f"    第{rank}名: {portfolio_id} - 夏普比率 {record.value}")
                assert float(record.value) >= 0, f"夏普比率应该为非负数，实际: {record.value}"

            # 统计分析
            if len(sorted_portfolios) > 0:
                sharpe_values = [float(r.value) for _, r in sorted_portfolios]
                avg_sharpe = sum(sharpe_values) / len(sharpe_values)
                max_sharpe = max(sharpe_values)
                min_sharpe = min(sharpe_values)

                print(f"✓ 夏普比率统计:")
                print(f"  - 平均夏普比率: {avg_sharpe:.3f}")
                print(f"  - 最高夏普比率: {max_sharpe:.3f}")
                print(f"  - 最低夏普比率: {min_sharpe:.3f}")

                # 断言验证统计数据的合理性
                assert max_sharpe >= min_sharpe, "最高夏普比率应该大于等于最低夏普比率"
                assert avg_sharpe >= min_sharpe and avg_sharpe <= max_sharpe, "平均夏普比率应该在最大值和最小值之间"

                # 如果有数据，验证排名是否按降序排列
                if len(sorted_portfolios) > 1:
                    for i in range(len(sorted_portfolios) - 1):
                        current_value = float(sorted_portfolios[i][1].value)
                        next_value = float(sorted_portfolios[i + 1][1].value)
                        assert current_value >= next_value, f"排名应该按夏普比率降序排列，但第{i+1}名({current_value}) < 第{i+2}名({next_value})"
            else:
                pytest.skip("没有找到投资组合表现数据，跳过排名分析验证")

            print("✓ 投资组合表现排名分析验证成功")

        except Exception as e:
            print(f"✗ 投资组合表现排名分析失败: {e}")
            raise

    def test_analyzer_trend_analysis(self):
        """测试分析器时序趋势分析"""
        print("\n" + "="*60)
        print("开始测试: 分析器时序趋势分析")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        try:
            # 查询特定分析器的时序数据
            start_time = datetime(2023, 1, 1)
            end_time = datetime(2023, 12, 31)

            print(f"→ 查询时间范围 {start_time.date()} ~ {end_time.date()} 的分析器时序数据...")
            time_records = analyzer_record_crud.find(filters={
                "analyzer_id": "sharpe_ratio_analyzer",
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            })

            if len(time_records) < 10:
                pytest.skip("时序数据不足(少于10条)，跳过趋势分析")

            # 按时间排序
            time_records.sort(key=lambda r: r.timestamp)

            # 计算趋势统计
            values = [float(r.value) for r in time_records]
            timestamps = [r.timestamp for r in time_records]

            # 断言基础数据验证
            assert len(values) >= 10, f"应该有至少10条时序数据，实际: {len(values)}"
            assert len(values) == len(timestamps), "数值和时间戳数量应该一致"

            if len(values) >= 2:
                first_value = values[0]
                last_value = values[-1]
                total_change = last_value - first_value
                total_change_pct = (total_change / first_value) * 100 if first_value != 0 else 0

                print(f"✓ 分析器时序趋势分析结果:")
                print(f"  - 数据点数: {len(time_records)}")
                print(f"  - 时间跨度: {timestamps[0].date()} ~ {timestamps[-1].date()}")
                print(f"  - 初始值: {first_value:.3f}")
                print(f"  - 最终值: {last_value:.3f}")
                print(f"  - 总变化: {total_change:+.3f} ({total_change_pct:+.2f}%)")

                # 断言验证时序数据的合理性
                assert timestamps[0] <= timestamps[-1], "时间戳应该按时间顺序排列"
                for i, value in enumerate(values):
                    assert isinstance(value, (int, float)), f"第{i+1}个值应该是数字类型，实际: {type(value)}"
                    assert not (value != value), f"第{i+1}个值不应该是NaN，实际: {value}"  # NaN检查

                # 计算简单移动平均趋势
                if len(values) >= 5:
                    # 计算最后5个点的平均
                    recent_avg = sum(values[-5:]) / 5
                    early_avg = sum(values[:5]) / 5
                    trend_direction = "上升" if recent_avg > early_avg else "下降"
                    trend_strength = abs(recent_avg - early_avg) / early_avg * 100

                    print(f"  - 近期趋势: {trend_direction}")
                    print(f"  - 趋势强度: {trend_strength:.2f}%")

                    # 断言验证趋势计算
                    assert early_avg > 0 or early_avg < 0, "早期平均值应该是有效数字"
                    assert recent_avg > 0 or recent_avg < 0, "近期平均值应该是有效数字"
                    assert trend_strength >= 0, f"趋势强度应该为非负数，实际: {trend_strength}"
            else:
                pytest.skip("时序数据点不足，无法进行趋势分析")

            print("✓ 分析器时序趋势分析验证成功")

        except Exception as e:
            print(f"✗ 分析器时序趋势分析失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestAnalyzerRecordCRUDDelete:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': AnalyzerRecordCRUD}

    """3. CRUD层删除操作测试 - AnalyzerRecord数据删除验证"""

    def test_delete_analyzer_record_by_portfolio_id(self):
        """测试根据投资组合ID删除AnalyzerRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据投资组合ID删除AnalyzerRecord")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_record = MAnalyzerRecord(
            portfolio_id="DELETE_TEST_PORTFOLIO",
            engine_id="delete_test_engine",
            analyzer_id="delete_test_analyzer",
            name="Delete Test Analyzer",
            value=Decimal("1.2345"),
            timestamp=datetime(2023, 6, 15, 10, 30)
        )
        test_record.source = SOURCE_TYPES.TEST
        analyzer_record_crud.add(test_record)
        print(f"✓ 插入测试数据: {test_record.name}")

        # 验证数据存在
        before_records = analyzer_record_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"})
        before_count = len(before_records)
        print(f"✓ 删除前数据量: {before_count}")
        assert before_count > 0, "删除前应该有测试数据存在"

        # 验证插入的数据是正确的
        test_record_found = any(r.name == "Delete Test Analyzer" for r in before_records)
        assert test_record_found, "应该能找到插入的测试数据"

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            analyzer_record_crud.remove(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_records = analyzer_record_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"})
            after_count = len(after_records)
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            # 额外验证：确保其他portfolio_id的数据不受影响
            other_portfolio_records = analyzer_record_crud.find(filters={"portfolio_id": "OTHER_PORTFOLIO"})
            print(f"✓ 其他投资组合数据保留验证: {len(other_portfolio_records)}条")
            # 这里不强制断言，因为可能没有其他数据

            print("✓ 根据投资组合ID删除AnalyzerRecord验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_analyzer_record_by_engine_id(self):
        """测试根据引擎ID删除AnalyzerRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据引擎ID删除AnalyzerRecord")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        # 准备测试数据 - 特定引擎ID的数据
        print("→ 准备测试数据...")
        test_engines = [
            ("delete_engine_001", "analyzer_A"),
            ("delete_engine_001", "analyzer_B"),
            ("delete_engine_002", "analyzer_C"),
        ]

        for engine_id, analyzer_id in test_engines:
            test_record = MAnalyzerRecord(
                portfolio_id="ENGINE_TEST_PORTFOLIO",
                engine_id=engine_id,
                analyzer_id=analyzer_id,
                name=f"Engine {engine_id} Analyzer {analyzer_id}",
                value=Decimal("2.3456"),
                timestamp=datetime(2023, 7, 1, 10, 30)
            )
            test_record.source = SOURCE_TYPES.TEST
            analyzer_record_crud.add(test_record)

        print(f"✓ 插入引擎测试数据: {len(test_engines)}条")

        # 验证数据存在
        before_engine_001 = analyzer_record_crud.find(filters={"engine_id": "delete_engine_001"})
        before_engine_002 = analyzer_record_crud.find(filters={"engine_id": "delete_engine_002"})
        before_count_001 = len(before_engine_001)
        before_count_002 = len(before_engine_002)
        print(f"✓ 删除前引擎001数据量: {before_count_001}")
        print(f"✓ 删除前引擎002数据量: {before_count_002}")

        # 断言验证插入数据的正确性
        assert before_count_001 >= 2, f"引擎001应该至少有2条数据，实际: {before_count_001}"
        assert before_count_002 >= 1, f"引擎002应该至少有1条数据，实际: {before_count_002}"

        # 验证插入的数据内容正确
        engine_001_analyzers = {r.analyzer_id for r in before_engine_001}
        expected_analyzers = {"analyzer_A", "analyzer_B"}
        assert expected_analyzers.issubset(engine_001_analyzers), f"引擎001应该包含分析器{expected_analyzers}"

        try:
            # 删除特定引擎的数据
            print("\n→ 执行引擎ID删除操作...")
            analyzer_record_crud.remove(filters={"engine_id": "delete_engine_001"})
            print("✓ 引擎ID删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_engine_001 = analyzer_record_crud.find(filters={"engine_id": "delete_engine_001"})
            after_engine_002 = analyzer_record_crud.find(filters={"engine_id": "delete_engine_002"})
            after_count_001 = len(after_engine_001)
            after_count_002 = len(after_engine_002)
            print(f"✓ 删除后引擎001数据量: {after_count_001}")
            print(f"✓ 删除后引擎002数据量: {after_count_002}")

            assert after_count_001 == 0, "删除后应该没有引擎001的数据"
            assert after_count_002 == before_count_002, "引擎002的数据应该完全保留"

            # 确认其他引擎数据未受影响
            print(f"✓ 其他引擎数据保留验证: {after_count_002}条")
            # 验证保留数据的完整性
            retained_analyzers = {r.analyzer_id for r in after_engine_002}
            assert "analyzer_C" in retained_analyzers, "分析器C的数据应该保留"

            print("✓ 根据引擎ID删除AnalyzerRecord验证成功")

        except Exception as e:
            print(f"✗ 引擎ID删除操作失败: {e}")
            raise

    def test_delete_analyzer_record_by_analyzer_id(self):
        """测试根据分析器ID删除AnalyzerRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据分析器ID删除AnalyzerRecord")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        # 准备测试数据 - 特定分析器ID的数据
        print("→ 准备测试数据...")
        test_analyzers = [
            ("delete_sharpe_analyzer", "Sharpe Ratio"),
            ("delete_drawdown_analyzer", "Max Drawdown"),
            ("delete_sharpe_analyzer", "Sharpe Ratio Updated"),
        ]

        for analyzer_id, name in test_analyzers:
            test_record = MAnalyzerRecord(
                portfolio_id="ANALYZER_TEST_PORTFOLIO",
                engine_id="analyzer_test_engine",
                analyzer_id=analyzer_id,
                name=name,
                value=Decimal("3.4567"),
                timestamp=datetime(2023, 8, 15, 10, 30)
            )
            test_record.source = SOURCE_TYPES.TEST
            analyzer_record_crud.add(test_record)

        print(f"✓ 插入分析器测试数据: {len(test_analyzers)}条")

        # 验证插入的数据
        before_sharpe_records = analyzer_record_crud.find(filters={"analyzer_id": "delete_sharpe_analyzer"})
        before_drawdown_records = analyzer_record_crud.find(filters={"analyzer_id": "delete_drawdown_analyzer"})
        before_sharpe_count = len(before_sharpe_records)
        before_drawdown_count = len(before_drawdown_records)

        print(f"✓ 插入数据验证:")
        print(f"  - 夏普分析器数据: {before_sharpe_count}条")
        print(f"  - 最大回撤分析器数据: {before_drawdown_count}条")

        # 断言验证插入数据的正确性
        assert before_sharpe_count >= 2, f"夏普分析器应该至少有2条数据，实际: {before_sharpe_count}"
        assert before_drawdown_count >= 1, f"最大回撤分析器应该至少有1条数据，实际: {before_drawdown_count}"

        # 验证插入的数据内容
        sharpe_names = {r.name for r in before_sharpe_records}
        expected_names = {"Sharpe Ratio", "Sharpe Ratio Updated"}
        assert expected_names.issubset(sharpe_names), f"夏普分析器应该包含名称{expected_names}"

        try:
            # 删除特定分析器的数据
            print("\n→ 执行分析器ID删除操作...")
            analyzer_record_crud.remove(filters={"analyzer_id": "delete_sharpe_analyzer"})
            print("✓ 分析器ID删除操作完成")

            # 验证删除结果
            after_sharpe_records = analyzer_record_crud.find(filters={"analyzer_id": "delete_sharpe_analyzer"})
            after_drawdown_records = analyzer_record_crud.find(filters={"analyzer_id": "delete_drawdown_analyzer"})
            after_sharpe_count = len(after_sharpe_records)
            after_drawdown_count = len(after_drawdown_records)

            print(f"✓ 删除后数据验证:")
            print(f"  - 夏普分析器数据: {after_sharpe_count}条")
            print(f"  - 最大回撤分析器数据: {after_drawdown_count}条")

            assert after_sharpe_count == 0, "删除后应该没有夏普分析器数据"
            assert after_drawdown_count == before_drawdown_count, "最大回撤分析器数据应该完全保留"

            # 确认其他分析器数据未受影响
            print(f"✓ 其他分析器数据保留验证: {after_drawdown_count}条")

            # 验证保留数据的完整性
            drawdown_names = {r.name for r in after_drawdown_records}
            assert "Max Drawdown" in drawdown_names, "最大回撤分析器的数据应该保留"

            print("✓ 根据分析器ID删除AnalyzerRecord验证成功")

        except Exception as e:
            print(f"✗ 分析器ID删除操作失败: {e}")
            raise

    def test_delete_analyzer_record_by_time_range(self):
        """测试根据时间范围删除AnalyzerRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围删除AnalyzerRecord")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        # 准备测试数据 - 特定时间范围的数据
        print("→ 准备测试数据...")
        test_time_range = [
            datetime(2023, 9, 1, 10, 30),
            datetime(2023, 9, 2, 10, 30),
            datetime(2023, 9, 3, 10, 30)
        ]

        for i, test_time in enumerate(test_time_range):
            test_record = MAnalyzerRecord(
                portfolio_id="TIME_RANGE_TEST_PORTFOLIO",
                engine_id="time_range_test_engine",
                analyzer_id=f"time_analyzer_{i+1}",
                name=f"Time Range Analyzer {i+1}",
                value=Decimal(f"4.{1000+i}"),
                timestamp=test_time
            )
            test_record.source = SOURCE_TYPES.TEST
            analyzer_record_crud.add(test_record)

        print(f"✓ 插入时间范围测试数据: {len(test_time_range)}条")

        # 验证数据存在
        time_range_filter = {
            "timestamp__gte": datetime(2023, 9, 1),
            "timestamp__lte": datetime(2023, 9, 3, 23, 59, 59)
        }
        before_records = analyzer_record_crud.find(filters=time_range_filter)
        before_count = len(before_records)
        print(f"✓ 删除前时间范围内数据量: {before_count}")

        # 断言验证插入数据的正确性
        assert before_count >= 3, f"时间范围内应该至少有3条数据，实际: {before_count}"

        # 验证插入数据的时序性
        timestamps = [r.timestamp for r in before_records]
        timestamps.sort()
        assert len(timestamps) >= 3, "应该有至少3个时间戳"

        # 验证时间戳都在预期范围内
        start_boundary = datetime(2023, 9, 1)
        end_boundary = datetime(2023, 9, 3, 23, 59, 59)
        for ts in timestamps:
            assert start_boundary <= ts <= end_boundary, f"时间戳{ts}应该在删除范围内"

        # 准备范围外的数据用于验证不误删
        outside_filter = {
            "timestamp__gte": datetime(2023, 9, 4),
            "timestamp__lte": datetime(2023, 9, 5)
        }
        before_outside_count = len(analyzer_record_crud.find(filters=outside_filter))

        try:
            # 执行删除
            print("\n→ 执行时间范围删除操作...")
            analyzer_record_crud.remove(filters=time_range_filter)
            print("✓ 时间范围删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_records = analyzer_record_crud.find(filters=time_range_filter)
            after_count = len(after_records)
            print(f"✓ 删除后时间范围内数据量: {after_count}")
            assert after_count == 0, "删除后时间范围内应该没有数据"

            # 验证范围外的数据未被误删
            after_outside_count = len(analyzer_record_crud.find(filters=outside_filter))
            print(f"✓ 时间范围外数据保留验证: {after_outside_count}条")
            assert after_outside_count == before_outside_count, "时间范围外的数据应该完全保留"

            # 验证删除的精确性 - 检查边界时间
            boundary_check_filter = {
                "timestamp__gte": datetime(2023, 9, 1, 0, 0, 1),  # 删除范围内
                "timestamp__lte": datetime(2023, 9, 3, 23, 59, 58)   # 删除范围内
            }
            boundary_check_count = len(analyzer_record_crud.find(filters=boundary_check_filter))
            assert boundary_check_count == 0, "边界时间范围内的数据也应该被删除"

            print("✓ 根据时间范围删除AnalyzerRecord验证成功")

        except Exception as e:
            print(f"✗ 时间范围删除操作失败: {e}")
            raise

    def test_delete_analyzer_record_by_value_range(self):
        """测试根据分析器值范围删除AnalyzerRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据分析器值范围删除AnalyzerRecord")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        # 准备测试数据 - 特定分析器值的数据
        print("→ 准备测试数据...")
        test_values = [
            ("low_value_analyzer", Decimal("0.1")),     # 低值
            ("high_value_analyzer", Decimal("5.0")),     # 高值
            ("extreme_value_analyzer", Decimal("10.0")), # 极高值
        ]

        for analyzer_id, value in test_values:
            test_record = MAnalyzerRecord(
                portfolio_id="VALUE_RANGE_TEST_PORTFOLIO",
                engine_id="value_range_test_engine",
                analyzer_id=analyzer_id,
                name=f"Value Range {analyzer_id}",
                value=value,
                timestamp=datetime(2023, 10, 15, 10, 30)
            )
            test_record.source = SOURCE_TYPES.TEST
            analyzer_record_crud.add(test_record)

        print(f"✓ 插入值范围测试数据: {len(test_values)}条")

        try:
            # 删除高值数据 (> 3.0)
            print("\n→ 执行高值数据删除操作...")
            before_high = len(analyzer_record_crud.find(filters={"value__gt": Decimal("3.0")}))
            print(f"✓ 删除前高值数据量: {before_high}")

            analyzer_record_crud.remove(filters={"value__gt": Decimal("3.0")})
            print("✓ 高值删除操作完成")

            after_high = len(analyzer_record_crud.find(filters={"value__gt": Decimal("3.0")}))
            print(f"✓ 删除后高值数据量: {after_high}")
            assert after_high == 0, "删除后应该没有高值数据"

            # 删除低值数据 (< 1.0)
            print("\n→ 执行低值数据删除操作...")
            before_low = len(analyzer_record_crud.find(filters={"value__lt": Decimal("1.0")}))
            print(f"✓ 删除前低值数据量: {before_low}")

            analyzer_record_crud.remove(filters={"value__lt": Decimal("1.0")})
            print("✓ 低值删除操作完成")

            after_low = len(analyzer_record_crud.find(filters={"value__lt": Decimal("1.0")}))
            print(f"✓ 删除后低值数据量: {after_low}")
            assert after_low == 0, "删除后应该没有低值数据"

            print("✓ 根据分析器值范围删除AnalyzerRecord验证成功")

        except Exception as e:
            print(f"✗ 值范围删除操作失败: {e}")
            raise

    def test_delete_analyzer_record_batch_cleanup(self):
        """测试批量清理AnalyzerRecord数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理AnalyzerRecord数据")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        # 准备批量清理数据
        print("→ 准备批量清理测试数据...")
        cleanup_analyzers = []
        base_time = datetime(2023, 11, 1)

        for i in range(8):
            analyzer_id = f"cleanup_analyzer_{i+1:03d}"
            cleanup_analyzers.append(analyzer_id)

            test_record = MAnalyzerRecord(
                portfolio_id="CLEANUP_TEST_PORTFOLIO",
                engine_id="cleanup_test_engine",
                analyzer_id=analyzer_id,
                name=f"Cleanup Analyzer {i+1}",
                value=Decimal(f"5.{1000+i}"),
                timestamp=base_time + timedelta(hours=i)
            )
            test_record.source = SOURCE_TYPES.TEST
            analyzer_record_crud.add(test_record)

        print(f"✓ 插入批量清理测试数据: {len(cleanup_analyzers)}条")

        # 验证数据存在
        before_count = len(analyzer_record_crud.find(filters={
            "analyzer_id__like": "cleanup_analyzer_%"
        }))
        print(f"✓ 删除前批量数据量: {before_count}")

        try:
            # 批量删除
            print("\n→ 执行批量清理操作...")
            analyzer_record_crud.remove(filters={
                "analyzer_id__like": "cleanup_analyzer_%"
            })
            print("✓ 批量清理操作完成")

            # 验证删除结果
            print("\n→ 验证批量清理结果...")
            after_count = len(analyzer_record_crud.find(filters={
                "analyzer_id__like": "cleanup_analyzer_%"
            }))
            print(f"✓ 删除后批量数据量: {after_count}")
            assert after_count == 0, "删除后应该没有批量清理数据"

            # 确认其他数据未受影响
            other_data_count = len(analyzer_record_crud.find(page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理AnalyzerRecord数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：AnalyzerRecord CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_analyzer_record_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 分析器记录存储和性能分析功能")
