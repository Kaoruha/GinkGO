# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: SliceDataManager切片数据管理器提供数据切片管理支持数据分段支持交易系统功能支持相关功能






"""
Slice Data Manager

This module manages data retrieval and slicing operations for backtest evaluation.
It handles analyzer records, signals, and orders data from the database.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from decimal import Decimal

from ginkgo.libs import GLOG, datetime_normalize
from ginkgo.data.operations import (
    get_analyzer_records_page_filtered,
    get_signals_page_filtered,
    get_order_records_page_filtered
)


class SliceDataManager:
    """
    切片数据管理器
    负责从数据库获取回测数据，并进行切片处理
    """
    
    def __init__(self):
        """初始化数据管理器"""
        self.cache = {}  # 数据缓存
        
    def get_backtest_data(self, 
                         portfolio_id: str,
                         engine_id: str,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        """
        获取回测的analyzer、signal、order数据
        
        Args:
            portfolio_id: 投资组合ID
            engine_id: 引擎ID
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict: 包含analyzer_data, signal_data, order_data的字典
        """
        GLOG.info(f"获取回测数据: portfolio={portfolio_id}, engine={engine_id}")
        
        try:
            # 获取analyzer记录
            analyzer_data = get_analyzer_records_page_filtered(
                portfolio_id=portfolio_id,
                engine_id=engine_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # 获取信号记录
            signal_data = get_signals_page_filtered(
                portfolio_id=portfolio_id,
                engine_id=engine_id,
                start_date=start_date,
                end_date=end_date,
                as_dataframe=True
            )
            
            # 获取订单记录
            order_data = get_order_records_page_filtered(
                portfolio_id=portfolio_id,
                engine_id=engine_id,
                start_date=start_date,
                end_date=end_date
            )
            
            # 数据预处理
            analyzer_data = self._preprocess_analyzer_data(analyzer_data)
            signal_data = self._preprocess_signal_data(signal_data)
            order_data = self._preprocess_order_data(order_data)
            
            GLOG.info(f"数据获取完成: analyzer={len(analyzer_data)}, signal={len(signal_data)}, order={len(order_data)}")
            
            return {
                'analyzer_data': analyzer_data,
                'signal_data': signal_data,
                'order_data': order_data
            }
            
        except Exception as e:
            GLOG.error(f"获取回测数据失败: {e}")
            raise
            
    def _preprocess_analyzer_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        预处理analyzer数据
        
        Args:
            data: 原始analyzer数据
            
        Returns:
            pd.DataFrame: 预处理后的数据
        """
        if data.empty:
            return data
            
        # 确保timestamp列为datetime类型
        if 'timestamp' in data.columns:
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            
        # 确保value列为数值类型
        if 'value' in data.columns:
            data['value'] = pd.to_numeric(data['value'], errors='coerce')
            
        # 按时间排序
        data = data.sort_values('timestamp').reset_index(drop=True)
        
        return data
        
    def _preprocess_signal_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        预处理信号数据
        
        Args:
            data: 原始信号数据
            
        Returns:
            pd.DataFrame: 预处理后的数据
        """
        if data.empty:
            return data
            
        # 确保timestamp列为datetime类型
        if 'timestamp' in data.columns:
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            
        # 按时间排序
        data = data.sort_values('timestamp').reset_index(drop=True)
        
        return data
        
    def _preprocess_order_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        预处理订单数据
        
        Args:
            data: 原始订单数据
            
        Returns:
            pd.DataFrame: 预处理后的数据
        """
        if data.empty:
            return data
            
        # 确保timestamp列为datetime类型
        if 'timestamp' in data.columns:
            data['timestamp'] = pd.to_datetime(data['timestamp'])
            
        # 确保数值列为数值类型
        numeric_columns = ['volume', 'limit_price', 'transaction_price', 'fee']
        for col in numeric_columns:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')
                
        # 按时间排序
        data = data.sort_values('timestamp').reset_index(drop=True)
        
        return data
        
    def slice_data_by_period(self, 
                           backtest_data: Dict[str, pd.DataFrame],
                           period_days: int) -> List[Dict]:
        """
        按指定周期切片数据
        
        Args:
            backtest_data: 回测数据字典
            period_days: 切片周期（天）
            
        Returns:
            List[Dict]: 切片列表
        """
        analyzer_data = backtest_data['analyzer_data']
        signal_data = backtest_data['signal_data']
        order_data = backtest_data['order_data']
        
        # 确定时间范围
        start_date, end_date = self._get_data_time_range(analyzer_data, signal_data, order_data)
        
        if start_date is None or end_date is None:
            GLOG.warn("无法确定数据时间范围")
            return []
            
        GLOG.info(f"数据时间范围: {start_date} 到 {end_date}")
        
        # 创建切片
        slices = []
        current_start = start_date
        slice_index = 0
        
        while current_start < end_date:
            current_end = current_start + timedelta(days=period_days)
            
            # 获取当前切片的数据
            slice_analyzer = self._filter_data_by_time(analyzer_data, current_start, current_end)
            slice_signals = self._filter_data_by_time(signal_data, current_start, current_end)
            slice_orders = self._filter_data_by_time(order_data, current_start, current_end)
            
            slice_data = {
                'slice_index': slice_index,
                'start_date': current_start,
                'end_date': current_end,
                'period_days': period_days,
                'analyzer_data': slice_analyzer,
                'signal_data': slice_signals,
                'order_data': slice_orders,
                'signal_count': len(slice_signals),
                'order_count': len(slice_orders),
                'analyzer_count': len(slice_analyzer)
            }
            
            slices.append(slice_data)
            current_start = current_end
            slice_index += 1
            
        GLOG.info(f"数据切片完成: 共{len(slices)}个切片")
        return slices
        
    def _get_data_time_range(self, *dataframes) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        获取数据的时间范围
        
        Args:
            dataframes: 数据框列表
            
        Returns:
            Tuple: (开始时间, 结束时间)
        """
        min_times = []
        max_times = []
        
        for df in dataframes:
            if not df.empty and 'timestamp' in df.columns:
                min_times.append(df['timestamp'].min())
                max_times.append(df['timestamp'].max())
                
        if not min_times or not max_times:
            return None, None
            
        return min(min_times), max(max_times)
        
    def _filter_data_by_time(self, 
                           data: pd.DataFrame,
                           start_time: datetime,
                           end_time: datetime) -> pd.DataFrame:
        """
        按时间过滤数据
        
        Args:
            data: 数据框
            start_time: 开始时间
            end_time: 结束时间
            
        Returns:
            pd.DataFrame: 过滤后的数据
        """
        if data.empty or 'timestamp' not in data.columns:
            return data
            
        mask = (data['timestamp'] >= start_time) & (data['timestamp'] < end_time)
        return data[mask].copy()
        
    def balance_slice_boundaries(self, 
                                slices: List[Dict],
                                min_signals_per_slice: int,
                                min_orders_per_slice: int) -> List[Dict]:
        """
        调整切片边界确保平衡
        
        Args:
            slices: 原始切片列表
            min_signals_per_slice: 每个切片最少信号数
            min_orders_per_slice: 每个切片最少订单数
            
        Returns:
            List[Dict]: 调整后的切片列表
        """
        if not slices:
            return slices
            
        balanced_slices = []
        current_slice = None
        
        for slice_data in slices:
            if current_slice is None:
                current_slice = slice_data.copy()
                continue
                
            # 检查当前累积切片是否满足最小要求
            if (current_slice['signal_count'] >= min_signals_per_slice and 
                current_slice['order_count'] >= min_orders_per_slice):
                # 满足要求，保存当前切片
                balanced_slices.append(current_slice)
                current_slice = slice_data.copy()
            else:
                # 不满足要求，合并到当前切片
                current_slice = self._merge_slices(current_slice, slice_data)
                
        # 处理最后一个切片
        if current_slice is not None:
            if balanced_slices:
                # 如果最后一个切片太小，合并到前一个
                if (current_slice['signal_count'] < min_signals_per_slice or 
                    current_slice['order_count'] < min_orders_per_slice):
                    last_slice = balanced_slices.pop()
                    merged_slice = self._merge_slices(last_slice, current_slice)
                    balanced_slices.append(merged_slice)
                else:
                    balanced_slices.append(current_slice)
            else:
                balanced_slices.append(current_slice)
                
        GLOG.info(f"切片平衡调整完成: {len(slices)} -> {len(balanced_slices)}")
        return balanced_slices
        
    def _merge_slices(self, slice1: Dict, slice2: Dict) -> Dict:
        """
        合并两个切片
        
        Args:
            slice1: 第一个切片
            slice2: 第二个切片
            
        Returns:
            Dict: 合并后的切片
        """
        merged_slice = {
            'slice_index': slice1['slice_index'],
            'start_date': slice1['start_date'],
            'end_date': slice2['end_date'],
            'period_days': (slice2['end_date'] - slice1['start_date']).days,
            'analyzer_data': pd.concat([slice1['analyzer_data'], slice2['analyzer_data']], ignore_index=True),
            'signal_data': pd.concat([slice1['signal_data'], slice2['signal_data']], ignore_index=True),
            'order_data': pd.concat([slice1['order_data'], slice2['order_data']], ignore_index=True)
        }
        
        # 更新计数
        merged_slice['signal_count'] = len(merged_slice['signal_data'])
        merged_slice['order_count'] = len(merged_slice['order_data'])
        merged_slice['analyzer_count'] = len(merged_slice['analyzer_data'])
        
        return merged_slice
        
    def validate_slice_quality(self, slices: List[Dict]) -> Dict:
        """
        验证切片质量
        
        Args:
            slices: 切片列表
            
        Returns:
            Dict: 质量评估结果
        """
        if not slices:
            return {'is_valid': False, 'reason': '没有有效切片'}
            
        # 检查基本要求
        total_signals = sum(s['signal_count'] for s in slices)
        total_orders = sum(s['order_count'] for s in slices)
        
        if total_signals == 0:
            return {'is_valid': False, 'reason': '总信号数为0'}
            
        if total_orders == 0:
            return {'is_valid': False, 'reason': '总订单数为0'}
            
        # 检查数据完整性
        empty_slices = sum(1 for s in slices if s['analyzer_count'] == 0)
        if empty_slices > len(slices) * 0.3:  # 超过30%的切片没有analyzer数据
            return {'is_valid': False, 'reason': f'过多空切片: {empty_slices}/{len(slices)}'}
            
        # 检查时间连续性
        for i in range(1, len(slices)):
            if slices[i]['start_date'] != slices[i-1]['end_date']:
                return {'is_valid': False, 'reason': f'时间不连续: 切片{i-1}和{i}'}
                
        return {
            'is_valid': True,
            'slice_count': len(slices),
            'total_signals': total_signals,
            'total_orders': total_orders,
            'average_signals_per_slice': total_signals / len(slices),
            'average_orders_per_slice': total_orders / len(slices),
            'time_span_days': (slices[-1]['end_date'] - slices[0]['start_date']).days
        }
        
    def get_slice_summary(self, slices: List[Dict]) -> Dict:
        """
        获取切片摘要信息
        
        Args:
            slices: 切片列表
            
        Returns:
            Dict: 摘要信息
        """
        if not slices:
            return {'status': 'empty'}
            
        signal_counts = [s['signal_count'] for s in slices]
        order_counts = [s['order_count'] for s in slices]
        analyzer_counts = [s['analyzer_count'] for s in slices]
        
        return {
            'status': 'available',
            'slice_count': len(slices),
            'time_span': {
                'start': slices[0]['start_date'],
                'end': slices[-1]['end_date'],
                'days': (slices[-1]['end_date'] - slices[0]['start_date']).days
            },
            'signal_stats': {
                'total': sum(signal_counts),
                'mean': np.mean(signal_counts),
                'std': np.std(signal_counts),
                'min': min(signal_counts),
                'max': max(signal_counts)
            },
            'order_stats': {
                'total': sum(order_counts),
                'mean': np.mean(order_counts),
                'std': np.std(order_counts),
                'min': min(order_counts),
                'max': max(order_counts)
            },
            'analyzer_stats': {
                'total': sum(analyzer_counts),
                'mean': np.mean(analyzer_counts),
                'std': np.std(analyzer_counts),
                'min': min(analyzer_counts),
                'max': max(analyzer_counts)
            }
        }