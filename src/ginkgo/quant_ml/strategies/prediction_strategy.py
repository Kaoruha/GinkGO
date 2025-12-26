"""
预测策略实现

基于机器学习模型预测股价未来收益率的具体策略实现。
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, timedelta

from ginkgo.quant_ml.strategies.ml_strategy_base import MLBaseStrategy
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.bar import Bar
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.libs import GLOG


class PredictionStrategy(MLBaseStrategy):
    """
    预测策略
    
    基于ML模型预测未来N期收益率，根据预测结果生成买卖信号。
    """
    
    def __init__(self, 
                 name: str = "PredictionStrategy",
                 prediction_horizon: int = 5,
                 min_prediction_confidence: float = 0.6,
                 position_sizing_method: str = "equal_weight",
                 max_position_size: float = 0.1,
                 **kwargs):
        """
        初始化预测策略
        
        Args:
            name: 策略名称
            prediction_horizon: 预测时间窗口（天）
            min_prediction_confidence: 最小预测置信度
            position_sizing_method: 头寸大小确定方法
            max_position_size: 最大头寸比例
            **kwargs: 其他参数传递给基类
        """
        super().__init__(name, **kwargs)
        
        self.prediction_horizon = prediction_horizon
        self.min_prediction_confidence = min_prediction_confidence
        self.position_sizing_method = position_sizing_method
        self.max_position_size = max_position_size
        
        GLOG.INFO(f"初始化预测策略: {name}, 预测期: {prediction_horizon}天")
    
    def _prepare_training_data(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        准备训练数据
        
        创建特征和目标变量，目标变量为未来N期收益率
        """
        try:
            if len(data) < self.prediction_horizon + 20:
                GLOG.WARN("数据长度不足以创建训练集")
                return pd.DataFrame(), pd.DataFrame()
            
            # 计算未来收益率作为目标变量
            data = data.copy()
            data['future_return'] = (
                data['close'].shift(-self.prediction_horizon) / data['close'] - 1
            )
            
            # 移除包含NaN的行
            valid_data = data.dropna()
            
            if len(valid_data) < 50:
                GLOG.WARN("有效训练数据不足")
                return pd.DataFrame(), pd.DataFrame()
            
            # 排除目标变量和非特征列
            exclude_cols = [
                'timestamp', 'code', 'future_return',
                'open', 'high', 'low', 'close', 'volume'  # 原始价格数据
            ]
            
            feature_cols = [col for col in valid_data.columns if col not in exclude_cols]
            
            # 特征数据
            features = valid_data[feature_cols].copy()
            
            # 目标变量
            targets = valid_data[['future_return']].copy()
            
            # 数据质量检查
            features = features.select_dtypes(include=[np.number])  # 只保留数值列
            features = features.replace([np.inf, -np.inf], np.nan)  # 替换无穷值
            features = features.dropna(axis=1, how='all')  # 删除全NaN的列
            
            # 确保特征和目标对齐
            common_idx = features.index.intersection(targets.index)
            features = features.loc[common_idx]
            targets = targets.loc[common_idx]
            
            GLOG.INFO(f"训练数据准备完成，特征数: {features.shape[1]}, 样本数: {len(features)}")
            
            return features, targets
            
        except Exception as e:
            GLOG.ERROR(f"训练数据准备失败: {e}")
            return pd.DataFrame(), pd.DataFrame()
    
    def _generate_signal_from_prediction(self, bar: Bar, prediction: float, portfolio_info: Any) -> Optional[Signal]:
        """
        从预测结果生成交易信号
        """
        try:
            # 预测置信度检查
            if abs(prediction) < self.signal_threshold:
                return None
            
            # 确定交易方向
            if prediction > self.signal_threshold:
                direction = DIRECTION_TYPES.LONG
                signal_strength = min(prediction, 1.0)
            elif prediction < -self.signal_threshold:
                direction = DIRECTION_TYPES.SHORT
                signal_strength = min(abs(prediction), 1.0)
            else:
                return None
            
            # 计算信号置信度
            confidence = self._calculate_signal_confidence(prediction, bar)
            
            if confidence < self.min_prediction_confidence:
                GLOG.DEBUG(f"信号置信度不足: {confidence:.3f}")
                return None
            
            # 计算头寸大小
            position_size = self._calculate_position_size(
                prediction, signal_strength, confidence, portfolio_info
            )
            
            if position_size <= 0:
                return None
            
            # 创建交易信号
            signal = Signal(
                code=bar.code,
                direction=direction,
                size=position_size,
                timestamp=bar.timestamp,
                price=bar.close
            )
            
            # 添加策略信息
            signal.strategy_name = self.name
            signal.prediction = prediction
            signal.confidence = confidence
            signal.signal_strength = signal_strength
            
            GLOG.DEBUG(f"生成信号: {bar.code}, 方向: {direction.name}, 大小: {position_size:.4f}, 预测: {prediction:.4f}")
            
            return signal
            
        except Exception as e:
            GLOG.ERROR(f"信号生成失败: {e}")
            return None
    
    def _calculate_signal_confidence(self, prediction: float, bar: Bar) -> float:
        """
        计算信号置信度
        
        基于多个因素计算信号的置信度：
        - 预测值的绝对大小
        - 历史预测准确性
        - 市场波动率
        """
        try:
            # 基础置信度基于预测值大小
            base_confidence = min(abs(prediction) * 2, 1.0)
            
            # 历史准确性调整
            if len(self.predictions) > 20:
                recent_predictions = self.predictions.tail(20)
                if 'actual_return' in recent_predictions.columns:
                    # 计算历史准确性
                    pred_direction = np.sign(recent_predictions['prediction'])
                    actual_direction = np.sign(recent_predictions['actual_return'])
                    accuracy = np.mean(pred_direction == actual_direction)
                    
                    # 根据准确性调整置信度
                    accuracy_multiplier = max(0.5, accuracy * 2)
                    base_confidence *= accuracy_multiplier
            
            # 市场波动率调整
            if len(self.feature_data) > 20:
                recent_returns = self.feature_data['close'].pct_change().tail(20)
                volatility = recent_returns.std()
                
                # 高波动时降低置信度
                vol_adjustment = max(0.7, 1 - volatility * 10)
                base_confidence *= vol_adjustment
            
            return np.clip(base_confidence, 0.0, 1.0)
            
        except Exception as e:
            GLOG.WARN(f"置信度计算失败: {e}")
            return 0.5  # 默认置信度
    
    def _calculate_position_size(self, 
                                prediction: float, 
                                signal_strength: float, 
                                confidence: float,
                                portfolio_info: Any) -> float:
        """
        计算头寸大小
        """
        try:
            if self.position_sizing_method == "equal_weight":
                # 等权重
                base_size = self.max_position_size
            elif self.position_sizing_method == "prediction_weighted":
                # 基于预测强度加权
                base_size = self.max_position_size * signal_strength
            elif self.position_sizing_method == "confidence_weighted":
                # 基于置信度加权
                base_size = self.max_position_size * confidence
            elif self.position_sizing_method == "combined":
                # 综合权重
                base_size = self.max_position_size * signal_strength * confidence
            else:
                base_size = self.max_position_size
            
            # 风险调整
            risk_multiplier = self._calculate_risk_multiplier(portfolio_info)
            adjusted_size = base_size * risk_multiplier
            
            return max(0.001, min(adjusted_size, self.max_position_size))
            
        except Exception as e:
            GLOG.WARN(f"头寸大小计算失败: {e}")
            return 0.01  # 默认小头寸
    
    def _calculate_risk_multiplier(self, portfolio_info: Any) -> float:
        """
        计算风险乘数
        
        根据当前投资组合状态调整头寸大小
        """
        try:
            # 如果没有投资组合信息，返回默认值
            if portfolio_info is None:
                return 1.0
            
            risk_multiplier = 1.0
            
            # 检查当前持仓集中度
            if hasattr(portfolio_info, 'positions'):
                total_positions = len(portfolio_info.positions)
                if total_positions > 20:  # 持仓过于分散
                    risk_multiplier *= 0.8
                elif total_positions < 5:  # 持仓过于集中
                    risk_multiplier *= 1.2
            
            # 检查当前收益状态
            if hasattr(portfolio_info, 'total_return'):
                if portfolio_info.total_return < -0.1:  # 亏损超过10%
                    risk_multiplier *= 0.7  # 降低风险
                elif portfolio_info.total_return > 0.2:  # 盈利超过20%
                    risk_multiplier *= 0.9  # 适当降低风险
            
            # 检查现金比例
            if hasattr(portfolio_info, 'cash_ratio'):
                if portfolio_info.cash_ratio < 0.05:  # 现金不足5%
                    risk_multiplier *= 0.5  # 大幅降低风险
            
            return np.clip(risk_multiplier, 0.1, 2.0)
            
        except Exception as e:
            GLOG.WARN(f"风险乘数计算失败: {e}")
            return 1.0
    
    def update_prediction_accuracy(self, actual_returns: pd.Series) -> None:
        """
        更新预测准确性
        
        Args:
            actual_returns: 实际收益率数据
        """
        try:
            if self.predictions.empty:
                return
            
            # 匹配预测和实际收益
            for idx, row in self.predictions.iterrows():
                timestamp = row['timestamp']
                prediction = row['prediction']
                
                # 查找对应的实际收益率
                if timestamp in actual_returns.index:
                    actual_return = actual_returns[timestamp]
                    self.predictions.loc[idx, 'actual_return'] = actual_return
                    
                    # 计算预测误差
                    error = abs(prediction - actual_return)
                    self.predictions.loc[idx, 'prediction_error'] = error
            
            # 更新策略性能指标
            self._update_performance_metrics()
            
        except Exception as e:
            GLOG.ERROR(f"预测准确性更新失败: {e}")
    
    def _update_performance_metrics(self) -> None:
        """更新策略性能指标"""
        try:
            if 'actual_return' not in self.predictions.columns:
                return
            
            valid_predictions = self.predictions.dropna(subset=['actual_return'])
            
            if len(valid_predictions) < 10:
                return
            
            # 方向预测准确率
            pred_direction = np.sign(valid_predictions['prediction'])
            actual_direction = np.sign(valid_predictions['actual_return'])
            direction_accuracy = np.mean(pred_direction == actual_direction)
            
            # 信息系数
            ic = valid_predictions['prediction'].corr(valid_predictions['actual_return'])
            
            # 平均绝对误差
            mae = valid_predictions['prediction_error'].mean()
            
            # 记录性能指标
            self.signal_performance.append({
                'timestamp': datetime.now(),
                'direction_accuracy': direction_accuracy,
                'information_coefficient': ic,
                'mean_absolute_error': mae,
                'prediction_count': len(valid_predictions)
            })
            
            # 保持性能历史长度
            if len(self.signal_performance) > 100:
                self.signal_performance = self.signal_performance[-100:]
            
            GLOG.INFO(f"策略性能更新 - 方向准确率: {direction_accuracy:.3f}, IC: {ic:.3f}, MAE: {mae:.4f}")
            
        except Exception as e:
            GLOG.WARN(f"性能指标更新失败: {e}")
    
    def get_strategy_summary(self) -> Dict[str, Any]:
        """获取策略摘要"""
        base_metrics = self.get_strategy_metrics()
        
        strategy_specific = {
            'prediction_horizon': self.prediction_horizon,
            'min_prediction_confidence': self.min_prediction_confidence,
            'position_sizing_method': self.position_sizing_method,
            'max_position_size': self.max_position_size
        }
        
        # 添加最近性能指标
        if self.signal_performance:
            latest_performance = self.signal_performance[-1]
            strategy_specific.update({
                'latest_direction_accuracy': latest_performance['direction_accuracy'],
                'latest_information_coefficient': latest_performance['information_coefficient'],
                'latest_mean_absolute_error': latest_performance['mean_absolute_error']
            })
        
        base_metrics.update(strategy_specific)
        return base_metrics