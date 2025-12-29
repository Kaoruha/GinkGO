# Upstream: All Modules
# Downstream: Standard Library
# Role: StabilityUtils稳定性工具提供重试和容错机制支持系统稳定性保障和故障恢复支持交易系统功能和组件集成提供完整业务支持






"""
Stability Utilities

This module provides utility functions for stability analysis and statistical computations.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from scipy import stats
from decimal import Decimal


def calculate_rolling_statistics(values: List[float], 
                               window_size: int) -> Dict[str, List[float]]:
    """
    计算滚动统计量
    
    Args:
        values: 数值列表
        window_size: 滚动窗口大小
        
    Returns:
        Dict: 滚动统计量字典
    """
    if len(values) < window_size:
        return {}
        
    rolling_means = []
    rolling_stds = []
    rolling_mins = []
    rolling_maxs = []
    
    for i in range(window_size - 1, len(values)):
        window_data = values[i - window_size + 1:i + 1]
        
        rolling_means.append(np.mean(window_data))
        rolling_stds.append(np.std(window_data, ddof=1) if len(window_data) > 1 else 0)
        rolling_mins.append(min(window_data))
        rolling_maxs.append(max(window_data))
        
    return {
        'means': rolling_means,
        'stds': rolling_stds,
        'mins': rolling_mins,
        'maxs': rolling_maxs
    }


def detect_statistical_outliers(values: List[float], 
                               method: str = 'iqr',
                               threshold: float = 1.5) -> List[int]:
    """
    检测统计异常值
    
    Args:
        values: 数值列表
        method: 检测方法 ('iqr', 'zscore', 'mad')
        threshold: 阈值
        
    Returns:
        List[int]: 异常值的索引列表
    """
    if not values or len(values) < 3:
        return []
        
    outlier_indices = []
    
    if method == 'iqr':
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - threshold * iqr
        upper_bound = q3 + threshold * iqr
        
        for i, value in enumerate(values):
            if value < lower_bound or value > upper_bound:
                outlier_indices.append(i)
                
    elif method == 'zscore':
        mean_val = np.mean(values)
        std_val = np.std(values, ddof=1)
        
        if std_val > 0:
            for i, value in enumerate(values):
                z_score = abs((value - mean_val) / std_val)
                if z_score > threshold:
                    outlier_indices.append(i)
                    
    elif method == 'mad':
        median_val = np.median(values)
        mad = np.median([abs(v - median_val) for v in values])
        
        if mad > 0:
            for i, value in enumerate(values):
                modified_z_score = 0.6745 * (value - median_val) / mad
                if abs(modified_z_score) > threshold:
                    outlier_indices.append(i)
                    
    return outlier_indices


def calculate_confidence_intervals(values: List[float], 
                                 confidence_levels: List[float] = [0.68, 0.95, 0.99]) -> Dict:
    """
    计算置信区间
    
    Args:
        values: 数值列表
        confidence_levels: 置信水平列表
        
    Returns:
        Dict: 置信区间字典
    """
    if not values or len(values) < 2:
        return {}
        
    mean_val = np.mean(values)
    std_val = np.std(values, ddof=1)
    n = len(values)
    
    intervals = {}
    
    for confidence in confidence_levels:
        # 计算t值
        alpha = 1 - confidence
        t_value = stats.t.ppf(1 - alpha/2, df=n-1)
        
        # 计算标准误
        se = std_val / np.sqrt(n)
        
        # 计算置信区间
        margin_error = t_value * se
        lower_bound = mean_val - margin_error
        upper_bound = mean_val + margin_error
        
        intervals[confidence] = {
            'lower': lower_bound,
            'upper': upper_bound,
            'margin_error': margin_error
        }
        
    return intervals


def test_normality(values: List[float]) -> Dict:
    """
    正态性检验
    
    Args:
        values: 数值列表
        
    Returns:
        Dict: 检验结果
    """
    if not values or len(values) < 3:
        return {'is_normal': False, 'reason': 'insufficient_data'}
        
    results = {}
    
    # Shapiro-Wilk检验
    if 3 <= len(values) <= 5000:
        try:
            sw_stat, sw_pvalue = stats.shapiro(values)
            results['shapiro_wilk'] = {
                'statistic': sw_stat,
                'p_value': sw_pvalue,
                'is_normal': sw_pvalue > 0.05
            }
        except:
            results['shapiro_wilk'] = {'error': 'test_failed'}
            
    # Kolmogorov-Smirnov检验
    if len(values) >= 5:
        try:
            # 与标准正态分布比较
            normalized_values = (np.array(values) - np.mean(values)) / np.std(values, ddof=1)
            ks_stat, ks_pvalue = stats.kstest(normalized_values, 'norm')
            results['kolmogorov_smirnov'] = {
                'statistic': ks_stat,
                'p_value': ks_pvalue,
                'is_normal': ks_pvalue > 0.05
            }
        except:
            results['kolmogorov_smirnov'] = {'error': 'test_failed'}
            
    # Anderson-Darling检验
    if len(values) >= 7:
        try:
            ad_stat, ad_critical, ad_significance = stats.anderson(values, dist='norm')
            # 使用5%显著性水平
            is_normal = ad_stat < ad_critical[2]  # 5%水平的临界值
            results['anderson_darling'] = {
                'statistic': ad_stat,
                'critical_values': ad_critical,
                'significance_levels': ad_significance,
                'is_normal': is_normal
            }
        except:
            results['anderson_darling'] = {'error': 'test_failed'}
            
    # 综合判断
    normal_tests = [test.get('is_normal', False) for test in results.values() 
                   if isinstance(test, dict) and 'is_normal' in test]
    
    if normal_tests:
        results['summary'] = {
            'is_normal': sum(normal_tests) > len(normal_tests) / 2,
            'tests_passed': sum(normal_tests),
            'total_tests': len(normal_tests)
        }
    else:
        results['summary'] = {'is_normal': False, 'reason': 'no_valid_tests'}
        
    return results


def calculate_distribution_metrics(values: List[float]) -> Dict:
    """
    计算分布特征指标
    
    Args:
        values: 数值列表
        
    Returns:
        Dict: 分布指标字典
    """
    if not values:
        return {}
        
    # 基本统计量
    mean_val = np.mean(values)
    median_val = np.median(values)
    std_val = np.std(values, ddof=1) if len(values) > 1 else 0
    var_val = np.var(values, ddof=1) if len(values) > 1 else 0
    
    # 分位数
    percentiles = [5, 10, 25, 75, 90, 95]
    percentile_values = {f'p{p}': np.percentile(values, p) for p in percentiles}
    
    # 偏度和峰度
    skewness = stats.skew(values) if len(values) > 2 else 0
    kurtosis = stats.kurtosis(values) if len(values) > 3 else 0
    
    # 变异系数
    cv = std_val / abs(mean_val) if mean_val != 0 else float('inf')
    
    # 四分位距
    iqr = percentile_values['p75'] - percentile_values['p25']
    
    # 极值比率
    range_val = max(values) - min(values)
    
    return {
        'basic_stats': {
            'count': len(values),
            'mean': mean_val,
            'median': median_val,
            'std': std_val,
            'variance': var_val,
            'min': min(values),
            'max': max(values),
            'range': range_val
        },
        'percentiles': percentile_values,
        'shape_metrics': {
            'skewness': skewness,
            'kurtosis': kurtosis,
            'coefficient_of_variation': cv
        },
        'spread_metrics': {
            'iqr': iqr,
            'relative_iqr': iqr / median_val if median_val != 0 else float('inf'),
            'range_ratio': range_val / median_val if median_val != 0 else float('inf')
        }
    }


def compare_distributions(values1: List[float], values2: List[float]) -> Dict:
    """
    比较两个分布
    
    Args:
        values1: 第一组数值
        values2: 第二组数值
        
    Returns:
        Dict: 比较结果
    """
    if not values1 or not values2:
        return {'status': 'insufficient_data'}
        
    results = {}
    
    # 基本统计量比较
    stats1 = calculate_distribution_metrics(values1)
    stats2 = calculate_distribution_metrics(values2)
    
    results['basic_comparison'] = {
        'mean_diff': stats1['basic_stats']['mean'] - stats2['basic_stats']['mean'],
        'std_ratio': stats1['basic_stats']['std'] / stats2['basic_stats']['std'] if stats2['basic_stats']['std'] > 0 else float('inf'),
        'cv_diff': stats1['shape_metrics']['coefficient_of_variation'] - stats2['shape_metrics']['coefficient_of_variation']
    }
    
    # t检验（均值比较）
    if len(values1) >= 2 and len(values2) >= 2:
        try:
            t_stat, t_pvalue = stats.ttest_ind(values1, values2)
            results['t_test'] = {
                'statistic': t_stat,
                'p_value': t_pvalue,
                'means_equal': t_pvalue > 0.05
            }
        except:
            results['t_test'] = {'error': 'test_failed'}
            
    # F检验（方差比较）
    if len(values1) >= 2 and len(values2) >= 2:
        try:
            var1 = np.var(values1, ddof=1)
            var2 = np.var(values2, ddof=1)
            
            if var2 > 0:
                f_stat = var1 / var2
                df1 = len(values1) - 1
                df2 = len(values2) - 1
                f_pvalue = 2 * min(stats.f.cdf(f_stat, df1, df2), 1 - stats.f.cdf(f_stat, df1, df2))
                
                results['f_test'] = {
                    'statistic': f_stat,
                    'p_value': f_pvalue,
                    'variances_equal': f_pvalue > 0.05
                }
        except:
            results['f_test'] = {'error': 'test_failed'}
            
    # Kolmogorov-Smirnov检验（分布形状比较）
    if len(values1) >= 3 and len(values2) >= 3:
        try:
            ks_stat, ks_pvalue = stats.ks_2samp(values1, values2)
            results['ks_test'] = {
                'statistic': ks_stat,
                'p_value': ks_pvalue,
                'distributions_equal': ks_pvalue > 0.05
            }
        except:
            results['ks_test'] = {'error': 'test_failed'}
            
    return results


def calculate_stability_trends(values: List[float], window_sizes: List[int] = [5, 10, 20]) -> Dict:
    """
    计算稳定性趋势
    
    Args:
        values: 数值列表
        window_sizes: 滚动窗口大小列表
        
    Returns:
        Dict: 稳定性趋势分析
    """
    if not values or len(values) < min(window_sizes):
        return {}
        
    trends = {}
    
    for window_size in window_sizes:
        if len(values) >= window_size:
            rolling_stats = calculate_rolling_statistics(values, window_size)
            
            if rolling_stats:
                # 计算滚动变异系数
                rolling_cvs = []
                for i in range(len(rolling_stats['means'])):
                    mean_val = rolling_stats['means'][i]
                    std_val = rolling_stats['stds'][i]
                    cv = std_val / abs(mean_val) if mean_val != 0 else float('inf')
                    rolling_cvs.append(cv)
                    
                # 趋势分析
                if len(rolling_cvs) > 1:
                    x = np.arange(len(rolling_cvs))
                    slope, intercept, r_value, p_value, std_err = stats.linregress(x, rolling_cvs)
                    
                    trends[f'window_{window_size}'] = {
                        'rolling_cvs': rolling_cvs,
                        'trend_slope': slope,
                        'trend_r_squared': r_value ** 2,
                        'trend_p_value': p_value,
                        'is_stable_trend': abs(slope) < 0.01 and p_value > 0.05,
                        'stability_direction': 'improving' if slope < 0 else 'deteriorating' if slope > 0 else 'stable'
                    }
                    
    return trends


def identify_regime_changes(values: List[float], 
                          method: str = 'variance',
                          sensitivity: float = 0.5) -> List[int]:
    """
    识别数据中的结构性变化点
    
    Args:
        values: 数值列表
        method: 检测方法 ('variance', 'mean', 'trend')
        sensitivity: 敏感度参数
        
    Returns:
        List[int]: 变化点索引列表
    """
    if not values or len(values) < 6:
        return []
        
    change_points = []
    window_size = max(3, int(len(values) * 0.1))  # 动态窗口大小
    
    if method == 'variance':
        # 基于方差变化检测
        for i in range(window_size, len(values) - window_size):
            before_window = values[i-window_size:i]
            after_window = values[i:i+window_size]
            
            var_before = np.var(before_window, ddof=1) if len(before_window) > 1 else 0
            var_after = np.var(after_window, ddof=1) if len(after_window) > 1 else 0
            
            if var_before > 0 and var_after > 0:
                var_ratio = max(var_after / var_before, var_before / var_after)
                if var_ratio > (1 + sensitivity):
                    change_points.append(i)
                    
    elif method == 'mean':
        # 基于均值变化检测
        for i in range(window_size, len(values) - window_size):
            before_window = values[i-window_size:i]
            after_window = values[i:i+window_size]
            
            mean_before = np.mean(before_window)
            mean_after = np.mean(after_window)
            std_total = np.std(values, ddof=1)
            
            if std_total > 0:
                mean_change = abs(mean_after - mean_before) / std_total
                if mean_change > sensitivity:
                    change_points.append(i)
                    
    elif method == 'trend':
        # 基于趋势变化检测
        for i in range(window_size, len(values) - window_size):
            before_window = values[i-window_size:i]
            after_window = values[i:i+window_size]
            
            # 计算趋势斜率
            x_before = np.arange(len(before_window))
            x_after = np.arange(len(after_window))
            
            if len(before_window) > 1 and len(after_window) > 1:
                slope_before = np.polyfit(x_before, before_window, 1)[0]
                slope_after = np.polyfit(x_after, after_window, 1)[0]
                
                slope_change = abs(slope_after - slope_before)
                if slope_change > sensitivity:
                    change_points.append(i)
                    
    # 去除过于接近的变化点
    if len(change_points) > 1:
        filtered_points = [change_points[0]]
        for point in change_points[1:]:
            if point - filtered_points[-1] > window_size:
                filtered_points.append(point)
        change_points = filtered_points
        
    return change_points


def calculate_persistence_score(values: List[float], lag: int = 1) -> float:
    """
    计算持续性评分（自相关性）
    
    Args:
        values: 数值列表
        lag: 滞后期
        
    Returns:
        float: 持续性评分 (-1到1)
    """
    if not values or len(values) <= lag:
        return 0.0
        
    # 计算自相关系数
    n = len(values)
    mean_val = np.mean(values)
    
    # 去均值
    centered = np.array(values) - mean_val
    
    # 计算自相关
    numerator = np.sum(centered[:-lag] * centered[lag:])
    denominator = np.sum(centered**2)
    
    if denominator == 0:
        return 0.0
        
    autocorr = numerator / denominator
    return autocorr