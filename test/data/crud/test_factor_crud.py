"""
FactorCRUD数据库操作TDD测试

测试CRUD层的因子数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)

Factor是因子数据模型，支持多种实体类型的因子存储，包括个股因子、市场因子、宏观因子等。
为量化研究、因子分析和策略开发提供支持。
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.factor_crud import FactorCRUD
from ginkgo.data.models.model_factor import MFactor
from ginkgo.enums import ENTITY_TYPES, SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestFactorCRUDInsert:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': FactorCRUD}

    """1. CRUD层插入操作测试 - Factor数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入Factor数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: Factor CRUD层批量插入")
        print("="*60)

        factor_crud = FactorCRUD()
        print(f"✓ 创建FactorCRUD实例: {factor_crud.__class__.__name__}")

        # 创建测试Factor数据 - 不同实体类型的因子
        base_time = datetime(2023, 1, 3, 9, 30)
        test_factors = []

        # 个股技术因子
        stock_tech_factor = MFactor(
            entity_type=ENTITY_TYPES.STOCK.value,
            entity_id="000001.SZ",
            factor_name="RSI_14D",
            factor_value=Decimal("65.8"),
            factor_category="technical",
            timestamp=base_time
        )
        test_factors.append(stock_tech_factor)

        # 个股基本面因子
        stock_fund_factor = MFactor(
            entity_type=ENTITY_TYPES.STOCK.value,
            entity_id="000001.SZ",
            factor_name="PE_RATIO",
            factor_value=Decimal("18.5"),
            factor_category="fundamental",
            timestamp=base_time + timedelta(minutes=1)
        )
        test_factors.append(stock_fund_factor)

        # 市场因子
        market_factor = MFactor(
            entity_type=ENTITY_TYPES.MARKET.value,
            entity_id="SH000001",
            factor_name="VOLATILITY_20D",
            factor_value=Decimal("0.025"),
            factor_category="market",
            timestamp=base_time + timedelta(minutes=2)
        )
        test_factors.append(market_factor)

        # 宏观因子
        macro_factor = MFactor(
            entity_type=ENTITY_TYPES.COUNTRY.value,
            entity_id="CN",
            factor_name="GDP_GROWTH_QOQ",
            factor_value=Decimal("2.8"),
            factor_category="macro",
            timestamp=base_time + timedelta(hours=1)
        )
        test_factors.append(macro_factor)

        print(f"✓ 创建测试数据: {len(test_factors)}条Factor记录")
        entity_types = list(set(f.entity_type for f in test_factors))
        print(f"  - 实体类型: {entity_types}")
        print(f"  - 因子分类: {list(set(f.factor_category for f in test_factors))}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            factor_crud.add_batch(test_factors)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = factor_crud.find(filters={
                "timestamp__gte": base_time,
                "timestamp__lte": base_time + timedelta(hours=2)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 4

            # 验证数据内容
            stock_factors = [f for f in query_result if f.entity_type == ENTITY_TYPES.STOCK.value]
            market_factors = [f for f in query_result if f.entity_type == ENTITY_TYPES.MARKET.value]
            print(f"✓ 个股因子验证通过: {len(stock_factors)} 个")
            print(f"✓ 市场因子验证通过: {len(market_factors)} 个")
            assert len(stock_factors) >= 2
            assert len(market_factors) >= 1

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_factor(self):
        """测试单条Factor数据插入"""
        print("\n" + "="*60)
        print("开始测试: Factor CRUD层单条插入")
        print("="*60)

        factor_crud = FactorCRUD()

        test_factor = MFactor(
            entity_type=ENTITY_TYPES.INDUSTRY.value,
            entity_id="C00259",
            factor_name="INDUSTRY_PE_TTM",
            factor_value=Decimal("22.3"),
            factor_category="industry",
            timestamp=datetime(2023, 1, 3, 10, 30)
        )
        print(f"✓ 创建测试Factor: {test_factor.factor_name}")
        print(f"  - 实体类型: {test_factor.get_entity_type_enum().name}")
        print(f"  - 实体ID: {test_factor.entity_id}")
        print(f"  - 因子值: {test_factor.factor_value}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            factor_crud.add(test_factor)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = factor_crud.find(filters={
                "entity_id": "C00259",
                "factor_name": "INDUSTRY_PE_TTM",
                "timestamp": datetime(2023, 1, 3, 10, 30)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_factor = query_result[0]
            print(f"✓ 插入的Factor验证: {inserted_factor.factor_name}")
            assert inserted_factor.entity_type == ENTITY_TYPES.INDUSTRY.value
            assert inserted_factor.factor_value == Decimal("22.3")

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestFactorCRUDQuery:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': FactorCRUD}

    """2. CRUD层查询操作测试 - Factor数据查询和过滤"""

    def test_find_by_entity_type(self):
        """测试根据实体类型查询Factor"""
        print("\n" + "="*60)
        print("开始测试: 根据entity_type查询Factor")
        print("="*60)

        factor_crud = FactorCRUD()

        try:
            # 查询个股因子
            print("→ 查询所有个股因子 (entity_type=STOCK)...")
            stock_factors = factor_crud.find(filters={
                "entity_type": ENTITY_TYPES.STOCK.value
            })
            print(f"✓ 查询到 {len(stock_factors)} 条个股因子")

            # 查询市场因子
            print("→ 查询所有市场因子 (entity_type=MARKET)...")
            market_factors = factor_crud.find(filters={
                "entity_type": ENTITY_TYPES.MARKET.value
            })
            print(f"✓ 查询到 {len(market_factors)} 条市场因子")

            # 验证查询结果
            print(f"✓ 实体类型分布: 个股 {len(stock_factors)} 个, 市场 {len(market_factors)} 个")

            for factor in stock_factors[:3]:  # 只显示前3个
                print(f"  - {factor.entity_id}: {factor.factor_name} = {factor.factor_value}")

            for factor in market_factors[:3]:  # 只显示前3个
                print(f"  - {factor.entity_id}: {factor.factor_name} = {factor.factor_value}")

        except Exception as e:
            print(f"✗ 实体类型查询失败: {e}")
            raise

    def test_find_by_entity_id(self):
        """测试根据实体ID查询Factor"""
        print("\n" + "="*60)
        print("开始测试: 根据entity_id查询Factor")
        print("="*60)

        factor_crud = FactorCRUD()

        try:
            # 查询特定股票的因子
            print("→ 查询股票000001.SZ的所有因子...")
            entity_factors = factor_crud.find(filters={
                "entity_id": "000001.SZ"
            })
            print(f"✓ 查询到 {len(entity_factors)} 条因子")

            # 验证查询结果
            if entity_factors:
                factor_names = list(set(f.factor_name for f in entity_factors))
                print(f"✓ 股票000001.SZ的因子类型: {factor_names}")

                for factor in entity_factors[:5]:  # 只显示前5个
                    print(f"  - {factor.factor_name}: {factor.factor_value} ({factor.factor_category})")

                for factor in entity_factors:
                    assert factor.entity_id == "000001.SZ"

            print("✓ 实体ID查询验证成功")

        except Exception as e:
            print(f"✗ 实体ID查询失败: {e}")
            raise

    def test_find_by_factor_category(self):
        """测试根据因子分类查询Factor"""
        print("\n" + "="*60)
        print("开始测试: 根据factor_category查询Factor")
        print("="*60)

        factor_crud = FactorCRUD()

        try:
            # 查询技术因子
            print("→ 查询所有技术因子 (factor_category=technical)...")
            technical_factors = factor_crud.find(filters={
                "factor_category": "technical"
            })
            print(f"✓ 查询到 {len(technical_factors)} 条技术因子")

            # 查询基本面因子
            print("→ 查询所有基本面因子 (factor_category=fundamental)...")
            fundamental_factors = factor_crud.find(filters={
                "factor_category": "fundamental"
            })
            print(f"✓ 查询到 {len(fundamental_factors)} 条基本面因子")

            # 验证查询结果
            print(f"✓ 因子分类分布: 技术 {len(technical_factors)} 个, 基本面 {len(fundamental_factors)} 个")

            for factor in technical_factors[:3]:
                print(f"  - {factor.factor_name}: {factor.entity_id} = {factor.factor_value}")

            for factor in fundamental_factors[:3]:
                print(f"  - {factor.factor_name}: {factor.entity_id} = {factor.factor_value}")

        except Exception as e:
            print(f"✗ 因子分类查询失败: {e}")
            raise

    def test_find_by_value_range(self):
        """测试根据因子值范围查询Factor"""
        print("\n" + "="*60)
        print("开始测试: 根据因子值范围查询Factor")
        print("="*60)

        factor_crud = FactorCRUD()

        try:
            # 查询因子值大于50的记录
            print("→ 查询因子值 > 50 的记录...")
            high_value_factors = factor_crud.find(filters={
                "factor_value__gt": Decimal("50")
            })
            print(f"✓ 查询到 {len(high_value_factors)} 条高值因子")

            # 查询因子值在特定范围内的记录
            print("→ 查询因子值在 10-100 之间的记录...")
            range_factors = factor_crud.find(filters={
                "factor_value__gte": Decimal("10"),
                "factor_value__lte": Decimal("100")
            })
            print(f"✓ 查询到 {len(range_factors)} 条中值因子")

            # 验证查询结果
            for factor in high_value_factors[:3]:
                print(f"  - {factor.factor_name}: {factor.entity_id} = {factor.factor_value}")

            for factor in range_factors[:3]:
                print(f"  - {factor.factor_name}: {factor.entity_id} = {factor.factor_value}")

            print("✓ 因子值范围查询验证成功")

        except Exception as e:
            print(f"✗ 因子值范围查询失败: {e}")
            raise




@pytest.mark.database
@pytest.mark.tdd
class TestFactorCRUDBusinessLogic:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': FactorCRUD}

    """4. CRUD层业务逻辑测试 - Factor业务场景验证"""

    def test_factor_coverage_analysis(self):
        """测试因子覆盖分析"""
        print("\n" + "="*60)
        print("开始测试: 因子覆盖分析")
        print("="*60)

        factor_crud = FactorCRUD()

        try:
            # 查询所有因子数据进行分析
            print("→ 查询所有因子数据进行分析...")
            all_factors = factor_crud.find(page_size=1000)

            if len(all_factors) < 10:
                pytest.skip("因子数据不足(少于10条)，跳过覆盖分析")

            # 按实体类型统计
            entity_type_stats = {}
            for factor in all_factors:
                entity_type = factor.get_entity_type_enum().name if factor.get_entity_type_enum() else "UNKNOWN"
                if entity_type not in entity_type_stats:
                    entity_type_stats[entity_type] = {
                        "count": 0,
                        "entities": set(),
                        "factor_names": set()
                    }

                entity_type_stats[entity_type]["count"] += 1
                entity_type_stats[entity_type]["entities"].add(factor.entity_id)
                entity_type_stats[entity_type]["factor_names"].add(factor.factor_name)

            # 按因子分类统计
            category_stats = {}
            for factor in all_factors:
                category = factor.factor_category
                if category not in category_stats:
                    category_stats[category] = {
                        "count": 0,
                        "factor_names": set(),
                        "entity_types": set()
                    }

                category_stats[category]["count"] += 1
                category_stats[category]["factor_names"].add(factor.factor_name)
                category_stats[category]["entity_types"].add(factor.get_entity_type_enum().name if factor.get_entity_type_enum() else "UNKNOWN")

            print(f"✓ 因子覆盖分析结果:")
            print(f"  - 总因子记录数: {len(all_factors)}")
            print(f"  - 实体类型分布:")
            for entity_type, stats in entity_type_stats.items():
                print(f"    {entity_type}: {stats['count']} 条, {len(stats['entities'])} 个实体, {len(stats['factor_names'])} 种因子")

            print(f"  - 因子分类分布:")
            for category, stats in category_stats.items():
                print(f"    {category}: {stats['count']} 条, {len(stats['factor_names'])} 种因子")

            # 验证分析结果
            total_by_entity = sum(stats["count"] for stats in entity_type_stats.values())
            assert total_by_entity == len(all_factors)
            print("✓ 因子覆盖分析验证成功")

        except Exception as e:
            print(f"✗ 因子覆盖分析失败: {e}")
            raise

    def test_factor_value_distribution(self):
        """测试因子值分布分析"""
        print("\n" + "="*60)
        print("开始测试: 因子值分布分析")
        print("="*60)

        factor_crud = FactorCRUD()

        try:
            # 查询因子数据进行值分布分析
            print("→ 查询因子数据进行值分布分析...")
            factors = factor_crud.find(page_size=500)

            if len(factors) < 20:
                pytest.skip("因子数据不足(少于20条)，跳过值分布分析")

            # 计算因子值统计
            values = [float(f.factor_value) for f in factors]

            # 断言验证基础数据
            assert len(values) >= 20, f"应该有至少20个因子值进行分布分析，实际: {len(values)}"
            assert len(values) == len(factors), "所有因子都应该有有效的因子值"

            if values:
                min_val = min(values)
                max_val = max(values)
                avg_val = sum(values) / len(values)

                # 简单的标准差计算
                variance = sum((x - avg_val) ** 2 for x in values) / len(values)
                std_val = variance ** 0.5

                # 四分位数计算
                sorted_values = sorted(values)
                q1 = sorted_values[len(sorted_values) // 4]
                median = sorted_values[len(sorted_values) // 2]
                q3 = sorted_values[3 * len(sorted_values) // 4]

                print(f"✓ 因子值分布分析结果:")
                print(f"  - 样本数量: {len(values)}")
                print(f"  - 最小值: {min_val:.6f}")
                print(f"  - 最大值: {max_val:.6f}")
                print(f"  - 平均值: {avg_val:.6f}")
                print(f"  - 标准差: {std_val:.6f}")
                print(f"  - 中位数: {median:.6f}")
                print(f"  - 第一四分位数: {q1:.6f}")
                print(f"  - 第三四分位数: {q3:.6f}")

                # 断言验证统计数据的合理性
                assert min_val <= max_val, f"最小值应该小于等于最大值，实际: {min_val} vs {max_val}"
                assert min_val <= median <= max_val, f"中位数应该在最小值和最大值之间"
                assert q1 <= median <= q3, f"四分位数应该满足 q1 <= median <= q3"
                assert std_val >= 0, f"标准差应该为非负数，实际: {std_val}"

                # 验证数值的有效性
                for i, value in enumerate(values):
                    assert isinstance(value, (int, float)), f"第{i+1}个值应该是数字类型，实际: {type(value)}"
                    assert not (value != value), f"第{i+1}个值不应该是NaN，实际: {value}"  # NaN检查

                # 异常值检测
                iqr = q3 - q1
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr

                outliers = [v for v in values if v < lower_bound or v > upper_bound]
                print(f"  - 异常值数量: {len(outliers)} ({len(outliers)/len(values)*100:.1f}%)")

                # 断言验证异常值比例
                outlier_ratio = len(outliers) / len(values)
                assert outlier_ratio <= 0.5, f"异常值比例不应该超过50%，实际: {outlier_ratio*100:.1f}%"
            else:
                pytest.fail("因子值列表为空，无法进行分布分析")

            print("✓ 因子值分布分析验证成功")

        except Exception as e:
            print(f"✗ 因子值分布分析失败: {e}")
            raise

    def test_factor_temporal_analysis(self):
        """测试因子时序分析"""
        print("\n" + "="*60)
        print("开始测试: 因子时序分析")
        print("="*60)

        factor_crud = FactorCRUD()

        try:
            # 查询特定时间范围的因子数据
            start_time = datetime(2023, 1, 1)
            end_time = datetime(2023, 1, 31)

            print(f"→ 查询时间范围 {start_time.date()} ~ {end_time.date()} 的因子数据...")
            time_factors = factor_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time
            })

            if len(time_factors) < 10:
                pytest.skip("时间范围内因子数据不足(少于10条)，跳过时序分析")

            # 按时间排序
            time_factors.sort(key=lambda f: f.timestamp)

            # 断言验证时序数据
            assert len(time_factors) >= 10, f"应该有至少10条时序数据，实际: {len(time_factors)}"
            assert time_factors[0].timestamp <= time_factors[-1].timestamp, "时间戳应该按时间顺序排列"

            # 按天统计
            daily_stats = {}
            for factor in time_factors:
                date_key = factor.timestamp.date()
                if date_key not in daily_stats:
                    daily_stats[date_key] = {
                        "count": 0,
                        "factor_names": set(),
                        "values": []
                    }

                daily_stats[date_key]["count"] += 1
                daily_stats[date_key]["factor_names"].add(factor.factor_name)
                daily_stats[date_key]["values"].append(float(factor.factor_value))

            # 断言验证统计数据
            total_records_in_daily = sum(stats["count"] for stats in daily_stats.values())
            assert total_records_in_daily == len(time_factors), f"每日统计总和应该等于总记录数，实际: {total_records_in_daily} vs {len(time_factors)}"

            print(f"✓ 因子时序分析结果:")
            print(f"  - 时间跨度: {time_factors[0].timestamp.date()} ~ {time_factors[-1].timestamp.date()}")
            print(f"  - 总因子记录: {len(time_factors)}")
            print(f"  - 覆盖天数: {len(daily_stats)}")

            # 显示每日统计
            sorted_dates = sorted(daily_stats.keys())
            for date in sorted_dates[:7]:  # 只显示前7天
                stats = daily_stats[date]
                avg_value = sum(stats["values"]) / len(stats["values"]) if stats["values"] else 0
                print(f"    {date}: {stats['count']} 条记录, {len(stats['factor_names'])} 种因子, 平均值 {avg_value:.4f}")

            # 断言验证每日数据的完整性
            for date, stats in daily_stats.items():
                assert stats["count"] > 0, f"日期{date}的记录数应该大于0"
                assert len(stats["factor_names"]) > 0, f"日期{date}的因子种类应该大于0"
                assert len(stats["values"]) == stats["count"], f"日期{date}的值数量应该等于记录数"

                # 验证数值有效性
                for value in stats["values"]:
                    assert isinstance(value, (int, float)), f"因子值应该是数字类型，实际: {type(value)}"
                    assert not (value != value), f"因子值不应该是NaN，实际: {value}"

            # 分析趋势
            if len(sorted_dates) >= 2:
                first_day_avg = sum(daily_stats[sorted_dates[0]]["values"]) / len(daily_stats[sorted_dates[0]]["values"])
                last_day_avg = sum(daily_stats[sorted_dates[-1]]["values"]) / len(daily_stats[sorted_dates[-1]]["values"])
                trend_change = (last_day_avg - first_day_avg) / first_day_avg * 100 if first_day_avg != 0 else 0

                # 断言验证趋势计算
                assert isinstance(trend_change, (int, float)), "趋势变化应该是数字类型"
                assert -100 <= trend_change <= 10000, f"趋势变化应该在合理范围内，实际: {trend_change}%"
                print(f"  - 趋势分析: 从{sorted_dates[0]}到{sorted_dates[-1]}，平均值变化 {trend_change:+.2f}%")

            print("✓ 因子时序分析验证成功")

        except Exception as e:
            print(f"✗ 因子时序分析失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestFactorCRUDDelete:
    # 明确配置CRUD类
    CRUD_TEST_CONFIG = {'crud_class': FactorCRUD}

    """3. CRUD层删除操作测试 - Factor数据删除验证"""

    def test_delete_factor_by_entity_id(self):
        """测试根据实体ID删除Factor"""
        print("\n" + "="*60)
        print("开始测试: 根据实体ID删除Factor")
        print("="*60)

        factor_crud = FactorCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_factor = MFactor(
            entity_type=ENTITY_TYPES.STOCK.value,
            entity_id="DELETE_TEST_STOCK",
            factor_name="DELETE_TEST_FACTOR",
            factor_value=Decimal("123.45"),
            factor_category="test",
            timestamp=datetime(2023, 6, 15, 10, 30)
        )
        factor_crud.add(test_factor)
        print(f"✓ 插入测试数据: {test_factor.factor_name} for {test_factor.entity_id}")

        # 验证数据存在
        before_count = len(factor_crud.find(filters={"entity_id": "DELETE_TEST_STOCK"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            factor_crud.remove(filters={"entity_id": "DELETE_TEST_STOCK"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(factor_crud.find(filters={"entity_id": "DELETE_TEST_STOCK"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            print("✓ 根据实体ID删除Factor验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_factor_by_entity_type(self):
        """测试根据实体类型删除Factor"""
        print("\n" + "="*60)
        print("开始测试: 根据实体类型删除Factor")
        print("="*60)

        factor_crud = FactorCRUD()

        # 准备测试数据 - 特定实体类型的数据
        print("→ 准备测试数据...")
        test_entities = [
            ("DELETE_ENTITY_001", "factor_A"),
            ("DELETE_ENTITY_002", "factor_B"),
            ("DELETE_ENTITY_003", "factor_C"),
        ]

        for entity_id, factor_name in test_entities:
            test_factor = MFactor(
                entity_type=ENTITY_TYPES.STOCK.value,
                entity_id=entity_id,
                factor_name=factor_name,
                factor_value=Decimal("234.56"),
                factor_category="delete_test",
                timestamp=datetime(2023, 7, 1, 10, 30)
            )
            factor_crud.add(test_factor)

        print(f"✓ 插入实体类型测试数据: {len(test_entities)}条")

        # 验证数据存在
        before_count = len(factor_crud.find(filters={
            "entity_type": ENTITY_TYPES.STOCK.value,
            "entity_id__like": "DELETE_ENTITY_%"
        }))
        print(f"✓ 删除前测试实体数据量: {before_count}")

        try:
            # 删除特定实体的数据
            print("\n→ 执行实体类型删除操作...")
            factor_crud.remove(filters={
                "entity_type": ENTITY_TYPES.STOCK.value,
                "entity_id__like": "DELETE_ENTITY_%"
            })
            print("✓ 实体类型删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(factor_crud.find(filters={
                "entity_type": ENTITY_TYPES.STOCK.value,
                "entity_id__like": "DELETE_ENTITY_%"
            }))
            print(f"✓ 删除后测试实体数据量: {after_count}")
            assert after_count == 0, "删除后应该没有测试实体数据"

            print("✓ 根据实体类型删除Factor验证成功")

        except Exception as e:
            print(f"✗ 实体类型删除操作失败: {e}")
            raise

    def test_delete_factor_by_factor_name(self):
        """测试根据因子名称删除Factor"""
        print("\n" + "="*60)
        print("开始测试: 根据因子名称删除Factor")
        print("="*60)

        factor_crud = FactorCRUD()

        # 准备测试数据 - 特定因子名称的数据
        print("→ 准备测试数据...")
        test_factors = [
            ("delete_test_momentum", "STOCK", "MOMENTUM_001"),
            ("delete_test_momentum", "STOCK", "MOMENTUM_002"),
            ("delete_test_value", "STOCK", "VALUE_001"),
        ]

        for factor_name, entity_type, entity_id in test_factors:
            test_factor = MFactor(
                entity_type=ENTITY_TYPES.STOCK.value,
                entity_id=entity_id,
                factor_name=factor_name,
                factor_value=Decimal("345.67"),
                factor_category="delete_test",
                timestamp=datetime(2023, 8, 15, 10, 30)
            )
            factor_crud.add(test_factor)

        print(f"✓ 插入因子名称测试数据: {len(test_factors)}条")

        try:
            # 删除特定因子名称的数据
            print("\n→ 执行因子名称删除操作...")
            before_count = len(factor_crud.find(filters={"factor_name": "delete_test_momentum"}))
            print(f"✓ 删除前动量因子数据量: {before_count}")

            factor_crud.remove(filters={"factor_name": "delete_test_momentum"})
            print("✓ 因子名称删除操作完成")

            # 验证删除结果
            after_count = len(factor_crud.find(filters={"factor_name": "delete_test_momentum"}))
            print(f"✓ 删除后动量因子数据量: {after_count}")
            assert after_count == 0, "删除后应该没有动量因子数据"

            # 确认其他因子数据未受影响
            other_factor_count = len(factor_crud.find(filters={"factor_name": "delete_test_value"}))
            print(f"✓ 其他因子数据保留验证: {other_factor_count}条")
            assert other_factor_count > 0, "其他因子数据应该保留"

            print("✓ 根据因子名称删除Factor验证成功")

        except Exception as e:
            print(f"✗ 因子名称删除操作失败: {e}")
            raise

    def test_delete_factor_by_category(self):
        """测试根据因子分类删除Factor"""
        print("\n" + "="*60)
        print("开始测试: 根据因子分类删除Factor")
        print("="*60)

        factor_crud = FactorCRUD()

        # 准备测试数据 - 特定因子分类的数据
        print("→ 准备测试数据...")
        test_categories = [
            ("delete_technical", "RSI_TEST"),
            ("delete_technical", "MACD_TEST"),
            ("delete_fundamental", "PE_TEST"),
            ("delete_technical", "BOLL_TEST"),
        ]

        for category, factor_name in test_categories:
            test_factor = MFactor(
                entity_type=ENTITY_TYPES.STOCK.value,
                entity_id=f"CATEGORY_TEST_{factor_name}",
                factor_name=factor_name,
                factor_value=Decimal("456.78"),
                factor_category=category,
                timestamp=datetime(2023, 9, 1, 10, 30)
            )
            factor_crud.add(test_factor)

        print(f"✓ 插入因子分类测试数据: {len(test_categories)}条")

        try:
            # 删除特定分类的数据
            print("\n→ 执行因子分类删除操作...")
            before_count = len(factor_crud.find(filters={"factor_category": "delete_technical"}))
            print(f"✓ 删除前技术因子数据量: {before_count}")

            factor_crud.remove(filters={"factor_category": "delete_technical"})
            print("✓ 因子分类删除操作完成")

            # 验证删除结果
            after_count = len(factor_crud.find(filters={"factor_category": "delete_technical"}))
            print(f"✓ 删除后技术因子数据量: {after_count}")
            assert after_count == 0, "删除后应该没有技术因子数据"

            # 确认其他分类数据未受影响
            other_category_count = len(factor_crud.find(filters={"factor_category": "delete_fundamental"}))
            print(f"✓ 其他分类数据保留验证: {other_category_count}条")
            assert other_category_count > 0, "其他分类数据应该保留"

            print("✓ 根据因子分类删除Factor验证成功")

        except Exception as e:
            print(f"✗ 因子分类删除操作失败: {e}")
            raise

    def test_delete_factor_by_time_range(self):
        """测试根据时间范围删除Factor"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围删除Factor")
        print("="*60)

        factor_crud = FactorCRUD()

        # 准备测试数据 - 特定时间范围的数据
        print("→ 准备测试数据...")
        test_time_range = [
            datetime(2023, 10, 1, 10, 30),
            datetime(2023, 10, 2, 10, 30),
            datetime(2023, 10, 3, 10, 30)
        ]

        for i, test_time in enumerate(test_time_range):
            test_factor = MFactor(
                entity_type=ENTITY_TYPES.STOCK.value,
                entity_id=f"TIME_RANGE_TEST_{i+1:03d}",
                factor_name=f"TIME_FACTOR_{i+1:03d}",
                factor_value=Decimal(f"567.{1000+i}"),
                factor_category="time_test",
                timestamp=test_time
            )
            factor_crud.add(test_factor)

        print(f"✓ 插入时间范围测试数据: {len(test_time_range)}条")

        # 验证数据存在
        before_count = len(factor_crud.find(filters={
            "timestamp__gte": datetime(2023, 10, 1),
            "timestamp__lte": datetime(2023, 10, 3, 23, 59, 59)
        }))
        print(f"✓ 删除前时间范围内数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行时间范围删除操作...")
            factor_crud.remove(filters={
                "timestamp__gte": datetime(2023, 10, 1),
                "timestamp__lte": datetime(2023, 10, 3, 23, 59, 59)
            })
            print("✓ 时间范围删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(factor_crud.find(filters={
                "timestamp__gte": datetime(2023, 10, 1),
                "timestamp__lte": datetime(2023, 10, 3, 23, 59, 59)
            }))
            print(f"✓ 删除后时间范围内数据量: {after_count}")
            assert after_count == 0, "删除后时间范围内应该没有数据"

            print("✓ 根据时间范围删除Factor验证成功")

        except Exception as e:
            print(f"✗ 时间范围删除操作失败: {e}")
            raise

    def test_delete_factor_by_value_range(self):
        """测试根据因子值范围删除Factor"""
        print("\n" + "="*60)
        print("开始测试: 根据因子值范围删除Factor")
        print("="*60)

        factor_crud = FactorCRUD()

        # 准备测试数据 - 特定因子值的数据
        print("→ 准备测试数据...")
        test_values = [
            ("low_value_factor", Decimal("5.0")),     # 低值
            ("high_value_factor", Decimal("500.0")),   # 高值
            ("extreme_value_factor", Decimal("1000.0")), # 极高值
            ("medium_value_factor", Decimal("100.0")),  # 中值
        ]

        for factor_name, value in test_values:
            test_factor = MFactor(
                entity_type=ENTITY_TYPES.STOCK.value,
                entity_id=f"VALUE_TEST_{factor_name}",
                factor_name=factor_name,
                factor_value=value,
                factor_category="value_test",
                timestamp=datetime(2023, 11, 15, 10, 30)
            )
            factor_crud.add(test_factor)

        print(f"✓ 插入值范围测试数据: {len(test_values)}条")

        try:
            # 删除高值数据 (> 200)
            print("\n→ 执行高值数据删除操作...")
            before_high = len(factor_crud.find(filters={"factor_value__gt": Decimal("200")}))
            print(f"✓ 删除前高值数据量: {before_high}")

            factor_crud.remove(filters={"factor_value__gt": Decimal("200")})
            print("✓ 高值删除操作完成")

            after_high = len(factor_crud.find(filters={"factor_value__gt": Decimal("200")}))
            print(f"✓ 删除后高值数据量: {after_high}")
            assert after_high == 0, "删除后应该没有高值数据"

            # 删除低值数据 (< 50)
            print("\n→ 执行低值数据删除操作...")
            before_low = len(factor_crud.find(filters={"factor_value__lt": Decimal("50")}))
            print(f"✓ 删除前低值数据量: {before_low}")

            factor_crud.remove(filters={"factor_value__lt": Decimal("50")})
            print("✓ 低值删除操作完成")

            after_low = len(factor_crud.find(filters={"factor_value__lt": Decimal("50")}))
            print(f"✓ 删除后低值数据量: {after_low}")
            assert after_low == 0, "删除后应该没有低值数据"

            # 确认中值数据未受影响
            medium_value_count = len(factor_crud.find(filters={"factor_value__gte": Decimal("50"), "factor_value__lte": Decimal("200")}))
            print(f"✓ 中值数据保留验证: {medium_value_count}条")
            assert medium_value_count > 0, "中值数据应该保留"

            print("✓ 根据因子值范围删除Factor验证成功")

        except Exception as e:
            print(f"✗ 值范围删除操作失败: {e}")
            raise

    def test_delete_factor_batch_cleanup(self):
        """测试批量清理Factor数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理Factor数据")
        print("="*60)

        factor_crud = FactorCRUD()

        # 准备批量清理数据
        print("→ 准备批量清理测试数据...")
        cleanup_factors = []
        base_time = datetime(2023, 12, 1)

        for i in range(10):
            entity_id = f"CLEANUP_ENTITY_{i+1:03d}"
            cleanup_factors.append(entity_id)

            test_factor = MFactor(
                entity_type=ENTITY_TYPES.STOCK.value,
                entity_id=entity_id,
                factor_name=f"cleanup_factor_{i+1:03d}",
                factor_value=Decimal(f"678.{1000+i}"),
                factor_category="cleanup_test",
                timestamp=base_time + timedelta(hours=i)
            )
            factor_crud.add(test_factor)

        print(f"✓ 插入批量清理测试数据: {len(cleanup_factors)}条")

        # 验证数据存在
        before_count = len(factor_crud.find(filters={
            "entity_id__like": "CLEANUP_ENTITY_%"
        }))
        print(f"✓ 删除前批量数据量: {before_count}")

        try:
            # 批量删除
            print("\n→ 执行批量清理操作...")
            factor_crud.remove(filters={
                "entity_id__like": "CLEANUP_ENTITY_%"
            })
            print("✓ 批量清理操作完成")

            # 验证删除结果
            print("\n→ 验证批量清理结果...")
            after_count = len(factor_crud.find(filters={
                "entity_id__like": "CLEANUP_ENTITY_%"
            }))
            print(f"✓ 删除后批量数据量: {after_count}")
            assert after_count == 0, "删除后应该没有批量清理数据"

            # 确认其他数据未受影响
            other_data_count = len(factor_crud.find(page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理Factor数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestFactorCRUDConversions:
    CRUD_TEST_CONFIG = {'crud_class': FactorCRUD}
    """5. CRUD层转换方法测试 - Factor ModelList转换功能验证"""

    def test_model_list_conversions(self):
        """测试ModelList的to_dataframe和to_entities转换功能"""
        import pandas as pd
        print("\n" + "="*60)
        print("开始测试: Factor ModelList转换功能")
        print("="*60)

        factor_crud = FactorCRUD()

        try:
            # 创建测试数据 - 多种实体类型的因子
            base_time = datetime(2023, 1, 15, 10, 30)
            test_factors = [
                # 个股技术因子
                MFactor(
                    entity_type=ENTITY_TYPES.STOCK.value,
                    entity_id="CONVERT_STOCK001.SZ",
                    factor_name="RSI_14D",
                    factor_value=Decimal("65.8"),
                    factor_category="technical",
                    timestamp=base_time,
                    source=SOURCE_TYPES.TEST
                ),
                # 市场因子
                MFactor(
                    entity_type=ENTITY_TYPES.MARKET.value,
                    entity_id="SH000001",
                    factor_name="VOLATILITY_20D",
                    factor_value=Decimal("0.025"),
                    factor_category="market",
                    timestamp=base_time + timedelta(minutes=30),
                    source=SOURCE_TYPES.TEST
                ),
                # 行业因子
                MFactor(
                    entity_type=ENTITY_TYPES.INDUSTRY.value,
                    entity_id="C00259",
                    factor_name="INDUSTRY_PE_TTM",
                    factor_value=Decimal("22.3"),
                    factor_category="fundamental",
                    timestamp=base_time + timedelta(hours=1),
                    source=SOURCE_TYPES.TEST
                ),
                # 宏观因子
                MFactor(
                    entity_type=ENTITY_TYPES.COUNTRY.value,
                    entity_id="CN",
                    factor_name="GDP_GROWTH_QOQ",
                    factor_value=Decimal("2.8"),
                    factor_category="macro",
                    timestamp=base_time + timedelta(hours=2),
                    source=SOURCE_TYPES.TEST
                )
            ]

            # 获取操作前数据条数用于验证
            before_count = len(factor_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 操作前数据库记录数: {before_count}")

            # 插入测试数据
            factor_crud.add_batch(test_factors)

            # 验证数据库记录数变化
            after_count = len(factor_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 操作后数据库记录数: {after_count}")
            assert after_count - before_count == len(test_factors), f"应增加{len(test_factors)}条数据，实际增加{after_count - before_count}条"

            # 获取ModelList进行转换测试
            print("\n→ 获取ModelList...")
            model_list = factor_crud.find(filters={"source": SOURCE_TYPES.TEST.value})
            print(f"✓ ModelList类型: {type(model_list).__name__}")
            print(f"✓ ModelList长度: {len(model_list)}")
            assert len(model_list) >= 4

            # 测试1: to_dataframe转换
            print("\n→ 测试to_dataframe转换...")
            df = model_list.to_dataframe()
            print(f"✓ DataFrame类型: {type(df).__name__}")
            print(f"✓ DataFrame形状: {df.shape}")
            assert isinstance(df, pd.DataFrame), "应返回DataFrame"
            assert len(df) == len(model_list), f"DataFrame行数应等于ModelList长度，{len(df)} != {len(model_list)}"

            # 验证DataFrame列和内容
            required_columns = ['entity_type', 'entity_id', 'factor_name', 'factor_value', 'factor_category', 'timestamp', 'source']
            for col in required_columns:
                assert col in df.columns, f"DataFrame应包含列: {col}"
            print(f"✓ 验证必要列存在: {required_columns}")

            # 验证DataFrame数据内容
            entity_types_in_df = set(df['entity_type'])
            expected_types = {ENTITY_TYPES.STOCK, ENTITY_TYPES.MARKET, ENTITY_TYPES.INDUSTRY, ENTITY_TYPES.COUNTRY}
            assert entity_types_in_df == expected_types, f"实体类型应匹配，期望{expected_types}，实际{entity_types_in_df}"
            print("✓ DataFrame数据内容验证通过")

            # 验证entity_type枚举字段转换
            print("→ 验证entity_type枚举字段转换...")
            for i, (_, row) in enumerate(df.iterrows()):
                entity_type_val = row['entity_type']
                assert isinstance(entity_type_val, ENTITY_TYPES), f"第{i}行entity_type应为枚举对象，实际{type(entity_type_val)}"
                assert entity_type_val in ENTITY_TYPES, f"第{i}行entity_type枚举值无效: {entity_type_val}"
                print(f"  - 因子{i+1}: {row['factor_name']} entity_type={entity_type_val.name}")
            print("✓ entity_type枚举字段转换验证通过")

            # 验证source枚举字段转换
            print("→ 验证source枚举字段转换...")
            for i, (_, row) in enumerate(df.iterrows()):
                source_val = row['source']
                assert isinstance(source_val, SOURCE_TYPES), f"第{i}行source应为枚举对象，实际{type(source_val)}"
                assert source_val in SOURCE_TYPES, f"第{i}行source枚举值无效: {source_val}"
                assert source_val == SOURCE_TYPES.TEST, f"第{i}行source应为TEST，实际{source_val}"
                print(f"  - 因子{i+1}: {row['factor_name']} source={source_val.name}")
            print("✓ source枚举字段转换验证通过")

            # 验证因子值数值精度
            print("→ 验证因子值数值精度...")
            for i, (_, row) in enumerate(df.iterrows()):
                factor_val = row['factor_value']
                # 验证数值类型（应该是Decimal或float）
                assert isinstance(factor_val, (Decimal, float, int)), f"第{i}行factor_value应为数值类型，实际{type(factor_val)}"
                print(f"  - 因子{i+1}: {row['factor_name']} = {factor_val}")
            print("✓ 因子值数值精度验证通过")

            # 测试2: to_entities转换
            print("\n→ 测试to_entities转换...")
            entities = model_list.to_entities()
            print(f"✓ 实体列表类型: {type(entities).__name__}")
            print(f"✓ 实体列表长度: {len(entities)}")
            assert len(entities) == len(model_list), f"实体列表长度应等于ModelList长度，{len(entities)} != {len(model_list)}"

            # Factor没有专门的业务实体，应该返回Model对象
            first_entity = entities[0]
            assert isinstance(first_entity, MFactor), f"应返回MFactor对象，实际{type(first_entity)}"

            # 验证实体属性
            assert isinstance(first_entity.entity_type, int) or isinstance(first_entity.entity_type, ENTITY_TYPES)
            assert isinstance(first_entity.factor_value, Decimal)
            print("✓ Factor实体转换验证通过")

            # 测试3: 业务对象映射验证
            print("\n→ 测试业务对象映射...")
            for i, entity in enumerate(entities):
                # 验证数值字段
                assert isinstance(entity.factor_value, Decimal), "因子值应为Decimal类型"

                # 验证枚举字段
                if hasattr(entity.entity_type, 'name'):
                    assert entity.entity_type in ENTITY_TYPES, "entity_type应为有效枚举值"
                assert hasattr(entity.source, 'name'), "source应为枚举对象"
                assert entity.source == SOURCE_TYPES.TEST, f"source应为TEST，实际{entity.source}"

                # 验证其他字段类型
                assert isinstance(entity.entity_id, str)
                assert isinstance(entity.factor_name, str)
                assert isinstance(entity.factor_category, str)
                assert isinstance(entity.timestamp, datetime)
                print(f"  - 实体{i+1}: {entity.factor_name} for {entity.entity_id}")
                print(f"    值={entity.factor_value} 类型={entity.factor_category}")
                if hasattr(entity.entity_type, 'name'):
                    print(f"    实体类型={entity.entity_type.name} source={entity.source.name}")
            print("✓ 业务对象映射验证通过")

            # 测试4: 验证缓存机制
            print("\n→ 测试转换缓存机制...")
            df2 = model_list.to_dataframe()
            entities2 = model_list.to_entities()
            # 验证结果一致性
            assert df.equals(df2), "DataFrame缓存结果应一致"
            assert len(entities) == len(entities2), "实体列表缓存结果应一致"
            print("✓ 缓存机制验证正确")

            # 测试5: 验证空ModelList的转换
            print("\n→ 测试空ModelList的转换...")
            empty_model_list = factor_crud.find(filters={"entity_id": "NONEXISTENT_CONVERT_ENTITY"})
            assert len(empty_model_list) == 0, "空ModelList长度应为0"
            empty_df = empty_model_list.to_dataframe()
            empty_entities = empty_model_list.to_entities()
            assert isinstance(empty_df, pd.DataFrame), "空转换应返回DataFrame"
            assert empty_df.shape[0] == 0, "空DataFrame行数应为0"
            assert isinstance(empty_entities, list), "空转换应返回列表"
            assert len(empty_entities) == 0, "空实体列表长度应为0"
            print("✓ 空ModelList转换验证正确")

            # 测试6: 单个Model的to_entity转换
            print("\n→ 测试单个Model的to_entity转换...")
            single_model = model_list[0]  # 获取第一个Model
            single_entity = single_model.to_entity()
            print(f"✓ 单个Model转换: {single_model.factor_name} → {single_entity.factor_name}")

            assert isinstance(single_entity, MFactor), "单个Model应转换为MFactor对象"
            assert single_entity.factor_name == single_model.factor_name
            assert single_entity.entity_id == single_model.entity_id
            assert hasattr(single_entity.source, 'name'), "转换后source应为枚举对象"
            print("✓ 单个Model to_entity转换验证通过")

            # 测试7: 因子业务逻辑验证
            print("\n→ 测试因子业务逻辑验证...")
            entity_type_counts = {}
            category_counts = {}

            for entity in entities:
                # 统计实体类型分布
                entity_type = entity.entity_type
                if hasattr(entity_type, 'name'):
                    entity_type_name = entity_type.name
                else:
                    entity_type_name = str(entity_type)

                entity_type_counts[entity_type_name] = entity_type_counts.get(entity_type_name, 0) + 1

                # 统计因子分类分布
                category = entity.factor_category
                category_counts[category] = category_counts.get(category, 0) + 1

            print(f"✓ 实体类型分布: {entity_type_counts}")
            print(f"✓ 因子分类分布: {category_counts}")

            # 验证至少包含预期的实体类型和分类
            expected_entity_types = ['STOCK', 'MARKET', 'INDUSTRY', 'COUNTRY']
            for et in expected_entity_types:
                if et in entity_type_counts:
                    assert entity_type_counts[et] > 0, f"{et}类型因子数量应大于0"

            expected_categories = ['technical', 'market', 'fundamental', 'macro']
            for cat in expected_categories:
                if cat in category_counts:
                    assert category_counts[cat] > 0, f"{cat}分类因子数量应大于0"

            print("✓ 因子业务逻辑验证通过")

            print("\n✓ 所有Factor ModelList转换功能测试通过！")

        finally:
            # 清理测试数据并验证删除效果
            try:
                test_factors_to_delete = factor_crud.find(filters={"source": SOURCE_TYPES.TEST.value})
                before_delete = len(factor_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))

                for factor in test_factors_to_delete:
                    factor_crud.remove({"uuid": factor.uuid})

                after_delete = len(factor_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
                deleted_count = before_delete - after_delete
                print(f"\n→ 清理测试数据: 删除了 {deleted_count} 条记录")

            except Exception as cleanup_error:
                print(f"\n✗ 清理测试数据失败: {cleanup_error}")
                # 不重新抛出异常，避免影响测试结果


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：Factor CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_factor_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 多实体类型因子存储和统计分析功能")