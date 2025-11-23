"""
Alpha158因子工厂 - 基于QLib Alpha158实现
提供批量创建和管理Alpha因子的接口
"""

from typing import Dict, List, Union
import pandas as pd
import numpy as np
from ginkgo.trading.computation.technical.alpha_factors import *
from ginkgo.trading.computation.technical.base_indicator import BaseIndicator


class Alpha158Factory:
    """
    Alpha158因子工厂
    提供批量创建、计算和管理Alpha因子的功能
    """
    
    # 定义Alpha158因子配置
    ALPHA158_CONFIG = {
        # 基础价格因子 (4个)
        'KMID': {'class': KMID, 'params': {}},
        'KLEN': {'class': KLEN, 'params': {}},
        'KLOW': {'class': KLOW, 'params': {}},
        'KHIGH': {'class': KHIGH, 'params': {}},
        
        # 移动平均因子 (30个) - 不同窗口
        **{f'MA{w}': {'class': MA, 'params': {'window': w}} 
           for w in [5, 10, 20, 30, 60]},
        
        # 标准差因子 (30个) - 不同窗口  
        **{f'STD{w}': {'class': STD, 'params': {'window': w}} 
           for w in [5, 10, 20, 30, 60]},
        
        # Beta因子 (30个) - 不同窗口
        **{f'BETA{w}': {'class': BETA, 'params': {'window': w}} 
           for w in [5, 10, 20, 30, 60]},
        
        # 变化率因子 (20个) - 不同周期
        **{f'ROC{p}': {'class': ROC, 'params': {'period': p}} 
           for p in [1, 2, 3, 4, 5, 10, 20, 30]},
        
        # 最大值因子 (25个) - 不同窗口
        **{f'MAX{w}': {'class': MAX, 'params': {'window': w}} 
           for w in [5, 10, 20, 30, 60]},
        
        # 最小值因子 (25个) - 不同窗口
        **{f'MIN{w}': {'class': MIN, 'params': {'window': w}} 
           for w in [5, 10, 20, 30, 60]},
        
        # 分位数因子 (10个)
        **{f'QTLU{w}': {'class': QTLU, 'params': {'window': w, 'quantile': 0.8}} 
           for w in [5, 10, 20, 30, 60]},
        **{f'QTLD{w}': {'class': QTLD, 'params': {'window': w, 'quantile': 0.2}} 
           for w in [5, 10, 20, 30, 60]},
        
        # 排名因子 (5个)
        **{f'RANK{w}': {'class': RANK, 'params': {'window': w}} 
           for w in [5, 10, 20, 30, 60]},
        
        # RSV因子 (5个)
        **{f'RSV{w}': {'class': RSV, 'params': {'window': w}} 
           for w in [6, 10, 14, 20, 30]},
        
        # 位置因子 (15个)
        **{f'IMAX{w}': {'class': IMAX, 'params': {'window': w}} 
           for w in [5, 10, 20, 30, 60]},
        **{f'IMIN{w}': {'class': IMIN, 'params': {'window': w}} 
           for w in [5, 10, 20, 30, 60]},
        **{f'IMXD{w}': {'class': IMXD, 'params': {'window': w}} 
           for w in [5, 10, 20, 30, 60]},
    }
    
    @classmethod
    def get_available_factors(cls) -> List[str]:
        """获取所有可用因子名称"""
        return list(cls.ALPHA158_CONFIG.keys())
    
    @classmethod
    def create_factor(cls, factor_name: str) -> BaseIndicator:
        """
        创建单个因子实例
        
        Args:
            factor_name: 因子名称
            
        Returns:
            因子实例
        """
        if factor_name not in cls.ALPHA158_CONFIG:
            raise ValueError(f"Unknown factor: {factor_name}")
        
        config = cls.ALPHA158_CONFIG[factor_name]
        factor_class = config['class']
        params = config['params'].copy()
        
        # 设置因子名称
        params['name'] = factor_name
        
        return factor_class(**params)
    
    @classmethod
    def create_factor_set(cls, factor_names: List[str] = None) -> Dict[str, BaseIndicator]:
        """
        创建因子集合
        
        Args:
            factor_names: 因子名称列表，None表示创建所有因子
            
        Returns:
            因子字典 {factor_name: factor_instance}
        """
        if factor_names is None:
            factor_names = cls.get_available_factors()
        
        factors = {}
        for name in factor_names:
            try:
                factors[name] = cls.create_factor(name)
            except Exception as e:
                print(f"Warning: Failed to create factor {name}: {e}")
                continue
        
        return factors
    
    @classmethod
    def calculate_single_stock(cls, data: pd.DataFrame, 
                             factor_names: List[str] = None) -> pd.DataFrame:
        """
        计算单只股票的因子值（事件模式）
        
        Args:
            data: 股票OHLCV数据
            factor_names: 要计算的因子名称列表
            
        Returns:
            包含所有因子值的DataFrame
        """
        if factor_names is None:
            factor_names = cls.get_available_factors()
        
        # 创建因子实例
        factors = cls.create_factor_set(factor_names)
        
        # 计算所有因子
        base_df = pd.DataFrame()
        base_df["timestamp"] = data["timestamp"]
        
        for factor_name, factor in factors.items():
            try:
                factor_result = factor.cal(data)
                if factor_name in factor_result.columns:
                    base_df[factor_name] = factor_result[factor_name]
            except Exception as e:
                print(f"Warning: Failed to calculate factor {factor_name}: {e}")
                base_df[factor_name] = np.nan
        
        return base_df
    
    @classmethod
    def calculate_matrix(cls, matrix_data: Dict[str, pd.DataFrame], 
                        dates: List, codes: List,
                        factor_names: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        批量计算因子矩阵（矩阵模式）
        
        Args:
            matrix_data: 矩阵格式的OHLCV数据
            dates: 日期列表
            codes: 股票代码列表
            factor_names: 要计算的因子名称列表
            
        Returns:
            因子矩阵字典 {factor_name: factor_matrix}
        """
        if factor_names is None:
            factor_names = cls.get_available_factors()
        
        # 创建因子实例
        factors = cls.create_factor_set(factor_names)
        
        # 批量计算因子矩阵
        factor_matrices = {}
        
        for factor_name, factor in factors.items():
            try:
                factor_matrix = factor.cal_vectorized(matrix_data, dates, codes)
                factor_matrices[factor_name] = factor_matrix
            except Exception as e:
                print(f"Warning: Failed to calculate factor matrix {factor_name}: {e}")
                # 创建空矩阵
                factor_matrices[factor_name] = pd.DataFrame(
                    index=dates, columns=codes, dtype=float
                )
        
        return factor_matrices
    
    @classmethod
    def get_factor_categories(cls) -> Dict[str, List[str]]:
        """
        按类别获取因子分组
        
        Returns:
            因子分类字典
        """
        categories = {
            'price_momentum': ['KMID', 'KLEN', 'KLOW', 'KHIGH'],
            'moving_average': [name for name in cls.ALPHA158_CONFIG.keys() if name.startswith('MA')],
            'volatility': [name for name in cls.ALPHA158_CONFIG.keys() if name.startswith('STD')],
            'beta': [name for name in cls.ALPHA158_CONFIG.keys() if name.startswith('BETA')],
            'return': [name for name in cls.ALPHA158_CONFIG.keys() if name.startswith('ROC')],
            'extremes': [name for name in cls.ALPHA158_CONFIG.keys() if name.startswith(('MAX', 'MIN'))],
            'quantiles': [name for name in cls.ALPHA158_CONFIG.keys() if name.startswith('QTL')],
            'ranking': [name for name in cls.ALPHA158_CONFIG.keys() if name.startswith('RANK')],
            'rsv': [name for name in cls.ALPHA158_CONFIG.keys() if name.startswith('RSV')],
            'position': [name for name in cls.ALPHA158_CONFIG.keys() if name.startswith(('IMAX', 'IMIN', 'IMXD'))],
        }
        
        return categories
    
    @classmethod
    def create_core_factors(cls) -> Dict[str, BaseIndicator]:
        """
        创建核心因子集合（最重要的20个因子）
        
        Returns:
            核心因子字典
        """
        core_factor_names = [
            'KMID', 'KLEN', 'KLOW', 'KHIGH',  # 基础价格因子
            'MA5', 'MA10', 'MA20',              # 移动平均
            'STD5', 'STD10', 'STD20',           # 波动率
            'ROC1', 'ROC5', 'ROC20',            # 收益率
            'MAX5', 'MIN5',                     # 极值
            'QTLU5', 'QTLD5',                   # 分位数
            'RSV14',                            # RSV
            'RANK10'                            # 排名
        ]
        
        return cls.create_factor_set(core_factor_names)