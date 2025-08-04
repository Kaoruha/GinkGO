"""
增强版矩阵回测引擎 - 支持高性能向量化处理和并行计算
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing as mp
from functools import partial
import gc
import psutil

from ginkgo.backtest.execution.engines.matrix_engine import MatrixEngine
from ginkgo.backtest.execution.engines.base_engine import BaseEngine
from ginkgo.data.containers import container
from ginkgo.libs import GLOG
from ginkgo.backtest.strategy.selectors.base_selector import SelectorBase
from ginkgo.backtest.strategy.strategies.base_strategy import StrategyBase
from ginkgo.backtest.strategy.risk_managements.base_risk import RiskManagementBase
from ginkgo.backtest.strategy.sizers.base_sizer import SizerBase
from ginkgo.backtest.execution.portfolios.base_portfolio import PortfolioBase


@dataclass
class MatrixEngineConfig:
    """矩阵引擎配置"""
    chunk_size: int = 1000  # 数据分块大小
    parallel_workers: int = mp.cpu_count()  # 并行工作进程数
    memory_limit_gb: float = 4.0  # 内存限制 (GB)
    enable_gpu_acceleration: bool = False  # GPU加速
    cache_intermediate_results: bool = True  # 缓存中间结果
    optimize_memory_usage: bool = True  # 内存优化
    enable_progress_tracking: bool = True  # 进度跟踪


class DataChunker:
    """数据分块器 - 将大数据集分块处理以节省内存"""
    
    def __init__(self, chunk_size: int = 1000):
        self.chunk_size = chunk_size
    
    def chunk_by_time(self, data: Dict[str, pd.DataFrame]) -> List[Dict[str, pd.DataFrame]]:
        """按时间分块"""
        if not data or 'close' not in data:
            return []
        
        total_rows = len(data['close'])
        chunks = []
        
        for start_idx in range(0, total_rows, self.chunk_size):
            end_idx = min(start_idx + self.chunk_size, total_rows)
            
            chunk = {}
            for key, df in data.items():
                chunk[key] = df.iloc[start_idx:end_idx].copy()
            
            chunks.append(chunk)
        
        GLOG.INFO(f"数据分为 {len(chunks)} 个时间块，每块最多 {self.chunk_size} 行")
        return chunks
    
    def chunk_by_symbols(self, data: Dict[str, pd.DataFrame], symbols_per_chunk: int = 100) -> List[Dict[str, pd.DataFrame]]:
        """按股票代码分块"""
        if not data or 'close' not in data:
            return []
        
        all_symbols = data['close'].columns.tolist()
        chunks = []
        
        for i in range(0, len(all_symbols), symbols_per_chunk):
            chunk_symbols = all_symbols[i:i + symbols_per_chunk]
            
            chunk = {}
            for key, df in data.items():
                chunk[key] = df[chunk_symbols].copy()
            
            chunks.append(chunk)
        
        GLOG.INFO(f"数据分为 {len(chunks)} 个股票块，每块最多 {symbols_per_chunk} 只股票")
        return chunks


class VectorizedCalculator:
    """向量化计算器 - 提供高性能的向量化计算方法"""
    
    @staticmethod
    def fast_rolling_apply(data: pd.DataFrame, window: int, func: str, **kwargs) -> pd.DataFrame:
        """快速滚动计算"""
        if func == 'mean':
            return data.rolling(window=window, **kwargs).mean()
        elif func == 'std':
            return data.rolling(window=window, **kwargs).std()
        elif func == 'max':
            return data.rolling(window=window, **kwargs).max()
        elif func == 'min':
            return data.rolling(window=window, **kwargs).min()
        elif func == 'sum':
            return data.rolling(window=window, **kwargs).sum()
        else:
            return data.rolling(window=window, **kwargs).apply(func, **kwargs)
    
    @staticmethod
    def calculate_returns(prices: pd.DataFrame, method: str = 'pct_change') -> pd.DataFrame:
        """计算收益率"""
        if method == 'pct_change':
            return prices.pct_change()
        elif method == 'log_return':
            return np.log(prices / prices.shift(1))
        elif method == 'diff':
            return prices.diff()
        else:
            raise ValueError(f"不支持的收益率计算方法: {method}")
    
    @staticmethod
    def calculate_technical_indicators(data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """批量计算技术指标"""
        indicators = {}
        
        close = data['close']
        high = data['high']
        low = data['low']
        volume = data['volume']
        
        # 移动平均线
        indicators['ma5'] = close.rolling(5).mean()
        indicators['ma10'] = close.rolling(10).mean()
        indicators['ma20'] = close.rolling(20).mean()
        
        # 布林带
        ma20 = indicators['ma20']
        std20 = close.rolling(20).std()
        indicators['bb_upper'] = ma20 + 2 * std20
        indicators['bb_lower'] = ma20 - 2 * std20
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        indicators['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = close.ewm(span=12).mean()
        ema26 = close.ewm(span=26).mean()
        indicators['macd'] = ema12 - ema26
        indicators['macd_signal'] = indicators['macd'].ewm(span=9).mean()
        
        # ATR
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        indicators['atr'] = tr.rolling(14).mean()
        
        return indicators
    
    @staticmethod
    def optimize_dataframe_memory(df: pd.DataFrame) -> pd.DataFrame:
        """优化DataFrame内存使用"""
        for col in df.columns:
            if df[col].dtype == 'float64':
                df[col] = pd.to_numeric(df[col], downcast='float')
            elif df[col].dtype == 'int64':
                df[col] = pd.to_numeric(df[col], downcast='integer')
        
        return df


class ParallelProcessor:
    """并行处理器"""
    
    def __init__(self, max_workers: int = None):
        self.max_workers = max_workers or mp.cpu_count()
    
    def parallel_strategy_calculation(
        self, 
        strategies: List[StrategyBase], 
        data_chunks: List[Dict[str, pd.DataFrame]]
    ) -> List[pd.DataFrame]:
        """并行计算策略信号"""
        
        def calculate_strategy_chunk(strategy, chunk):
            """单个策略在单个数据块上的计算"""
            try:
                if hasattr(strategy, 'cal_vectorized'):
                    return strategy.cal_vectorized(chunk)
                else:
                    # 为不支持向量化的策略提供适配
                    return self._adapt_strategy_for_vectorization(strategy, chunk)
            except Exception as e:
                GLOG.ERROR(f"策略 {strategy.name} 计算失败: {e}")
                return pd.DataFrame()
        
        all_results = []
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 为每个策略和数据块的组合创建任务
            future_to_info = {}
            
            for strategy in strategies:
                for chunk_idx, chunk in enumerate(data_chunks):
                    future = executor.submit(calculate_strategy_chunk, strategy, chunk)
                    future_to_info[future] = (strategy.name, chunk_idx)
            
            # 收集结果
            for future in as_completed(future_to_info):
                strategy_name, chunk_idx = future_to_info[future]
                try:
                    result = future.result()
                    all_results.append({
                        'strategy': strategy_name,
                        'chunk_idx': chunk_idx,
                        'signals': result
                    })
                except Exception as e:
                    GLOG.ERROR(f"策略 {strategy_name} 块 {chunk_idx} 处理失败: {e}")
        
        return all_results
    
    def _adapt_strategy_for_vectorization(self, strategy: StrategyBase, data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """为不支持向量化的策略提供适配"""
        # 逐行处理策略
        signals = []
        close_data = data['close']
        
        for date in close_data.index:
            # 构造当前时间点的数据
            current_data = {}
            for key, df in data.items():
                if date in df.index:
                    current_data[key] = df.loc[date]
            
            # 调用策略的计算方法
            try:
                if hasattr(strategy, 'cal'):
                    strategy_signals = strategy.cal()  # 假设返回Signal列表
                    for signal in strategy_signals:
                        signals.append({
                            'date': date,
                            'code': signal.code,
                            'direction': signal.direction.value,
                            'weight': 1.0
                        })
            except Exception as e:
                continue
        
        # 转换为矩阵格式
        if signals:
            signal_df = pd.DataFrame(signals)
            return signal_df.pivot_table(
                index='date', 
                columns='code', 
                values='weight', 
                fill_value=0
            )
        else:
            return pd.DataFrame(index=close_data.index, columns=close_data.columns).fillna(0)


class EnhancedMatrixEngine(MatrixEngine):
    """增强版矩阵回测引擎"""
    
    def __init__(
        self, 
        name: str = "EnhancedMatrixEngine",
        config: MatrixEngineConfig = None,
        *args, 
        **kwargs
    ):
        super().__init__(name, *args, **kwargs)
        self.config = config or MatrixEngineConfig()
        
        # 初始化组件
        self.data_chunker = DataChunker(self.config.chunk_size)
        self.vectorized_calc = VectorizedCalculator()
        self.parallel_processor = ParallelProcessor(self.config.parallel_workers)
        
        # 缓存
        self.result_cache = {} if self.config.cache_intermediate_results else None
        
        # 性能监控
        self.performance_stats = {
            'data_loading_time': 0,
            'signal_calculation_time': 0,
            'simulation_time': 0,
            'memory_peak_mb': 0,
            'chunks_processed': 0
        }
    
    def set_config(self, config):
        """设置配置参数"""
        if hasattr(config, 'start_date'):
            self.start_date = config.start_date
        if hasattr(config, 'end_date'):
            self.end_date = config.end_date
        if hasattr(config, 'batch_size'):
            self.config.chunk_size = config.batch_size
        if hasattr(config, 'parallel_workers'):
            self.config.parallel_workers = config.parallel_workers
    
    def run(self, portfolio: PortfolioBase) -> Dict[str, Any]:
        """运行增强版矩阵回测"""
        GLOG.INFO(f"启动增强版矩阵回测引擎: {self.name}")
        
        start_time = datetime.now()
        
        try:
            # 从投资组合中提取参数
            strategies = portfolio.strategies
            selectors = portfolio.selectors
            risk_managements = getattr(portfolio, 'risk_managements', [])
            sizer = getattr(portfolio, 'sizer', None)
            
            # 1. 数据获取和预处理
            GLOG.INFO("开始数据获取和预处理...")
            data_start_time = datetime.now()
            
            all_data = self._fetch_and_prepare_data_enhanced(
                self.start_date, 
                self.end_date
            )
            
            if not all_data or all_data['close'].empty:
                raise ValueError("未找到回测数据")
            
            self.performance_stats['data_loading_time'] = (datetime.now() - data_start_time).total_seconds()
            
            # 2. 数据分块处理
            GLOG.INFO("开始数据分块...")
            data_chunks = self.data_chunker.chunk_by_time(all_data)
            self.performance_stats['chunks_processed'] = len(data_chunks)
            
            # 3. 并行信号计算
            GLOG.INFO("开始并行信号计算...")
            signal_start_time = datetime.now()
            
            all_signals = self._calculate_signals_parallel(strategies, data_chunks)
            
            self.performance_stats['signal_calculation_time'] = (datetime.now() - signal_start_time).total_seconds()
            
            # 4. 合并信号结果
            GLOG.INFO("合并信号结果...")
            combined_signals = self._combine_signal_results(all_signals, all_data)
            
            # 5. 应用选择器和风险管理
            GLOG.INFO("应用选择器和风险管理...")
            final_signals = self._apply_filters_enhanced(
                combined_signals, 
                selectors, 
                risk_managements, 
                all_data
            )
            
            # 6. 计算目标持仓
            GLOG.INFO("计算目标持仓...")
            target_positions = self._calculate_positions_enhanced(
                final_signals, 
                sizer, 
                all_data, 
                portfolio.initial_capital
            )
            
            # 7. 运行仿真
            GLOG.INFO("运行仿真...")
            sim_start_time = datetime.now()
            
            equity_curve, returns, trades = self._run_simulation_enhanced(
                target_positions, 
                all_data, 
                portfolio.initial_capital
            )
            
            self.performance_stats['simulation_time'] = (datetime.now() - sim_start_time).total_seconds()
            
            # 8. 性能分析
            GLOG.INFO("进行性能分析...")
            results = self._analyze_performance_enhanced(equity_curve, returns, trades)
            
            # 添加性能统计
            total_time = (datetime.now() - start_time).total_seconds()
            results['performance_stats'] = self.performance_stats
            results['performance_stats']['total_time'] = total_time
            results['performance_stats']['memory_peak_mb'] = self._get_peak_memory_usage()
            
            GLOG.INFO(f"增强版矩阵回测完成，耗时 {total_time:.2f} 秒")
            
            return results
            
        except Exception as e:
            GLOG.ERROR(f"增强版矩阵回测失败: {e}")
            raise
        finally:
            # 清理内存
            if self.config.optimize_memory_usage:
                gc.collect()
    
    def _fetch_and_prepare_data_enhanced(
        self, 
        start_date: str, 
        end_date: str
    ) -> Dict[str, pd.DataFrame]:
        """增强版数据获取和预处理"""
        
        # 检查缓存
        cache_key = f"data_{start_date}_{end_date}"
        if self.result_cache and cache_key in self.result_cache:
            GLOG.INFO("使用缓存的数据")
            return self.result_cache[cache_key]
        
        # 获取原始数据
        bar_crud = container.cruds.bar()
        raw_df = bar_crud.get_bar_df_by_time_range(start=start_date, end=end_date)
        
        if raw_df.empty:
            return {}
        
        # 数据清洗
        raw_df = self._clean_data(raw_df)
        
        # 向量化数据透视
        data_matrices = {}
        columns_to_pivot = ["open", "high", "low", "close", "volume"]
        
        for col in columns_to_pivot:
            try:
                # 使用更高效的pivot操作
                matrix = raw_df.pivot_table(
                    index="trade_date", 
                    columns="code", 
                    values=col,
                    aggfunc='last'  # 如果有重复，取最后一个值
                )
                
                matrix.index = pd.to_datetime(matrix.index)
                matrix = matrix.sort_index()
                
                # 内存优化
                if self.config.optimize_memory_usage:
                    matrix = self.vectorized_calc.optimize_dataframe_memory(matrix)
                
                data_matrices[col] = matrix
                
            except Exception as e:
                GLOG.ERROR(f"处理列 {col} 失败: {e}")
                return {}
        
        # 计算技术指标
        GLOG.INFO("计算技术指标...")
        technical_indicators = self.vectorized_calc.calculate_technical_indicators(data_matrices)
        data_matrices.update(technical_indicators)
        
        # 缓存结果
        if self.result_cache:
            self.result_cache[cache_key] = data_matrices
        
        return data_matrices
    
    def _clean_data(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗"""
        # 移除异常值
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in raw_df.columns:
                # 移除负值和零值（价格不能为负或零）
                if col != 'volume':
                    raw_df = raw_df[raw_df[col] > 0]
                
                # 移除极端异常值 (超过99.9%分位数的值)
                q99 = raw_df[col].quantile(0.999)
                q01 = raw_df[col].quantile(0.001)
                raw_df = raw_df[(raw_df[col] >= q01) & (raw_df[col] <= q99)]
        
        # 移除停牌数据（成交量为0的数据）
        raw_df = raw_df[raw_df['volume'] > 0]
        
        # 检查价格逻辑性 (high >= low, close在high和low之间)
        raw_df = raw_df[
            (raw_df['high'] >= raw_df['low']) &
            (raw_df['close'] >= raw_df['low']) &
            (raw_df['close'] <= raw_df['high'])
        ]
        
        return raw_df
    
    def _calculate_signals_parallel(
        self, 
        strategies: List[StrategyBase], 
        data_chunks: List[Dict[str, pd.DataFrame]]
    ) -> List[Dict[str, Any]]:
        """并行计算策略信号"""
        
        GLOG.INFO(f"使用 {self.config.parallel_workers} 个进程并行计算信号")
        
        return self.parallel_processor.parallel_strategy_calculation(strategies, data_chunks)
    
    def _combine_signal_results(
        self, 
        signal_results: List[Dict[str, Any]], 
        all_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """合并信号计算结果"""
        
        # 按策略分组
        strategy_signals = {}
        for result in signal_results:
            strategy_name = result['strategy']
            if strategy_name not in strategy_signals:
                strategy_signals[strategy_name] = []
            strategy_signals[strategy_name].append(result['signals'])
        
        # 合并每个策略的所有块
        combined_by_strategy = {}
        for strategy_name, signal_chunks in strategy_signals.items():
            if signal_chunks:
                # 按索引合并所有块
                combined_signals = pd.concat(signal_chunks, axis=0).sort_index()
                combined_by_strategy[strategy_name] = combined_signals
        
        # 聚合所有策略的信号
        if combined_by_strategy:
            all_strategy_signals = list(combined_by_strategy.values())
            # 简单平均聚合（可以改为其他聚合方法）
            final_signals = sum(all_strategy_signals) / len(all_strategy_signals)
        else:
            # 如果没有信号，返回全零信号
            final_signals = pd.DataFrame(
                0.0, 
                index=all_data['close'].index, 
                columns=all_data['close'].columns
            )
        
        return final_signals
    
    def _apply_filters_enhanced(
        self,
        signals: pd.DataFrame,
        selectors: List[SelectorBase],
        risk_managements: List[RiskManagementBase],
        all_data: Dict[str, pd.DataFrame]
    ) -> pd.DataFrame:
        """增强版过滤器应用"""
        
        filtered_signals = signals.copy()
        
        # 应用选择器
        for selector in selectors:
            if hasattr(selector, 'cal_vectorized'):
                universe_mask = selector.cal_vectorized(all_data)
                filtered_signals = filtered_signals * universe_mask.reindex_like(filtered_signals).fillna(0)
            else:
                GLOG.WARN(f"选择器 {selector.name} 不支持向量化，跳过")
        
        # 应用风险管理
        for risk_mgmt in risk_managements:
            if hasattr(risk_mgmt, 'filter_signals_vectorized'):
                filtered_signals = risk_mgmt.filter_signals_vectorized(filtered_signals, all_data)
            else:
                GLOG.WARN(f"风险管理 {risk_mgmt.name} 不支持向量化，跳过")
        
        return filtered_signals
    
    def _calculate_positions_enhanced(
        self,
        signals: pd.DataFrame,
        sizer: SizerBase,
        all_data: Dict[str, pd.DataFrame],
        initial_capital: float
    ) -> pd.DataFrame:
        """增强版持仓计算"""
        
        if sizer is None:
            # 默认等权重
            position_weights = signals / signals.abs().sum(axis=1, skipna=True).replace(0, 1).values[:, np.newaxis]
            position_weights = position_weights.fillna(0)
        elif hasattr(sizer, 'cal_vectorized'):
            position_weights = sizer.cal_vectorized(signals, all_data, initial_capital)
        else:
            # 为不支持向量化的sizer提供适配
            position_weights = self._adapt_sizer_for_vectorization(sizer, signals, all_data, initial_capital)
        
        return position_weights
    
    def _adapt_sizer_for_vectorization(
        self,
        sizer: SizerBase,
        signals: pd.DataFrame,
        all_data: Dict[str, pd.DataFrame],
        initial_capital: float
    ) -> pd.DataFrame:
        """为不支持向量化的sizer提供适配"""
        # 这里需要根据具体的sizer接口实现
        # 简化实现：等权重
        position_weights = signals / signals.abs().sum(axis=1, skipna=True).replace(0, 1).values[:, np.newaxis]
        return position_weights.fillna(0)
    
    def _run_simulation_enhanced(
        self,
        positions: pd.DataFrame,
        all_data: Dict[str, pd.DataFrame],
        initial_capital: float
    ) -> Tuple[pd.Series, pd.Series, pd.DataFrame]:
        """增强版回测仿真"""
        
        prices = all_data['close']
        returns = self.vectorized_calc.calculate_returns(prices)
        
        # 计算组合收益
        portfolio_returns = (positions.shift(1) * returns).sum(axis=1, skipna=True)
        
        # 计算权益曲线
        equity_curve = (1 + portfolio_returns).cumprod() * initial_capital
        
        # 生成交易记录
        position_changes = positions.diff().fillna(positions)
        trades = self._generate_trade_records(position_changes, prices)
        
        return equity_curve, portfolio_returns, trades
    
    def _generate_trade_records(self, position_changes: pd.DataFrame, prices: pd.DataFrame) -> pd.DataFrame:
        """生成交易记录"""
        trades = []
        
        for date in position_changes.index:
            for code in position_changes.columns:
                change = position_changes.loc[date, code]
                if abs(change) > 1e-6:  # 忽略极小的变化
                    trades.append({
                        'date': date,
                        'code': code,
                        'direction': 'BUY' if change > 0 else 'SELL',
                        'quantity': abs(change),
                        'price': prices.loc[date, code] if not pd.isna(prices.loc[date, code]) else 0
                    })
        
        return pd.DataFrame(trades)
    
    def _analyze_performance_enhanced(
        self, 
        equity_curve: pd.Series, 
        returns: pd.Series, 
        trades: pd.DataFrame
    ) -> Dict[str, Any]:
        """增强版性能分析"""
        
        results = {}
        
        # 基础指标
        results['total_return'] = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        results['annualized_return'] = results['total_return'] ** (252 / len(returns)) - 1
        results['volatility'] = returns.std() * np.sqrt(252)
        results['sharpe_ratio'] = results['annualized_return'] / results['volatility'] if results['volatility'] > 0 else 0
        
        # 最大回撤
        peak = equity_curve.expanding().max()
        drawdown = (equity_curve - peak) / peak
        results['max_drawdown'] = drawdown.min()
        
        # 交易统计
        if not trades.empty:
            results['total_trades'] = len(trades)
            results['avg_trades_per_day'] = len(trades) / len(returns)
        else:
            results['total_trades'] = 0
            results['avg_trades_per_day'] = 0
        
        # Calmar比率
        results['calmar_ratio'] = results['annualized_return'] / abs(results['max_drawdown']) if results['max_drawdown'] != 0 else 0
        
        return results
    
    def _get_peak_memory_usage(self) -> float:
        """获取峰值内存使用量 (MB)"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def get_performance_report(self) -> Dict[str, Any]:
        """获取性能报告"""
        return {
            'engine_name': self.name,
            'config': {
                'chunk_size': self.config.chunk_size,
                'parallel_workers': self.config.parallel_workers,
                'memory_limit_gb': self.config.memory_limit_gb,
                'cache_enabled': self.config.cache_intermediate_results,
                'memory_optimization': self.config.optimize_memory_usage
            },
            'performance_stats': self.performance_stats
        }