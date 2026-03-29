"""
策略接口单元测试

测试 IStrategy、IMLStrategy 接口定义，
验证构造、参数管理、向量化支持、回调机制等功能。
"""

import pytest
from unittest.mock import MagicMock

from ginkgo.core.interfaces.strategy_interface import IStrategy, IMLStrategy
from ginkgo.enums import STRATEGY_TYPES


# ── 具体实现用于测试抽象类 ──────────────────────────────────────────


class ConcreteStrategy(IStrategy):
    """IStrategy 的具体实现"""

    def initialize(self, **kwargs):
        self._initialized = True

    def cal(self, *args, **kwargs):
        return []

    def set_parameters(self, **parameters):
        self._parameters.update(parameters)


class ConcreteMLStrategy(IMLStrategy):
    """IMLStrategy 的具体实现"""

    def initialize(self, **kwargs):
        self._initialized = True

    def cal(self, *args, **kwargs):
        return []

    def set_parameters(self, **parameters):
        self._parameters.update(parameters)

    def train(self, training_data, **kwargs):
        self._is_trained = True

    def predict(self, features):
        import pandas as pd
        return pd.DataFrame({"prediction": [1.0]})


# ── IStrategy 构造测试 ──────────────────────────────────────────────


@pytest.mark.unit
class TestIStrategyConstruction:
    """IStrategy 构造测试"""

    def test_default_construction(self):
        """默认参数构造"""
        strategy = ConcreteStrategy()
        assert strategy.name == "UnknownStrategy"
        assert strategy.strategy_type == STRATEGY_TYPES.UNKNOWN
        assert strategy.parameters == {}
        assert strategy.is_trained is False
        assert strategy.supports_vectorization is False

    def test_custom_name(self):
        """自定义名称"""
        strategy = ConcreteStrategy()
        strategy.name = "MyStrategy"
        assert strategy.name == "MyStrategy"


# ── IStrategy 参数管理测试 ──────────────────────────────────────────


@pytest.mark.unit
class TestIStrategyParameters:
    """IStrategy 参数管理测试"""

    def test_set_parameters(self):
        """设置参数"""
        strategy = ConcreteStrategy()
        strategy.set_parameters(period=20, threshold=0.5)
        assert strategy.parameters["period"] == 20
        assert strategy.parameters["threshold"] == 0.5

    def test_get_parameter(self):
        """获取参数"""
        strategy = ConcreteStrategy()
        strategy.set_parameters(period=20)
        assert strategy.get_parameter("period") == 20

    def test_get_parameter_default(self):
        """获取不存在参数返回默认值"""
        strategy = ConcreteStrategy()
        assert strategy.get_parameter("nonexistent", 10) == 10

    def test_validate_parameters_default_true(self):
        """默认参数验证返回 True"""
        strategy = ConcreteStrategy()
        assert strategy.validate_parameters() is True


# ── IStrategy 向量化测试 ────────────────────────────────────────────


@pytest.mark.unit
class TestIStrategyVectorization:
    """IStrategy 向量化支持测试"""

    def test_cal_vectorized_not_supported_raises(self):
        """不支持向量化时调用抛出异常"""
        strategy = ConcreteStrategy()
        import pandas as pd
        data = {"close": pd.DataFrame({"A": [1, 2, 3]})}
        with pytest.raises(NotImplementedError, match="不支持向量化"):
            strategy.cal_vectorized(data)

    def test_get_required_data_columns(self):
        """获取所需数据列"""
        strategy = ConcreteStrategy()
        assert strategy.get_required_data_columns() == ["close"]

    def test_get_warmup_period(self):
        """获取预热期"""
        strategy = ConcreteStrategy()
        assert strategy.get_warmup_period() == 0


# ── IStrategy 回调和重置测试 ────────────────────────────────────────


@pytest.mark.unit
class TestIStrategyCallbacks:
    """IStrategy 回调和重置测试"""

    def test_on_market_update_default_noop(self):
        """市场更新回调默认无操作"""
        strategy = ConcreteStrategy()
        strategy.on_market_update({"close": 10.0})  # 不应抛出异常

    def test_on_signal_generated_default_noop(self):
        """信号生成回调默认无操作"""
        strategy = ConcreteStrategy()
        strategy.on_signal_generated([])  # 不应抛出异常

    def test_reset_default_noop(self):
        """重置默认无操作"""
        strategy = ConcreteStrategy()
        strategy.reset()  # 不应抛出异常

    def test_str_representation(self):
        """字符串表示"""
        strategy = ConcreteStrategy()
        s = str(strategy)
        assert "UnknownStrategy" in s

    def test_repr_equals_str(self):
        """repr 与 str 相同"""
        strategy = ConcreteStrategy()
        assert repr(strategy) == str(strategy)


# ── IMLStrategy 测试 ────────────────────────────────────────────────


@pytest.mark.unit
class TestIMLStrategy:
    """ML策略接口测试"""

    def test_default_type_is_ml(self):
        """默认策略类型为 ML"""
        strategy = ConcreteMLStrategy()
        assert strategy.strategy_type == STRATEGY_TYPES.ML

    def test_initial_model_none(self):
        """初始模型为 None"""
        strategy = ConcreteMLStrategy()
        assert strategy.model is None

    def test_initial_feature_columns_empty(self):
        """初始特征列为空"""
        strategy = ConcreteMLStrategy()
        assert strategy.feature_columns == []

    def test_train_sets_trained(self):
        """训练后标记为已训练"""
        import pandas as pd
        strategy = ConcreteMLStrategy()
        strategy.train(pd.DataFrame({"feature": [1, 2, 3]}))
        assert strategy.is_trained is True

    def test_predict_returns_result(self):
        """预测返回结果"""
        import pandas as pd
        strategy = ConcreteMLStrategy()
        strategy.train(pd.DataFrame({"feature": [1, 2, 3]}))
        result = strategy.predict(pd.DataFrame({"feature": [1]}))
        assert "prediction" in result.columns

    def test_prepare_features_with_close(self):
        """有收盘价时准备特征"""
        import pandas as pd
        strategy = ConcreteMLStrategy()
        data = {"close": pd.DataFrame({"A": [1, 2, 3]})}
        features = strategy.prepare_features(data)
        assert features.equals(data["close"])

    def test_prepare_features_without_close_raises(self):
        """无收盘价时抛出异常"""
        strategy = ConcreteMLStrategy()
        with pytest.raises(ValueError, match="无法从市场数据中准备特征"):
            strategy.prepare_features({"volume": "data"})

    def test_save_model_default_noop(self):
        """保存模型默认无操作"""
        strategy = ConcreteMLStrategy()
        strategy.save_model("/tmp/model.pkl")  # 不应抛出异常

    def test_load_model_default_noop(self):
        """加载模型默认无操作"""
        strategy = ConcreteMLStrategy()
        strategy.load_model("/tmp/model.pkl")  # 不应抛出异常

    def test_inherits_from_istrategy(self):
        """继承 IStrategy"""
        assert issubclass(IMLStrategy, IStrategy)

    def test_cannot_instantiate_abstract(self):
        """不能直接实例化抽象类"""
        with pytest.raises(TypeError):
            IStrategy()
