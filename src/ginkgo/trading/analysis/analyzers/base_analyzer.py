import pandas as pd
import numpy as np
import warnings
import time
import json
from datetime import datetime
from ginkgo.trading.time.clock import now as clock_now
from typing import TYPE_CHECKING, List
from decimal import Decimal


from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.data.containers import container
from ginkgo.libs import datetime_normalize, to_decimal, Number
from ginkgo.enums import GRAPHY_TYPES, RECORDSTAGE_TYPES, SOURCE_TYPES


class BaseAnalyzer(BacktestBase, TimeMixin):
    # 类级别的监控统计（所有实例共享）
    _execution_stats = {}
    _performance_log = []

    def __init__(self, name: str, timestamp=None, *args, **kwargs):
        BacktestBase.__init__(self, name=name, *args, **kwargs)
        TimeMixin.__init__(self, timestamp=timestamp, *args, **kwargs)
        self._active_stage = []
        self._record_stage = RECORDSTAGE_TYPES.NEWDAY
        self._analyzer_id = ""
        self._portfolio_id = ""
        self._graph_type = GRAPHY_TYPES.OTHER
        
        # 高效数据存储结构 - 替代原有的DataFrame
        self._capacity = 1000
        self._size = 0
        self._timestamps = np.empty(self._capacity, dtype='datetime64[ns]')
        self._values = np.empty(self._capacity, dtype=np.float64)
        self._index_map = {}  # timestamp_str -> index映射，用于O(1)查询
        
        # 错误处理相关
        self._error_count = 0
        self._last_error = None
        self._error_log = []
        
        # 性能监控相关
        self._activation_count = 0
        self._record_count = 0
        self._total_activation_time = 0.0
        self._total_record_time = 0.0

    @property
    def values(self) -> pd.DataFrame:
        """
        As same as data.
        """
        warnings.warn(
            "`values` is deprecated, please use `data` instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return self.data

    @property
    def data(self) -> pd.DataFrame:
        """
        保持向后兼容，返回DataFrame格式
        """
        if self._size == 0:
            return pd.DataFrame(columns=["timestamp", "value"])
        
        return pd.DataFrame({
            "timestamp": self._timestamps[:self._size],
            "value": self._values[:self._size]
        })

    def set_graph_type(self, graph_type: GRAPHY_TYPES, *args, **kwargs) -> None:
        """
        Set Graph Type.
        Args:
            graph_type(enum): Bar, Line
        Returns:
            None
        """
        self._graph_type = graph_type

    @property
    def analyzer_id(self) -> str:
        return self._analyzer_id

    def set_analyzer_id(self, analyzer_id: str) -> str:
        """
        Analyzer ID update.
        Args:
            analyzer_id(str): new ID
        Returns:
            new Analyzer ID
        """
        self._analyzer_id = analyzer_id
        return self.analyzer_id

    @property
    def portfolio_id(self) -> str:
        return self._portfolio_id

    @portfolio_id.setter
    def portfolio_id(self, value: str) -> None:
        self._portfolio_id = value

    def set_portfolio_id(self, value: str) -> None:
        """向后兼容方法，建议使用 portfolio_id 属性赋值"""
        self.portfolio_id = value

    @property
    def active_stage(self) -> List[RECORDSTAGE_TYPES]:
        return self._active_stage

    @property
    def record_stage(self) -> RECORDSTAGE_TYPES:
        return self._record_stage

    def add_active_stage(self, stage: RECORDSTAGE_TYPES, *args, **kwargs) -> None:
        """
        Add Active Stage, active will activate the counter.
        Args:
            stage(enum): newday, signalgeneration, ordersend, orderfilled, ordercanceled
        Returns:
            None
        """
        if stage not in self._active_stage:
            self._active_stage.append(stage)

    def set_record_stage(self, stage: RECORDSTAGE_TYPES, *args, **kwargs) -> None:
        """
        Set Record Stage, record will interact with the db.
        Args:
            stage(enum): newday, signalgeneration, ordersend, orderfilled, ordercanceled
        Returns:
            new record stage
        """
        if isinstance(stage, RECORDSTAGE_TYPES):
            self._record_stage = stage
        else:
            pass

    def activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """
        激活分析器进行计算（模板方法）- 带性能监控和错误处理
        
        Args:
            stage(RECORDSTAGE_TYPES): 当前记录阶段
            portfolio_info(dict): 投资组合信息字典，包含positions, cash, worth等信息
        Returns:
            None
        """
        # Base类负责阶段检查，确保只在配置的阶段激活
        if stage not in self._active_stage:
            return
        
        start_time = time.perf_counter()
        try:
            # 调用子类实现的具体激活逻辑
            self._do_activate(stage, portfolio_info, *args, **kwargs)
            self._activation_count += 1
        except Exception as e:
            self._handle_error("activate", stage, e, portfolio_info)
            raise
        finally:
            # 记录执行时间
            duration = time.perf_counter() - start_time
            self._total_activation_time += duration
            self._record_performance("activate", stage.name, duration)

    def record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """
        记录分析器数据到数据库（模板方法）- 带性能监控和错误处理
        
        Args:
            stage(RECORDSTAGE_TYPES): 当前记录阶段
            portfolio_info(dict): 投资组合信息字典，包含positions, cash, worth等信息
        Returns:
            None
        """
        # Base类负责阶段检查，确保只在配置的阶段记录
        if stage != self._record_stage:
            return
        
        start_time = time.perf_counter()
        try:
            # 调用子类实现的具体记录逻辑
            self._do_record(stage, portfolio_info, *args, **kwargs)
            self._record_count += 1
        except Exception as e:
            self._handle_error("record", stage, e, portfolio_info)
            raise
        finally:
            # 记录执行时间
            duration = time.perf_counter() - start_time
            self._total_record_time += duration
            self._record_performance("record", stage.name, duration)
        
    def _do_activate(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """
        子类需要重写的具体激活逻辑
        
        Args:
            stage(RECORDSTAGE_TYPES): 当前记录阶段
            portfolio_info(dict): 投资组合信息字典
        Returns:
            None
        """
        raise NotImplementedError(
            "ANALYZER should complete the Function _do_activate(), _do_activate() will activate the analyzer counter."
        )

    def _do_record(self, stage: RECORDSTAGE_TYPES, portfolio_info: dict, *args, **kwargs) -> None:
        """
        子类需要重写的具体记录逻辑
        
        Args:
            stage(RECORDSTAGE_TYPES): 当前记录阶段
            portfolio_info(dict): 投资组合信息字典
        Returns:
            None
        """
        raise NotImplementedError(
            "ANALYZER should complete the Function _do_record(), _do_record() will store the data into db."
        )

    def add_data(self, value: Number, *args, **kwargs) -> None:
        """
        O(1)复杂度的数据添加，替代O(n)的DataFrame concat
        Args:
            value(Number): new data
        Returns:
            None
        """
        current_time = self.get_current_time()
        if current_time is None:
            return

        value = to_decimal(value)
        date = current_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # 检查是否需要扩容
        if self._size >= self._capacity:
            self._resize()
        
        # 检查是否是更新现有数据
        if date in self._index_map:
            # 更新现有记录
            idx = self._index_map[date]
            self._values[idx] = float(value)
        else:
            # 添加新记录
            idx = self._size
            self._timestamps[idx] = pd.Timestamp(date)
            self._values[idx] = float(value)
            self._index_map[date] = idx
            self._size += 1

    def get_data(self, time: any, *args, **kwargs) -> Decimal:
        """
        O(1)复杂度的数据查询，替代O(n)的线性搜索
        Args:
            time(any): query time
        Returns:
            the value at query time
        """
        time = datetime_normalize(time)
        date = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # O(1)哈希查找替代O(n)线性搜索
        idx = self._index_map.get(date)
        if idx is not None:
            return to_decimal(self._values[idx])
        else:
            return None

    def add_record(self, *args, **kwargs) -> None:
        """
        Add record to database.
        """
        current_time = self.get_current_time()
        if current_time is None:
            return
        date = current_time.strftime("%Y-%m-%d %H:%M:%S")
        if date not in self.data["timestamp"].values:
            return
        value = self.get_data(date)
        if value is not None:
            analyzer_crud = container.cruds.analyzer_record()
            analyzer_crud.create(
                portfolio_id=self._portfolio_id,
                engine_id=self._engine_id,
                timestamp=date,
                value=value,
                name=self.name,
                analyzer_id=self._analyzer_id,
                source=SOURCE_TYPES.OTHER,
            )

    @property
    def mean(self) -> Decimal:
        if self._size == 0:
            return Decimal("0.0")
        mean = np.mean(self._values[:self._size])
        return to_decimal(mean)

    @property
    def variance(self) -> Decimal:
        if self._size == 0:
            return Decimal("0.0")
        var = np.var(self._values[:self._size], ddof=1)  # 样本方差
        return to_decimal(var)

    @property
    def current_value(self) -> float:
        """当前值（通用只读属性）- 返回最新的分析器数值"""
        if self._size > 0:
            return float(self._values[self._size - 1])
        return 0.0
    
    def _resize(self):
        """动态扩容"""
        new_capacity = self._capacity * 2
        new_timestamps = np.empty(new_capacity, dtype='datetime64[ns]')
        new_values = np.empty(new_capacity, dtype=np.float64)
        
        # 复制现有数据
        new_timestamps[:self._size] = self._timestamps[:self._size]
        new_values[:self._size] = self._values[:self._size]
        
        self._timestamps = new_timestamps
        self._values = new_values
        self._capacity = new_capacity
    
    def _handle_error(self, method, stage, error, context):
        """内部错误处理方法"""
        self._error_count += 1
        self._last_error = error
        
        error_record = {
            'method': method,
            'stage': stage.name if hasattr(stage, 'name') else str(stage),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': clock_now(),
            'context_keys': list(context.keys()) if isinstance(context, dict) else str(type(context))
        }
        self._error_log.append(error_record)
        
        # 详细错误日志
        self.log("ERROR", f"Error in {method} at stage {stage}: {error}")
    
    def _record_performance(self, method, stage, duration):
        """记录性能数据"""
        # 实例统计
        key = f"{self.name}_{method}_{stage}"
        if key not in BaseAnalyzer._execution_stats:
            BaseAnalyzer._execution_stats[key] = []
        BaseAnalyzer._execution_stats[key].append(duration)
        
        # 详细记录
        BaseAnalyzer._performance_log.append({
            'analyzer': self.name,
            'uuid': self.uuid,
            'method': method,
            'stage': stage,
            'duration': duration,
            'timestamp': clock_now()
        })
    
    @property
    def error_summary(self):
        """获取错误摘要"""
        return {
            'total_errors': self._error_count,
            'last_error': str(self._last_error) if self._last_error else None,
            'recent_errors': self._error_log[-5:] if self._error_log else []
        }
    
    @property
    def performance_summary(self):
        """获取性能摘要"""
        avg_activation_time = (self._total_activation_time / self._activation_count 
                             if self._activation_count > 0 else 0)
        avg_record_time = (self._total_record_time / self._record_count 
                          if self._record_count > 0 else 0)
        
        return {
            'activation_count': self._activation_count,
            'record_count': self._record_count,
            'avg_activation_time': avg_activation_time,
            'avg_record_time': avg_record_time,
            'total_time': self._total_activation_time + self._total_record_time
        }
    
    @classmethod
    def get_global_performance_report(cls):
        """获取全局性能报告"""
        report = {}
        for key, durations in cls._execution_stats.items():
            report[key] = {
                'call_count': len(durations),
                'avg_duration': np.mean(durations),
                'max_duration': np.max(durations),
                'min_duration': np.min(durations),
                'total_duration': np.sum(durations)
            }
        return report
    
    @classmethod
    def export_performance_log(cls, filepath):
        """导出详细性能日志"""
        with open(filepath, 'w') as f:
            json.dump(cls._performance_log, f, indent=2, default=str)
