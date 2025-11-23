"""
策略适配器

提供传统策略和ML策略的统一适配能力，确保不同类型的策略可以在相同的框架下运行。
"""

from typing import Dict, Any, List, Type, Optional, Union
import pandas as pd
import numpy as np

from ginkgo.core.adapters.base_adapter import BaseAdapter, AdapterError
from ginkgo.core.interfaces.strategy_interface import IStrategy, IMLStrategy
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import STRATEGY_TYPES, DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import GLOG


class StrategyAdapter(BaseAdapter):
    """策略适配器"""
    
    def __init__(self, name: str = "StrategyAdapter"):
        super().__init__(name)
        self._adaptation_registry = {}
        
    def can_adapt(self, source: Any, target_type: Type = None) -> bool:
        """检查是否可以适配"""
        # 检查源对象类型
        if not (isinstance(source, BaseStrategy) or isinstance(source, IStrategy)):
            return False
        
        # 检查目标类型
        if target_type:
            return issubclass(target_type, IStrategy)
        
        return True
    
    def adapt(self, source: Any, target_type: Type = None, **kwargs) -> IStrategy:
        """
        策略适配主方法
        
        Args:
            source: 源策略对象
            target_type: 目标策略接口类型
            **kwargs: 适配参数
            
        Returns:
            IStrategy: 适配后的策略对象
        """
        if not self.can_adapt(source, target_type):
            raise AdapterError(f"无法适配策略: {type(source).__name__}")
        
        try:
            # 如果源对象已经实现了目标接口，直接返回
            if target_type and isinstance(source, target_type):
                return source
            
            # 根据源策略类型选择适配方法
            if isinstance(source, BaseStrategy):
                return self._adapt_base_strategy(source, target_type, **kwargs)
            elif hasattr(source, 'strategy_type') and source.strategy_type == STRATEGY_TYPES.ML:
                return self._adapt_ml_strategy(source, target_type, **kwargs)
            else:
                return self._adapt_generic_strategy(source, target_type, **kwargs)
                
        except Exception as e:
            raise AdapterError(f"策略适配失败: {e}")
    
    def _adapt_base_strategy(self, strategy: BaseStrategy, target_type: Type = None, **kwargs) -> IStrategy:
        """
        适配传统BaseStrategy策略
        
        Args:
            strategy: 传统策略对象
            target_type: 目标类型
            **kwargs: 适配参数
            
        Returns:
            IStrategy: 适配后的策略
        """
        return BaseStrategyAdapter(strategy, **kwargs)
    
    def _adapt_ml_strategy(self, strategy: Any, target_type: Type = None, **kwargs) -> IStrategy:
        """
        适配ML策略
        
        Args:
            strategy: ML策略对象
            target_type: 目标类型
            **kwargs: 适配参数
            
        Returns:
            IStrategy: 适配后的策略
        """
        return MLStrategyAdapter(strategy, **kwargs)
    
    def _adapt_generic_strategy(self, strategy: Any, target_type: Type = None, **kwargs) -> IStrategy:
        """
        适配通用策略
        
        Args:
            strategy: 通用策略对象
            target_type: 目标类型
            **kwargs: 适配参数
            
        Returns:
            IStrategy: 适配后的策略
        """
        return GenericStrategyAdapter(strategy, **kwargs)
    
    def register_adaptation(self, source_type: Type, target_type: Type, adapter_func) -> None:
        """
        注册自定义适配函数
        
        Args:
            source_type: 源类型
            target_type: 目标类型
            adapter_func: 适配函数
        """
        key = (source_type, target_type)
        self._adaptation_registry[key] = adapter_func
    
    def get_registered_adaptations(self) -> Dict[str, Any]:
        """获取已注册的适配"""
        return {
            f"{src.__name__}->{tgt.__name__}": func.__name__ 
            for (src, tgt), func in self._adaptation_registry.items()
        }


