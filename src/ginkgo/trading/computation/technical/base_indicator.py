# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: BaseIndicator技术指标基类定义指标计算框架和接口支持技术指标开发和扩展实现指标体系支持交易系统功能和组件集成提供完整业务支持






import pandas as pd
import numpy as np
from typing import Union, Dict, List, Tuple, Optional


class BaseIndicator:
    """
    技术指标基类 - 纯静态计算工具
    
    统一设计原则：
    - 纯静态方法，无需实例化
    - 统一返回DataFrame格式
    - 标准化列名规范
    - 容错处理，不打断回测
    """
    
    @staticmethod
    def _validate_and_prepare(data: pd.DataFrame, required_cols: list, min_periods: int = 1) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        统一的数据校验和准备
        
        Args:
            data: 输入数据
            required_cols: 必需的列名列表
            min_periods: 最小数据量要求
            
        Returns:
            (validated_data, error_message): 校验后的数据和错误信息
        """
        try:
            if data is None or data.empty:
                return None, "Empty data"
            
            missing_cols = [col for col in required_cols if col not in data.columns]
            if missing_cols:
                return None, f"Missing required columns: {missing_cols}"
                
            if len(data) < min_periods:
                return None, f"Insufficient data: {len(data)} < {min_periods}"
                
            return data.copy(), None
            
        except Exception as e:
            return None, str(e)
    
    @staticmethod
    def _create_result_df(data: pd.DataFrame, **series_dict) -> pd.DataFrame:
        """
        创建标准化结果DataFrame
        
        Args:
            data: 原始数据（用于获取timestamp）
            **series_dict: 指标计算结果，key为列名，value为Series
            
        Returns:
            标准化的DataFrame，包含timestamp和指标列
        """
        result = pd.DataFrame()
        result['timestamp'] = data['timestamp']
        
        for col_name, series_data in series_dict.items():
            result[col_name] = series_data
            
        return result
    
    @staticmethod
    def _handle_error(data: pd.DataFrame, columns: list) -> pd.DataFrame:
        """
        统一的错误处理，返回NaN填充的DataFrame
        
        Args:
            data: 原始数据
            columns: 指标列名列表
            
        Returns:
            NaN填充的标准DataFrame，不会打断回测流程
        """
        if data is None or data.empty:
            return pd.DataFrame(columns=['timestamp'] + columns)
            
        result = pd.DataFrame()
        result['timestamp'] = data['timestamp'] if 'timestamp' in data.columns else pd.Series(range(len(data)))
        
        for col in columns:
            result[col] = float('nan')
            
        return result
    
    @staticmethod
    def cal_matrix(matrix_data: pd.DataFrame) -> pd.DataFrame:
        """
        Matrix回测计算接口 - 静态方法入口
        
        Args:
            matrix_data: DataFrame，支持两种格式：
                格式1（长格式）: columns=['timestamp', 'code', 'open', 'high', 'low', 'close', 'volume']
                格式2（宽格式）: index=timestamps, columns=codes, 单一字段如close价格矩阵
                
        Returns:
            pd.DataFrame: 计算结果，格式与输入格式保持一致
            
        Note:
            子类需要重写此方法以实现具体的Matrix计算逻辑
            默认实现返回空结果，不会打断程序运行
        """
        # 默认实现：返回空结果，不打断程序
        if 'code' in matrix_data.columns:
            # 长格式：返回原始数据结构，添加NaN指标列
            result = matrix_data.copy()
            result['indicator_value'] = float('nan')  # 占位列名
            return result
        else:
            # 宽格式：返回相同形状的NaN矩阵
            return pd.DataFrame(
                float('nan'), 
                index=matrix_data.index, 
                columns=matrix_data.columns
            )
