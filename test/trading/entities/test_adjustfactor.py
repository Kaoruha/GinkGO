"""
AdjustFactor类TDD测试

通过TDD方式开发AdjustFactor复权因子类的完整测试套件
涵盖复权因子计算和数据处理功能
"""
import pytest
import datetime

# 导入必要的类和模块
try:
    from ginkgo.trading.entities.adjustfactor import Adjustfactor
    from decimal import Decimal
    import pandas as pd
except ImportError as e:
    assert False, "TDD Red阶段：测试用例尚未实现"


@pytest.mark.unit
class TestAdjustFactorConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试默认构造函数 - 严格模式：要求核心参数"""
        # AdjustFactor与Position、Signal保持一致，要求核心业务参数不能为空
        with pytest.raises((ValueError, TypeError)):
            Adjustfactor()

    def test_full_parameter_constructor(self):
        """测试完整参数构造"""
        # 测试完整参数构造，所有字段正确赋值和严格类型检查
        adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=1.1234,
            back_adjustfactor=0.8901,
            adjustfactor=1.0567
        )

        # 验证字符串类型和值
        assert adjustfactor.code == "000001.SZ"
        assert isinstance(adjustfactor.code, str)

        # 验证时间戳类型和值
        assert adjustfactor.timestamp == datetime.datetime(2023, 1, 1)
        assert isinstance(adjustfactor.timestamp, datetime.datetime)

        # 验证Decimal类型和精度保持
        assert adjustfactor.fore_adjustfactor == Decimal("1.1234")
        assert isinstance(adjustfactor.fore_adjustfactor, Decimal)
        assert adjustfactor.back_adjustfactor == Decimal("0.8901")
        assert isinstance(adjustfactor.back_adjustfactor, Decimal)
        assert adjustfactor.adjustfactor == Decimal("1.0567")
        assert isinstance(adjustfactor.adjustfactor, Decimal)

    def test_base_class_inheritance(self):
        """测试Base类继承验证"""
        # 验证正确继承Base类的功能 - 使用有效参数创建实例
        from ginkgo.trading.core.base import Base

        adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=1.0,
            back_adjustfactor=1.0,
            adjustfactor=1.0
        )

        # 验证继承关系
        assert isinstance(adjustfactor, Base)

        # 验证Base类的基本功能（如UUID）
        assert hasattr(adjustfactor, 'uuid')
        assert hasattr(adjustfactor, 'component_type')
        assert len(adjustfactor.uuid) > 0

    def test_decimal_precision_handling(self):
        """测试复权因子精度处理"""
        # 验证复权因子数据使用Decimal精确处理，支持多种输入类型
        adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor="1.123456789",  # 高精度字符串
            back_adjustfactor=1.123456789,   # 浮点数
            adjustfactor=Decimal("1.987654321")  # 直接Decimal
        )

        # 验证所有复权因子属性都是Decimal类型
        assert isinstance(adjustfactor.fore_adjustfactor, Decimal)
        assert isinstance(adjustfactor.back_adjustfactor, Decimal)
        assert isinstance(adjustfactor.adjustfactor, Decimal)

        # 验证高精度字符串和直接Decimal的精度保持
        assert adjustfactor.fore_adjustfactor == Decimal("1.123456789")
        assert adjustfactor.adjustfactor == Decimal("1.987654321")

        # 验证浮点数转换为Decimal（可能有精度损失，但类型正确）
        assert isinstance(adjustfactor.back_adjustfactor, Decimal)

    def test_required_parameters_validation(self):
        """测试必需参数验证"""
        # 测试缺少code参数
        with pytest.raises((ValueError, TypeError)):
            Adjustfactor(
                timestamp="2023-01-01",
                fore_adjustfactor=1.0,
                back_adjustfactor=1.0,
                adjustfactor=1.0
            )

        # 测试缺少timestamp参数
        with pytest.raises((ValueError, TypeError)):
            Adjustfactor(
                code="000001.SZ",
                fore_adjustfactor=1.0,
                back_adjustfactor=1.0,
                adjustfactor=1.0
            )

        # 测试空字符串code
        with pytest.raises(ValueError):
            Adjustfactor(
                code="",
                timestamp="2023-01-01",
                fore_adjustfactor=1.0,
                back_adjustfactor=1.0,
                adjustfactor=1.0
            )

        # 测试无效时间戳
        with pytest.raises((ValueError, TypeError)):
            Adjustfactor(
                code="000001.SZ",
                timestamp="invalid_date",
                fore_adjustfactor=1.0,
                back_adjustfactor=1.0,
                adjustfactor=1.0
            )


@pytest.mark.unit
class TestAdjustFactorProperties:
    """2. 属性访问测试"""

    def test_code_property(self):
        """测试代码属性"""
        # 测试股票代码属性的正确读取 - 使用完整有效参数
        adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=1.0,
            back_adjustfactor=1.0,
            adjustfactor=1.0
        )

        assert adjustfactor.code == "000001.SZ"
        assert isinstance(adjustfactor.code, str)

        # 测试不同的股票代码格式
        adjustfactor2 = Adjustfactor(
            code="600000.SH",
            timestamp="2023-01-01",
            fore_adjustfactor=1.0,
            back_adjustfactor=1.0,
            adjustfactor=1.0
        )
        assert adjustfactor2.code == "600000.SH"

    def test_timestamp_property(self):
        """测试时间戳属性"""
        # 测试时间戳属性的正确读取和格式
        adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-12-25",
            fore_adjustfactor=0,
            back_adjustfactor=0,
            adjustfactor=0
        )

        assert adjustfactor.timestamp == datetime.datetime(2023, 12, 25)
        assert isinstance(adjustfactor.timestamp, datetime.datetime)

        # 测试默认时间戳
        default_adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="1990-01-01",
            fore_adjustfactor=0,
            back_adjustfactor=0,
            adjustfactor=0
        )
        assert default_adjustfactor.timestamp == datetime.datetime(1990, 1, 1)

    def test_fore_adjustfactor_property(self):
        """测试前复权因子属性"""
        # 测试fore_adjustfactor属性的正确读取和Decimal类型
        adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=1.2345,
            back_adjustfactor=0,
            adjustfactor=0
        )

        assert adjustfactor.fore_adjustfactor == Decimal("1.2345")
        assert isinstance(adjustfactor.fore_adjustfactor, Decimal)

        # 测试默认值
        default_adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=0,
            back_adjustfactor=0,
            adjustfactor=0
        )
        assert default_adjustfactor.fore_adjustfactor == Decimal("0")

    def test_back_adjustfactor_property(self):
        """测试后复权因子属性"""
        # 测试back_adjustfactor属性的正确读取和Decimal类型
        adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=0,
            back_adjustfactor=0.8765,
            adjustfactor=0
        )

        assert adjustfactor.back_adjustfactor == Decimal("0.8765")
        assert isinstance(adjustfactor.back_adjustfactor, Decimal)

        # 测试默认值
        default_adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=0,
            back_adjustfactor=0,
            adjustfactor=0
        )
        assert default_adjustfactor.back_adjustfactor == Decimal("0")

    def test_adjustfactor_property(self):
        """测试标准复权因子属性"""
        # 测试adjustfactor属性的正确读取和Decimal类型
        adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=0,
            back_adjustfactor=0,
            adjustfactor=1.5432
        )

        assert adjustfactor.adjustfactor == Decimal("1.5432")
        assert isinstance(adjustfactor.adjustfactor, Decimal)

        # 测试默认值
        default_adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=0,
            back_adjustfactor=0,
            adjustfactor=0
        )
        assert default_adjustfactor.adjustfactor == Decimal("0")


@pytest.mark.unit
class TestAdjustFactorDataSetting:
    """3. 数据设置测试"""

    def test_direct_parameter_setting(self):
        """测试直接参数设置"""
        # 测试直接参数方式设置复权因子数据
        adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=1.0,
            back_adjustfactor=1.0,
            adjustfactor=1.0
        )

        # 使用set方法更新数据
        adjustfactor.set(
            "000002.SZ",
            "2023-06-15",
            1.1111,
            0.9999,
            1.0555
        )

        assert adjustfactor.code == "000002.SZ"
        assert adjustfactor.timestamp == datetime.datetime(2023, 6, 15)
        assert adjustfactor.fore_adjustfactor == Decimal("1.1111")
        assert adjustfactor.back_adjustfactor == Decimal("0.9999")
        assert adjustfactor.adjustfactor == Decimal("1.0555")

    def test_pandas_series_setting(self):
        """测试pandas.Series设置"""
        # 测试从pandas.Series设置复权因子数据
        series_data = pd.Series({
            "code": "000003.SZ",
            "timestamp": "2023-09-30",
            "fore_adjustfactor": 1.2222,
            "back_adjustfactor": 0.7777,
            "adjustfactor": 1.1111
        })

        adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=1.0,
            back_adjustfactor=1.0,
            adjustfactor=1.0
        )
        adjustfactor.set(series_data)

        assert adjustfactor.code == "000003.SZ"
        assert adjustfactor.timestamp == datetime.datetime(2023, 9, 30)
        assert adjustfactor.fore_adjustfactor == Decimal("1.2222")
        assert adjustfactor.back_adjustfactor == Decimal("0.7777")
        assert adjustfactor.adjustfactor == Decimal("1.1111")

    def test_singledispatch_routing(self):
        """测试方法分派路由"""
        # 测试方法分派路由的正确性
        adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=1.0,
            back_adjustfactor=1.0,
            adjustfactor=1.0
        )

        # 测试不支持的类型会抛异常
        with pytest.raises(NotImplementedError):
            adjustfactor.set(["unsupported", "list", "type"])

        # 测试支持的类型能正确路由
        # 直接参数路由
        adjustfactor.set("000004.SZ", "2023-03-15", 1.5, 0.5, 1.0)
        assert adjustfactor.code == "000004.SZ"

        # pandas.Series路由
        series = pd.Series({
            "code": "000005.SZ",
            "timestamp": "2023-04-15",
            "fore_adjustfactor": 2.0,
            "back_adjustfactor": 0.5,
            "adjustfactor": 1.5
        })
        adjustfactor.set(series)
        assert adjustfactor.code == "000005.SZ"


@pytest.mark.unit
class TestAdjustFactorCalculation:
    """4. 复权因子计算测试"""

    def test_price_adjustment_calculation(self):
        """测试价格复权计算"""
        # 测试使用复权因子进行价格调整的计算
        adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=Decimal("1.2"),  # 前复权因子
            back_adjustfactor=Decimal("0.8"),  # 后复权因子
            adjustfactor=Decimal("1.1")       # 标准复权因子
        )

        # 测试前复权价格计算：原价 * 前复权因子
        original_price = Decimal("10.00")
        fore_adjusted_price = original_price * adjustfactor.fore_adjustfactor
        assert fore_adjusted_price == Decimal("12.00")

        # 测试后复权价格计算：原价 * 后复权因子
        back_adjusted_price = original_price * adjustfactor.back_adjustfactor
        assert back_adjusted_price == Decimal("8.00")

        # 测试标准复权价格计算：原价 * 复权因子
        standard_adjusted_price = original_price * adjustfactor.adjustfactor
        assert standard_adjusted_price == Decimal("11.00")

    def test_fore_back_adjustment_consistency(self):
        """测试前后复权一致性"""
        # 测试前复权和后复权因子的一致性关系
        adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=Decimal("1.25"),  # 前复权因子
            back_adjustfactor=Decimal("0.80"),  # 后复权因子
            adjustfactor=Decimal("1.00")       # 标准复权因子
        )

        # 理论上前复权因子和后复权因子应该满足：fore * back ≈ 1 (忽略精度误差)
        product = adjustfactor.fore_adjustfactor * adjustfactor.back_adjustfactor
        expected = Decimal("1.00")

        # 验证乘积接近1（允许小的精度误差）
        assert abs(product - expected) < Decimal("0.01")

        # 验证前复权和后复权因子都是正数
        assert adjustfactor.fore_adjustfactor > 0
        assert adjustfactor.back_adjustfactor > 0
        assert adjustfactor.adjustfactor >= 0

    def test_adjustment_factor_validation(self):
        """测试复权因子验证"""
        # 测试复权因子的合理性验证

        # 测试正常范围内的复权因子
        valid_adjustfactor = Adjustfactor(
            code="000001.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=Decimal("1.05"),  # 5%分红
            back_adjustfactor=Decimal("0.95"),  # 对应的后复权
            adjustfactor=Decimal("1.00")       # 标准复权
        )

        # 验证正常值都是Decimal类型且在合理范围内
        assert isinstance(valid_adjustfactor.fore_adjustfactor, Decimal)
        assert isinstance(valid_adjustfactor.back_adjustfactor, Decimal)
        assert isinstance(valid_adjustfactor.adjustfactor, Decimal)

        # 验证复权因子在合理范围内（通常在0.1到10之间）
        assert Decimal("0.1") <= valid_adjustfactor.fore_adjustfactor <= Decimal("10.0")
        assert Decimal("0.1") <= valid_adjustfactor.back_adjustfactor <= Decimal("10.0")
        assert Decimal("0.0") <= valid_adjustfactor.adjustfactor <= Decimal("10.0")

        # 测试边界值
        boundary_adjustfactor = Adjustfactor(
            code="000002.SZ",
            timestamp="2023-01-01",
            fore_adjustfactor=Decimal("0.1"),   # 极低值
            back_adjustfactor=Decimal("10.0"),  # 极高值
            adjustfactor=Decimal("0.0")        # 零值
        )

        assert boundary_adjustfactor.fore_adjustfactor == Decimal("0.1")
        assert boundary_adjustfactor.back_adjustfactor == Decimal("10.0")
        assert boundary_adjustfactor.adjustfactor == Decimal("0.0")
