# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: QuantML机器学习模块提供机器学习模型训练/预测和评估功能支持量化交易策略开发支持交易系统功能支持相关功能






"""
Ginkgo机器学习模块

提供量化投资所需的机器学习能力，包括：
- 传统机器学习模型（LightGBM, XGBoost, Random Forest等）
- 深度学习模型
- 特征工程和数据预处理
- ML策略集成
- 模型管理和服务
"""

from ginkgo.quant_ml.containers import ml_container

__all__ = ["ml_container"]