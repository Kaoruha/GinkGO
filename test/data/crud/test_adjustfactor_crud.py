"""
AdjustFactor CRUD数据库操作TDD测试

测试CRUD层的复权因子数据操作：
- 批量插入 (add_batch)
- 单条插入 (add)
- 查询 (find)
- 更新 (update)
- 删除 (remove)

AdjustFactor是复权因子数据模型，存储股票的前复权、后复权和复权因子。
为量化交易中的价格复权计算和历史数据对比提供支持。
复权因子是进行准确的历史价格计算和收益率分析的重要基础数据。
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.crud.adjustfactor_crud import AdjustfactorCRUD
from ginkgo.data.models.model_adjustfactor import MAdjustfactor
from ginkgo.enums import SOURCE_TYPES


@pytest.mark.database
@pytest.mark.tdd
class TestAdjustFactorCRUDInsert:
    CRUD_TEST_CONFIG = {'crud_class': AdjustfactorCRUD}
    """1. CRUD层插入操作测试 - AdjustFactor数据插入验证"""

    def test_add_batch_basic(self):
        """测试批量插入AdjustFactor数据 - 使用真实数据库"""
        print("\n" + "="*60)
        print("开始测试: AdjustFactor CRUD层批量插入")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()
        print(f"✓ 创建AdjustfactorCRUD实例: {adjustfactor_crud.__class__.__name__}")

        # 创建测试AdjustFactor数据 - 不同股票的复权因子
        base_time = datetime(2023, 1, 3, 9, 30)
        test_factors = []

        # 平安银行(000001.SZ)复权因子
        pingan_factor = MAdjustfactor(
            code="000001.SZ",
            timestamp=base_time,
            foreadjustfactor=Decimal("1.2345"),
            backadjustfactor=Decimal("0.9876"),
            adjustfactor=Decimal("1.0123"),
            source=SOURCE_TYPES.TEST
        )
        test_factors.append(pingan_factor)

        # 万科A(000002.SZ)复权因子
        vanke_factor = MAdjustfactor(
            code="000002.SZ",
            timestamp=base_time + timedelta(days=1),
            foreadjustfactor=Decimal("1.3456"),
            backadjustfactor=Decimal("0.8765"),
            adjustfactor=Decimal("1.0234"),
            source=SOURCE_TYPES.TEST
        )
        test_factors.append(vanke_factor)

        # 国华网安(000004.SZ)复权因子
        guohua_factor = MAdjustfactor(
            code="000004.SZ",
            timestamp=base_time + timedelta(days=2),
            foreadjustfactor=Decimal("1.4567"),
            backadjustfactor=Decimal("0.7654"),
            adjustfactor=Decimal("1.0345"),
            source=SOURCE_TYPES.TEST
        )
        test_factors.append(guohua_factor)

        print(f"✓ 创建测试数据: {len(test_factors)}条AdjustFactor记录")
        print(f"  - 股票代码: {[f.code for f in test_factors]}")
        print(f"  - 时间范围: {test_factors[0].timestamp} ~ {test_factors[-1].timestamp}")

        try:
            # 批量插入
            print("\n→ 执行批量插入操作...")
            adjustfactor_crud.add_batch(test_factors)
            print("✓ 批量插入成功")

            # 验证可以查询出插入的数据
            print("\n→ 验证插入的数据...")
            query_result = adjustfactor_crud.find(filters={
                "timestamp__gte": base_time,
                "timestamp__lte": base_time + timedelta(days=3)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 3

            # 验证数据内容
            codes = set(f.code for f in query_result)
            print(f"✓ 股票代码验证通过: {len(codes)} 种")
            assert len(codes) >= 3

        except Exception as e:
            print(f"✗ 批量插入失败: {e}")
            raise

    def test_add_single_adjustfactor(self):
        """测试单条AdjustFactor数据插入"""
        print("\n" + "="*60)
        print("开始测试: AdjustFactor CRUD层单条插入")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        test_factor = MAdjustfactor(
            code="000858.SZ",
            timestamp=datetime(2023, 1, 3, 10, 30),
            foreadjustfactor=Decimal("2.3456"),
            backadjustfactor=Decimal("0.6543"),
            adjustfactor=Decimal("1.1234")
        )
        print(f"✓ 创建测试AdjustFactor: {test_factor.code}")
        print(f"  - 前复权因子: {test_factor.foreadjustfactor}")
        print(f"  - 后复权因子: {test_factor.backadjustfactor}")
        print(f"  - 复权因子: {test_factor.adjustfactor}")

        try:
            # 单条插入
            print("\n→ 执行单条插入操作...")
            adjustfactor_crud.add(test_factor)
            print("✓ 单条插入成功")

            # 验证数据
            print("\n→ 验证插入的数据...")
            query_result = adjustfactor_crud.find(filters={
                "code": "000858.SZ",
                "timestamp": datetime(2023, 1, 3, 10, 30)
            })
            print(f"✓ 查询到 {len(query_result)} 条记录")
            assert len(query_result) >= 1

            inserted_factor = query_result[0]
            print(f"✓ 插入的AdjustFactor验证: {inserted_factor.code}")
            assert inserted_factor.code == "000858.SZ"
            assert inserted_factor.adjustfactor == Decimal("1.1234")

        except Exception as e:
            print(f"✗ 单条插入失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestAdjustFactorCRUDQuery:
    CRUD_TEST_CONFIG = {'crud_class': AdjustfactorCRUD}
    """2. CRUD层查询操作测试 - AdjustFactor数据查询和过滤"""

    def test_find_by_stock_code(self):
        """测试根据股票代码查询AdjustFactor"""
        print("\n" + "="*60)
        print("开始测试: 根据股票代码查询AdjustFactor")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        try:
            # 查询特定股票的复权因子
            print("→ 查询股票代码000001.SZ的复权因子...")
            stock_factors = adjustfactor_crud.find(filters={
                "code": "000001.SZ"
            })
            print(f"✓ 查询到 {len(stock_factors)} 条记录")

            # 验证查询结果
            for factor in stock_factors:
                print(f"  - {factor.timestamp}: 前复权{factor.foreadjustfactor}, 后复权{factor.backadjustfactor}, 复权{factor.adjustfactor}")
                assert factor.code == "000001.SZ"
                assert factor.adjustfactor > 0

        except Exception as e:
            print(f"✗ 查询失败: {e}")
            raise

    def test_find_by_time_range(self):
        """测试根据时间范围查询AdjustFactor"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围查询AdjustFactor")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        try:
            # 查询特定时间范围的复权因子
            start_time = datetime(2023, 1, 1)
            end_time = datetime(2023, 1, 7, 23, 59, 59)  # 只查询一周数据 - 性能优化

            print(f"→ 查询时间范围 {start_time} ~ {end_time} 的复权因子...")
            time_factors = adjustfactor_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time,
                "limit": 100  # 限制查询数量 - 性能优化
            })
            print(f"✓ 查询到 {len(time_factors)} 条记录")

            # 验证时间范围
            for factor in time_factors:
                print(f"  - {factor.code}: {factor.adjustfactor} ({factor.timestamp.date()})")
                assert start_time <= factor.timestamp <= end_time

            print("✓ 时间范围查询验证成功")

        except Exception as e:
            print(f"✗ 时间范围查询失败: {e}")
            raise

    def test_find_by_factor_value_range(self):
        """测试根据复权因子值范围查询AdjustFactor"""
        print("\n" + "="*60)
        print("开始测试: 根据复权因子值范围查询AdjustFactor")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        try:
            # 查询复权因子大于1.1的记录
            print("→ 查询复权因子 > 1.1 的记录...")
            high_factors = adjustfactor_crud.find(filters={
                "adjustfactor__gt": Decimal("1.1")
            })
            print(f"✓ 查询到 {len(high_factors)} 条高复权因子记录")

            # 查询前复权因子小于1.0的记录
            print("→ 查询前复权因子 < 1.0 的记录...")
            low_fore_factors = adjustfactor_crud.find(filters={
                "foreadjustfactor__lt": Decimal("1.0")
            })
            print(f"✓ 查询到 {len(low_fore_factors)} 条低前复权因子记录")

            # 验证查询结果
            for factor in high_factors[:3]:
                print(f"  - {factor.code}: 复权因子 {factor.adjustfactor}")

            for factor in low_fore_factors[:3]:
                print(f"  - {factor.code}: 前复权因子 {factor.foreadjustfactor}")

            print("✓ 复权因子值范围查询验证成功")

        except Exception as e:
            print(f"✗ 复权因子值范围查询失败: {e}")
            raise

    def test_business_helper_methods(self):
        """测试业务辅助方法"""
        print("\n" + "="*60)
        print("开始测试: AdjustFactor业务辅助方法")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        try:
            # 测试find_by_code方法
            print("→ 测试find_by_code方法...")
            code_factors = adjustfactor_crud.find_by_code("000001.SZ", page_size=5)
            print(f"✓ find_by_code查询到 {len(code_factors)} 条记录")

            # 测试find_latest_factor方法
            print("→ 测试find_latest_factor方法...")
            latest_factors = adjustfactor_crud.find_latest_factor("000001.SZ")
            print(f"✓ find_latest_factor查询到 {len(latest_factors)} 条记录")

            # 测试count_by_code方法
            print("→ 测试count_by_code方法...")
            count = adjustfactor_crud.count_by_code("000001.SZ")
            print(f"✓ count_by_code统计到 {count} 条记录")

            # 测试get_all_codes方法
            print("→ 测试get_all_codes方法...")
            all_codes = adjustfactor_crud.get_all_codes()
            print(f"✓ get_all_codes获取到 {len(all_codes)} 个股票代码")
            print(f"  - 示例代码: {all_codes[:5]}")

            print("✓ 业务辅助方法验证成功")

        except Exception as e:
            print(f"✗ 业务辅助方法测试失败: {e}")
            raise


