"""
模式适配器

提供不同回测模式间的适配能力，支持策略在事件驱动和矩阵模式间无缝切换。
"""

from typing import Dict, Any, List, Type, Union
import pandas as pd
import numpy as np

from ginkgo.core.adapters.base_adapter import BaseAdapter, AdapterError
from ginkgo.core.interfaces.strategy_interface import IStrategy
from ginkgo.trading.entities.signal import Signal
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES
from ginkgo.libs import GLOG


class ModeAdapter(BaseAdapter):
    """回测模式适配器"""
    
    def __init__(self, name: str = "ModeAdapter"):
        super().__init__(name)
        self._conversion_cache = {}  # 转换结果缓存
        
    def can_adapt(self, source: Any, target_type: Type = None) -> bool:
        """检查是否可以适配"""
        # 检查是否为策略对象
        if not isinstance(source, IStrategy):
            return False
            
        # 检查目标模式
        if target_type and hasattr(target_type, '__name__'):
            target_name = target_type.__name__.lower()
            return 'event' in target_name or 'matrix' in target_name or 'vectorized' in target_name
        
        return True
    
    def adapt(self, source: Any, target_type: Type = None, **kwargs) -> Any:
        """
        模式适配主方法
        
        Args:
            source: 源策略对象
            target_type: 目标模式类型
            **kwargs: 适配参数，可包含：
                - mode: 'event_to_matrix' 或 'matrix_to_event'
                - data: 市场数据
                
        Returns:
            适配后的策略或信号
        """
        if not self.can_adapt(source, target_type):
            raise AdapterError(f"无法适配策略 {source.name}")
        
        mode = kwargs.get('mode', 'auto')
        
        if mode == 'auto':
            # 自动推断模式
            if kwargs.get('data') is not None and isinstance(kwargs['data'], dict):
                mode = 'event_to_matrix'
            else:
                mode = 'matrix_to_event'
        
        try:
            if mode == 'event_to_matrix':
                return self._adapt_event_to_matrix(source, **kwargs)
            elif mode == 'matrix_to_event':
                return self._adapt_matrix_to_event(source, **kwargs)
            else:
                raise AdapterError(f"不支持的适配模式: {mode}")
                
        except Exception as e:
            raise AdapterError(f"模式适配失败: {e}")
    
    def _adapt_event_to_matrix(self, strategy: IStrategy, **kwargs) -> pd.DataFrame:
        """
        将事件驱动策略适配为矩阵模式
        
        Args:
            strategy: 策略对象
            **kwargs: 包含市场数据等参数
            
        Returns:
            pd.DataFrame: 信号矩阵
        """
        data = kwargs.get('data')
        if not data or 'close' not in data:
            raise AdapterError("事件转矩阵模式需要提供完整的市场数据")
        
        close_data = data['close']
        
        # 如果策略已经支持向量化，直接调用
        if strategy.supports_vectorization:
            try:
                return strategy.cal_vectorized(data)
            except Exception as e:
                GLOG.WARNING(f"策略 {strategy.name} 向量化计算失败，使用逐行适配: {e}")
        
        # 逐行模拟事件驱动
        signal_matrix = pd.DataFrame(0.0, index=close_data.index, columns=close_data.columns)
        
        # 模拟逐日处理
        for date in close_data.index:
            try:
                # 构造当前日期的市场数据
                current_market_data = self._extract_current_data(data, date)
                
                # 设置策略的当前状态（如果支持）
                if hasattr(strategy, 'set_current_data'):
                    strategy.set_current_data(current_market_data)
                elif hasattr(strategy, '_current_bar'):
                    strategy._current_bar = current_market_data
                
                # 调用策略计算
                signals = strategy.cal()
                
                # 转换信号到矩阵格式
                if signals:
                    for signal in signals:
                        if hasattr(signal, 'code') and signal.code in signal_matrix.columns:
                            # 根据方向设置信号强度
                            if signal.direction == DIRECTION_TYPES.LONG:
                                signal_matrix.loc[date, signal.code] = 1.0
                            elif signal.direction == DIRECTION_TYPES.SHORT:
                                signal_matrix.loc[date, signal.code] = -1.0
                            
            except Exception as e:
                GLOG.DEBUG(f"日期 {date} 策略计算失败: {e}")
                continue
        
        return signal_matrix
    
    def _adapt_matrix_to_event(self, strategy: IStrategy, **kwargs) -> 'EventAdapter':
        """
        将矩阵策略适配为事件驱动模式
        
        Args:
            strategy: 策略对象
            
        Returns:
            EventAdapter: 事件适配器包装
        """
        return EventAdapter(strategy, **kwargs)
    
    def _extract_current_data(self, data: Dict[str, pd.DataFrame], date) -> Dict[str, Any]:
        """
        提取当前日期的数据
        
        Args:
            data: 完整数据字典
            date: 当前日期
            
        Returns:
            Dict[str, Any]: 当前日期的数据
        """
        current_data = {}
        
        for key, df in data.items():
            if date in df.index:
                current_data[key] = df.loc[date]
            else:
                # 如果没有该日期的数据，使用最近的数据
                available_dates = df.index[df.index <= date]
                if len(available_dates) > 0:
                    recent_date = available_dates[-1]
                    current_data[key] = df.loc[recent_date]
        
        return current_data
    
    def adapt_signals_to_matrix(self, signals: List[Signal], index, columns) -> pd.DataFrame:
        """
        将信号列表转换为矩阵格式
        
        Args:
            signals: 信号列表
            index: 时间索引
            columns: 股票代码列
            
        Returns:
            pd.DataFrame: 信号矩阵
        """
        signal_matrix = pd.DataFrame(0.0, index=index, columns=columns)
        
        for signal in signals:
            if hasattr(signal, 'timestamp') and hasattr(signal, 'code'):
                if signal.timestamp in index and signal.code in columns:
                    if signal.direction == DIRECTION_TYPES.LONG:
                        signal_matrix.loc[signal.timestamp, signal.code] = 1.0
                    elif signal.direction == DIRECTION_TYPES.SHORT:
                        signal_matrix.loc[signal.timestamp, signal.code] = -1.0
        
        return signal_matrix
    
    def adapt_matrix_to_signals(self, signal_matrix: pd.DataFrame, portfolio_id: str = "", engine_id: str = "") -> List[Signal]:
        """
        将信号矩阵转换为信号列表
        
        Args:
            signal_matrix: 信号矩阵
            portfolio_id: 组合ID
            engine_id: 引擎ID
            
        Returns:
            List[Signal]: 信号列表
        """
        signals = []
        
        for date in signal_matrix.index:
            for code in signal_matrix.columns:
                signal_value = signal_matrix.loc[date, code]
                
                if abs(signal_value) > 1e-6:  # 忽略极小的信号
                    direction = DIRECTION_TYPES.LONG if signal_value > 0 else DIRECTION_TYPES.SHORT
                    
                    try:
                        signal = Signal(
                            portfolio_id=portfolio_id,
                            engine_id=engine_id,
                            timestamp=date,
                            code=code,
                            direction=direction,
                            reason=f"Matrix signal {signal_value:.4f}",
                            source=SOURCE_TYPES.STRATEGY
                        )
                        signals.append(signal)
                    except Exception as e:
                        GLOG.DEBUG(f"创建信号失败 {code}@{date}: {e}")
                        continue
        
        return signals


