# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: LiveDeviationDetector实盘偏差检测器检测实盘回测偏差支持交易系统功能支持相关功能






"""
Live Deviation Detector

This module monitors live trading performance and detects deviations from backtest baseline.
It accumulates live data and compares against historical slice distributions.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from ginkgo.trading.time.clock import now as clock_now
from decimal import Decimal

from ginkgo.libs import GLOG, datetime_normalize


class LiveDeviationDetector:
    """
    场景2专用：实盘统计与偏离判断
    根据回测基准，监控实盘表现并检测偏离程度
    """
    
    def __init__(self, 
                 baseline_stats: Dict,
                 slice_period_days: int,
                 confidence_levels: List[float] = [0.68, 0.95, 0.99]):
        """
        初始化实盘偏离检测器
        
        Args:
            baseline_stats: 回测基准统计数据
            slice_period_days: 切片周期（天）
            confidence_levels: 置信水平列表
        """
        self.baseline_stats = baseline_stats
        self.slice_period_days = slice_period_days
        self.confidence_levels = confidence_levels
        
        # 当前切片数据缓存
        self.current_slice_data = {
            'start_date': None,
            'analyzer_data': [],
            'signal_data': [],
            'order_data': []
        }
        
        # 历史偏离记录
        self.deviation_history = []
        
    def accumulate_live_data(self, 
                           analyzer_records: List[Dict] = None,
                           signal_records: List[Dict] = None,
                           order_records: List[Dict] = None) -> bool:
        """
        累积实盘数据到当前切片
        
        Args:
            analyzer_records: 新的analyzer记录
            signal_records: 新的信号记录
            order_records: 新的订单记录
            
        Returns:
            bool: 是否完成了一个切片
        """
        current_time = clock_now()
        
        # 初始化当前切片
        if self.current_slice_data['start_date'] is None:
            self.current_slice_data['start_date'] = current_time
            GLOG.info(f"开始新的切片: {current_time}")
            
        # 添加新数据
        if analyzer_records:
            self.current_slice_data['analyzer_data'].extend(analyzer_records)
            
        if signal_records:
            self.current_slice_data['signal_data'].extend(signal_records)
            
        if order_records:
            self.current_slice_data['order_data'].extend(order_records)
            
        # 检查是否完成切片
        slice_end_time = self.current_slice_data['start_date'] + timedelta(days=self.slice_period_days)
        
        if current_time >= slice_end_time:
            GLOG.info(f"切片完成: {self.current_slice_data['start_date']} 到 {slice_end_time}")
            return True
            
        return False
        
    def check_deviation_on_slice_complete(self) -> Dict:
        """
        切片完成时检查偏离程度
        
        Returns:
            Dict: 偏离分析结果
        """
        if not self.current_slice_data['analyzer_data']:
            GLOG.warn("当前切片无analyzer数据，跳过偏离检测")
            return {'status': 'no_data'}
            
        # 计算当前切片指标
        current_metrics = self._calculate_slice_metrics(self.current_slice_data)
        
        # 与基准比较
        deviation_results = {}
        overall_deviation_level = "NORMAL"
        
        for metric_name, current_value in current_metrics.items():
            if metric_name in self.baseline_stats:
                deviation_info = self._calculate_metric_deviation(
                    metric_name, current_value, self.baseline_stats[metric_name]
                )
                deviation_results[metric_name] = deviation_info
                
                # 更新整体偏离等级
                if deviation_info['level'] == "SEVERE":
                    overall_deviation_level = "SEVERE"
                elif deviation_info['level'] == "MODERATE" and overall_deviation_level == "NORMAL":
                    overall_deviation_level = "MODERATE"
                    
        # 记录偏离历史
        deviation_record = {
            'timestamp': clock_now(),
            'slice_start': self.current_slice_data['start_date'],
            'metrics': current_metrics,
            'deviations': deviation_results,
            'overall_level': overall_deviation_level
        }
        
        self.deviation_history.append(deviation_record)
        
        # 重置当前切片
        self._reset_current_slice()
        
        GLOG.info(f"偏离检测完成，整体等级: {overall_deviation_level}")
        
        return {
            'status': 'completed',
            'overall_level': overall_deviation_level,
            'metrics': current_metrics,
            'deviations': deviation_results,
            'slice_period': self.slice_period_days
        }
        
    def _calculate_slice_metrics(self, slice_data: Dict) -> Dict:
        """
        计算切片的关键指标
        
        Args:
            slice_data: 切片数据
            
        Returns:
            Dict: 指标值字典
        """
        metrics = {}
        
        # 从analyzer数据中提取指标
        for record in slice_data['analyzer_data']:
            metric_name = record.get('name', 'unknown')
            metric_value = float(record.get('value', 0))
            
            if metric_name not in metrics:
                metrics[metric_name] = []
            metrics[metric_name].append(metric_value)
            
        # 计算每个指标的聚合值（使用最后一个值或平均值）
        aggregated_metrics = {}
        for metric_name, values in metrics.items():
            if values:
                # 对于累积型指标（如净值、利润），使用最后一个值
                if metric_name.lower() in ['net_value', 'profit', 'total_return']:
                    aggregated_metrics[metric_name] = values[-1]
                else:
                    # 对于其他指标，使用平均值
                    aggregated_metrics[metric_name] = np.mean(values)
                    
        # 添加交易活跃度指标
        aggregated_metrics['signal_count'] = len(slice_data['signal_data'])
        aggregated_metrics['order_count'] = len(slice_data['order_data'])
        
        return aggregated_metrics
        
    def _calculate_metric_deviation(self, 
                                  metric_name: str,
                                  current_value: float,
                                  baseline_stats: Dict) -> Dict:
        """
        计算单个指标的偏离程度
        
        Args:
            metric_name: 指标名称
            current_value: 当前值
            baseline_stats: 基准统计数据
            
        Returns:
            Dict: 偏离信息
        """
        baseline_mean = baseline_stats.get('mean', 0)
        baseline_std = baseline_stats.get('std', 1)
        baseline_values = baseline_stats.get('values', [])
        
        # 计算标准化偏离（Z-score）
        z_score = (current_value - baseline_mean) / baseline_std if baseline_std > 0 else 0
        
        # 计算分位数位置
        percentile = self._calculate_percentile(current_value, baseline_values)
        
        # 判断偏离等级
        deviation_level = self._classify_deviation_level(z_score, percentile)
        
        # 计算偏离方向
        deviation_direction = "HIGHER" if current_value > baseline_mean else "LOWER"
        
        return {
            'current_value': current_value,
            'baseline_mean': baseline_mean,
            'baseline_std': baseline_std,
            'z_score': z_score,
            'percentile': percentile,
            'level': deviation_level,
            'direction': deviation_direction,
            'deviation_magnitude': abs(z_score)
        }
        
    def _calculate_percentile(self, value: float, baseline_values: List[float]) -> float:
        """
        计算值在基准分布中的分位数位置
        
        Args:
            value: 当前值
            baseline_values: 基准值列表
            
        Returns:
            float: 分位数位置 (0-100)
        """
        if not baseline_values:
            return 50.0  # 默认中位数
            
        return float(np.percentile(baseline_values, 50) if len(baseline_values) == 1 
                    else (np.searchsorted(sorted(baseline_values), value) / len(baseline_values) * 100))
        
    def _classify_deviation_level(self, z_score: float, percentile: float) -> str:
        """
        根据Z-score和分位数分类偏离等级
        
        Args:
            z_score: 标准化偏离
            percentile: 分位数位置
            
        Returns:
            str: 偏离等级 (NORMAL, MODERATE, SEVERE)
        """
        abs_z = abs(z_score)
        
        # 严重偏离：Z-score > 2 或在极端分位数
        if abs_z > 2.0 or percentile < 2.5 or percentile > 97.5:
            return "SEVERE"
            
        # 中等偏离：Z-score > 1 或在边缘分位数
        elif abs_z > 1.0 or percentile < 16 or percentile > 84:
            return "MODERATE"
            
        # 正常范围
        else:
            return "NORMAL"
            
    def _reset_current_slice(self):
        """重置当前切片数据"""
        self.current_slice_data = {
            'start_date': None,
            'analyzer_data': [],
            'signal_data': [],
            'order_data': []
        }
        
    def get_deviation_summary(self, last_n_slices: int = 10) -> Dict:
        """
        获取最近N个切片的偏离摘要
        
        Args:
            last_n_slices: 最近N个切片
            
        Returns:
            Dict: 偏离摘要
        """
        if not self.deviation_history:
            return {'status': 'no_history'}
            
        recent_history = self.deviation_history[-last_n_slices:]
        
        # 统计偏离等级分布
        level_counts = {'NORMAL': 0, 'MODERATE': 0, 'SEVERE': 0}
        for record in recent_history:
            level = record['overall_level']
            level_counts[level] += 1
            
        # 识别持续偏离的指标
        persistent_deviations = {}
        for record in recent_history:
            for metric_name, deviation_info in record['deviations'].items():
                if deviation_info['level'] != 'NORMAL':
                    if metric_name not in persistent_deviations:
                        persistent_deviations[metric_name] = 0
                    persistent_deviations[metric_name] += 1
                    
        return {
            'status': 'available',
            'total_slices': len(recent_history),
            'level_distribution': level_counts,
            'persistent_deviations': persistent_deviations,
            'latest_overall_level': recent_history[-1]['overall_level'],
            'risk_score': self._calculate_risk_score(recent_history)
        }
        
    def _calculate_risk_score(self, history: List[Dict]) -> float:
        """
        计算风险评分
        
        Args:
            history: 偏离历史记录
            
        Returns:
            float: 风险评分 (0-100, 越高越危险)
        """
        if not history:
            return 0.0
            
        total_score = 0
        total_weight = 0
        
        for i, record in enumerate(history):
            # 时间权重（越近越重要）
            time_weight = (i + 1) / len(history)
            
            # 偏离等级得分
            level_score = {'NORMAL': 0, 'MODERATE': 30, 'SEVERE': 70}[record['overall_level']]
            
            total_score += level_score * time_weight
            total_weight += time_weight
            
        return total_score / total_weight if total_weight > 0 else 0.0
