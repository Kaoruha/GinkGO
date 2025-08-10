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