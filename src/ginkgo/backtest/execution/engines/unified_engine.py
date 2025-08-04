"""
统一回测引擎 - 支持事件驱动和矩阵两种回测模式
"""

import datetime
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import pandas as pd

from ginkgo.libs import GLOG
from ginkgo.backtest.core.base import Base
from ginkgo.backtest.execution.engines.base_engine import BaseEngine
from ginkgo.backtest.execution.engines.historic_engine import HistoricEngine
from ginkgo.backtest.execution.engines.matrix_engine import MatrixEngine
from ginkgo.backtest.execution.engines.enhanced_historic_engine import EnhancedHistoricEngine
from ginkgo.backtest.execution.engines.config.backtest_config import BacktestConfig, EngineMode
from ginkgo.core.interfaces.engine_interface import EngineInterface
from ginkgo.enums import SOURCE_TYPES, ENGINE_TYPES
from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio
from ginkgo.backtest.strategy.strategies.base_strategy import BaseStrategy


# 使用新的配置系统
BacktestMode = EngineMode


class ModeSelector:
    """智能模式选择器"""
    
    def __init__(self):
        self._performance_cache = {}
    
    def select_optimal_mode(
        self, 
        strategy: BaseStrategy,
        data_size: int,
        config: BacktestConfig
    ) -> EngineMode:
        """选择最优回测模式"""
        
        if config.engine_mode != EngineMode.AUTO:
            return config.engine_mode
            
        # 估算内存使用
        estimated_memory = config.estimate_memory_usage()
        
        # 基于策略特征选择模式
        if hasattr(strategy, 'cal_vectorized') and callable(getattr(strategy, 'cal_vectorized')):
            # 策略支持向量化，优先使用矩阵模式
            if data_size > config.hybrid_engine_config.get('auto_switch_threshold', 10000):
                GLOG.INFO(f"选择矩阵模式：策略支持向量化且数据量大 ({data_size})")
                return EngineMode.MATRIX
        
        # 检查策略是否需要逐个事件处理
        if hasattr(strategy, '_requires_event_order'):
            GLOG.INFO("选择事件驱动模式：策略需要逐个事件处理")
            return EngineMode.EVENT_DRIVEN
            
        # 基于数据量和内存使用选择
        if estimated_memory < 100:  # 小于100MB
            return EngineMode.EVENT_DRIVEN
        elif estimated_memory > 1000:  # 大于1GB
            return EngineMode.MATRIX
        else:
            return EngineMode.HYBRID
    
    def should_switch_mode(
        self, 
        current_mode: EngineMode,
        performance_metrics: Dict[str, float]
    ) -> Optional[EngineMode]:
        """基于性能指标判断是否应该切换模式"""
        
        memory_usage = performance_metrics.get('memory_usage_mb', 0)
        processing_speed = performance_metrics.get('bars_per_second', 0)
        
        if current_mode == EngineMode.EVENT_DRIVEN:
            if memory_usage < 100 and processing_speed < 100:
                GLOG.INFO("建议切换到矩阵模式以提高性能")
                return EngineMode.MATRIX
                
        elif current_mode == EngineMode.MATRIX:
            if memory_usage > 1000:  # 内存使用过高
                GLOG.INFO("建议切换到事件驱动模式以节省内存")
                return EngineMode.EVENT_DRIVEN
                
        return None


class StrategyAdapter:
    """策略适配器 - 在不同模式间转换策略"""
    
    @staticmethod
    def adapt_for_event_mode(strategy: BaseStrategy) -> BaseStrategy:
        """为事件驱动模式适配策略"""
        if not hasattr(strategy, 'cal'):
            raise ValueError("策略必须实现 cal() 方法用于事件驱动模式")
        return strategy
    
    @staticmethod
    def adapt_for_matrix_mode(strategy: BaseStrategy) -> BaseStrategy:
        """为矩阵模式适配策略"""
        if hasattr(strategy, 'cal_vectorized'):
            return strategy
            
        # 为不支持向量化的策略创建适配器
        class VectorizedAdapter(strategy.__class__):
            def cal_vectorized(self, data: pd.DataFrame) -> pd.DataFrame:
                """将逐行策略转换为向量化处理"""
                signals = []
                for _, row in data.iterrows():
                    # 设置策略状态
                    self._current_bar = row
                    signal_list = self.cal()
                    if signal_list:
                        for signal in signal_list:
                            signals.append({
                                'timestamp': row['timestamp'],
                                'code': signal.code,
                                'direction': signal.direction,
                                'reason': signal.reason
                            })
                
                return pd.DataFrame(signals)
        
        adapted_strategy = VectorizedAdapter()
        # 复制原策略的属性
        for attr in dir(strategy):
            if not attr.startswith('_') and not callable(getattr(strategy, attr)):
                setattr(adapted_strategy, attr, getattr(strategy, attr))
                
        return adapted_strategy


