"""
Slice Period Optimizer

This module finds the optimal slice period for backtest stability analysis.
It ensures balanced slices with similar signal and order counts while maximizing stability.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from decimal import Decimal

from ginkgo.libs import GLOG


class SlicePeriodOptimizer:
    """
    场景1专用：回测完成后参数化查询最佳切片周期
    确保每个周期的信号数量、订单数量基本持平，计算分析指标平稳性
    """
    
    def __init__(self, min_signals_per_slice: int = 10, min_orders_per_slice: int = 5):
        """
        初始化切片周期优化器
        
        Args:
            min_signals_per_slice: 每个切片最少信号数量
            min_orders_per_slice: 每个切片最少订单数量
        """
        self.min_signals_per_slice = min_signals_per_slice
        self.min_orders_per_slice = min_orders_per_slice
        self.candidate_periods = [7, 14, 21, 30, 45, 60, 90]  # 候选周期（天）
        
    def find_optimal_slice_period(self, 
                                analyzer_data: pd.DataFrame,
                                signal_data: pd.DataFrame, 
                                order_data: pd.DataFrame) -> Tuple[int, float, Dict]:
        """
        参数化查询最佳切片周期
        
        Args:
            analyzer_data: analyzer记录数据
            signal_data: 信号数据
            order_data: 订单数据
            
        Returns:
            tuple: (最优周期, 稳定性评分, 详细分析结果)
        """
        GLOG.info("开始寻找最佳切片周期...")
        
        best_period = None
        best_score = 0
        analysis_results = {}
        
        for period in self.candidate_periods:
            GLOG.info(f"测试周期: {period}天")
            
            # 1. 按周期切片
            slices = self._slice_data_by_period(analyzer_data, signal_data, order_data, period)
            
            # 2. 检查平衡性
            balance_check = self._check_slice_balance(slices)
            if not balance_check['is_balanced']:
                GLOG.warn(f"周期{period}天不满足平衡性要求: {balance_check['reason']}")
                continue
                
            # 3. 计算稳定性评分
            stability_score = self._calculate_stability_score(slices)
            
            analysis_results[period] = {
                'stability_score': stability_score,
                'slice_count': len(slices),
                'balance_check': balance_check,
                'slice_stats': self._get_slice_statistics(slices)
            }
            
            # 4. 更新最优周期
            if stability_score > best_score:
                best_score = stability_score
                best_period = period
                
        if best_period is None:
            raise ValueError("未找到满足条件的切片周期")
            
        GLOG.info(f"最优切片周期: {best_period}天, 稳定性评分: {best_score:.4f}")
        return best_period, best_score, analysis_results
        
    def _slice_data_by_period(self, 
                            analyzer_data: pd.DataFrame,
                            signal_data: pd.DataFrame,
                            order_data: pd.DataFrame,
                            period_days: int) -> List[Dict]:
        """
        按指定周期切片数据
        
        Args:
            analyzer_data: analyzer记录
            signal_data: 信号记录  
            order_data: 订单记录
            period_days: 切片周期（天）
            
        Returns:
            List[Dict]: 切片列表，每个切片包含analyzer、signal、order数据
        """
        # 获取时间范围
        start_date = min(
            analyzer_data['timestamp'].min(),
            signal_data['timestamp'].min() if not signal_data.empty else pd.Timestamp.max,
            order_data['timestamp'].min() if not order_data.empty else pd.Timestamp.max
        )
        end_date = max(
            analyzer_data['timestamp'].max(),
            signal_data['timestamp'].max() if not signal_data.empty else pd.Timestamp.min,
            order_data['timestamp'].max() if not order_data.empty else pd.Timestamp.min
        )
        
        # 创建切片边界
        slices = []
        current_start = start_date
        
        while current_start < end_date:
            current_end = current_start + pd.Timedelta(days=period_days)
            
            # 获取当前切片的数据
            slice_analyzer = analyzer_data[
                (analyzer_data['timestamp'] >= current_start) & 
                (analyzer_data['timestamp'] < current_end)
            ].copy()
            
            slice_signals = signal_data[
                (signal_data['timestamp'] >= current_start) & 
                (signal_data['timestamp'] < current_end)
            ].copy()
            
            slice_orders = order_data[
                (order_data['timestamp'] >= current_start) & 
                (order_data['timestamp'] < current_end)
            ].copy()
            
            slice_data = {
                'start_date': current_start,
                'end_date': current_end,
                'analyzer_data': slice_analyzer,
                'signal_data': slice_signals,
                'order_data': slice_orders,
                'signal_count': len(slice_signals),
                'order_count': len(slice_orders)
            }
            
            slices.append(slice_data)
            current_start = current_end
            
        return slices
        
    def _check_slice_balance(self, slices: List[Dict]) -> Dict:
        """
        检查切片平衡性：确保信号数量、订单数量基本持平
        
        Args:
            slices: 切片列表
            
        Returns:
            Dict: 平衡性检查结果
        """
        if not slices:
            return {'is_balanced': False, 'reason': '没有有效切片'}
            
        signal_counts = [slice_data['signal_count'] for slice_data in slices]
        order_counts = [slice_data['order_count'] for slice_data in slices]
        
        # 检查最小数量要求
        if min(signal_counts) < self.min_signals_per_slice:
            return {
                'is_balanced': False, 
                'reason': f'最小信号数量({min(signal_counts)})低于要求({self.min_signals_per_slice})'
            }
            
        if min(order_counts) < self.min_orders_per_slice:
            return {
                'is_balanced': False,
                'reason': f'最小订单数量({min(order_counts)})低于要求({self.min_orders_per_slice})'
            }
            
        # 检查分布均匀性（变异系数不超过50%）
        signal_cv = np.std(signal_counts) / np.mean(signal_counts) if np.mean(signal_counts) > 0 else float('inf')
        order_cv = np.std(order_counts) / np.mean(order_counts) if np.mean(order_counts) > 0 else float('inf')
        
        if signal_cv > 0.5:
            return {
                'is_balanced': False,
                'reason': f'信号数量分布不均匀(CV={signal_cv:.3f} > 0.5)'
            }
            
        if order_cv > 0.5:
            return {
                'is_balanced': False,
                'reason': f'订单数量分布不均匀(CV={order_cv:.3f} > 0.5)'
            }
            
        return {
            'is_balanced': True,
            'signal_cv': signal_cv,
            'order_cv': order_cv,
            'signal_range': (min(signal_counts), max(signal_counts)),
            'order_range': (min(order_counts), max(order_counts))
        }
        
    def _calculate_stability_score(self, slices: List[Dict]) -> float:
        """
        计算所有分析指标的平稳性评分
        
        Args:
            slices: 切片列表
            
        Returns:
            float: 稳定性评分 (0-1, 越高越稳定)
        """
        if not slices:
            return 0.0
            
        # 提取所有analyzer指标
        metric_values = {}
        
        for slice_data in slices:
            analyzer_data = slice_data['analyzer_data']
            
            # 按指标名称分组
            for _, row in analyzer_data.iterrows():
                metric_name = row['name']
                if metric_name not in metric_values:
                    metric_values[metric_name] = []
                metric_values[metric_name].append(float(row['value']))
                
        if not metric_values:
            return 0.0
            
        # 计算每个指标的稳定性
        total_score = 0
        valid_metrics = 0
        
        for metric_name, values in metric_values.items():
            if len(values) < 2:  # 至少需要2个数据点
                continue
                
            # 变异系数（越小越稳定）
            cv = np.std(values) / np.mean(values) if np.mean(values) != 0 else float('inf')
            cv_score = 1 / (1 + cv) if cv != float('inf') else 0
            
            # 一致性比率（正值占比）
            positive_ratio = sum(1 for v in values if v > 0) / len(values)
            consistency_score = 2 * abs(positive_ratio - 0.5)  # 偏离0.5越远越一致
            
            # 趋势稳定性（斜率绝对值的倒数）
            x = np.arange(len(values))
            slope = np.polyfit(x, values, 1)[0] if len(values) > 1 else 0
            trend_stability = 1 / (1 + abs(slope))
            
            # 加权平均
            metric_score = cv_score * 0.4 + consistency_score * 0.3 + trend_stability * 0.3
            total_score += metric_score
            valid_metrics += 1
            
        return total_score / valid_metrics if valid_metrics > 0 else 0.0
        
    def _get_slice_statistics(self, slices: List[Dict]) -> Dict:
        """
        获取切片统计信息
        
        Args:
            slices: 切片列表
            
        Returns:
            Dict: 统计信息
        """
        signal_counts = [s['signal_count'] for s in slices]
        order_counts = [s['order_count'] for s in slices]
        
        return {
            'slice_count': len(slices),
            'signal_stats': {
                'mean': np.mean(signal_counts),
                'std': np.std(signal_counts),
                'min': min(signal_counts),
                'max': max(signal_counts)
            },
            'order_stats': {
                'mean': np.mean(order_counts),
                'std': np.std(order_counts),
                'min': min(order_counts),
                'max': max(order_counts)
            }
        }