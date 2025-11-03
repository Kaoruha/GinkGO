"""
策略统一接口定义

定义所有策略（传统策略、ML策略）必须实现的统一接口，
支持事件驱动和矩阵两种回测模式。
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import pandas as pd
from datetime import datetime

from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import STRATEGY_TYPES, DIRECTION_TYPES


class IStrategy(ABC):
    """策略统一接口"""
    
    def __init__(self, name: str = "UnknownStrategy"):
        self.name = name
        self._strategy_type = STRATEGY_TYPES.UNKNOWN
        self._parameters = {}
        self._is_trained = False
        self._supports_vectorization = False
        
    @property
    def strategy_type(self) -> STRATEGY_TYPES:
        """策略类型"""
        return self._strategy_type
    
    @property
    def parameters(self) -> Dict[str, Any]:
        """策略参数"""
        return self._parameters
    
    @property
    def is_trained(self) -> bool:
        """是否已训练（主要用于ML策略）"""
        return self._is_trained
    
    @property 
    def supports_vectorization(self) -> bool:
        """是否支持向量化计算"""
        return self._supports_vectorization
    
    @abstractmethod
    def initialize(self, **kwargs) -> None:
        """
        策略初始化
        
        Args:
            **kwargs: 初始化参数
        """
        pass
    
    @abstractmethod
    def cal(self, *args, **kwargs) -> List[Signal]:
        """
        事件驱动模式信号计算
        
        Returns:
            List[Signal]: 生成的信号列表
        """
        pass
    
    def cal_vectorized(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        矩阵模式向量化信号计算（可选实现）
        
        Args:
            data: 市场数据字典 {'close': DataFrame, 'volume': DataFrame, ...}
            
        Returns:
            pd.DataFrame: 信号矩阵，index为时间，columns为股票代码，values为信号强度
        """
        if not self.supports_vectorization:
            raise NotImplementedError(f"策略 {self.name} 不支持向量化计算")
        
        # 默认实现：逐行调用cal方法
        return self._default_vectorization(data)
    
    def _default_vectorization(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """默认向量化实现：逐行处理"""
        if 'close' not in data:
            raise ValueError("数据中必须包含'close'价格信息")
            
        close_data = data['close']
        signals_matrix = pd.DataFrame(0.0, index=close_data.index, columns=close_data.columns)
        
        # 这里需要子类实现具体的逐行处理逻辑
        # 由于cal()方法通常需要当前市场状态，这里只是框架
        return signals_matrix
    
    @abstractmethod
    def set_parameters(self, **parameters) -> None:
        """
        设置策略参数
        
        Args:
            **parameters: 策略参数
        """
        pass
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """获取单个参数"""
        return self._parameters.get(key, default)
    
    def validate_parameters(self) -> bool:
        """验证参数有效性"""
        return True
    
    def get_required_data_columns(self) -> List[str]:
        """
        获取策略所需的数据列
        
        Returns:
            List[str]: 所需数据列名列表，如['close', 'volume', 'high', 'low']
        """
        return ['close']  # 默认只需要收盘价
    
    def get_warmup_period(self) -> int:
        """
        获取策略预热期长度
        
        Returns:
            int: 预热期天数
        """
        return 0
    
    def on_market_update(self, market_data: Dict[str, Any]) -> None:
        """
        市场数据更新回调（可选实现）
        
        Args:
            market_data: 最新市场数据
        """
        pass
    
    def on_signal_generated(self, signals: List[Signal]) -> None:
        """
        信号生成后回调（可选实现）
        
        Args:
            signals: 生成的信号列表
        """
        pass
    
    def reset(self) -> None:
        """重置策略状态"""
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, type={self.strategy_type})"
    
    def __repr__(self) -> str:
        return self.__str__()


class IMLStrategy(IStrategy):
    """机器学习策略接口（继承自统一策略接口）"""
    
    def __init__(self, name: str = "MLStrategy"):
        super().__init__(name)
        self._strategy_type = STRATEGY_TYPES.ML
        self._model = None
        self._feature_columns = []
        
    @property
    def model(self):
        """获取底层ML模型"""
        return self._model
    
    @property
    def feature_columns(self) -> List[str]:
        """获取特征列"""
        return self._feature_columns
    
    @abstractmethod
    def train(self, training_data: pd.DataFrame, **kwargs) -> None:
        """
        训练ML模型
        
        Args:
            training_data: 训练数据
            **kwargs: 训练参数
        """
        pass
    
    @abstractmethod
    def predict(self, features: pd.DataFrame) -> pd.DataFrame:
        """
        模型预测
        
        Args:
            features: 特征数据
            
        Returns:
            pd.DataFrame: 预测结果
        """
        pass
    
    def prepare_features(self, market_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        准备模型特征
        
        Args:
            market_data: 市场数据
            
        Returns:
            pd.DataFrame: 特征数据
        """
        # 默认实现：直接使用价格数据作为特征
        if 'close' in market_data:
            return market_data['close']
        else:
            raise ValueError("无法从市场数据中准备特征")
    
    def save_model(self, filepath: str) -> None:
        """保存模型"""
        pass
    
    def load_model(self, filepath: str) -> None:
        """加载模型"""
        pass