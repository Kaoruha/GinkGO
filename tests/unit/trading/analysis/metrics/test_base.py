"""
性能: 272MB RSS, 2.33s, 33 tests [PASS]
Metric Protocol, DataProvider, MetricRegistry TDD测试

通过TDD方式开发分析模块基础抽象层的核心逻辑测试套件
聚焦于Metric协议、DataProvider数据容器、MetricRegistry注册中心
"""
import pytest
import pandas as pd
from typing import List, Dict, Any

from ginkgo.trading.analysis.metrics.base import DataProvider, MetricRegistry
from ginkgo.trading.analysis.metrics.base import Metric


# ============================================================
# 测试用的具体Metric实现
# ============================================================

class TotalReturnMetric:
    """模拟总收益指标 - 用于测试基础功能"""

    name: str = "total_return"
    requires: List[str] = ["daily_pnl"]
    params: Dict[str, Any] = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> Any:
        df = data["daily_pnl"]
        return df["pnl"].sum()


class SharpeMetric:
    """模拟夏普比率指标 - 用于测试带参数的指标"""

    def __init__(self, risk_free_rate: float = 0.03):
        self.name = "sharpe_ratio"
        self.requires = ["daily_returns"]
        self.params = {"risk_free_rate": risk_free_rate}
        self._risk_free_rate = risk_free_rate

    def compute(self, data: Dict[str, pd.DataFrame]) -> Any:
        df = data["daily_returns"]
        excess = df["return"] - self._risk_free_rate / 252
        return excess.mean() / excess.std() * (252 ** 0.5)


class MultiSourceMetric:
    """模拟多数据源指标 - 需要 bar 和 trade 两个数据源"""

    name: str = "avg_trade_size"
    requires: List[str] = ["bars", "trades"]
    params: Dict[str, Any] = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> Any:
        return len(data["trades"]) / max(len(data["bars"]), 1)


# ============================================================
# DataProvider 测试
# ============================================================

@pytest.mark.unit
class TestDataProvider:
    """DataProvider 数据容器测试"""

    def test_init_with_kwargs(self):
        """通过构造函数关键字参数传入数据"""
        df1 = pd.DataFrame({"a": [1, 2, 3]})
        dp = DataProvider(daily_pnl=df1)
        assert dp.get("daily_pnl") is df1

    def test_add_and_get(self):
        """通过add方法添加数据，get方法获取"""
        df = pd.DataFrame({"x": [10, 20]})
        dp = DataProvider()
        dp.add("bars", df)
        assert dp.get("bars") is df

    def test_get_missing_key_returns_none(self):
        """获取不存在的key返回None"""
        dp = DataProvider()
        assert dp.get("nonexistent") is None

    def test_available_property(self):
        """available返回所有已注册的key列表"""
        df1 = pd.DataFrame({"a": [1]})
        df2 = pd.DataFrame({"b": [2]})
        dp = DataProvider(foo=df1, bar=df2)
        dp.add("baz", pd.DataFrame())
        keys = dp.available
        assert set(keys) == {"foo", "bar", "baz"}

    def test_available_empty(self):
        """空的DataProvider返回空列表"""
        dp = DataProvider()
        assert dp.available == []


# ============================================================
# Metric Protocol 测试
# ============================================================

@pytest.mark.unit
class TestMetricProtocol:
    """Metric Protocol 运行时类型检查测试"""

    def test_concrete_metric_satisfies_protocol(self):
        """具体Metric类满足Protocol"""
        m = TotalReturnMetric()
        assert isinstance(m, Metric)

    def test_metric_with_params_satisfies_protocol(self):
        """带参数的Metric类满足Protocol"""
        m = SharpeMetric(risk_free_rate=0.02)
        assert isinstance(m, Metric)

    def test_compute_returns_result(self):
        """compute方法返回计算结果"""
        m = TotalReturnMetric()
        df = pd.DataFrame({"pnl": [100, -50, 200]})
        data = {"daily_pnl": df}
        result = m.compute(data)
        assert result == 250

    def test_compute_with_params(self):
        """带参数的指标compute使用正确参数"""
        m = SharpeMetric(risk_free_rate=0.03)
        df = pd.DataFrame({"return": [0.01, 0.02, -0.01, 0.03, 0.01]})
        data = {"daily_returns": df}
        result = m.compute(data)
        assert isinstance(result, float)

    def test_metric_requires(self):
        """指标声明所需的data key"""
        m = TotalReturnMetric()
        assert "daily_pnl" in m.requires

    def test_metric_name(self):
        """指标有name属性"""
        m = TotalReturnMetric()
        assert m.name == "total_return"

    def test_metric_params(self):
        """指标有params属性"""
        m = TotalReturnMetric()
        assert isinstance(m.params, dict)


