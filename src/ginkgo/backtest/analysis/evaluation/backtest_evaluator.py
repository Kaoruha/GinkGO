"""
Backtest Evaluator

This module provides the main interface for backtest stability evaluation and live monitoring setup.
It orchestrates the slice analysis process and creates monitoring baselines.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json

from ginkgo.libs import GLOG
from .slice_period_optimizer import SlicePeriodOptimizer
from .live_deviation_detector import LiveDeviationDetector
from .metric_stability_calculator import MetricStabilityCalculator
from .slice_data_manager import SliceDataManager


class BacktestEvaluator:
    """
    回测评估器统一接口
    整合场景1（回测稳定性评估）和场景2（实盘监控基准建立）的完整流程
    """
    
    def __init__(self, 
                 min_signals_per_slice: int = 10,
                 min_orders_per_slice: int = 5,
                 candidate_periods: List[int] = None):
        """
        初始化回测评估器
        
        Args:
            min_signals_per_slice: 每个切片最少信号数量
            min_orders_per_slice: 每个切片最少订单数量
            candidate_periods: 候选切片周期列表
        """
        self.data_manager = SliceDataManager()
        self.period_optimizer = SlicePeriodOptimizer(min_signals_per_slice, min_orders_per_slice)
        self.stability_calculator = MetricStabilityCalculator()
        
        if candidate_periods:
            self.period_optimizer.candidate_periods = candidate_periods
            
    def evaluate_backtest_stability(self, 
                                  portfolio_id: str,
                                  engine_id: str,
                                  start_date: Optional[str] = None,
                                  end_date: Optional[str] = None) -> Dict:
        """
        场景1：完整回测稳定性评估流程
        
        Args:
            portfolio_id: 投资组合ID
            engine_id: 引擎ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict: 完整的评估结果
        """
        GLOG.info(f"开始回测稳定性评估: portfolio={portfolio_id}, engine={engine_id}")
        
        try:
            # 1. 获取回测数据
            GLOG.info("步骤1: 获取回测数据")
            backtest_data = self.data_manager.get_backtest_data(
                portfolio_id=portfolio_id,
                engine_id=engine_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # 验证数据完整性
            if self._validate_backtest_data(backtest_data):
                GLOG.error("回测数据验证失败")
                return {'status': 'failed', 'reason': 'invalid_data'}
                
            # 2. 寻找最佳切片周期
            GLOG.info("步骤2: 寻找最佳切片周期")
            optimal_period, stability_score, period_analysis = self.period_optimizer.find_optimal_slice_period(
                analyzer_data=backtest_data['analyzer_data'],
                signal_data=backtest_data['signal_data'],
                order_data=backtest_data['order_data']
            )
            
            # 3. 使用最佳周期重新切片
            GLOG.info(f"步骤3: 使用最佳周期({optimal_period}天)重新切片")
            optimal_slices = self.data_manager.slice_data_by_period(backtest_data, optimal_period)
            
            # 4. 平衡切片
            balanced_slices = self.data_manager.balance_slice_boundaries(
                optimal_slices,
                self.period_optimizer.min_signals_per_slice,
                self.period_optimizer.min_orders_per_slice
            )
            
            # 5. 计算每个切片的指标
            GLOG.info("步骤4: 计算切片指标")
            slice_metrics = self._calculate_slice_metrics(balanced_slices)
            
            # 6. 计算稳定性分析
            GLOG.info("步骤5: 计算稳定性分析")
            stability_analysis = self._analyze_metric_stability(slice_metrics)
            
            # 7. 生成基准数据
            GLOG.info("步骤6: 生成监控基准")
            monitoring_baseline = self._create_monitoring_baseline(slice_metrics, optimal_period)
            
            # 8. 生成综合评估报告
            evaluation_result = {
                'status': 'success',
                'evaluation_time': datetime.now().isoformat(),
                'portfolio_id': portfolio_id,
                'engine_id': engine_id,
                'data_summary': {
                    'analyzer_records': len(backtest_data['analyzer_data']),
                    'signal_records': len(backtest_data['signal_data']),
                    'order_records': len(backtest_data['order_data']),
                    'time_span': self._get_time_span(backtest_data)
                },
                'optimal_slice_config': {
                    'period_days': optimal_period,
                    'stability_score': stability_score,
                    'slice_count': len(balanced_slices)
                },
                'period_analysis': period_analysis,
                'slice_summary': self.data_manager.get_slice_summary(balanced_slices),
                'stability_analysis': stability_analysis,
                'monitoring_baseline': monitoring_baseline,
                'recommendations': self._generate_recommendations(stability_analysis, optimal_period)
            }
            
            GLOG.info("回测稳定性评估完成")
            return evaluation_result
            
        except Exception as e:
            GLOG.error(f"回测稳定性评估失败: {e}")
            return {'status': 'error', 'error': str(e)}
            
    def create_live_monitor(self, 
                          monitoring_baseline: Dict,
                          confidence_levels: List[float] = [0.68, 0.95, 0.99]) -> LiveDeviationDetector:
        """
        场景2：创建实盘监控器
        
        Args:
            monitoring_baseline: 监控基准数据
            confidence_levels: 置信水平列表
            
        Returns:
            LiveDeviationDetector: 实盘偏离检测器实例
        """
        GLOG.info("创建实盘监控器")
        
        baseline_stats = monitoring_baseline.get('baseline_stats', {})
        slice_period = monitoring_baseline.get('slice_period_days', 30)
        
        monitor = LiveDeviationDetector(
            baseline_stats=baseline_stats,
            slice_period_days=slice_period,
            confidence_levels=confidence_levels
        )
        
        GLOG.info(f"实盘监控器创建完成，切片周期: {slice_period}天")
        return monitor
        
    def _validate_backtest_data(self, backtest_data: Dict[str, pd.DataFrame]) -> bool:
        """
        验证回测数据的完整性
        
        Args:
            backtest_data: 回测数据字典
            
        Returns:
            bool: True表示验证失败，False表示验证成功
        """
        analyzer_data = backtest_data['analyzer_data']
        signal_data = backtest_data['signal_data']
        order_data = backtest_data['order_data']
        
        # 检查基本数据存在
        if analyzer_data.empty:
            GLOG.error("Analyzer数据为空")
            return True
            
        # 检查必要列存在
        required_analyzer_cols = ['timestamp', 'name', 'value']
        if not all(col in analyzer_data.columns for col in required_analyzer_cols):
            GLOG.error(f"Analyzer数据缺少必要列: {required_analyzer_cols}")
            return True
            
        # 检查数据量
        if len(analyzer_data) < 10:
            GLOG.error(f"Analyzer数据量太少: {len(analyzer_data)}")
            return True
            
        return False
        
    def _calculate_slice_metrics(self, slices: List[Dict]) -> Dict[str, List[float]]:
        """
        计算每个切片的指标值
        
        Args:
            slices: 切片列表
            
        Returns:
            Dict: 指标名到数值列表的映射
        """
        metric_data = {}
        
        for slice_data in slices:
            analyzer_data = slice_data['analyzer_data']
            
            # 按指标名称分组并计算聚合值
            for _, row in analyzer_data.iterrows():
                metric_name = row['name']
                metric_value = float(row['value'])
                
                if metric_name not in metric_data:
                    metric_data[metric_name] = []
                    
                metric_data[metric_name].append(metric_value)
                
        # 对于每个切片，确保每个指标只有一个值（取最后一个或平均值）
        final_metrics = {}
        for metric_name, all_values in metric_data.items():
            # 按切片重新组织数据
            slice_values = []
            values_per_slice = len(all_values) // len(slices) if slices else 1
            
            for i in range(len(slices)):
                start_idx = i * values_per_slice
                end_idx = start_idx + values_per_slice
                slice_metric_values = all_values[start_idx:end_idx]
                
                if slice_metric_values:
                    # 对于累积型指标，取最后一个值；对于其他指标，取平均值
                    if metric_name.lower() in ['net_value', 'profit', 'total_return']:
                        slice_values.append(slice_metric_values[-1])
                    else:
                        slice_values.append(np.mean(slice_metric_values))
                        
            if slice_values:
                final_metrics[metric_name] = slice_values
                
        return final_metrics
        
    def _analyze_metric_stability(self, slice_metrics: Dict[str, List[float]]) -> Dict:
        """
        分析指标稳定性
        
        Args:
            slice_metrics: 切片指标数据
            
        Returns:
            Dict: 稳定性分析结果
        """
        stability_results = {}
        
        # 计算每个指标的稳定性
        for metric_name, values in slice_metrics.items():
            if len(values) >= 2:  # 至少需要2个数据点
                stability_results[metric_name] = self.stability_calculator.get_comprehensive_stability_score(values)
                
        # 跨指标比较
        comparison_result = self.stability_calculator.compare_stability_across_metrics(slice_metrics)
        
        return {
            'individual_metrics': stability_results,
            'cross_metric_comparison': comparison_result
        }
        
    def _create_monitoring_baseline(self, 
                                  slice_metrics: Dict[str, List[float]],
                                  slice_period_days: int) -> Dict:
        """
        创建监控基准数据
        
        Args:
            slice_metrics: 切片指标数据
            slice_period_days: 切片周期
            
        Returns:
            Dict: 监控基准数据
        """
        baseline_stats = {}
        
        for metric_name, values in slice_metrics.items():
            if values:
                baseline_stats[metric_name] = {
                    'mean': np.mean(values),
                    'std': np.std(values, ddof=1) if len(values) > 1 else 0,
                    'median': np.median(values),
                    'values': values,  # 保留原始数据用于分位数计算
                    'min': min(values),
                    'max': max(values),
                    'count': len(values)
                }
                
        return {
            'slice_period_days': slice_period_days,
            'baseline_stats': baseline_stats,
            'creation_time': datetime.now().isoformat(),
            'total_slices': len(next(iter(slice_metrics.values()))) if slice_metrics else 0
        }
        
    def _get_time_span(self, backtest_data: Dict[str, pd.DataFrame]) -> Dict:
        """
        获取回测数据的时间跨度
        
        Args:
            backtest_data: 回测数据
            
        Returns:
            Dict: 时间跨度信息
        """
        all_timestamps = []
        
        for data_type, df in backtest_data.items():
            if not df.empty and 'timestamp' in df.columns:
                all_timestamps.extend(df['timestamp'].tolist())
                
        if all_timestamps:
            start_time = min(all_timestamps)
            end_time = max(all_timestamps)
            return {
                'start': start_time.isoformat(),
                'end': end_time.isoformat(),
                'days': (end_time - start_time).days
            }
        else:
            return {'start': None, 'end': None, 'days': 0}
            
    def _generate_recommendations(self, 
                                stability_analysis: Dict,
                                optimal_period: int) -> List[str]:
        """
        基于稳定性分析生成建议
        
        Args:
            stability_analysis: 稳定性分析结果
            optimal_period: 最优切片周期
            
        Returns:
            List[str]: 建议列表
        """
        recommendations = []
        
        # 分析跨指标比较结果
        comparison = stability_analysis.get('cross_metric_comparison', {})
        avg_stability = comparison.get('average_stability', 0)
        
        if avg_stability > 0.8:
            recommendations.append("策略表现非常稳定，适合实盘交易")
        elif avg_stability > 0.6:
            recommendations.append("策略表现较为稳定，建议小仓位试运行")
        else:
            recommendations.append("策略稳定性较差，建议优化后再考虑实盘")
            
        # 分析最稳定和最不稳定的指标
        most_stable = comparison.get('most_stable')
        least_stable = comparison.get('least_stable')
        
        if most_stable:
            recommendations.append(f"最稳定指标: {most_stable}，可重点关注")
            
        if least_stable:
            recommendations.append(f"最不稳定指标: {least_stable}，需要重点监控")
            
        # 切片周期建议
        if optimal_period <= 14:
            recommendations.append("建议密切监控短期表现变化")
        elif optimal_period >= 60:
            recommendations.append("建议关注长期趋势，避免过度频繁调整")
            
        return recommendations
        
    def export_evaluation_report(self, evaluation_result: Dict, file_path: str) -> bool:
        """
        导出评估报告到文件
        
        Args:
            evaluation_result: 评估结果
            file_path: 文件路径
            
        Returns:
            bool: 是否成功
        """
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(evaluation_result, f, indent=2, ensure_ascii=False, default=str)
            GLOG.info(f"评估报告已导出到: {file_path}")
            return True
        except Exception as e:
            GLOG.error(f"导出评估报告失败: {e}")
            return False