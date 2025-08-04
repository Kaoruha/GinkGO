"""
Metric Stability Calculator

This module provides comprehensive stability metrics calculation for backtest slice analysis.
It includes coefficient of variation, consistency ratio, trend stability and other statistical measures.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy import stats
from decimal import Decimal

from ginkgo.libs import GLOG


class MetricStabilityCalculator:
    """
    分析指标平稳性计算器
    提供各种稳定性指标的计算方法，用于评估策略在不同时间切片的表现一致性
    """
    
    def __init__(self, outlier_threshold: float = 2.0):
        """
        初始化稳定性计算器
        
        Args:
            outlier_threshold: 异常值判断阈值（Z-score）
        """
        self.outlier_threshold = outlier_threshold
        
    def calculate_coefficient_of_variation(self, values: List[float]) -> float:
        """
        计算变异系数 (Coefficient of Variation)
        变异系数 = 标准差 / 均值，用于衡量相对变异程度
        
        Args:
            values: 数值列表
            
        Returns:
            float: 变异系数，越小表示越稳定
        """
        if not values or len(values) < 2:
            return float('inf')
            
        mean_val = np.mean(values)
        if mean_val == 0:
            return float('inf')
            
        std_val = np.std(values, ddof=1)  # 样本标准差
        cv = std_val / abs(mean_val)
        
        return cv
        
    def calculate_consistency_ratio(self, values: List[float]) -> float:
        """
        计算一致性比率
        一致性比率 = 稳定切片数 / 总切片数
        稳定切片定义为在均值±1个标准差范围内的切片
        
        Args:
            values: 数值列表
            
        Returns:
            float: 一致性比率 (0-1)，越大表示越一致
        """
        if not values or len(values) < 2:
            return 0.0
            
        mean_val = np.mean(values)
        std_val = np.std(values, ddof=1)
        
        # 计算在均值±1个标准差范围内的数值个数
        stable_count = sum(1 for v in values if abs(v - mean_val) <= std_val)
        
        return stable_count / len(values)
        
    def calculate_trend_stability(self, values: List[float]) -> float:
        """
        计算趋势稳定性
        趋势稳定性 = 1 - |标准化趋势斜率|，用于衡量指标是否有明显趋势
        
        Args:
            values: 数值列表
            
        Returns:
            float: 趋势稳定性 (0-1)，越大表示趋势越稳定
        """
        if not values or len(values) < 2:
            return 0.0
            
        x = np.arange(len(values))
        
        # 计算线性回归斜率
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)
        
        # 标准化斜率（除以数值范围）
        value_range = max(values) - min(values)
        if value_range == 0:
            return 1.0  # 完全平稳
            
        normalized_slope = abs(slope * len(values) / value_range)
        
        # 趋势稳定性
        trend_stability = 1 / (1 + normalized_slope)
        
        return trend_stability
        
    def calculate_outlier_ratio(self, values: List[float]) -> float:
        """
        计算异常值比率
        异常值定义为超出均值±threshold个标准差的数值
        
        Args:
            values: 数值列表
            
        Returns:
            float: 异常值比率 (0-1)，越小表示越稳定
        """
        if not values or len(values) < 2:
            return 0.0
            
        mean_val = np.mean(values)
        std_val = np.std(values, ddof=1)
        
        if std_val == 0:
            return 0.0  # 所有值相同，无异常值
            
        # 计算Z-scores
        z_scores = [(v - mean_val) / std_val for v in values]
        
        # 统计异常值
        outlier_count = sum(1 for z in z_scores if abs(z) > self.outlier_threshold)
        
        return outlier_count / len(values)
        
    def calculate_autocorrelation(self, values: List[float], lag: int = 1) -> float:
        """
        计算自相关系数
        用于检测时间序列的依赖性
        
        Args:
            values: 数值列表
            lag: 滞后阶数
            
        Returns:
            float: 自相关系数 (-1到1)
        """
        if not values or len(values) <= lag:
            return 0.0
            
        # 计算滞后自相关
        n = len(values)
        values_array = np.array(values)
        
        # 去均值
        mean_val = np.mean(values)
        centered = values_array - mean_val
        
        # 计算自相关
        c0 = np.sum(centered**2) / n  # 方差
        if c0 == 0:
            return 0.0
            
        c_lag = np.sum(centered[:-lag] * centered[lag:]) / (n - lag)
        
        autocorr = c_lag / c0
        
        return autocorr
        
    def calculate_normality_score(self, values: List[float]) -> float:
        """
        计算正态性评分
        基于Shapiro-Wilk检验，评估数据的正态性
        
        Args:
            values: 数值列表
            
        Returns:
            float: 正态性评分 (0-1)，越大表示越接近正态分布
        """
        if not values or len(values) < 3:
            return 0.0
            
        # Shapiro-Wilk检验只适用于样本量3-5000
        if len(values) > 5000:
            values = np.random.choice(values, 5000, replace=False).tolist()
            
        try:
            statistic, p_value = stats.shapiro(values)
            # p_value越大，越接近正态分布
            return min(p_value, 1.0)
        except:
            return 0.0
            
    def get_comprehensive_stability_score(self, values: List[float], weights: Dict[str, float] = None) -> Dict:
        """
        计算综合稳定性评分
        整合多个稳定性指标，给出综合评价
        
        Args:
            values: 数值列表
            weights: 各指标权重，默认为均等权重
            
        Returns:
            Dict: 包含各项指标和综合评分的字典
        """
        if weights is None:
            weights = {
                'cv': 0.25,           # 变异系数
                'consistency': 0.25,   # 一致性比率
                'trend': 0.20,        # 趋势稳定性
                'outlier': 0.15,      # 异常值比率
                'normality': 0.15     # 正态性
            }
            
        # 计算各项指标
        cv = self.calculate_coefficient_of_variation(values)
        consistency = self.calculate_consistency_ratio(values)
        trend_stability = self.calculate_trend_stability(values)
        outlier_ratio = self.calculate_outlier_ratio(values)
        normality = self.calculate_normality_score(values)
        autocorr = self.calculate_autocorrelation(values)
        
        # 标准化指标到0-1范围
        # 变异系数：转换为稳定性评分
        cv_score = 1 / (1 + cv) if cv != float('inf') else 0
        
        # 一致性比率：已经在0-1范围
        consistency_score = consistency
        
        # 趋势稳定性：已经在0-1范围
        trend_score = trend_stability
        
        # 异常值比率：转换为稳定性评分
        outlier_score = 1 - outlier_ratio
        
        # 正态性：已经在0-1范围
        normality_score = normality
        
        # 计算加权综合评分
        comprehensive_score = (
            cv_score * weights['cv'] +
            consistency_score * weights['consistency'] +
            trend_score * weights['trend'] +
            outlier_score * weights['outlier'] +
            normality_score * weights['normality']
        )
        
        return {
            'comprehensive_score': comprehensive_score,
            'individual_scores': {
                'coefficient_of_variation': cv,
                'cv_score': cv_score,
                'consistency_ratio': consistency,
                'trend_stability': trend_stability,
                'outlier_ratio': outlier_ratio,
                'outlier_score': outlier_score,
                'normality_score': normality,
                'autocorrelation': autocorr
            },
            'weights': weights,
            'sample_size': len(values),
            'basic_stats': {
                'mean': np.mean(values) if values else 0,
                'std': np.std(values, ddof=1) if len(values) > 1 else 0,
                'min': min(values) if values else 0,
                'max': max(values) if values else 0,
                'median': np.median(values) if values else 0
            }
        }
        
    def compare_stability_across_metrics(self, metric_data: Dict[str, List[float]]) -> Dict:
        """
        比较多个指标的稳定性
        
        Args:
            metric_data: 指标数据字典 {指标名: 数值列表}
            
        Returns:
            Dict: 各指标稳定性比较结果
        """
        stability_results = {}
        
        for metric_name, values in metric_data.items():
            stability_results[metric_name] = self.get_comprehensive_stability_score(values)
            
        # 按综合评分排序
        sorted_metrics = sorted(
            stability_results.items(),
            key=lambda x: x[1]['comprehensive_score'],
            reverse=True
        )
        
        return {
            'metric_stability': stability_results,
            'ranking': [(name, score['comprehensive_score']) for name, score in sorted_metrics],
            'most_stable': sorted_metrics[0][0] if sorted_metrics else None,
            'least_stable': sorted_metrics[-1][0] if sorted_metrics else None,
            'average_stability': np.mean([score['comprehensive_score'] for score in stability_results.values()])
        }
        
    def detect_regime_changes(self, values: List[float], window_size: int = 5) -> List[int]:
        """
        检测数据中的结构性变化点
        使用滑动窗口方差比较来识别regime changes
        
        Args:
            values: 数值列表
            window_size: 滑动窗口大小
            
        Returns:
            List[int]: 变化点的索引列表
        """
        if not values or len(values) < 2 * window_size:
            return []
            
        change_points = []
        
        for i in range(window_size, len(values) - window_size):
            # 前窗口和后窗口
            before_window = values[i-window_size:i]
            after_window = values[i:i+window_size]
            
            # 计算方差比
            var_before = np.var(before_window, ddof=1) if len(before_window) > 1 else 0
            var_after = np.var(after_window, ddof=1) if len(after_window) > 1 else 0
            
            # 避免除零
            if var_before == 0 and var_after == 0:
                continue
            elif var_before == 0:
                var_ratio = float('inf')
            elif var_after == 0:
                var_ratio = 0
            else:
                var_ratio = var_after / var_before
                
            # 检测显著变化（方差比超过阈值）
            if var_ratio > 2.0 or var_ratio < 0.5:
                change_points.append(i)
                
        return change_points