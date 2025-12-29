# Upstream: All Modules
# Downstream: Standard Library
# Role: SliceUtils切片工具提供数据切片和分页处理的辅助方法支持大数据集处理和内存优化支持交易系统功能和组件集成提供完整业务支持






"""
Slice Utilities

This module provides utility functions for data slicing operations.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta

from ginkgo.libs import datetime_normalize


def create_time_slices(start_date: datetime, 
                      end_date: datetime, 
                      period_days: int) -> List[Tuple[datetime, datetime]]:
    """
    创建时间切片边界
    
    Args:
        start_date: 开始时间
        end_date: 结束时间
        period_days: 切片周期（天）
        
    Returns:
        List[Tuple]: 时间切片边界列表 [(start, end), ...]
    """
    slices = []
    current_start = start_date
    
    while current_start < end_date:
        current_end = min(current_start + timedelta(days=period_days), end_date)
        slices.append((current_start, current_end))
        current_start = current_end
        
    return slices


def balance_slice_data_distribution(data_counts: List[int], 
                                  min_count: int,
                                  max_cv: float = 0.5) -> List[int]:
    """
    平衡切片数据分布
    
    Args:
        data_counts: 每个切片的数据计数
        min_count: 最小计数要求
        max_cv: 最大变异系数
        
    Returns:
        List[int]: 调整后的边界索引
    """
    if not data_counts:
        return []
        
    # 检查基本要求
    if min(data_counts) < min_count:
        # 需要合并切片
        return _merge_small_slices(data_counts, min_count)
        
    # 检查变异系数
    cv = np.std(data_counts) / np.mean(data_counts) if np.mean(data_counts) > 0 else float('inf')
    
    if cv > max_cv:
        # 需要重新平衡
        return _rebalance_slices(data_counts, max_cv)
        
    return list(range(len(data_counts)))


def _merge_small_slices(data_counts: List[int], min_count: int) -> List[int]:
    """合并小切片"""
    merged_indices = []
    current_sum = 0
    current_start = 0
    
    for i, count in enumerate(data_counts):
        current_sum += count
        
        if current_sum >= min_count:
            merged_indices.append((current_start, i + 1))
            current_sum = 0
            current_start = i + 1
            
    # 处理剩余数据
    if current_start < len(data_counts) and merged_indices:
        # 合并到最后一个切片
        last_start, last_end = merged_indices[-1]
        merged_indices[-1] = (last_start, len(data_counts))
    elif current_start < len(data_counts):
        # 创建最后一个切片
        merged_indices.append((current_start, len(data_counts)))
        
    return merged_indices


def _rebalance_slices(data_counts: List[int], max_cv: float) -> List[int]:
    """重新平衡切片"""
    total_count = sum(data_counts)
    target_count_per_slice = total_count / len(data_counts)
    
    balanced_indices = []
    current_sum = 0
    current_start = 0
    
    for i, count in enumerate(data_counts):
        current_sum += count
        
        if current_sum >= target_count_per_slice:
            balanced_indices.append((current_start, i + 1))
            current_sum = 0
            current_start = i + 1
            
    # 处理剩余数据
    if current_start < len(data_counts) and balanced_indices:
        last_start, last_end = balanced_indices[-1]
        balanced_indices[-1] = (last_start, len(data_counts))
    elif current_start < len(data_counts):
        balanced_indices.append((current_start, len(data_counts)))
        
    return balanced_indices


def calculate_slice_overlap(slice1: Tuple[datetime, datetime], 
                          slice2: Tuple[datetime, datetime]) -> float:
    """
    计算两个时间切片的重叠程度
    
    Args:
        slice1: 第一个切片 (start, end)
        slice2: 第二个切片 (start, end)
        
    Returns:
        float: 重叠比例 (0-1)
    """
    start1, end1 = slice1
    start2, end2 = slice2
    
    # 计算重叠区间
    overlap_start = max(start1, start2)
    overlap_end = min(end1, end2)
    
    if overlap_start >= overlap_end:
        return 0.0  # 无重叠
        
    # 计算重叠时长
    overlap_duration = (overlap_end - overlap_start).total_seconds()
    
    # 计算较短切片的时长
    duration1 = (end1 - start1).total_seconds()
    duration2 = (end2 - start2).total_seconds()
    min_duration = min(duration1, duration2)
    
    if min_duration == 0:
        return 0.0
        
    return overlap_duration / min_duration


def filter_dataframe_by_time(df: pd.DataFrame,
                           start_time: datetime,
                           end_time: datetime,
                           time_column: str = 'timestamp') -> pd.DataFrame:
    """
    按时间过滤DataFrame
    
    Args:
        df: 数据框
        start_time: 开始时间
        end_time: 结束时间
        time_column: 时间列名
        
    Returns:
        pd.DataFrame: 过滤后的数据框
    """
    if df.empty or time_column not in df.columns:
        return df.copy()
        
    # 确保时间列为datetime类型
    df = df.copy()
    df[time_column] = pd.to_datetime(df[time_column])
    
    # 应用时间过滤
    mask = (df[time_column] >= start_time) & (df[time_column] < end_time)
    return df[mask].reset_index(drop=True)


def validate_slice_continuity(slices: List[Tuple[datetime, datetime]]) -> Dict:
    """
    验证切片的时间连续性
    
    Args:
        slices: 时间切片列表
        
    Returns:
        Dict: 验证结果
    """
    if not slices:
        return {'is_continuous': True, 'gaps': [], 'overlaps': []}
        
    gaps = []
    overlaps = []
    
    for i in range(1, len(slices)):
        prev_end = slices[i-1][1]
        curr_start = slices[i][0]
        
        if prev_end < curr_start:
            # 发现时间间隙
            gaps.append({
                'slice_index': i-1,
                'gap_start': prev_end,
                'gap_end': curr_start,
                'gap_duration': (curr_start - prev_end).total_seconds()
            })
        elif prev_end > curr_start:
            # 发现时间重叠
            overlaps.append({
                'slice_index': i-1,
                'overlap_start': curr_start,
                'overlap_end': prev_end,
                'overlap_duration': (prev_end - curr_start).total_seconds()
            })
            
    return {
        'is_continuous': len(gaps) == 0 and len(overlaps) == 0,
        'gaps': gaps,
        'overlaps': overlaps,
        'total_gaps': len(gaps),
        'total_overlaps': len(overlaps)
    }


def optimize_slice_boundaries(data: pd.DataFrame,
                            initial_slices: List[Tuple[datetime, datetime]],
                            target_count_per_slice: int,
                            time_column: str = 'timestamp') -> List[Tuple[datetime, datetime]]:
    """
    优化切片边界以获得更均匀的数据分布
    
    Args:
        data: 原始数据
        initial_slices: 初始切片边界
        target_count_per_slice: 目标每切片数据量
        time_column: 时间列名
        
    Returns:
        List[Tuple]: 优化后的切片边界
    """
    if data.empty or not initial_slices:
        return initial_slices
        
    # 确保时间列为datetime类型
    data = data.copy()
    data[time_column] = pd.to_datetime(data[time_column])
    data = data.sort_values(time_column)
    
    optimized_slices = []
    start_idx = 0
    
    for i, (slice_start, slice_end) in enumerate(initial_slices):
        # 找到当前切片的数据
        slice_data = data[(data[time_column] >= slice_start) & 
                         (data[time_column] < slice_end)]
        
        if len(slice_data) == 0:
            continue
            
        # 如果数据量接近目标，保持原边界
        if abs(len(slice_data) - target_count_per_slice) <= target_count_per_slice * 0.2:
            optimized_slices.append((slice_start, slice_end))
            continue
            
        # 如果数据量过多，分割切片
        if len(slice_data) > target_count_per_slice * 1.5:
            sub_slices = _split_slice_by_count(slice_data, target_count_per_slice, time_column)
            optimized_slices.extend(sub_slices)
        else:
            optimized_slices.append((slice_start, slice_end))
            
    return optimized_slices


def _split_slice_by_count(data: pd.DataFrame, 
                         target_count: int,
                         time_column: str) -> List[Tuple[datetime, datetime]]:
    """按数据量分割切片"""
    sub_slices = []
    
    for start_idx in range(0, len(data), target_count):
        end_idx = min(start_idx + target_count, len(data))
        
        if start_idx < len(data):
            sub_start = data.iloc[start_idx][time_column]
            sub_end = data.iloc[end_idx - 1][time_column] + timedelta(seconds=1)
            sub_slices.append((sub_start, sub_end))
            
    return sub_slices


def calculate_slice_statistics(slices: List[Dict]) -> Dict:
    """
    计算切片统计信息
    
    Args:
        slices: 切片数据列表
        
    Returns:
        Dict: 统计信息
    """
    if not slices:
        return {'count': 0}
        
    signal_counts = [s.get('signal_count', 0) for s in slices]
    order_counts = [s.get('order_count', 0) for s in slices]
    analyzer_counts = [s.get('analyzer_count', 0) for s in slices]
    
    durations = []
    for s in slices:
        if 'start_date' in s and 'end_date' in s:
            duration = (s['end_date'] - s['start_date']).total_seconds() / 86400  # 转换为天
            durations.append(duration)
            
    return {
        'count': len(slices),
        'signal_stats': _calculate_list_stats(signal_counts),
        'order_stats': _calculate_list_stats(order_counts),
        'analyzer_stats': _calculate_list_stats(analyzer_counts),
        'duration_stats': _calculate_list_stats(durations) if durations else {},
        'balance_metrics': {
            'signal_cv': np.std(signal_counts) / np.mean(signal_counts) if np.mean(signal_counts) > 0 else float('inf'),
            'order_cv': np.std(order_counts) / np.mean(order_counts) if np.mean(order_counts) > 0 else float('inf'),
        }
    }


def _calculate_list_stats(values: List[float]) -> Dict:
    """计算列表的基本统计量"""
    if not values:
        return {}
        
    return {
        'count': len(values),
        'sum': sum(values),
        'mean': np.mean(values),
        'std': np.std(values, ddof=1) if len(values) > 1 else 0,
        'min': min(values),
        'max': max(values),
        'median': np.median(values),
        'q25': np.percentile(values, 25),
        'q75': np.percentile(values, 75)
    }