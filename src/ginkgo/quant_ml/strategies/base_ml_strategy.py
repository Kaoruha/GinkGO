"""
ML策略基类

实现IMLStrategy接口，为所有ML策略提供统一的基础功能。
"""

from typing import Dict, Any, List, Optional, Union
import pandas as pd
import numpy as np
from datetime import datetime

from ginkgo.core.interfaces.strategy_interface import IMLStrategy
from ginkgo.core.interfaces.model_interface import IModel
from ginkgo.backtest.entities.signal import Signal
from ginkgo.enums import STRATEGY_TYPES, DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import GLOG


class BaseMLStrategy(IMLStrategy):
    """ML策略基类"""
    
    def __init__(self, name: str = "BaseMLStrategy", model: IModel = None):
        super().__init__(name)
        self._model = model
        self._supports_vectorization = True
        
        # 特征相关
        self._feature_config = {}
        self._feature_cache = {}
        
        # 信号相关
        self._signal_threshold = 0.5  # 信号阈值
        self._signal_config = {}
        
        # 性能追踪
        self._prediction_history = []
        self._signal_history = []
        
    @property
    def model(self) -> Optional[IModel]:
        """获取ML模型"""
        return self._model
    
    def set_model(self, model: IModel) -> None:
        """设置ML模型"""
        self._model = model
        self._is_trained = model.is_trained if model else False
        
        # 同步特征信息
        if model and hasattr(model, 'feature_names'):
            self._feature_columns = model.feature_names
    
    def initialize(self, **kwargs) -> None:
        """初始化策略"""
        # 设置特征配置
        self._feature_config = kwargs.get('feature_config', {})
        
        # 设置信号配置
        self._signal_config = kwargs.get('signal_config', {})
        self._signal_threshold = self._signal_config.get('threshold', 0.5)
        
        # 初始化模型
        if self._model and hasattr(self._model, 'initialize'):
            self._model.initialize(**kwargs.get('model_config', {}))
    
    def train(self, training_data: pd.DataFrame, **kwargs) -> None:
        """训练ML模型"""
        if not self._model:
            raise ValueError("必须先设置ML模型")
        
        try:
            GLOG.INFO(f"开始训练ML策略 {self.name}")
            
            # 准备训练数据
            features, targets = self._prepare_training_data(training_data, **kwargs)
            
            # 训练模型
            self._model.fit(features, targets, **kwargs)
            self._is_trained = True
            
            # 记录训练信息
            self._record_training_info(features, targets)
            
            GLOG.INFO(f"ML策略 {self.name} 训练完成")
            
        except Exception as e:
            GLOG.ERROR(f"ML策略 {self.name} 训练失败: {e}")
            raise
    
    def _prepare_training_data(self, data: pd.DataFrame, **kwargs) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        准备训练数据
        
        Args:
            data: 原始数据
            **kwargs: 额外参数
            
        Returns:
            tuple: (features, targets)
        """
        # 准备特征
        features = self.prepare_features_from_raw_data(data)
        
        # 准备目标变量
        targets = self._prepare_targets(data, **kwargs)
        
        # 对齐数据
        common_index = features.index.intersection(targets.index)
        features = features.loc[common_index]
        targets = targets.loc[common_index]
        
        return features, targets
    
    def _prepare_targets(self, data: pd.DataFrame, **kwargs) -> pd.DataFrame:
        """
        准备目标变量 - 子类可重写
        
        Args:
            data: 原始数据
            **kwargs: 额外参数
            
        Returns:
            pd.DataFrame: 目标变量
        """
        # 默认使用未来收益率作为目标
        target_horizon = kwargs.get('target_horizon', 1)
        
        if 'close' in data.columns:
            close = data['close']
            future_returns = close.pct_change(target_horizon).shift(-target_horizon)
            return pd.DataFrame({'target': future_returns}, index=data.index)
        else:
            raise ValueError("数据中必须包含'close'列")
    
    def _record_training_info(self, features: pd.DataFrame, targets: pd.DataFrame) -> None:
        """记录训练信息"""
        self._parameters['training_info'] = {
            'features_shape': features.shape,
            'targets_shape': targets.shape,
            'feature_columns': list(features.columns),
            'training_period': f"{features.index[0]} to {features.index[-1]}",
            'training_samples': len(features),
        }
    
    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """模型预测"""
        if not self._model:
            raise ValueError("模型未设置")
        
        if not self._is_trained:
            raise ValueError("模型未训练")
        
        try:
            predictions = self._model.predict(features)
            
            # 记录预测历史
            self._prediction_history.append({
                'timestamp': datetime.now(),
                'features_shape': features.shape,
                'predictions_shape': predictions.shape if hasattr(predictions, 'shape') else len(predictions)
            })
            
            return predictions
            
        except Exception as e:
            GLOG.ERROR(f"ML策略 {self.name} 预测失败: {e}")
            raise
    
    def cal(self, *args, **kwargs) -> List[Signal]:
        """事件驱动模式信号计算"""
        try:
            # 获取当前市场数据
            market_data = kwargs.get('market_data') or self._get_current_market_data(*args, **kwargs)
            
            if not market_data:
                return []
            
            # 准备特征
            features = self._prepare_features_for_prediction(market_data)
            
            if features.empty:
                return []
            
            # 模型预测
            predictions = self.predict(features)
            
            # 转换为信号
            signals = self._convert_predictions_to_signals(predictions, market_data)
            
            # 记录信号历史
            self._record_signals(signals)
            
            return signals
            
        except Exception as e:
            GLOG.ERROR(f"ML策略 {self.name} 信号计算失败: {e}")
            return []
    
    def cal_vectorized(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """矩阵模式向量化计算"""
        try:
            # 准备特征矩阵
            features = self.prepare_features(data)
            
            if features.empty:
                return pd.DataFrame()
            
            # 模型预测
            predictions = self.predict(features)
            
            # 转换为信号矩阵
            signal_matrix = self._convert_predictions_to_matrix(predictions, data)
            
            return signal_matrix
            
        except Exception as e:
            GLOG.ERROR(f"ML策略 {self.name} 向量化计算失败: {e}")
            return pd.DataFrame()
    
    def prepare_features(self, market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        准备模型特征
        
        Args:
            market_data: 市场数据字典
            
        Returns:
            pd.DataFrame: 特征数据
        """
        try:
            # 基础价格特征
            features = self._extract_price_features(market_data)
            
            # 技术指标特征
            technical_features = self._extract_technical_features(market_data)
            if not technical_features.empty:
                features = pd.concat([features, technical_features], axis=1)
            
            # 自定义特征
            custom_features = self._extract_custom_features(market_data)
            if not custom_features.empty:
                features = pd.concat([features, custom_features], axis=1)
            
            # 特征后处理
            features = self._postprocess_features(features)
            
            return features
            
        except Exception as e:
            GLOG.ERROR(f"特征准备失败: {e}")
            return pd.DataFrame()
    
    def prepare_features_from_raw_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """
        从原始数据准备特征（用于训练）
        
        Args:
            raw_data: 原始数据DataFrame
            
        Returns:
            pd.DataFrame: 特征数据
        """
        # 将原始数据转换为市场数据格式
        market_data = self._raw_data_to_market_data(raw_data)
        
        # 使用标准特征提取流程
        return self.prepare_features(market_data)
    
    def _raw_data_to_market_data(self, raw_data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """将原始数据转换为市场数据格式"""
        market_data = {}
        
        # 假设原始数据包含OHLCV列
        price_columns = ['open', 'high', 'low', 'close', 'volume']
        
        for col in price_columns:
            if col in raw_data.columns:
                market_data[col] = raw_data[[col]]
        
        return market_data
    
    def _extract_price_features(self, market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """提取价格特征"""
        features = []
        
        if 'close' in market_data:
            close = market_data['close']
            
            # 收益率特征
            returns = close.pct_change()
            features.append(returns.add_suffix('_return'))
            
            # 对数收益率
            log_returns = np.log(close / close.shift(1))
            features.append(log_returns.add_suffix('_log_return'))
            
            # 价格动量
            momentum_5 = close / close.shift(5) - 1
            momentum_20 = close / close.shift(20) - 1
            features.extend([momentum_5.add_suffix('_mom5'), momentum_20.add_suffix('_mom20')])
        
        if features:
            return pd.concat(features, axis=1).fillna(0)
        else:
            return pd.DataFrame()
    
    def _extract_technical_features(self, market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """提取技术指标特征"""
        features = []
        
        if 'close' in market_data:
            close = market_data['close']
            
            # 移动平均线
            ma5 = close.rolling(5).mean()
            ma20 = close.rolling(20).mean()
            ma_ratio = ma5 / ma20 - 1
            features.append(ma_ratio.add_suffix('_ma_ratio'))
            
            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            features.append(rsi.add_suffix('_rsi'))
            
            # 布林带
            bb_middle = close.rolling(20).mean()
            bb_std = close.rolling(20).std()
            bb_upper = bb_middle + 2 * bb_std
            bb_lower = bb_middle - 2 * bb_std
            bb_position = (close - bb_lower) / (bb_upper - bb_lower)
            features.append(bb_position.add_suffix('_bb_pos'))
        
        if 'volume' in market_data:
            volume = market_data['volume']
            
            # 成交量变化率
            volume_change = volume.pct_change()
            features.append(volume_change.add_suffix('_vol_change'))
            
            # 成交量移动平均比率
            vol_ma = volume.rolling(20).mean()
            vol_ratio = volume / vol_ma
            features.append(vol_ratio.add_suffix('_vol_ratio'))
        
        if features:
            return pd.concat(features, axis=1).fillna(0)
        else:
            return pd.DataFrame()
    
    def _extract_custom_features(self, market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """提取自定义特征 - 子类可重写"""
        return pd.DataFrame()
    
    def _postprocess_features(self, features: pd.DataFrame) -> pd.DataFrame:
        """特征后处理"""
        # 处理无穷大和NaN值
        features = features.replace([np.inf, -np.inf], np.nan).fillna(0)
        
        # 特征标准化（如果配置中启用）
        if self._feature_config.get('normalize', False):
            numeric_columns = features.select_dtypes(include=[np.number]).columns
            features[numeric_columns] = (features[numeric_columns] - features[numeric_columns].mean()) / features[numeric_columns].std()
        
        return features
    
    def _get_current_market_data(self, *args, **kwargs) -> Optional[Dict[str, Any]]:
        """获取当前市场数据 - 子类可重写"""
        # 从参数中提取市场数据
        if args and isinstance(args[0], dict):
            return args[0]
        
        return None
    
    def _prepare_features_for_prediction(self, market_data: Dict[str, Any]) -> pd.DataFrame:
        """为预测准备特征"""
        # 将单个时刻的数据转换为DataFrame格式
        data_dict = {}
        for key, value in market_data.items():
            if isinstance(value, (int, float)):
                data_dict[key] = pd.DataFrame([value], index=[datetime.now()])
            elif hasattr(value, 'to_frame'):
                data_dict[key] = value.to_frame().T
        
        # 使用标准特征提取流程
        return self.prepare_features(data_dict)
    
    def _convert_predictions_to_signals(self, predictions: pd.DataFrame, market_data: Dict[str, Any]) -> List[Signal]:
        """将预测结果转换为信号列表"""
        signals = []
        
        # 简单的阈值转换
        for i, (index, pred_row) in enumerate(predictions.iterrows()):
            pred_value = pred_row.iloc[0] if len(pred_row) > 0 else 0
            
            if abs(pred_value) > self._signal_threshold:
                direction = DIRECTION_TYPES.LONG if pred_value > 0 else DIRECTION_TYPES.SHORT
                
                # 从市场数据中获取股票代码
                code = market_data.get('code', 'UNKNOWN')
                
                try:
                    signal = Signal(
                        portfolio_id="",
                        engine_id="",
                        timestamp=index if hasattr(index, 'date') else datetime.now(),
                        code=str(code),
                        direction=direction,
                        reason=f"ML prediction: {pred_value:.4f}",
                        source=SOURCE_TYPES.STRATEGY
                    )
                    signals.append(signal)
                except Exception as e:
                    GLOG.DEBUG(f"创建信号失败: {e}")
                    continue
        
        return signals
    
    def _convert_predictions_to_matrix(self, predictions: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """将预测结果转换为信号矩阵"""
        if 'close' in data:
            index = data['close'].index
            columns = data['close'].columns
        else:
            return pd.DataFrame()
        
        # 创建信号矩阵
        signal_matrix = pd.DataFrame(0.0, index=index, columns=columns)
        
        # 应用阈值转换
        if not predictions.empty:
            # 确保predictions的索引和列与信号矩阵匹配
            aligned_predictions = predictions.reindex_like(signal_matrix).fillna(0)
            
            # 应用阈值
            signal_matrix = np.where(
                np.abs(aligned_predictions) > self._signal_threshold,
                np.sign(aligned_predictions),
                0
            )
            
            signal_matrix = pd.DataFrame(signal_matrix, index=index, columns=columns)
        
        return signal_matrix
    
    def _record_signals(self, signals: List[Signal]) -> None:
        """记录信号历史"""
        if signals:
            self._signal_history.append({
                'timestamp': datetime.now(),
                'signal_count': len(signals),
                'signal_summary': {
                    'long_signals': sum(1 for s in signals if s.direction == DIRECTION_TYPES.LONG),
                    'short_signals': sum(1 for s in signals if s.direction == DIRECTION_TYPES.SHORT),
                }
            })
    
    def get_prediction_history(self) -> List[Dict[str, Any]]:
        """获取预测历史"""
        return self._prediction_history
    
    def get_signal_history(self) -> List[Dict[str, Any]]:
        """获取信号历史"""
        return self._signal_history
    
    def set_parameters(self, **parameters) -> None:
        """设置策略参数"""
        super().set_parameters(**parameters)
        
        # 更新信号阈值
        if 'signal_threshold' in parameters:
            self._signal_threshold = parameters['signal_threshold']
        
        # 更新特征配置
        if 'feature_config' in parameters:
            self._feature_config.update(parameters['feature_config'])
        
        # 更新信号配置
        if 'signal_config' in parameters:
            self._signal_config.update(parameters['signal_config'])
    
    def get_strategy_summary(self) -> Dict[str, Any]:
        """获取策略摘要"""
        summary = {
            'name': self.name,
            'strategy_type': self.strategy_type.value if hasattr(self.strategy_type, 'value') else str(self.strategy_type),
            'is_trained': self._is_trained,
            'model_info': self._model.get_metadata() if self._model else None,
            'feature_count': len(self._feature_columns),
            'signal_threshold': self._signal_threshold,
            'prediction_history_count': len(self._prediction_history),
            'signal_history_count': len(self._signal_history),
            'parameters': self._parameters,
        }
        
        return summary
    
    def __str__(self) -> str:
        model_name = self._model.name if self._model else "None"
        return f"{self.__class__.__name__}(name={self.name}, model={model_name}, trained={self._is_trained})"
    
    def __repr__(self) -> str:
        return self.__str__()