class BaseStrategyAdapter(IStrategy):
    """传统策略适配器"""
    
    def __init__(self, base_strategy: BaseStrategy, **kwargs):
        super().__init__(name=getattr(base_strategy, 'name', 'AdaptedBaseStrategy'))
        self.base_strategy = base_strategy
        self._strategy_type = STRATEGY_TYPES.TRADITIONAL
        self._supports_vectorization = kwargs.get('supports_vectorization', False)
        
        # 复制基础策略的参数
        if hasattr(base_strategy, '_parameters'):
            self._parameters = base_strategy._parameters.copy()
        
    def initialize(self, **kwargs) -> None:
        """初始化策略"""
        if hasattr(self.base_strategy, 'initialize'):
            self.base_strategy.initialize(**kwargs)
        elif hasattr(self.base_strategy, '__init__'):
            # 如果没有initialize方法，尝试重新初始化
            try:
                self.base_strategy.__init__(**kwargs)
            except Exception as e:
                GLOG.WARNING(f"策略初始化失败: {e}")
    
    def cal(self, *args, **kwargs) -> List[Signal]:
        """事件驱动模式信号计算"""
        try:
            # 调用原始策略的cal方法
            if hasattr(self.base_strategy, 'cal'):
                result = self.base_strategy.cal(*args, **kwargs)
                
                # 确保返回Signal列表
                if isinstance(result, list):
                    return result
                elif result is None:
                    return []
                else:
                    # 尝试转换单个结果
                    return [result] if hasattr(result, 'code') else []
            else:
                GLOG.WARNING(f"策略 {self.name} 没有cal方法")
                return []
                
        except Exception as e:
            GLOG.ERROR(f"策略 {self.name} 计算失败: {e}")
            return []
    
    def cal_vectorized(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """矩阵模式向量化计算"""
        if self._supports_vectorization and hasattr(self.base_strategy, 'cal_vectorized'):
            return self.base_strategy.cal_vectorized(data)
        else:
            # 使用默认的逐行处理
            return self._default_vectorization(data)
    
    def set_parameters(self, **parameters) -> None:
        """设置策略参数"""
        self._parameters.update(parameters)
        
        # 如果原始策略有参数设置方法，调用它
        if hasattr(self.base_strategy, 'set_parameters'):
            self.base_strategy.set_parameters(**parameters)
        else:
            # 尝试直接设置属性
            for key, value in parameters.items():
                if hasattr(self.base_strategy, key):
                    setattr(self.base_strategy, key, value)
    
    def get_required_data_columns(self) -> List[str]:
        """获取所需数据列"""
        if hasattr(self.base_strategy, 'get_required_data_columns'):
            return self.base_strategy.get_required_data_columns()
        else:
            # 默认数据列
            return ['close', 'volume', 'high', 'low', 'open']
    
    def get_warmup_period(self) -> int:
        """获取预热期"""
        if hasattr(self.base_strategy, 'get_warmup_period'):
            return self.base_strategy.get_warmup_period()
        else:
            # 根据策略类型推断预热期
            return self._infer_warmup_period()
    
    def _infer_warmup_period(self) -> int:
        """推断预热期长度"""
        # 检查策略中是否有移动窗口参数
        common_window_params = ['window', 'period', 'lookback', 'ma_period', 'n_days']
        
        for param_name in common_window_params:
            if hasattr(self.base_strategy, param_name):
                param_value = getattr(self.base_strategy, param_name)
                if isinstance(param_value, int) and param_value > 0:
                    return param_value
        
        # 默认预热期
        return 20
    
    def reset(self) -> None:
        """重置策略状态"""
        if hasattr(self.base_strategy, 'reset'):
            self.base_strategy.reset()
        
        # 重置适配器状态
        super().reset()
    
    def __getattr__(self, name):
        """代理属性访问到原始策略"""
        if hasattr(self.base_strategy, name):
            return getattr(self.base_strategy, name)
        raise AttributeError(f"'{self.__class__.__name__}' 和 '{type(self.base_strategy).__name__}' 都没有属性 '{name}'")


class MLStrategyAdapter(IMLStrategy):
    """ML策略适配器"""
    
    def __init__(self, ml_strategy: Any, **kwargs):
        super().__init__(name=getattr(ml_strategy, 'name', 'AdaptedMLStrategy'))
        self.ml_strategy = ml_strategy
        self._supports_vectorization = True  # ML策略通常支持向量化
        
        # 复制ML策略的模型和特征信息
        if hasattr(ml_strategy, 'model'):
            self._model = ml_strategy.model
        if hasattr(ml_strategy, 'feature_columns'):
            self._feature_columns = ml_strategy.feature_columns
        
    def initialize(self, **kwargs) -> None:
        """初始化ML策略"""
        if hasattr(self.ml_strategy, 'initialize'):
            self.ml_strategy.initialize(**kwargs)
    
    def cal(self, *args, **kwargs) -> List[Signal]:
        """事件驱动模式信号计算"""
        try:
            if hasattr(self.ml_strategy, 'cal'):
                return self.ml_strategy.cal(*args, **kwargs)
            elif hasattr(self.ml_strategy, 'predict'):
                # 如果只有predict方法，尝试转换
                return self._convert_prediction_to_signals(*args, **kwargs)
            else:
                GLOG.WARNING(f"ML策略 {self.name} 没有cal或predict方法")
                return []
        except Exception as e:
            GLOG.ERROR(f"ML策略 {self.name} 计算失败: {e}")
            return []
    
    def cal_vectorized(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """矩阵模式向量化计算"""
        try:
            if hasattr(self.ml_strategy, 'cal_vectorized'):
                return self.ml_strategy.cal_vectorized(data)
            elif hasattr(self.ml_strategy, 'predict'):
                # 准备特征数据
                features = self.prepare_features(data)
                predictions = self.ml_strategy.predict(features)
                
                # 转换预测结果为信号矩阵
                return self._convert_predictions_to_matrix(predictions, data)
            else:
                return super().cal_vectorized(data)
        except Exception as e:
            GLOG.ERROR(f"ML策略 {self.name} 向量化计算失败: {e}")
            return pd.DataFrame()
    
    def train(self, training_data: pd.DataFrame, **kwargs) -> None:
        """训练ML模型"""
        if hasattr(self.ml_strategy, 'train'):
            self.ml_strategy.train(training_data, **kwargs)
        elif hasattr(self.ml_strategy, 'fit'):
            self.ml_strategy.fit(training_data, **kwargs)
        else:
            raise NotImplementedError(f"ML策略 {self.name} 没有train或fit方法")
        
        self._is_trained = True
    
    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """模型预测"""
        if hasattr(self.ml_strategy, 'predict'):
            return self.ml_strategy.predict(features)
        else:
            raise NotImplementedError(f"ML策略 {self.name} 没有predict方法")
    
    def prepare_features(self, market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """准备特征数据"""
        if hasattr(self.ml_strategy, 'prepare_features'):
            return self.ml_strategy.prepare_features(market_data)
        else:
            # 默认特征准备：使用价格和技术指标
            return self._default_feature_preparation(market_data)
    
    def _default_feature_preparation(self, market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """默认特征准备"""
        features = []
        
        if 'close' in market_data:
            close = market_data['close']
            
            # 价格特征
            features.append(close.pct_change().fillna(0))  # 收益率
            features.append(close.rolling(5).mean() / close - 1)  # 5日均线偏离度
            features.append(close.rolling(20).std())  # 20日波动率
            
        if 'volume' in market_data:
            volume = market_data['volume']
            features.append(volume.pct_change().fillna(0))  # 成交量变化率
        
        if features:
            # 合并所有特征
            feature_df = pd.concat(features, axis=1, keys=range(len(features)))
            return feature_df.fillna(0)
        else:
            return pd.DataFrame()
    
    def _convert_prediction_to_signals(self, *args, **kwargs) -> List[Signal]:
        """将预测结果转换为信号列表"""
        # 这需要根据具体的预测结果格式实现
        return []
    
    def _convert_predictions_to_matrix(self, predictions: pd.DataFrame, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """将预测结果转换为信号矩阵"""
        if 'close' in data:
            index = data['close'].index
            columns = data['close'].columns
        else:
            return pd.DataFrame()
        
        # 创建信号矩阵
        signal_matrix = pd.DataFrame(0.0, index=index, columns=columns)
        
        # 根据预测结果填充信号矩阵
        if predictions is not None and not predictions.empty:
            # 简单转换：正预测为买入信号，负预测为卖出信号
            signal_matrix = signal_matrix.add(predictions.reindex_like(signal_matrix).fillna(0))
            
            # 规范化信号强度到[-1, 1]
            signal_matrix = np.clip(signal_matrix, -1, 1)
        
        return signal_matrix
    
    def set_parameters(self, **parameters) -> None:
        """设置参数"""
        self._parameters.update(parameters)
        
        if hasattr(self.ml_strategy, 'set_parameters'):
            self.ml_strategy.set_parameters(**parameters)
    
    def __getattr__(self, name):
        """代理属性访问"""
        if hasattr(self.ml_strategy, name):
            return getattr(self.ml_strategy, name)
        raise AttributeError(f"'{self.__class__.__name__}' 和 '{type(self.ml_strategy).__name__}' 都没有属性 '{name}'")


class GenericStrategyAdapter(IStrategy):
    """通用策略适配器"""
    
    def __init__(self, strategy: Any, **kwargs):
        super().__init__(name=getattr(strategy, 'name', 'AdaptedGenericStrategy'))
        self.wrapped_strategy = strategy
        self._strategy_type = STRATEGY_TYPES.UNKNOWN
        
    def initialize(self, **kwargs) -> None:
        """初始化策略"""
        if hasattr(self.wrapped_strategy, 'initialize'):
            self.wrapped_strategy.initialize(**kwargs)
    
    def cal(self, *args, **kwargs) -> List[Signal]:
        """事件驱动计算"""
        try:
            if hasattr(self.wrapped_strategy, 'cal'):
                result = self.wrapped_strategy.cal(*args, **kwargs)
                
                # 尝试转换结果为Signal列表
                if isinstance(result, list):
                    return result
                elif result is None:
                    return []
                else:
                    return [result] if hasattr(result, 'code') else []
            else:
                return []
        except Exception as e:
            GLOG.ERROR(f"通用策略 {self.name} 计算失败: {e}")
            return []
    
    def set_parameters(self, **parameters) -> None:
        """设置参数"""
        self._parameters.update(parameters)
        
        if hasattr(self.wrapped_strategy, 'set_parameters'):
            self.wrapped_strategy.set_parameters(**parameters)
        else:
            # 尝试直接设置属性
            for key, value in parameters.items():
                if hasattr(self.wrapped_strategy, key):
                    setattr(self.wrapped_strategy, key, value)
    
    def __getattr__(self, name):
        """代理属性访问"""
        if hasattr(self.wrapped_strategy, name):
            return getattr(self.wrapped_strategy, name)
        raise AttributeError(f"'{self.__class__.__name__}' 和 '{type(self.wrapped_strategy).__name__}' 都没有属性 '{name}'")