# ============================================================
# MetricRegistry 测试
# ============================================================

@pytest.mark.unit
class TestMetricRegistry:
    """MetricRegistry 注册中心测试"""

    def test_register_and_get(self):
        """注册指标类并按名称获取"""
        registry = MetricRegistry()
        registry.register(TotalReturnMetric)
        cls = registry.get("total_return")
        assert cls is TotalReturnMetric

    def test_register_replaces_existing(self):
        """重复注册同名指标时替换旧的"""
        registry = MetricRegistry()
        registry.register(TotalReturnMetric)

        class AnotherReturn:
            name = "total_return"
            requires: List[str] = ["daily_pnl"]
            params: Dict[str, Any] = {}
            def compute(self, data): return 0

        registry.register(AnotherReturn)
        assert registry.get("total_return") is AnotherReturn

    def test_get_nonexistent_returns_none(self):
        """获取不存在的指标返回None"""
        registry = MetricRegistry()
        assert registry.get("nonexistent") is None

    def test_list_metrics(self):
        """列出所有已注册的指标名称"""
        registry = MetricRegistry()
        registry.register(TotalReturnMetric)
        registry.register(SharpeMetric)
        names = registry.list_metrics()
        assert "total_return" in names
        assert "sharpe_ratio" in names

    def test_list_metrics_empty(self):
        """空注册中心返回空列表"""
        registry = MetricRegistry()
        assert registry.list_metrics() == []

    def test_check_availability_all_available(self):
        """所有依赖数据都可用"""
        registry = MetricRegistry()
        registry.register(TotalReturnMetric)
        dp = DataProvider(daily_pnl=pd.DataFrame())
        available, missing = registry.check_availability(dp)
        assert "total_return" in available
        assert len(missing) == 0

    def test_check_availability_partial(self):
        """部分数据缺失"""
        registry = MetricRegistry()
        registry.register(TotalReturnMetric)
        registry.register(MultiSourceMetric)
        dp = DataProvider(daily_pnl=pd.DataFrame())
        available, missing = registry.check_availability(dp)
        assert "total_return" in available
        assert "avg_trade_size" in missing

    def test_check_availability_all_missing(self):
        """所有数据都缺失"""
        registry = MetricRegistry()
        registry.register(MultiSourceMetric)
        dp = DataProvider()
        available, missing = registry.check_availability(dp)
        assert len(available) == 0
        assert "avg_trade_size" in missing

    def test_instantiate_default_params(self):
        """使用默认参数实例化指标"""
        registry = MetricRegistry()
        registry.register(TotalReturnMetric)
        instance = registry.instantiate("total_return")
        assert isinstance(instance, TotalReturnMetric)
        assert instance.name == "total_return"

    def test_instantiate_with_params_override(self):
        """使用参数覆盖实例化指标"""
        registry = MetricRegistry()
        registry.register(SharpeMetric)
        instance = registry.instantiate("sharpe_ratio", risk_free_rate=0.05)
        assert isinstance(instance, SharpeMetric)
        assert instance.params["risk_free_rate"] == 0.05

    def test_instantiate_nonexistent_raises(self):
        """实例化不存在的指标抛出KeyError"""
        registry = MetricRegistry()
        with pytest.raises(KeyError):
            registry.instantiate("nonexistent")

    def test_check_availability_with_dict(self):
        """check_availability也支持直接传入dict"""
        registry = MetricRegistry()
        registry.register(TotalReturnMetric)
        data = {"daily_pnl": pd.DataFrame()}
        available, missing = registry.check_availability(data)
        assert "total_return" in available