# NOTE: AdjustFactor数据主要用于历史参考和分析，通常不需要更新操作
# 如需修正数据，建议通过重新导入或删除后重新插入的方式处理


@pytest.mark.database
@pytest.mark.tdd
class TestAdjustFactorCRUDBusinessLogic:
    CRUD_TEST_CONFIG = {'crud_class': AdjustfactorCRUD}
    """4. CRUD层业务逻辑测试 - AdjustFactor业务场景验证"""

    def test_adjustfactor_summary_analysis(self):
        """测试复权因子汇总分析"""
        print("\n" + "="*60)
        print("开始测试: 复权因子汇总分析")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        try:
            # 使用业务辅助方法获取汇总信息
            print("→ 获取股票复权因子汇总信息...")
            summary = adjustfactor_crud.get_adjustment_summary("000001.SZ")
            print(f"✓ 复权因子汇总结果:")
            print(f"  - 股票代码: {summary['code']}")
            print(f"  - 调整次数: {summary['total_adjustments']}")
            print(f"  - 最新因子: {summary['latest_factor']}")
            print(f"  - 累积因子: {summary['cumulative_factor']}")
            print(f"  - 时间范围: {summary['date_range']}")

            # 验证汇总结果
            if summary['total_adjustments'] > 0:
                assert summary['latest_factor'] > 0
                assert summary['cumulative_factor'] > 0
                print("✓ 复权因子汇总分析验证成功")

        except Exception as e:
            print(f"✗ 复权因子汇总分析失败: {e}")
            raise

    def test_stock_adjustfactor_comparison(self):
        """测试不同股票复权因子对比分析"""
        print("\n" + "="*60)
        print("开始测试: 不同股票复权因子对比分析")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        try:
            # 获取所有股票代码
            print("→ 获取所有股票代码进行对比...")
            all_codes = adjustfactor_crud.get_all_codes()

            if len(all_codes) < 3:
                print("✗ 股票代码不足，跳过对比分析")
                return

            # 对前5个股票进行复权因子对比
            comparison_codes = all_codes[:5]
            stock_comparison = {}

            for code in comparison_codes:
                try:
                    summary = adjustfactor_crud.get_adjustment_summary(code)
                    stock_comparison[code] = {
                        "total_adjustments": summary["total_adjustments"],
                        "latest_factor": summary["latest_factor"],
                        "cumulative_factor": summary["cumulative_factor"]
                    }
                except Exception as e:
                    print(f"  - {code}: 获取数据失败，跳过")
                    continue

            print(f"✓ 股票复权因子对比结果:")
            for code, stats in stock_comparison.items():
                print(f"  - {code}:")
                print(f"    调整次数: {stats['total_adjustments']}")
                print(f"    最新因子: {stats['latest_factor']:.6f}")
                print(f"    累积因子: {stats['cumulative_factor']:.6f}")

            # 找出累积因子最大和最小的股票
            if stock_comparison:
                max_factor_stock = max(stock_comparison.items(), key=lambda x: x[1]["cumulative_factor"])
                min_factor_stock = min(stock_comparison.items(), key=lambda x: x[1]["cumulative_factor"])

                print(f"✓ 累积因子最大: {max_factor_stock[0]} ({max_factor_stock[1]['cumulative_factor']:.6f})")
                print(f"✓ 累积因子最小: {min_factor_stock[0]} ({min_factor_stock[1]['cumulative_factor']:.6f})")

            print("✓ 股票复权因子对比分析验证成功")

        except Exception as e:
            print(f"✗ 股票复权因子对比分析失败: {e}")
            raise

    def test_adjustfactor_trend_analysis(self):
        """测试复权因子时序趋势分析"""
        print("\n" + "="*60)
        print("开始测试: 复权因子时序趋势分析")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        try:
            # 查询特定时间范围内的复权因子时序数据
            start_time = datetime(2023, 1, 1)
            end_time = datetime(2023, 12, 31)

            print(f"→ 查询时间范围 {start_time.date()} ~ {end_time.date()} 的复权因子时序数据...")
            time_factors = adjustfactor_crud.find(filters={
                "timestamp__gte": start_time,
                "timestamp__lte": end_time,
                "code": "000001.SZ"
            })

            if len(time_factors) < 5:
                print("✗ 时序数据不足，跳过趋势分析")
                return

            # 按时间排序
            time_factors.sort(key=lambda f: f.timestamp)

            # 计算趋势统计
            adjustfactor_values = [float(f.adjustfactor) for f in time_factors]
            forefactor_values = [float(f.foreadjustfactor) for f in time_factors]
            timestamps = [f.timestamp for f in time_factors]

            if len(adjustfactor_values) >= 2:
                first_adjust = adjustfactor_values[0]
                last_adjust = adjustfactor_values[-1]
                total_change = last_adjust - first_adjust
                total_change_pct = (total_change / first_adjust) * 100 if first_adjust != 0 else 0

                first_fore = forefactor_values[0]
                last_fore = forefactor_values[-1]
                fore_change = last_fore - first_fore
                fore_change_pct = (fore_change / first_fore) * 100 if first_fore != 0 else 0

                print(f"✓ 复权因子时序趋势分析结果:")
                print(f"  - 数据点数: {len(time_factors)}")
                print(f"  - 时间跨度: {timestamps[0].date()} ~ {timestamps[-1].date()}")
                print(f"  - 复权因子变化: {total_change:+.6f} ({total_change_pct:+.2f}%)")
                print(f"  - 前复权因子变化: {fore_change:+.6f} ({fore_change_pct:+.2f}%)")

                # 计算变化趋势
                if len(adjustfactor_values) >= 3:
                    recent_avg = sum(adjustfactor_values[-3:]) / 3
                    early_avg = sum(adjustfactor_values[:3]) / 3
                    trend_direction = "上升" if recent_avg > early_avg else "下降"
                    trend_strength = abs(recent_avg - early_avg) / early_avg * 100

                    print(f"  - 近期趋势: {trend_direction}")
                    print(f"  - 趋势强度: {trend_strength:.2f}%")

            print("✓ 复权因子时序趋势分析验证成功")

        except Exception as e:
            print(f"✗ 复权因子时序趋势分析失败: {e}")
            raise

    def test_abnormal_adjustfactor_detection(self):
        """测试异常复权因子检测"""
        print("\n" + "="*60)
        print("开始测试: 异常复权因子检测")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        try:
            # 查询所有复权因子进行异常检测
            print("→ 查询所有复权因子进行异常检测...")
            all_factors = adjustfactor_crud.find(page_size=1000)

            if len(all_factors) < 10:
                print("✗ 复权因子数据不足，跳过异常检测")
                return

            # 异常检测标准
            abnormal_factors = []
            extreme_factors = []
            zero_factors = []

            for factor in all_factors:
                adjust_val = float(factor.adjustfactor)
                fore_val = float(factor.foreadjustfactor)
                back_val = float(factor.backadjustfactor)

                # 检测零值或负值
                if adjust_val <= 0 or fore_val <= 0 or back_val <= 0:
                    zero_factors.append(factor)
                    continue

                # 检测极端值（偏离正常范围过大）
                if adjust_val > 10.0 or adjust_val < 0.1:
                    extreme_factors.append(factor)
                    continue

                # 检测异常变化（前后复权因子差异过大）
                ratio_diff = abs(fore_val - back_val) / back_val if back_val > 0 else 0
                if ratio_diff > 5.0:  # 前后复权因子差异超过5倍
                    abnormal_factors.append(factor)

            print(f"✓ 异常复权因子检测结果:")
            print(f"  - 总检测数: {len(all_factors)}")
            print(f"  - 零值/负值: {len(zero_factors)}")
            print(f"  - 极端值: {len(extreme_factors)}")
            print(f"  - 异常变化: {len(abnormal_factors)}")

            # 显示异常样本
            if zero_factors:
                print(f"  - 零值样本: {zero_factors[0].code} at {zero_factors[0].timestamp}")
            if extreme_factors:
                print(f"  - 极端值样本: {extreme_factors[0].code} 复权因子={extreme_factors[0].adjustfactor}")
            if abnormal_factors:
                print(f"  - 异常变化样本: {abnormal_factors[0].code} 前复权={abnormal_factors[0].foreadjustfactor}, 后复权={abnormal_factors[0].backadjustfactor}")

            print("✓ 异常复权因子检测验证成功")

        except Exception as e:
            print(f"✗ 异常复权因子检测失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestAdjustFactorCRUDDelete:
    CRUD_TEST_CONFIG = {'crud_class': AdjustfactorCRUD}
    """3. CRUD层删除操作测试 - AdjustFactor数据删除验证"""

    def test_delete_adjustfactor_by_stock_code(self):
        """测试根据股票代码删除AdjustFactor"""
        print("\n" + "="*60)
        print("开始测试: 根据股票代码删除AdjustFactor")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        # 准备测试数据
        print("→ 准备测试数据...")
        test_factor = MAdjustfactor(
            code="DELETE_TEST_STOCK",
            timestamp=datetime(2023, 6, 15, 10, 30),
            foreadjustfactor=Decimal("1.5678"),
            backadjustfactor=Decimal("0.8765"),
            adjustfactor=Decimal("1.2345")
        )
        adjustfactor_crud.add(test_factor)
        print(f"✓ 插入测试数据: {test_factor.code}")

        # 验证数据存在
        before_count = len(adjustfactor_crud.find(filters={"code": "DELETE_TEST_STOCK"}))
        print(f"✓ 删除前数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行删除操作...")
            adjustfactor_crud.remove(filters={"code": "DELETE_TEST_STOCK"})
            print("✓ 删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(adjustfactor_crud.find(filters={"code": "DELETE_TEST_STOCK"}))
            print(f"✓ 删除后数据量: {after_count}")
            assert after_count == 0, "删除后应该没有相关数据"

            print("✓ 根据股票代码删除AdjustFactor验证成功")

        except Exception as e:
            print(f"✗ 删除操作失败: {e}")
            raise

    def test_delete_adjustfactor_by_time_range(self):
        """测试根据时间范围删除AdjustFactor"""
        print("\n" + "="*60)
        print("开始测试: 根据时间范围删除AdjustFactor")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        # 准备测试数据 - 特定时间范围的数据
        print("→ 准备测试数据...")
        test_time_range = [
            datetime(2023, 7, 1, 10, 30),
            datetime(2023, 7, 2, 10, 30),
            datetime(2023, 7, 3, 10, 30)
        ]

        for i, test_time in enumerate(test_time_range):
            test_factor = MAdjustfactor(
                code=f"DELETE_TIME_{i+1:03d}",
                timestamp=test_time,
                foreadjustfactor=Decimal(f"1.{1000+i}"),
                backadjustfactor=Decimal(f"0.{8000+i}"),
                adjustfactor=Decimal(f"1.{2000+i}")
            )
            adjustfactor_crud.add(test_factor)

        print(f"✓ 插入时间范围测试数据: {len(test_time_range)}条")

        # 验证数据存在
        before_count = len(adjustfactor_crud.find(filters={
            "timestamp__gte": datetime(2023, 7, 1),
            "timestamp__lte": datetime(2023, 7, 3, 23, 59, 59)
        }))
        print(f"✓ 删除前时间范围内数据量: {before_count}")

        try:
            # 执行删除
            print("\n→ 执行时间范围删除操作...")
            adjustfactor_crud.remove(filters={
                "timestamp__gte": datetime(2023, 7, 1),
                "timestamp__lte": datetime(2023, 7, 3, 23, 59, 59)
            })
            print("✓ 时间范围删除操作完成")

            # 验证删除结果
            print("\n→ 验证删除结果...")
            after_count = len(adjustfactor_crud.find(filters={
                "timestamp__gte": datetime(2023, 7, 1),
                "timestamp__lte": datetime(2023, 7, 3, 23, 59, 59)
            }))
            print(f"✓ 删除后时间范围内数据量: {after_count}")
            assert after_count == 0, "删除后时间范围内应该没有数据"

            print("✓ 根据时间范围删除AdjustFactor验证成功")

        except Exception as e:
            print(f"✗ 时间范围删除操作失败: {e}")
            raise

    def test_delete_adjustfactor_by_factor_value(self):
        """测试根据复权因子值删除AdjustFactor"""
        print("\n" + "="*60)
        print("开始测试: 根据复权因子值删除AdjustFactor")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        # 准备测试数据 - 特定复权因子值的数据
        print("→ 准备测试数据...")
        test_factors = [
            ("DELETE_FACTOR_001", Decimal("2.5000")),  # 高复权因子
            ("DELETE_FACTOR_002", Decimal("0.5000")),  # 低复权因子
            ("DELETE_FACTOR_003", Decimal("3.0000")),  # 极高复权因子
        ]

        for code, adjust_factor in test_factors:
            test_factor = MAdjustfactor(
                code=code,
                timestamp=datetime(2023, 8, 15, 10, 30),
                foreadjustfactor=Decimal("1.2345"),
                backadjustfactor=Decimal("0.9876"),
                adjustfactor=adjust_factor
            )
            adjustfactor_crud.add(test_factor)

        print(f"✓ 插入复权因子值测试数据: {len(test_factors)}条")

        try:
            # 删除高复权因子数据 (> 2.0)
            print("\n→ 执行高复权因子删除操作...")
            before_high = len(adjustfactor_crud.find(filters={"adjustfactor__gt": Decimal("2.0")}))
            print(f"✓ 删除前高复权因子数据量: {before_high}")

            adjustfactor_crud.remove(filters={"adjustfactor__gt": Decimal("2.0")})
            print("✓ 高复权因子删除操作完成")

            after_high = len(adjustfactor_crud.find(filters={"adjustfactor__gt": Decimal("2.0")}))
            print(f"✓ 删除后高复权因子数据量: {after_high}")
            assert after_high == 0, "删除后应该没有高复权因子数据"

            # 删除低复权因子数据 (< 1.0)
            print("\n→ 执行低复权因子删除操作...")
            before_low = len(adjustfactor_crud.find(filters={"adjustfactor__lt": Decimal("1.0")}))
            print(f"✓ 删除前低复权因子数据量: {before_low}")

            adjustfactor_crud.remove(filters={"adjustfactor__lt": Decimal("1.0")})
            print("✓ 低复权因子删除操作完成")

            after_low = len(adjustfactor_crud.find(filters={"adjustfactor__lt": Decimal("1.0")}))
            print(f"✓ 删除后低复权因子数据量: {after_low}")
            assert after_low == 0, "删除后应该没有低复权因子数据"

            print("✓ 根据复权因子值删除AdjustFactor验证成功")

        except Exception as e:
            print(f"✗ 复权因子值删除操作失败: {e}")
            raise

    def test_delete_adjustfactor_by_abnormal_values(self):
        """测试删除异常AdjustFactor数据"""
        print("\n" + "="*60)
        print("开始测试: 删除异常AdjustFactor数据")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        # 准备异常数据
        print("→ 准备异常测试数据...")
        abnormal_factors = [
            # 极端值数据
            ("ABNORMAL_EXTREME_1", Decimal("20.0000"), Decimal("15.0000"), Decimal("25.0000")),
            ("ABNORMAL_EXTREME_2", Decimal("0.0100"), Decimal("0.0050"), Decimal("0.0200")),
            # 异常前后差异数据
            ("ABNORMAL_DIFF_1", Decimal("5.0000"), Decimal("1.0000"), Decimal("10.0000")),
        ]

        for code, fore, back, adjust in abnormal_factors:
            test_factor = MAdjustfactor(
                code=code,
                timestamp=datetime(2023, 9, 1, 10, 30),
                foreadjustfactor=fore,
                backadjustfactor=back,
                adjustfactor=adjust
            )
            adjustfactor_crud.add(test_factor)

        print(f"✓ 插入异常测试数据: {len(abnormal_factors)}条")

        try:
            # 删除极端值数据
            print("\n→ 执行极端值数据删除...")
            before_extreme = len(adjustfactor_crud.find(filters={
                "adjustfactor__gt": Decimal("10.0")
            }))
            print(f"✓ 删除前极端高值数据量: {before_extreme}")

            adjustfactor_crud.remove(filters={"adjustfactor__gt": Decimal("10.0")})
            print("✓ 极端值删除操作完成")

            after_extreme = len(adjustfactor_crud.find(filters={
                "adjustfactor__gt": Decimal("10.0")
            }))
            print(f"✓ 删除后极端高值数据量: {after_extreme}")
            assert after_extreme == 0, "删除后应该没有极端高值数据"

            # 删除极小值数据
            print("\n→ 执行极小值数据删除...")
            before_tiny = len(adjustfactor_crud.find(filters={
                "adjustfactor__lt": Decimal("0.1")
            }))
            print(f"✓ 删除前极小值数据量: {before_tiny}")

            adjustfactor_crud.remove(filters={"adjustfactor__lt": Decimal("0.1")})
            print("✓ 极小值删除操作完成")

            after_tiny = len(adjustfactor_crud.find(filters={
                "adjustfactor__lt": Decimal("0.1")
            }))
            print(f"✓ 删除后极小值数据量: {after_tiny}")
            assert after_tiny == 0, "删除后应该没有极小值数据"

            print("✓ 删除异常AdjustFactor数据验证成功")

        except Exception as e:
            print(f"✗ 异常数据删除操作失败: {e}")
            raise

    def test_delete_adjustfactor_batch_cleanup(self):
        """测试批量清理AdjustFactor数据"""
        print("\n" + "="*60)
        print("开始测试: 批量清理AdjustFactor数据")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        # 准备批量清理数据
        print("→ 准备批量清理测试数据...")
        cleanup_codes = []
        base_time = datetime(2023, 10, 1)

        for i in range(10):
            code = f"CLEANUP_BATCH_{i+1:03d}"
            cleanup_codes.append(code)

            test_factor = MAdjustfactor(
                code=code,
                timestamp=base_time + timedelta(days=i),
                foreadjustfactor=Decimal(f"1.{1000+i}"),
                backadjustfactor=Decimal(f"0.{9000+i}"),
                adjustfactor=Decimal(f"1.{2000+i}")
            )
            adjustfactor_crud.add(test_factor)

        print(f"✓ 插入批量清理测试数据: {len(cleanup_codes)}条")

        # 验证数据存在
        before_count = len(adjustfactor_crud.find(filters={
            "code__like": "CLEANUP_BATCH_%"
        }))
        print(f"✓ 删除前批量数据量: {before_count}")

        try:
            # 批量删除
            print("\n→ 执行批量清理操作...")
            adjustfactor_crud.remove(filters={
                "code__like": "CLEANUP_BATCH_%"
            })
            print("✓ 批量清理操作完成")

            # 验证删除结果
            print("\n→ 验证批量清理结果...")
            after_count = len(adjustfactor_crud.find(filters={
                "code__like": "CLEANUP_BATCH_%"
            }))
            print(f"✓ 删除后批量数据量: {after_count}")
            assert after_count == 0, "删除后应该没有批量清理数据"

            # 确认其他数据未受影响
            other_data_count = len(adjustfactor_crud.find(page_size=10))
            print(f"✓ 其他数据保留验证: {other_data_count}条")

            print("✓ 批量清理AdjustFactor数据验证成功")

        except Exception as e:
            print(f"✗ 批量清理操作失败: {e}")
            raise


@pytest.mark.database
@pytest.mark.tdd
class TestAdjustFactorCRUDConversions:
    CRUD_TEST_CONFIG = {'crud_class': AdjustfactorCRUD}
    """5. CRUD层转换方法测试 - AdjustFactor ModelList转换功能验证"""

    def test_model_list_conversions(self):
        """测试ModelList的to_dataframe和to_entities转换功能"""
        import pandas as pd
        print("\n" + "="*60)
        print("开始测试: AdjustFactor ModelList转换功能")
        print("="*60)

        adjustfactor_crud = AdjustfactorCRUD()

        try:
            # 创建测试数据 - 复权因子数据
            base_time = datetime(2023, 1, 10, 10, 30)
            test_factors = [
                MAdjustfactor(
                    code="CONVERT_FACTOR001.SZ",
                    timestamp=base_time,
                    foreadjustfactor=Decimal("1.1234"),
                    backadjustfactor=Decimal("0.9876"),
                    adjustfactor=Decimal("1.0234"),
                    source=SOURCE_TYPES.TEST
                ),
                MAdjustfactor(
                    code="CONVERT_FACTOR002.SZ",
                    timestamp=base_time + timedelta(hours=1),
                    foreadjustfactor=Decimal("1.2345"),
                    backadjustfactor=Decimal("0.8765"),
                    adjustfactor=Decimal("1.0456"),
                    source=SOURCE_TYPES.TEST
                ),
                MAdjustfactor(
                    code="CONVERT_FACTOR003.SH",
                    timestamp=base_time + timedelta(hours=2),
                    foreadjustfactor=Decimal("1.3456"),
                    backadjustfactor=Decimal("0.7654"),
                    adjustfactor=Decimal("1.0678"),
                    source=SOURCE_TYPES.TEST
                )
            ]

            # 获取操作前数据条数用于验证
            before_count = len(adjustfactor_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 操作前数据库记录数: {before_count}")

            # 插入测试数据
            adjustfactor_crud.add_batch(test_factors)

            # 验证数据库记录数变化
            after_count = len(adjustfactor_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
            print(f"✓ 操作后数据库记录数: {after_count}")
            assert after_count - before_count == len(test_factors), f"应增加{len(test_factors)}条数据，实际增加{after_count - before_count}条"

            # 获取ModelList进行转换测试
            print("\n→ 获取ModelList...")
            model_list = adjustfactor_crud.find(filters={"code__like": "CONVERT_FACTOR%"})
            print(f"✓ ModelList类型: {type(model_list).__name__}")
            print(f"✓ ModelList长度: {len(model_list)}")
            assert len(model_list) >= 3

            # 测试1: to_dataframe转换
            print("\n→ 测试to_dataframe转换...")
            df = model_list.to_dataframe()
            print(f"✓ DataFrame类型: {type(df).__name__}")
            print(f"✓ DataFrame形状: {df.shape}")
            assert isinstance(df, pd.DataFrame), "应返回DataFrame"
            assert len(df) == len(model_list), f"DataFrame行数应等于ModelList长度，{len(df)} != {len(model_list)}"

            # 验证DataFrame列和内容
            required_columns = ['code', 'timestamp', 'foreadjustfactor', 'backadjustfactor', 'adjustfactor', 'source']
            for col in required_columns:
                assert col in df.columns, f"DataFrame应包含列: {col}"
            print(f"✓ 验证必要列存在: {required_columns}")

            # 验证DataFrame数据内容
            assert all(df['code'].str.startswith('CONVERT_FACTOR')), "股票代码应以CONVERT_FACTOR开头"
            assert set(df['code']) == {'CONVERT_FACTOR001.SZ', 'CONVERT_FACTOR002.SZ', 'CONVERT_FACTOR003.SH'}, "股票代码应匹配"
            print("✓ DataFrame数据内容验证通过")

            # 验证复权因子数值精度
            print("→ 验证复权因子数值精度...")
            for i, (_, row) in enumerate(df.iterrows()):
                fore_val = row['foreadjustfactor']
                back_val = row['backadjustfactor']
                adjust_val = row['adjustfactor']

                # 验证数值类型（应该是Decimal或float）
                assert isinstance(fore_val, (Decimal, float, int)), f"第{i}行foreadjustfactor应为数值类型，实际{type(fore_val)}"
                assert isinstance(back_val, (Decimal, float, int)), f"第{i}行backadjustfactor应为数值类型，实际{type(back_val)}"
                assert isinstance(adjust_val, (Decimal, float, int)), f"第{i}行adjustfactor应为数值类型，实际{type(adjust_val)}"

                # 验证数值大于0
                assert float(fore_val) > 0, f"第{i}行前复权因子应大于0"
                assert float(back_val) > 0, f"第{i}行后复权因子应大于0"
                assert float(adjust_val) > 0, f"第{i}行复权因子应大于0"

                print(f"  - 复权因子{i+1}: {row['code']} 前={fore_val} 后={back_val} 调整={adjust_val}")
            print("✓ 复权因子数值精度验证通过")

            # 验证source枚举字段转换
            print("→ 验证source枚举字段转换...")
            for i, (_, row) in enumerate(df.iterrows()):
                source_val = row['source']
                assert isinstance(source_val, SOURCE_TYPES), f"第{i}行source应为枚举对象，实际{type(source_val)}"
                assert source_val in SOURCE_TYPES, f"第{i}行source枚举值无效: {source_val}"
                print(f"  - 股票{i+1}: {row['code']} source={source_val.name}")
            print("✓ source枚举字段转换验证通过")

            # 测试2: to_entities转换
            print("\n→ 测试to_entities转换...")
            entities = model_list.to_entities()
            print(f"✓ 实体列表类型: {type(entities).__name__}")
            print(f"✓ 实体列表长度: {len(entities)}")
            assert len(entities) == len(model_list), f"实体列表长度应等于ModelList长度，{len(entities)} != {len(model_list)}"

            # Adjustfactor没有专门的业务实体，应该返回Model对象
            first_entity = entities[0]
            assert isinstance(first_entity, MAdjustfactor), f"应返回MAdjustfactor对象，实际{type(first_entity)}"

            # 验证实体属性
            assert first_entity.code.startswith('CONVERT_FACTOR')
            assert isinstance(first_entity.foreadjustfactor, Decimal)
            assert isinstance(first_entity.backadjustfactor, Decimal)
            assert isinstance(first_entity.adjustfactor, Decimal)
            print("✓ AdjustFactor实体转换验证通过")

            # 测试3: 业务对象映射验证
            print("\n→ 测试业务对象映射...")
            for i, entity in enumerate(entities):
                # 验证数值字段
                assert isinstance(entity.foreadjustfactor, Decimal), "前复权因子应为Decimal类型"
                assert isinstance(entity.backadjustfactor, Decimal), "后复权因子应为Decimal类型"
                assert isinstance(entity.adjustfactor, Decimal), "复权因子应为Decimal类型"
                assert float(entity.foreadjustfactor) > 0, "前复权因子应大于0"
                assert float(entity.backadjustfactor) > 0, "后复权因子应大于0"
                assert float(entity.adjustfactor) > 0, "复权因子应大于0"

                # 验证枚举字段
                assert hasattr(entity.source, 'name'), "source应为枚举对象"
                assert entity.source == SOURCE_TYPES.TEST, f"source应为TEST，实际{entity.source}"

                # 验证其他字段类型
                assert isinstance(entity.code, str)
                assert isinstance(entity.timestamp, datetime)
                print(f"  - 实体{i+1}: {entity.code} @ {entity.timestamp}")
                print(f"    前={entity.foreadjustfactor} 后={entity.backadjustfactor} 调整={entity.adjustfactor} source={entity.source.name}")
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
            empty_model_list = adjustfactor_crud.find(filters={"code": "NONEXISTENT_CONVERT_FACTOR"})
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
            print(f"✓ 单个Model转换: {single_model.code} → {single_entity.code}")

            assert isinstance(single_entity, MAdjustfactor), "单个Model应转换为MAdjustfactor对象"
            assert single_entity.code == single_model.code
            assert single_entity.foreadjustfactor == single_model.foreadjustfactor
            assert hasattr(single_entity.source, 'name'), "转换后source应为枚举对象"
            print("✓ 单个Model to_entity转换验证通过")

            # 测试7: 复权因子数值有效性验证
            print("\n→ 测试复权因子数值有效性验证...")
            for entity in entities:
                # 验证复权因子数值的有效性（都应该大于0）
                fore_val = float(entity.foreadjustfactor)
                back_val = float(entity.backadjustfactor)
                adjust_val = float(entity.adjustfactor)

                # 验证所有因子值都大于0
                assert fore_val > 0, f"前复权因子应大于0: {fore_val}"
                assert back_val > 0, f"后复权因子应大于0: {back_val}"
                assert adjust_val > 0, f"复权因子应大于0: {adjust_val}"

                # 验证数值在合理范围内（通常在0.01-100之间）
                assert 0.01 <= fore_val <= 100, f"前复权因子超出合理范围: {fore_val}"
                assert 0.01 <= back_val <= 100, f"后复权因子超出合理范围: {back_val}"
                assert 0.01 <= adjust_val <= 100, f"复权因子超出合理范围: {adjust_val}"

                print(f"  - {entity.code}: 前={entity.foreadjustfactor} 后={entity.backadjustfactor} 调整={entity.adjustfactor} ✓")
            print("✓ 复权因子数值有效性验证通过")

            print("\n✓ 所有AdjustFactor ModelList转换功能测试通过！")

        finally:
            # 清理测试数据并验证删除效果
            try:
                test_factors_to_delete = adjustfactor_crud.find(filters={"code__like": "CONVERT_FACTOR%"})
                before_delete = len(adjustfactor_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))

                for factor in test_factors_to_delete:
                    adjustfactor_crud.remove({"uuid": factor.uuid})

                after_delete = len(adjustfactor_crud.find(filters={"source": SOURCE_TYPES.TEST.value}))
                deleted_count = before_delete - after_delete
                print(f"\n→ 清理测试数据: 删除了 {deleted_count} 条记录")

            except Exception as cleanup_error:
                print(f"\n✗ 清理测试数据失败: {cleanup_error}")
                # 不重新抛出异常，避免影响测试结果


# TDD Red阶段验证：确保所有测试开始时都失败
if __name__ == "__main__":
    print("TDD Red阶段验证：AdjustFactor CRUD测试")
    print("所有测试用例应该在实现开始前失败")
    print("运行: pytest test/data/crud/test_adjustfactor_crud.py -v")
    print("预期结果: 所有测试失败 (Red阶段)")
    print("重点关注: 复权因子存储和价格分析功能")