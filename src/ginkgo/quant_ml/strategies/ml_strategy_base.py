"""
机器学习策略基类

提供ML策略的统一框架，集成模型训练、预测和信号生成。
继承自ginkgo的BaseStrategy，支持事件驱动和矩阵模式。
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Union, Any, Tuple
from datetime import datetime, timedelta
from abc import abstractmethod

from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.bar import Bar
from ginkgo.core.interfaces.model_interface import IModel
from ginkgo.enums import DIRECTION_TYPES, STRATEGY_TYPES
from ginkgo.libs import GLOG
from ginkgo.quant_ml.features import FeatureProcessor, AlphaFactors


class MLBaseStrategy(BaseStrategy):
    """
    机器学习策略基类
    
    功能：
    - 集成ML模型和特征工程
    - 支持在线训练和预测
    - 自动特征更新和信号生成
    - 风险控制和头寸管理
    """
    
    def __init__(self, 
                 name: str = "MLStrategy",
                 model: Optional[IModel] = None,
                 feature_processor: Optional[FeatureProcessor] = None,
                 lookback_period: int = 252,
                 retrain_frequency: int = 60,
                 signal_threshold: float = 0.01,
                 **kwargs):
        """
        初始化ML策略
        
        Args:
            name: 策略名称
            model: 机器学习模型
            feature_processor: 特征处理器
            lookback_period: 训练数据回看期
            retrain_frequency: 重新训练频率（天）
            signal_threshold: 信号生成阈值
            **kwargs: 其他策略参数
        """
        super().__init__(name, **kwargs)
        
        self.model = model
        self.feature_processor = feature_processor or FeatureProcessor()
        self.alpha_factors = AlphaFactors()
        
        # 训练参数
        self.lookback_period = lookback_period
        self.retrain_frequency = retrain_frequency
        self.signal_threshold = signal_threshold
        
        # 策略状态
        self.last_train_date = None
        self.feature_data = pd.DataFrame()
        self.predictions = pd.DataFrame()
        
        # 性能跟踪
        self.prediction_accuracy = []
        self.signal_performance = []
        
        self.strategy_type = STRATEGY_TYPES.ML
        
        GLOG.INFO(f"初始化ML策略: {name}, 回看期: {lookback_period}天, 重训频率: {retrain_frequency}天")
    
    def cal(self, portfolio_info: Any = None, event: Any = None) -> List[Signal]:
        """
        策略主计算方法（事件驱动模式）
        
        Args:
            portfolio_info: 投资组合信息
            event: 市场事件
            
        Returns:
            List[Signal]: 生成的交易信号
        """
        try:
            signals = []
            
            if event is None or not hasattr(event, 'data'):
                return signals
            
            current_bar = event.data
            if not isinstance(current_bar, Bar):
                return signals
            
            current_date = current_bar.timestamp.date()
            
            # 更新特征数据
            self._update_feature_data(current_bar)
            
            # 检查是否需要重新训练
            if self._should_retrain(current_date):
                self._retrain_model()
                self.last_train_date = current_date
            
            # 生成预测和信号
            if self.model and self.model.is_trained:
                prediction = self._generate_prediction(current_bar)
                if prediction is not None:
                    signal = self._generate_signal_from_prediction(
                        current_bar, prediction, portfolio_info
                    )
                    if signal:
                        signals.append(signal)
            
            return signals
            
        except Exception as e:
            GLOG.ERROR(f"ML策略计算失败: {e}")
            return []
    
    def _update_feature_data(self, bar: Bar) -> None:
        """更新特征数据"""
        try:
            # 将Bar对象转换为DataFrame行
            bar_data = {
                'timestamp': bar.timestamp,
                'open': bar.open,
                'high': bar.high,
                'low': bar.low,
                'close': bar.close,
                'volume': bar.volume,
                'code': bar.code
            }
            
            # 添加到特征数据
            new_row = pd.DataFrame([bar_data])
            
            if self.feature_data.empty:
                self.feature_data = new_row
            else:
                self.feature_data = pd.concat([self.feature_data, new_row], ignore_index=True)
            
            # 保持数据长度
            max_length = self.lookback_period + 100  # 额外缓冲
            if len(self.feature_data) > max_length:
                self.feature_data = self.feature_data.tail(max_length).reset_index(drop=True)
            
            # 计算技术因子
            if len(self.feature_data) >= 20:  # 最少需要20个数据点
                self.feature_data = self.alpha_factors.calculate_all_factors(self.feature_data)
                
        except Exception as e:
            GLOG.ERROR(f"特征数据更新失败: {e}")
    
    def _should_retrain(self, current_date: datetime.date) -> bool:
        """判断是否需要重新训练模型"""
        if self.last_train_date is None:
            return True
        
        if self.model is None or not self.model.is_trained:
            return True
        
        days_since_training = (current_date - self.last_train_date).days
        return days_since_training >= self.retrain_frequency
    
    def _retrain_model(self) -> None:
        """重新训练模型"""
        try:
            if len(self.feature_data) < self.lookback_period:
                GLOG.WARN(f"训练数据不足: {len(self.feature_data)} < {self.lookback_period}")
                return
            
            GLOG.INFO("开始重新训练ML模型")
            
            # 准备训练数据
            train_data = self.feature_data.tail(self.lookback_period).copy()
            features, targets = self._prepare_training_data(train_data)
            
            if features.empty or targets.empty:
                GLOG.WARN("训练数据准备失败")
                return
            
            # 特征处理
            features_processed = self.feature_processor.fit_transform(features, targets)
            
            # 训练模型
            if self.model:
                self.model.fit(features_processed, targets)
                GLOG.INFO(f"模型训练完成，特征数: {features_processed.shape[1]}")
                
                # 记录训练性能
                if hasattr(self.model, 'get_training_info'):
                    train_info = self.model.get_training_info()
                    GLOG.INFO(f"训练信息: {train_info}")
            
        except Exception as e:
            GLOG.ERROR(f"模型重训失败: {e}")
    
    def _generate_prediction(self, bar: Bar) -> Optional[float]:
        """生成预测结果"""
        try:
            if len(self.feature_data) < 50:  # 需要足够的历史数据
                return None
            
            # 获取最新特征
            latest_features = self._get_latest_features()
            if latest_features is None or latest_features.empty:
                return None
            
            # 特征预处理
            features_processed = self.feature_processor.transform(latest_features)
            
            # 模型预测
            prediction = self.model.predict(features_processed)
            
            if isinstance(prediction, pd.DataFrame):
                pred_value = prediction.iloc[0, 0]
            else:
                pred_value = float(prediction[0])
            
            # 记录预测结果
            self.predictions = pd.concat([
                self.predictions,
                pd.DataFrame({
                    'timestamp': [bar.timestamp],
                    'prediction': [pred_value],
                    'actual_price': [bar.close]
                })
            ], ignore_index=True).tail(1000)  # 保持预测历史
            
            return pred_value
            
        except Exception as e:
            GLOG.ERROR(f"预测生成失败: {e}")
            return None
    
    def _get_latest_features(self) -> Optional[pd.DataFrame]:
        """获取最新的特征数据"""
        if self.feature_data.empty:
            return None
        
        try:
            # 获取最新一行数据的特征
            latest_data = self.feature_data.tail(1).copy()
            
            # 排除非特征列
            exclude_cols = ['timestamp', 'code']
            feature_cols = [col for col in latest_data.columns if col not in exclude_cols]
            
            features = latest_data[feature_cols]
            
            # 删除包含NaN的列
            features = features.dropna(axis=1)
            
            return features
            
        except Exception as e:
            GLOG.ERROR(f"获取最新特征失败: {e}")
            return None
    
    @abstractmethod
    def _prepare_training_data(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        准备训练数据（子类实现）
        
        Args:
            data: 历史数据
            
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: (特征数据, 目标变量)
        """
        pass
    
    @abstractmethod
    def _generate_signal_from_prediction(self, bar: Bar, prediction: float, portfolio_info: Any) -> Optional[Signal]:
        """
        从预测结果生成交易信号（子类实现）
        
        Args:
            bar: 当前bar数据
            prediction: 模型预测结果
            portfolio_info: 投资组合信息
            
        Returns:
            Optional[Signal]: 生成的交易信号
        """
        pass
    
    def get_strategy_metrics(self) -> Dict[str, Any]:
        """获取策略指标"""
        metrics = {
            'model_trained': self.model.is_trained if self.model else False,
            'last_train_date': self.last_train_date,
            'feature_count': self.feature_data.shape[1] if not self.feature_data.empty else 0,
            'data_points': len(self.feature_data),
            'predictions_count': len(self.predictions)
        }
        
        # 计算预测准确性
        if len(self.predictions) > 10:
            try:
                recent_predictions = self.predictions.tail(50)
                if 'actual_return' in recent_predictions.columns:
                    # 计算方向预测准确率
                    pred_direction = np.sign(recent_predictions['prediction'])
                    actual_direction = np.sign(recent_predictions['actual_return'])
                    accuracy = np.mean(pred_direction == actual_direction)
                    metrics['direction_accuracy'] = accuracy
                    
                    # 计算信息系数(IC)
                    ic = recent_predictions['prediction'].corr(recent_predictions['actual_return'])
                    metrics['information_coefficient'] = ic
            except Exception as e:
                GLOG.WARN(f"计算预测准确性失败: {e}")
        
        return metrics
    
    def save_strategy_state(self, filepath: str) -> None:
        """保存策略状态"""
        try:
            state = {
                'strategy_name': self.name,
                'last_train_date': self.last_train_date,
                'feature_data': self.feature_data.to_dict(),
                'predictions': self.predictions.to_dict(),
                'parameters': {
                    'lookback_period': self.lookback_period,
                    'retrain_frequency': self.retrain_frequency,
                    'signal_threshold': self.signal_threshold
                }
            }
            
            import pickle
            with open(filepath, 'wb') as f:
                pickle.dump(state, f)
            
            # 保存模型
            if self.model:
                model_path = filepath.replace('.pkl', '_model.pkl')
                self.model.save(model_path)
            
            GLOG.INFO(f"策略状态已保存: {filepath}")
            
        except Exception as e:
            GLOG.ERROR(f"保存策略状态失败: {e}")
    
    def load_strategy_state(self, filepath: str) -> None:
        """加载策略状态"""
        try:
            import pickle
            with open(filepath, 'rb') as f:
                state = pickle.load(f)
            
            self.last_train_date = state['last_train_date']
            self.feature_data = pd.DataFrame.from_dict(state['feature_data'])
            self.predictions = pd.DataFrame.from_dict(state['predictions'])
            
            # 恢复参数
            params = state['parameters']
            self.lookback_period = params['lookback_period']
            self.retrain_frequency = params['retrain_frequency']
            self.signal_threshold = params['signal_threshold']
            
            # 加载模型
            if self.model:
                model_path = filepath.replace('.pkl', '_model.pkl')
                try:
                    self.model = self.model.__class__.load(model_path)
                except FileNotFoundError:
                    GLOG.WARN("模型文件未找到，将重新训练")
            
            GLOG.INFO(f"策略状态已加载: {filepath}")
            
        except Exception as e:
            GLOG.ERROR(f"加载策略状态失败: {e}")
    
    def __str__(self) -> str:
        return f"MLStrategy(name={self.name}, model={self.model.__class__.__name__ if self.model else None})"