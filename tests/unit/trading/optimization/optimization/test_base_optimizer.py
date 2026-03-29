# Upstream: ginkgo.trading.optimization.base_optimizer
# Downstream: pytest
# Role: BaseOptimizer 基类测试

"""
BaseOptimizer 基类测试

TDD Green 阶段: 测试用例实现
"""

import pytest
from abc import ABC
from typing import Dict, Any


@pytest.mark.unit
class TestBaseOptimizer:
    """BaseOptimizer 测试"""

    def test_is_abstract(self):
        """测试是否为抽象类"""
        from ginkgo.trading.optimization.base_optimizer import BaseOptimizer

        assert issubclass(BaseOptimizer, ABC)
        assert "optimize" in BaseOptimizer.__abstractmethods__

    def test_init_with_param_ranges(self):
        """测试带参数范围初始化"""
        from ginkgo.trading.optimization.base_optimizer import BaseOptimizer
        from ginkgo.trading.optimization.models import ParameterRange

        # 创建具体实现类用于测试
        class ConcreteOptimizer(BaseOptimizer):
            def optimize(self, data, **kwargs):
                return None

        param_ranges = [
            ParameterRange(name="fast", min_value=5, max_value=20, step=5),
            ParameterRange(name="slow", min_value=20, max_value=60, step=10),
        ]

        optimizer = ConcreteOptimizer(param_ranges=param_ranges)
        assert len(optimizer.param_ranges) == 2

    def test_validate_params_success(self):
        """测试参数验证成功"""
        from ginkgo.trading.optimization.base_optimizer import BaseOptimizer
        from ginkgo.trading.optimization.models import ParameterRange

        class ConcreteOptimizer(BaseOptimizer):
            def optimize(self, data, **kwargs):
                return None

        param_ranges = [
            ParameterRange(name="fast", min_value=5, max_value=20, step=1),
        ]

        optimizer = ConcreteOptimizer(param_ranges=param_ranges)
        params = {"fast": 10}

        # 验证参数在范围内
        assert optimizer.validate_params(params) is True

    def test_validate_params_failure(self):
        """测试参数验证失败"""
        from ginkgo.trading.optimization.base_optimizer import BaseOptimizer
        from ginkgo.trading.optimization.models import ParameterRange

        class ConcreteOptimizer(BaseOptimizer):
            def optimize(self, data, **kwargs):
                return None

        param_ranges = [
            ParameterRange(name="fast", min_value=5, max_value=20, step=1),
        ]

        optimizer = ConcreteOptimizer(param_ranges=param_ranges)
        params = {"fast": 100}  # 超出范围

        assert optimizer.validate_params(params) is False

    def test_generate_param_combinations(self):
        """测试生成参数组合"""
        from ginkgo.trading.optimization.base_optimizer import BaseOptimizer
        from ginkgo.trading.optimization.models import ParameterRange

        class ConcreteOptimizer(BaseOptimizer):
            def optimize(self, data, **kwargs):
                return None

        param_ranges = [
            ParameterRange(name="fast", min_value=5, max_value=10, step=5),
            ParameterRange(name="slow", min_value=20, max_value=30, step=10),
        ]

        optimizer = ConcreteOptimizer(param_ranges=param_ranges)
        combinations = optimizer.generate_param_combinations()

        # 2 * 2 = 4 种组合
        assert len(combinations) == 4
        assert {"fast": 5, "slow": 20} in combinations
        assert {"fast": 10, "slow": 30} in combinations

    def test_set_objective(self):
        """测试设置优化目标"""
        from ginkgo.trading.optimization.base_optimizer import BaseOptimizer

        class ConcreteOptimizer(BaseOptimizer):
            def optimize(self, data, **kwargs):
                return None

        optimizer = ConcreteOptimizer(param_ranges=[])
        optimizer.set_objective(metric="sharpe", maximize=True)

        assert optimizer.objective_metric == "sharpe"
        assert optimizer.maximize is True

    def test_get_param_space_size(self):
        """测试获取参数空间大小"""
        from ginkgo.trading.optimization.base_optimizer import BaseOptimizer
        from ginkgo.trading.optimization.models import ParameterRange

        class ConcreteOptimizer(BaseOptimizer):
            def optimize(self, data, **kwargs):
                return None

        param_ranges = [
            ParameterRange(name="fast", min_value=5, max_value=15, step=5),  # 3 values
            ParameterRange(name="slow", min_value=20, max_value=40, step=10),  # 3 values
        ]

        optimizer = ConcreteOptimizer(param_ranges=param_ranges)
        size = optimizer.get_param_space_size()

        assert size == 9  # 3 * 3
