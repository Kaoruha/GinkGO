# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: 机器学习因子模块公共接口，导出AlphaFactors因子、FeatureProcessor特征处理器等ML特征工程组件






"""
特征工程模块

提供金融数据的特征工程能力，包括：
- 技术指标计算
- 时序特征构建
- 标准化和归一化
- 特征选择
- Alpha因子集成
"""

from ginkgo.quant_ml.features.feature_processor import FeatureProcessor
from ginkgo.quant_ml.features.alpha_factors import AlphaFactors

__all__ = [
    "FeatureProcessor",
    "AlphaFactors"
]