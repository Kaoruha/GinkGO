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
            timestamp=base_time
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
            timestamp=base_time + timedelta(hours=1)
        )
        drawdown_record.source = SOURCE_TYPES.TEST
        test_records.append(drawdown_record)

        # 胜胜率分析器记录
        winrate_record = MAnalyzerRecord(
            portfolio_id="test_portfolio_001",
            engine_id="test_engine_001",
            analyzer_id="win_rate_analyzer",
            name="Win Rate Analyzer",
            value=Decimal("0.65"),
            timestamp=base_time + timedelta(hours=2)
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
            timestamp=base_time + timedelta(hours=3)
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
            query_result = analyzer_record_crud.find(filters={
                "portfolio_id": "test_portfolio_001",
                "engine_id": "test_engine_001",
                "timestamp__gte": base_time,
                "timestamp__lte": base_time + timedelta(hours=4)
            })
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
            query_result = analyzer_record_crud.find(filters={
                "analyzer_id": "volatility_analyzer",
                "portfolio_id": "test_portfolio_002",
                "timestamp": datetime(2023, 1, 3, 10, 30)
            })
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
            portfolio_records = analyzer_record_crud.find(filters={
                "portfolio_id": "test_portfolio_001"
            })

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

    def test_find_by_value_range(self):
        """测试根据分析器值范围查询AnalyzerRecord"""
        print("\n" + "="*60)
        print("开始测试: 根据分析器值范围查询AnalyzerRecord")
        print("="*60)

        analyzer_record_crud = AnalyzerRecordCRUD()

        try:
            # 查询夏普比率大于2的记录
            print("→ 查询夏普比率 > 2.0 的记录...")
            high_sharpe_records = analyzer_record_crud.find(filters={
                "analyzer_id": "sharpe_ratio_analyzer",
                "value__gt": Decimal("2.0")
            })
            print(f"✓ 查询到 {len(high_sharpe_records)} 条高夏普比率记录")

            # 查询回撤率小于0.1的记录
            print("→ 查询最大回撤 < 0.1 的记录...")
            low_drawdown_records = analyzer_record_crud.find(filters={
                "analyzer_id": "max_drawdown_analyzer",
                "value__lt": Decimal("0.1")
            })
            print(f"✓ 查询到 {len(low_drawdown_records)} 条低回撤记录")

            # 验证查询结果
            for record in high_sharpe_records[:3]:
                print(f"  - {record.portfolio_id}: 夏普比率 {record.value}")

            for record in low_drawdown_records[:3]:
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
            total_records = sum(stats["count"] for stats in analyzer_stats.values())
            assert total_records == len(all_records)
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
                print("✗ 时序数据不足，跳过趋势分析")
                return

            # 按时间排序
            time_records.sort(key=lambda r: r.timestamp)

            # 计算趋势统计
            values = [float(r.value) for r in time_records]
            timestamps = [r.timestamp for r in time_records]

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

                # 计算简单移动平均趋势
                if len(values) >= 5:
                    # 计算最后5个点的平均
                    recent_avg = sum(values[-5:]) / 5
                    early_avg = sum(values[:5]) / 5
                    trend_direction = "上升" if recent_avg > early_avg else "下降"
                    trend_strength = abs(recent_avg - early_avg) / early_avg * 100

                    print(f"  - 近期趋势: {trend_direction}")
                    print(f"  - 趋势强度: {trend_strength:.2f}%")

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
        before_count = len(analyzer_record_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            analyzer_record_crud.remove(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(analyzer_record_crud.find(filters={"portfolio_id": "DELETE_TEST_PORTFOLIO"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

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
        before_count = len(analyzer_record_crud.find(filters={"engine_id": "delete_engine_001"}))
        print(f"✓ 删除前引擎001数据量: {before_count}")

        try:
            # 删除特定引擎的数据
            print("\n→ 执行引擎ID删除操作...")
            analyzer_record_crud.remove(filters={"engine_id": "delete_engine_001"})
            print("✓ 引擎ID删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(analyzer_record_crud.find(filters={"engine_id": "delete_engine_001"}))
            print(f"✓ 删除后引擎001数据量: {after_count}")
            assert after_count == 0, "删除后应该没有引擎001的数据"

            # 确认其他引擎数据未受影响
            other_engine_count = len(analyzer_record_crud.find(filters={"engine_id": "delete_engine_002"}))
            print(f"✓ 其他引擎数据保留验证: {other_engine_count}条")
            assert other_engine_count > 0, "其他引擎数据应该保留"

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

        try:
            # 删除特定分析器的数据
            print("\n→ 执行分析器ID删除操作...")
            before_count = len(analyzer_record_crud.find(filters={"analyzer_id": "delete_sharpe_analyzer"}))
            print(f"✓ 删除前夏普分析器数据量: {before_count}")

            analyzer_record_crud.remove(filters={"analyzer_id": "delete_sharpe_analyzer"})
            print("✓ 分析器ID删除操作完成")

            # 验证删除结果
            after_count = len(analyzer_record_crud.find(filters={"analyzer_id": "delete_sharpe_analyzer"}))
            print(f"✓ 删除后夏普分析器数据量: {after_count}")
            assert after_count == 0, "删除后应该没有夏普分析器数据"

            # 确认其他分析器数据未受影响
            other_analyzer_count = len(analyzer_record_crud.find(filters={"analyzer_id": "delete_drawdown_analyzer"}))
            print(f"✓ 其他分析器数据保留验证: {other_analyzer_count}条")
            assert other_analyzer_count > 0, "其他分析器数据应该保留"

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
        before_count = len(analyzer_record_crud.find(filters={
            "timestamp__gte": datetime(2023, 9, 1),
            "timestamp__lte": datetime(2023, 9, 3, 23, 59, 59)
        }))
        print(f"✓ 删除前时间范围内数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行时间范围删除操作...")
            analyzer_record_crud.remove(filters={
                "timestamp__gte": datetime(2023, 9, 1),
                "timestamp__lte": datetime(2023, 9, 3, 23, 59, 59)
            })
            print("✓ 时间范围删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(analyzer_record_crud.find(filters={
                "timestamp__gte": datetime(2023, 9, 1),
                "timestamp__lte": datetime(2023, 9, 3, 23, 59, 59)
            }))
            print(f"✓ 删除后时间范围内数据量: {after_count}")
            assert after_count == 0, "删除后时间范围内应该没有数据"

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
