# Upstream: ginkgo.research.layering
# Downstream: pytest
# Role: FactorLayering 单元测试

"""
FactorLayering 测试

TDD Green 阶段: 测试用例实现
"""

import pytest
from decimal import Decimal
import pandas as pd
import numpy as np


@pytest.fixture
def sample_factor_data():
    """创建示例因子数据"""
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=100, freq="D")
    codes = ["000001.SZ", "000002.SZ", "000003.SZ", "000004.SZ", "000005.SZ",
             "000006.SZ", "000007.SZ", "000008.SZ", "000009.SZ", "000010.SZ"]

    data = []
    for date in dates:
        for code in codes:
            data.append({
                "date": date.strftime("%Y%m%d"),
                "code": code,
                "factor_value": np.random.randn(),
            })

    return pd.DataFrame(data)


@pytest.fixture
def sample_return_data():
    """创建示例收益数据"""
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", periods=105, freq="D")
    codes = ["000001.SZ", "000002.SZ", "000003.SZ", "000004.SZ", "000005.SZ",
             "000006.SZ", "000007.SZ", "000008.SZ", "000009.SZ", "000010.SZ"]

    data = []
    for date in dates:
        for code in codes:
            data.append({
                "date": date.strftime("%Y%m%d"),
                "code": code,
                "return": np.random.randn() * 0.02,
            })

    return pd.DataFrame(data)


@pytest.mark.financial
class TestFactorLayering:
    """FactorLayering 单元测试"""

    def test_init(self, sample_factor_data, sample_return_data):
        """测试初始化"""
        from ginkgo.research.layering import FactorLayering

        layering = FactorLayering(sample_factor_data, sample_return_data)
        assert layering is not None
        assert layering.factor_data is not None

    def test_init_with_validation(self, sample_factor_data):
        """测试输入验证"""
        from ginkgo.research.layering import FactorLayering

        # 缺少必需列
        bad_data = pd.DataFrame({"date": [], "code": []})
        with pytest.raises(ValueError):
            FactorLayering(bad_data, sample_factor_data)

    def test_run_basic(self, sample_factor_data, sample_return_data):
        """测试基本分层运行"""
        from ginkgo.research.layering import FactorLayering
        from ginkgo.research.models import LayeringResult

        layering = FactorLayering(sample_factor_data, sample_return_data)
        result = layering.run(n_groups=5)

        assert isinstance(result, LayeringResult)
        assert result.n_groups == 5
        assert len(result.groups) == 5

    def test_run_group_returns(self, sample_factor_data, sample_return_data):
        """测试分组收益计算"""
        from ginkgo.research.layering import FactorLayering

        layering = FactorLayering(sample_factor_data, sample_return_data)
        result = layering.run(n_groups=5)

        # 每组应有收益数据
        for group_id, group in result.groups.items():
            assert group.count > 0 or group.mean_return is not None

    def test_long_short_return(self, sample_factor_data, sample_return_data):
        """测试多空收益计算"""
        from ginkgo.research.layering import FactorLayering

        layering = FactorLayering(sample_factor_data, sample_return_data)
        result = layering.run(n_groups=5)

        # 多空收益 = 最高组 - 最低组
        assert result.spread is not None

    def test_calculate_monotonicity(self, sample_factor_data, sample_return_data):
        """测试单调性计算"""
        from ginkgo.research.layering import FactorLayering

        layering = FactorLayering(sample_factor_data, sample_return_data)
        layering.run(n_groups=5)
        r2 = layering.calculate_monotonicity()

        # R² 应在 0-1 之间
        assert 0 <= r2 <= 1

    def test_different_group_numbers(self, sample_factor_data, sample_return_data):
        """测试不同分组数"""
        from ginkgo.research.layering import FactorLayering

        layering = FactorLayering(sample_factor_data, sample_return_data)

        for n_groups in [3, 5, 10]:
            result = layering.run(n_groups=n_groups)
            assert result.n_groups == n_groups
            assert len(result.groups) == n_groups

    def test_get_group_statistics(self, sample_factor_data, sample_return_data):
        """测试获取组统计"""
        from ginkgo.research.layering import FactorLayering

        layering = FactorLayering(sample_factor_data, sample_return_data)
        result = layering.run(n_groups=5)

        stats = layering.get_group_statistics()
        assert "mean_returns" in stats
        assert len(stats["mean_returns"]) == 5


@pytest.mark.financial
class TestLayerGroup:
    """LayerGroup 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.research.models import LayerGroup

        group = LayerGroup(
            group_id=1,
            name="Q1",
            mean_return=Decimal("0.02"),
            count=100,
        )

        assert group.group_id == 1
        assert group.name == "Q1"
        assert group.mean_return == Decimal("0.02")

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.research.models import LayerGroup

        group = LayerGroup(
            group_id=1,
            name="Q1",
            mean_return=Decimal("0.02"),
        )
        d = group.to_dict()

        assert d["group_id"] == 1
        assert d["name"] == "Q1"


@pytest.mark.financial
class TestLayeringResult:
    """LayeringResult 测试"""

    def test_init(self):
        """测试初始化"""
        from ginkgo.research.models import LayeringResult

        result = LayeringResult(
            factor_name="MOM_20",
            n_groups=5,
        )

        assert result.factor_name == "MOM_20"
        assert result.n_groups == 5

    def test_get_monotonicity(self):
        """测试单调性计算"""
        from ginkgo.research.models import LayeringResult, LayerGroup
        from decimal import Decimal

        # 创建单调递增的组收益
        result = LayeringResult(factor_name="test", n_groups=5)
        for i in range(5):
            result.groups[i + 1] = LayerGroup(
                group_id=i + 1,
                mean_return=Decimal(str(0.01 * i)),
            )

        mono = result.get_monotonicity()
        # 完全单调递增，单调性应为 1.0
        assert mono == Decimal("1.0")

    def test_to_dict(self):
        """测试序列化"""
        from ginkgo.research.models import LayeringResult

        result = LayeringResult(
            factor_name="MOM_20",
            n_groups=5,
            spread=Decimal("0.05"),
        )

        d = result.to_dict()
        assert d["factor_name"] == "MOM_20"
        assert d["n_groups"] == 5
        assert "spread" in d
