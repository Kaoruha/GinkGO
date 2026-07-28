# Upstream: FeatureContainer / 回测引擎装配
# Downstream: BaseStrategy.bind_factor_reader (trading 层注入)
# Role: 因子读取器 — 策略读取因子值的入口组件 (PIT 硬约束层, #6793)

from ginkgo.features.readers.pit_factor_reader import PITFactorReader

__all__ = ["PITFactorReader"]
