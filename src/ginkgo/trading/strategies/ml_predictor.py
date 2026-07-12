# Upstream: PortfolioBase, ComponentLoader
# Downstream: StrategyMLBase, BaseModel, FeatureProcessor, AlphaFactors, Signal, DIRECTION_TYPES
# Role: ML预测策略，基于已训练机器学习模型预测股价收益率并生成交易信号






"""
ML预测策略示例

基于机器学习模型的股价预测策略，展示如何使用StrategyMLBase
构建具体的ML交易策略。
"""

import datetime
import pandas as pd
from typing import List, Dict, Optional

from ginkgo.trading.strategies.ml_strategy_base import StrategyMLBase
from ginkgo.entities import Signal
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs import GLOG


class StrategyMLPredictor(StrategyMLBase):
    """
    ML预测策略
    
    基于已训练的机器学习模型预测股价未来收益率，
    根据预测结果生成买卖信号的具体策略实现。
    """
    
    __abstract__ = False

    def __init__(
        self,
        name: str = "MLPredictor",
        model_path: Optional[str] = None,
        prediction_horizon: int = 5,  # 预测天数
        confidence_threshold: float = 0.7,  # 置信度阈值
        return_threshold: float = 0.02,  # 收益率阈值
        *args,
        **kwargs,
    ):
        """
        初始化ML预测策略

        Args:
            name: 策略名称
            model_path: ML模型文件路径
            prediction_horizon: 预测时间窗口（天）
            confidence_threshold: 最小置信度阈值
            return_threshold: 预测收益率阈值
        """
        # 设置特征工程配置
        feature_config = kwargs.pop('feature_config', {
            'processor': {
                'scaling_method': 'standard',
                'imputation_method': 'mean',
                'feature_selection': True,
                'n_features': 50
            },
            'factors': {
                'use_talib': True
            },
            'min_confidence': confidence_threshold
        })
        
        super().__init__(
            name=name,
            model_path=model_path,
            signal_threshold=return_threshold,
            feature_config=feature_config,
            *args,
            **kwargs,
        )
        
        # 如果ML模块不可用，策略仍可创建但功能受限
        if not hasattr(self, '_model') or self._model is None:
            GLOG.WARN("ML模块不可用，预测策略将以受限模式运行")
            # 设置默认值
            self._prediction_horizon = prediction_horizon
            self._confidence_threshold = confidence_threshold
            self._return_threshold = return_threshold
            return

        self._prediction_horizon = prediction_horizon
        self._confidence_threshold = confidence_threshold
        self._return_threshold = return_threshold
        
        GLOG.INFO(f"初始化ML预测策略: {name}")
        GLOG.INFO(f"参数 - 预测期:{prediction_horizon}天, 置信度阈值:{confidence_threshold}, 收益率阈值:{return_threshold}")

    def generate_signals_from_prediction(self, portfolio_info, code: str, 
                                       prediction_result: Dict) -> List[Signal]:
        """
        从预测结果生成交易信号（重写父类方法以实现特定逻辑）
        
        Args:
            portfolio_info: 投资组合信息
            code: 股票代码
            prediction_result: 预测结果
            
        Returns:
            List[Signal]: 生成的信号列表
        """
        try:
            signals = []
            
            prediction = prediction_result['prediction']
            confidence = prediction_result['confidence']
            
            GLOG.DEBUG(f"处理预测结果: {code}, 预测:{prediction:.4f}, 置信度:{confidence:.3f}")

            # 置信度检查
            if confidence < self._confidence_threshold:
                GLOG.DEBUG(f"置信度不足: {code}, {confidence:.3f} < {self._confidence_threshold}")
                return signals
            
            # 预测收益率阈值检查
            if abs(prediction) < self._return_threshold:
                GLOG.DEBUG(f"预测收益率不足: {code}, {abs(prediction):.4f} < {self._return_threshold}")
                return signals
            
            # 检查当前持仓状态
            positions = portfolio_info.get("positions", {})
            has_position = code in positions
            
            # 生成交易信号
            if prediction > self._return_threshold and not has_position:
                # 看涨信号 - 买入
                reason = (f"ML_LONG_pred:{prediction:.4f}_conf:{confidence:.3f}_"
                         f"horizon:{self._prediction_horizon}d")
                
                signal = self._create_signal(
                    portfolio_info, code, DIRECTION_TYPES.LONG, reason
                )

                signals.append(signal)

            elif prediction < -self._return_threshold and has_position:
                # 看跌信号 - 卖出
                reason = (f"ML_SHORT_pred:{prediction:.4f}_conf:{confidence:.3f}_"
                         f"horizon:{self._prediction_horizon}d")

                signal = self._create_signal(
                    portfolio_info, code, DIRECTION_TYPES.SHORT, reason
                )

                signals.append(signal)

            elif prediction < -self._return_threshold and not has_position:
                # 纯做空信号（如果策略支持做空）
                if self._is_short_selling_allowed():
                    reason = (f"ML_SHORT_pred:{prediction:.4f}_conf:{confidence:.3f}_"
                             f"horizon:{self._prediction_horizon}d")

                    signal = self._create_signal(
                        portfolio_info, code, DIRECTION_TYPES.SHORT, reason
                    )

                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            GLOG.ERROR(f"ML预测信号生成失败: {code}, {e}")
            return []

    def _is_short_selling_allowed(self) -> bool:
        """检查是否允许做空（可以根据策略配置或市场规则决定）"""
        # 这里可以根据实际需求实现
        return False  # 默认不允许做空

    def get_strategy_summary(self) -> Dict[str, any]:
        """获取策略摘要（扩展父类方法）"""
        base_summary = super().get_strategy_summary()
        
        # 添加预测策略特定信息
        base_summary.update({
            'prediction_horizon': self._prediction_horizon,
            'confidence_threshold': self._confidence_threshold,
            'return_threshold': self._return_threshold,
        })
        
        return base_summary

    def __str__(self) -> str:
        model_name = self._model_info.get('name', 'No Model') if self._model_info else 'No Model'
        return (f"MLPredictor(name={self.name}, model={model_name}, "
                f"horizon={self._prediction_horizon}d, threshold={self._return_threshold})")