class UnifiedBacktestEngine(EngineInterface):
    """统一回测引擎 - 支持事件驱动和矩阵两种模式"""
    
    def __init__(self, name: str = "UnifiedBacktestEngine", config: BacktestConfig = None, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.config = config or BacktestConfig()
        self.mode_selector = ModeSelector()
        self.strategy_adapter = StrategyAdapter()
        
        # 初始化子引擎
        self.event_engine = None
        self.matrix_engine = None
        self.current_mode = None
        
        # 性能监控
        self.performance_metrics = {}
        self.start_time = None
        
    def _initialize_engines(self):
        """初始化子引擎"""
        # 获取配置
        event_engine_config = self.config.get_engine_config(EngineMode.EVENT_DRIVEN)
        matrix_engine_config = self.config.get_engine_config(EngineMode.MATRIX)
        
        # 创建增强历史引擎作为事件驱动引擎
        self.event_engine = EnhancedHistoricEngine(
            name=f"{self.name}_EventDriven",
            enable_caching=event_engine_config.get('enable_event_cache', True),
            enable_batching=event_engine_config.get('enable_batch_processing', True),
            batch_size=event_engine_config.get('batch_size', 100),
            cache_size=event_engine_config.get('cache_size', 1000),
            memory_limit_mb=event_engine_config.get('memory_limit_mb', 1000)
        )
        self.event_engine.set_config(self.config)
        
        # 创建矩阵引擎
        self.matrix_engine = MatrixEngine(name=f"{self.name}_Matrix")
        if hasattr(self.matrix_engine, 'set_config'):
            self.matrix_engine.set_config(matrix_engine_config)
        
    def add_portfolio(self, portfolio):
        """添加投资组合"""
        if not self.event_engine:
            self._initialize_engines()
        self.event_engine.add_portfolio(portfolio)
        self.matrix_engine.add_portfolio(portfolio)
    
    def add_strategy(self, strategy):
        """添加策略"""
        if not self.event_engine:
            self._initialize_engines()
        self.event_engine.add_strategy(strategy)
        self.matrix_engine.add_strategy(strategy)
    
    def add_feeder(self, feeder):
        """添加数据供给器"""
        if not self.event_engine:
            self._initialize_engines()
        self.event_engine.add_feeder(feeder)
        self.matrix_engine.add_feeder(feeder)
    
    def start(self):
        """启动引擎"""
        if not self.event_engine:
            self._initialize_engines()
        
        # 选择初始模式
        strategy = None
        if hasattr(self.event_engine, 'portfolios') and self.event_engine.portfolios:
            portfolio = self.event_engine.portfolios[0]
            strategy = portfolio.strategies[0] if portfolio.strategies else None
        
        if strategy:
            data_size = self._estimate_data_size()
            selected_mode = self.mode_selector.select_optimal_mode(
                strategy, data_size, self.config
            )
            self.current_mode = selected_mode
            GLOG.INFO(f"统一引擎启动，选择模式: {selected_mode.value}")
            
            # 启动对应的引擎
            if selected_mode == EngineMode.EVENT_DRIVEN:
                self.event_engine.start()
            elif selected_mode == EngineMode.MATRIX:
                self.matrix_engine.start()
            elif selected_mode == EngineMode.HYBRID:
                self._run_hybrid_mode()
        else:
            GLOG.WARN("没有策略，默认启动事件驱动引擎")
            self.event_engine.start()
    
    def stop(self):
        """停止引擎"""
        if self.event_engine:
            self.event_engine.stop()
        if self.matrix_engine:
            self.matrix_engine.stop()
        GLOG.INFO("统一引擎已停止")
    
    def get_result(self) -> Dict[str, Any]:
        """获取回测结果"""
        if self.current_mode == EngineMode.EVENT_DRIVEN and self.event_engine:
            return self.event_engine.get_result()
        elif self.current_mode == EngineMode.MATRIX and self.matrix_engine:
            return self.matrix_engine.get_result()
        else:
            return {}
    
    def run(self, portfolio: BasePortfolio) -> Dict[str, Any]:
        """运行回测（兼容旧接口）"""
        self.start_time = datetime.datetime.now()
        
        try:
            # 添加投资组合
            self.add_portfolio(portfolio)
            
            # 选择最优模式
            strategy = portfolio.strategies[0] if portfolio.strategies else None
            if not strategy:
                raise ValueError("投资组合必须包含至少一个策略")
                
            data_size = self._estimate_data_size()
            selected_mode = self.mode_selector.select_optimal_mode(
                strategy, data_size, self.config
            )
            
            GLOG.INFO(f"选择回测模式: {selected_mode.value}")
            
            # 运行回测
            result = self._execute_backtest(portfolio, selected_mode)
            
            # 性能统计
            self._update_performance_metrics()
            result['performance_metrics'] = self.performance_metrics
            result['backtest_mode'] = selected_mode.value
            
            return result
            
        except Exception as e:
            GLOG.ERROR(f"回测运行失败: {e}")
            raise
    
    def _estimate_data_size(self) -> int:
        """估算回测数据量"""
        # 简单估算：基于日期范围和股票数量
        start = pd.to_datetime(self.config.start_date)
        end = pd.to_datetime(self.config.end_date)
        days = (end - start).days
        
        # 假设平均每个交易日240根分钟K线
        estimated_bars = days * 240
        
        GLOG.DEBUG(f"估算数据量: {estimated_bars} 根K线")
        return estimated_bars
    
    def _execute_backtest(
        self, 
        portfolio: BasePortfolio, 
        mode: EngineMode
    ) -> Dict[str, Any]:
        """执行回测"""
        
        self.current_mode = mode
        self._initialize_engines()
        
        if mode == EngineMode.EVENT_DRIVEN:
            return self._run_event_driven(portfolio)
        elif mode == EngineMode.MATRIX:
            return self._run_matrix(portfolio)
        elif mode == EngineMode.HYBRID:
            return self._run_hybrid(portfolio)
        else:
            raise ValueError(f"不支持的回测模式: {mode}")
    
    def _run_hybrid_mode(self):
        """运行混合模式"""
        GLOG.INFO("启动混合模式")
        # 简化实现：先启动事件驱动引擎，后续可根据性能动态切换
        self.event_engine.start()
    
    def _run_event_driven(self, portfolio: BasePortfolio) -> Dict[str, Any]:
        """运行事件驱动回测"""
        GLOG.INFO("开始事件驱动回测")
        
        # 适配策略
        adapted_portfolio = self._adapt_portfolio_for_event_mode(portfolio)
        
        # 配置事件引擎
        self.event_engine.set_config(self.config)
        
        # 运行回测
        result = self.event_engine.run(adapted_portfolio)
        
        GLOG.INFO("事件驱动回测完成")
        return result
    
    def _run_matrix(self, portfolio: BasePortfolio) -> Dict[str, Any]:
        """运行矩阵回测"""
        GLOG.INFO("开始矩阵回测")
        
        # 适配策略
        adapted_portfolio = self._adapt_portfolio_for_matrix_mode(portfolio)
        
        # 配置矩阵引擎
        self.matrix_engine.set_config(self.config)
        
        # 运行回测
        result = self.matrix_engine.run(adapted_portfolio)
        
        GLOG.INFO("矩阵回测完成")  
        return result
    
    def _run_hybrid(self, portfolio: BasePortfolio) -> Dict[str, Any]:
        """运行混合模式回测"""
        GLOG.INFO("开始混合模式回测")
        
        # 混合模式：根据实时性能动态切换
        current_mode = EngineMode.EVENT_DRIVEN
        results = []
        
        # 分段回测，每段后评估性能
        segment_size = 5000  # 每5000根K线评估一次
        
        for segment_start in range(0, self._estimate_data_size(), segment_size):
            segment_end = min(segment_start + segment_size, self._estimate_data_size())
            
            # 运行当前段
            if current_mode == EngineMode.EVENT_DRIVEN:
                segment_result = self._run_event_driven(portfolio)
            else:
                segment_result = self._run_matrix(portfolio)
            
            results.append(segment_result)
            
            # 评估性能并决定是否切换模式
            self._update_performance_metrics()
            recommended_mode = self.mode_selector.should_switch_mode(
                current_mode, self.performance_metrics
            )
            
            if recommended_mode and recommended_mode != current_mode:
                GLOG.INFO(f"切换回测模式: {current_mode.value} -> {recommended_mode.value}")
                current_mode = recommended_mode
        
        # 合并结果
        final_result = self._merge_segment_results(results)
        GLOG.INFO("混合模式回测完成")
        
        return final_result
    
    def _adapt_portfolio_for_event_mode(self, portfolio: BasePortfolio) -> BasePortfolio:
        """为事件驱动模式适配投资组合"""
        adapted_portfolio = BasePortfolio()
        
        # 复制基本属性
        adapted_portfolio._uuid = portfolio._uuid
        adapted_portfolio._analyzers = portfolio._analyzers
        adapted_portfolio._sizers = portfolio._sizers
        adapted_portfolio._selectors = portfolio._selectors
        
        # 适配策略
        adapted_strategies = []
        for strategy in portfolio.strategies:
            adapted_strategy = self.strategy_adapter.adapt_for_event_mode(strategy)
            adapted_strategies.append(adapted_strategy)
        
        adapted_portfolio._strategies = adapted_strategies
        return adapted_portfolio
    
    def _adapt_portfolio_for_matrix_mode(self, portfolio: BasePortfolio) -> BasePortfolio:
        """为矩阵模式适配投资组合"""
        adapted_portfolio = BasePortfolio()
        
        # 复制基本属性
        adapted_portfolio._uuid = portfolio._uuid
        adapted_portfolio._analyzers = portfolio._analyzers
        adapted_portfolio._sizers = portfolio._sizers
        adapted_portfolio._selectors = portfolio._selectors
        
        # 适配策略
        adapted_strategies = []
        for strategy in portfolio.strategies:
            adapted_strategy = self.strategy_adapter.adapt_for_matrix_mode(strategy)
            adapted_strategies.append(adapted_strategy)
        
        adapted_portfolio._strategies = adapted_strategies
        return adapted_portfolio
    
    def _update_performance_metrics(self):
        """更新性能指标"""
        if self.start_time:
            elapsed = (datetime.datetime.now() - self.start_time).total_seconds()
            
            # 估算处理速度
            estimated_bars = self._estimate_data_size()
            bars_per_second = estimated_bars / elapsed if elapsed > 0 else 0
            
            self.performance_metrics.update({
                'elapsed_seconds': elapsed,
                'bars_per_second': bars_per_second,
                'memory_usage_mb': self._get_memory_usage()
            })
    
    def _get_memory_usage(self) -> float:
        """获取内存使用量 (MB)"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0
    
    def _merge_segment_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """合并分段回测结果"""
        if not results:
            return {}
        
        # 简单合并逻辑 - 实际实现需要更复杂的合并策略
        merged_result = results[0].copy()
        
        # 合并性能指标
        total_elapsed = sum(r.get('performance_metrics', {}).get('elapsed_seconds', 0) 
                          for r in results)
        merged_result['performance_metrics']['total_elapsed_seconds'] = total_elapsed
        merged_result['segments_count'] = len(results)
        
        return merged_result
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        current_engine_type = type(self._current_engine).__name__ if hasattr(self, '_current_engine') and self._current_engine else 'None'
        
        return {
            'engine_type': current_engine_type,
            'unified_engine_mode': self.current_mode.value if self.current_mode else 'None',
            'config': self.config.to_dict(),
            'performance_metrics': self.performance_metrics
        }
    
    def set_config(self, config):
        """设置配置"""
        self.config = config
        # 如果引擎已初始化，更新配置
        if self.event_engine and hasattr(self.event_engine, 'set_config'):
            self.event_engine.set_config(config)
        if self.matrix_engine and hasattr(self.matrix_engine, 'set_config'):
            matrix_config = config.get_engine_config(EngineMode.MATRIX)
            self.matrix_engine.set_config(matrix_config)
    
    def optimize_for_large_dataset(self):
        """为大数据集优化"""
        self.config.optimize_for_large_dataset()
        self.config.engine_mode = EngineMode.MATRIX
        GLOG.INFO("统一引擎已优化为大数据集模式")
    
    def optimize_for_realtime(self):
        """为实时处理优化"""
        self.config.optimize_for_realtime()
        self.config.engine_mode = EngineMode.EVENT_DRIVEN
        GLOG.INFO("统一引擎已优化为实时处理模式")