class EventAdapter:
    """事件驱动适配器包装类"""
    
    def __init__(self, matrix_strategy: IStrategy, **kwargs):
        self.matrix_strategy = matrix_strategy
        self.name = f"EventAdapter({matrix_strategy.name})"
        self._data_buffer = {}
        self._signal_cache = {}
        self.buffer_size = kwargs.get('buffer_size', 60)  # 缓冲区大小
        
    def cal(self) -> List[Signal]:
        """事件驱动模式的信号计算"""
        try:
            # 如果有足够的历史数据，使用矩阵计算
            if len(self._data_buffer) >= self.buffer_size:
                # 构造数据矩阵
                data_dict = self._buffer_to_matrix()
                
                # 调用原始策略的矩阵计算
                if hasattr(self.matrix_strategy, 'cal_vectorized'):
                    signal_matrix = self.matrix_strategy.cal_vectorized(data_dict)
                    
                    # 只返回最新的信号
                    latest_date = signal_matrix.index[-1]
                    signals = []
                    
                    for code in signal_matrix.columns:
                        signal_value = signal_matrix.loc[latest_date, code]
                        if abs(signal_value) > 1e-6:
                            direction = DIRECTION_TYPES.LONG if signal_value > 0 else DIRECTION_TYPES.SHORT
                            
                            signal = Signal(
                                portfolio_id="",
                                engine_id="",
                                timestamp=latest_date,
                                code=code,
                                direction=direction,
                                reason=f"Event adapted signal {signal_value:.4f}",
                                source=SOURCE_TYPES.STRATEGY
                            )
                            signals.append(signal)
                    
                    return signals
            
            # 数据不足时返回空信号
            return []
            
        except Exception as e:
            GLOG.ERROR(f"事件适配器计算失败: {e}")
            return []
    
    def update_data(self, market_data: Dict[str, Any]) -> None:
        """更新市场数据缓冲区"""
        timestamp = market_data.get('timestamp')
        if not timestamp:
            return
        
        # 添加到缓冲区
        self._data_buffer[timestamp] = market_data
        
        # 保持缓冲区大小
        if len(self._data_buffer) > self.buffer_size:
            # 移除最旧的数据
            oldest_key = min(self._data_buffer.keys())
            del self._data_buffer[oldest_key]
    
    def _buffer_to_matrix(self) -> Dict[str, pd.DataFrame]:
        """将缓冲区数据转换为矩阵格式"""
        if not self._data_buffer:
            return {}
        
        # 获取所有时间戳和股票代码
        timestamps = sorted(self._data_buffer.keys())
        all_codes = set()
        
        for data in self._data_buffer.values():
            if 'close' in data:
                all_codes.update(data['close'].keys())
        
        all_codes = sorted(list(all_codes))
        
        # 构造数据矩阵
        data_matrices = {}
        columns_to_extract = ['open', 'high', 'low', 'close', 'volume']
        
        for col in columns_to_extract:
            matrix = pd.DataFrame(index=timestamps, columns=all_codes, dtype=float)
            
            for timestamp in timestamps:
                market_data = self._data_buffer[timestamp]
                if col in market_data:
                    for code in all_codes:
                        if code in market_data[col]:
                            matrix.loc[timestamp, code] = market_data[col][code]
            
            data_matrices[col] = matrix.fillna(method='ffill')  # 前向填充
        
        return data_matrices


class VectorizedWrapper:
    """向量化包装器 - 为不支持向量化的策略提供向量化能力"""
    
    def __init__(self, strategy: IStrategy):
        self.strategy = strategy
        self.name = f"Vectorized({strategy.name})"
    
    def cal_vectorized(self, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """向量化计算包装"""
        mode_adapter = ModeAdapter()
        return mode_adapter._adapt_event_to_matrix(self.strategy, data=data)
    
    def __getattr__(self, name):
        """代理其他属性到原始策略"""
        return getattr(self.strategy, name)