# ============================================================
# MetricRegistry 实例级别注册测试 (Step 1 扩展)
# ============================================================

class ParametricMetric:
    """模拟参数化指标 — name 在 __init__ 中动态设置"""

    def __init__(self, base: str, window: int = 10):
        self.name = f"{base}.w{window}"
        self.requires = [base]
        self.params = {"base": base, "window": window}

    def compute(self, data):
        return data[self.requires[0]]["value"].rolling(self.params["window"]).mean()


@pytest.mark.unit
class TestMetricRegistryInstances:
    """MetricRegistry 实例级别注册 (register_instance / get_instance) 测试"""

    def test_register_instance_and_get(self):
        """注册实例并通过 get_instance 获取"""
        registry = MetricRegistry()
        m = ParametricMetric(base="sharpe", window=20)
        registry.register_instance(m)
        retrieved = registry.get_instance("sharpe.w20")
        assert retrieved is m
        assert retrieved.name == "sharpe.w20"

    def test_get_instance_nonexistent_returns_none(self):
        """获取不存在的实例返回 None"""
        registry = MetricRegistry()
        assert registry.get_instance("nonexistent") is None

    def test_register_instance_replaces_existing(self):
        """同名实例注册时覆盖旧的"""
        registry = MetricRegistry()
        m1 = ParametricMetric(base="sharpe", window=10)
        m2 = ParametricMetric(base="sharpe", window=20)
        # m1 和 m2 的 name 相同
        m2.name = m1.name  # 强制同名
        registry.register_instance(m1)
        registry.register_instance(m2)
        assert registry.get_instance(m1.name) is m2

    def test_register_instance_requires_name_attribute(self):
        """注册没有 name 属性的实例抛出 AttributeError"""
        registry = MetricRegistry()
        bad = type("Bad", (), {"requires": []})()
        with pytest.raises(AttributeError, match="must have a 'name' attribute"):
            registry.register_instance(bad)

    def test_list_metrics_includes_instances(self):
        """list_metrics 同时返回类级别和实例级别的名称"""
        registry = MetricRegistry()
        registry.register(TotalReturnMetric)
        m = ParametricMetric(base="sharpe", window=10)
        registry.register_instance(m)
        names = registry.list_metrics()
        assert "total_return" in names
        assert "sharpe.w10" in names

    def test_list_metrics_empty_instances(self):
        """没有实例注册时 list_metrics 仍返回类级别名称"""
        registry = MetricRegistry()
        registry.register(TotalReturnMetric)
        names = registry.list_metrics()
        assert "total_return" in names

    def test_check_availability_includes_instances(self):
        """check_availability 同时检查实例级别注册的指标"""
        registry = MetricRegistry()
        m = ParametricMetric(base="sharpe", window=10)
        registry.register_instance(m)
        # 数据包含 "sharpe" → 实例可用
        dp = DataProvider(sharpe=pd.DataFrame({"value": [1.0, 2.0, 3.0]}))
        available, missing = registry.check_availability(dp)
        assert "sharpe.w10" in available

    def test_check_availability_instance_missing_data(self):
        """实例依赖数据缺失时出现在 missing 列表"""
        registry = MetricRegistry()
        m = ParametricMetric(base="sharpe", window=10)
        registry.register_instance(m)
        dp = DataProvider()
        available, missing = registry.check_availability(dp)
        assert "sharpe.w10" in missing

    def test_check_availability_mixed_class_and_instance(self):
        """类级别和实例级别指标混合检查可用性"""
        registry = MetricRegistry()
        registry.register(TotalReturnMetric)
        m = ParametricMetric(base="sharpe", window=10)
        registry.register_instance(m)
        # 只提供 daily_pnl → TotalReturnMetric 可用, ParametricMetric 缺失
        dp = DataProvider(daily_pnl=pd.DataFrame())
        available, missing = registry.check_availability(dp)
        assert "total_return" in available
        assert "sharpe.w10" in missing
