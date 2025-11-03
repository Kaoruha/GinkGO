"""
StrategyDataMixin - 策略数据混入类

提供策略专用的数据访问功能，基于现有的data_feeder机制，
提供简单的缓存和pandas序列转换功能。

主要功能：
1. 基于data_feeder的缓存数据访问
2. 价格序列转换为pandas Series
3. 简单的缓存管理和统计
4. 当前价格快速获取

使用示例：
    class MyStrategy(BaseStrategy, StrategyDataMixin):
        def cal(self, portfolio_info, event):
            # 获取缓存的K线数据
            bars = self.get_bars_cached(event.symbol, count=50)

            # 转换为pandas序列便于计算
            close_prices = self.get_price_series(event.symbol, count=50)

            # 策略自己计算技术指标
            ma20 = close_prices.rolling(20).mean()
            ma5 = close_prices.rolling(5).mean()

            # 策略逻辑...
            return signals
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pandas as pd
from ginkgo.libs import GLOG


class StrategyDataMixin:
    """策略数据混入类"""

    def __init__(self):
        """初始化数据混入功能"""
        if not hasattr(self, '_strategy_data_initialized'):
            self._strategy_data_initialized = True
            self._init_strategy_data()

    def _init_strategy_data(self):
        """初始化数据功能内部状态"""
        # 数据缓存
        self._data_cache: Dict[str, Any] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl: timedelta = timedelta(minutes=5)

        # 数据统计
        self._data_stats: Dict[str, Any] = {
            'cache_hits': 0,
            'cache_misses': 0,
            'data_errors': 0
        }

    def get_bars_cached(self, symbol: str, count: int = 100, frequency: str = '1d',
                       start_date: Optional[datetime] = None, end_date: Optional[datetime] = None,
                       use_cache: bool = True) -> List[Any]:
        """
        获取缓存的K线数据 (Get Cached Bar Data)

        Args:
            symbol: 股票代码
            count: 数据条数
            frequency: 数据频率
            start_date: 开始日期
            end_date: 结束日期
            use_cache: 是否使用缓存

        Returns:
            List[Bar]: K线数据列表，失败时返回空列表
        """
        cache_key = f"bars_{symbol}_{count}_{frequency}_{start_date}_{end_date}"

        # 检查缓存
        if use_cache and self._is_cache_valid(cache_key):
            self._data_stats['cache_hits'] += 1
            return self._data_cache[cache_key]

        # 从data_feeder获取数据
        try:
            if hasattr(self, 'data_feeder') and self.data_feeder:
                bars = self.data_feeder.get_bars(
                    symbol=symbol,
                    count=count,
                    frequency=frequency,
                    start_date=start_date,
                    end_date=end_date
                )
            else:
                # data_feeder不存在时返回空列表
                return []

            # 缓存结果
            if use_cache and bars:
                self._cache_data(cache_key, bars)

            self._data_stats['cache_misses'] += 1
            return bars

        except Exception as e:
            self._data_stats['data_errors'] += 1
            GLOG.error(f"{self._get_name()}: 获取K线数据失败 {symbol}: {e}")
            return []

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        获取当前价格 (Get Current Price)

        Args:
            symbol: 股票代码

        Returns:
            Optional[float]: 当前价格，失败返回None
        """
        try:
            bars = self.get_bars_cached(symbol, count=1)
            if bars and hasattr(bars[0], 'close'):
                return bars[0].close
            return None
        except Exception as e:
            GLOG.error(f"{self._get_name()}: 获取当前价格失败 {symbol}: {e}")
            return None

    def get_price_series(self, symbol: str, count: int = 100, field: str = 'close',
                        frequency: str = '1d') -> pd.Series:
        """
        获取价格序列 (Get Price Series)

        Args:
            symbol: 股票代码
            count: 数据条数
            field: 价格字段 ('open', 'high', 'low', 'close')
            frequency: 数据频率

        Returns:
            pd.Series: 价格序列，失败时返回空Series
        """
        try:
            bars = self.get_bars_cached(symbol, count=count, frequency=frequency)
            if not bars:
                return pd.Series()

            # 提取价格数据
            prices = []
            timestamps = []

            for bar in bars:
                if hasattr(bar, field):
                    prices.append(getattr(bar, field))
                    timestamps.append(bar.timestamp)

            if not prices:
                return pd.Series()

            # 创建pandas Series
            series = pd.Series(prices, index=pd.to_datetime(timestamps))
            series.index.name = 'timestamp'
            series.name = f'{symbol}_{field}'

            return series.sort_index()

        except Exception as e:
            GLOG.error(f"{self._get_name()}: 获取价格序列失败 {symbol}: {e}")
            return pd.Series()

    def get_ohlcv_data(self, symbol: str, count: int = 100, frequency: str = '1d') -> pd.DataFrame:
        """
        获取OHLCV数据框 (Get OHLCV DataFrame)

        Args:
            symbol: 股票代码
            count: 数据条数
            frequency: 数据频率

        Returns:
            pd.DataFrame: OHLCV数据，失败时返回空DataFrame
        """
        try:
            bars = self.get_bars_cached(symbol, count=count, frequency=frequency)
            if not bars:
                return pd.DataFrame()

            # 转换为DataFrame
            data = []
            for bar in bars:
                data.append({
                    'open': getattr(bar, 'open', 0),
                    'high': getattr(bar, 'high', 0),
                    'low': getattr(bar, 'low', 0),
                    'close': getattr(bar, 'close', 0),
                    'volume': getattr(bar, 'volume', 0),
                    'timestamp': bar.timestamp
                })

            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)

            return df.sort_index()

        except Exception as e:
            GLOG.error(f"{self._get_name()}: 获取OHLCV数据失败 {symbol}: {e}")
            return pd.DataFrame()

    # ========== 缓存管理 ==========

    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        if key not in self._data_cache:
            return False
        if key not in self._cache_timestamps:
            return False
        age = datetime.now() - self._cache_timestamps[key]
        return age < self._cache_ttl

    def _cache_data(self, key: str, data: Any) -> None:
        """缓存数据"""
        self._data_cache[key] = data
        self._cache_timestamps[key] = datetime.now()

    def clear_data_cache(self, pattern: Optional[str] = None) -> None:
        """
        清理数据缓存 (Clear Data Cache)

        Args:
            pattern: 缓存键模式，为None时清理所有
        """
        if pattern:
            keys_to_remove = [k for k in self._data_cache.keys() if pattern in k]
            for key in keys_to_remove:
                self._data_cache.pop(key, None)
                self._cache_timestamps.pop(key, None)
            GLOG.debug(f"{self._get_name()}: 清理缓存模式 '{pattern}': {len(keys_to_remove)}项")
        else:
            cache_count = len(self._data_cache)
            self._data_cache.clear()
            self._cache_timestamps.clear()
            GLOG.debug(f"{self._get_name()}: 清理所有数据缓存: {cache_count}项")

    def set_cache_ttl(self, minutes: int) -> None:
        """
        设置缓存TTL (Set Cache TTL)

        Args:
            minutes: 缓存有效时间（分钟）
        """
        self._cache_ttl = timedelta(minutes=minutes)
        GLOG.debug(f"{self._get_name()}: 缓存TTL设置为 {minutes} 分钟")

    # ========== 统计和工具方法 ==========

    def get_data_statistics(self) -> Dict[str, Any]:
        """
        获取数据统计信息 (Get Data Statistics)

        Returns:
            Dict[str, Any]: 数据统计
        """
        total_requests = self._data_stats['cache_hits'] + self._data_stats['cache_misses']
        cache_hit_rate = self._data_stats['cache_hits'] / max(total_requests, 1)

        return {
            'cache_hit_rate': round(cache_hit_rate, 3),
            'total_requests': total_requests,
            'cache_hits': self._data_stats['cache_hits'],
            'cache_misses': self._data_stats['cache_misses'],
            'data_errors': self._data_stats['data_errors'],
            'cache_size': len(self._data_cache),
            'cache_ttl_minutes': int(self._cache_ttl.total_seconds() / 60)
        }

    def reset_data_statistics(self) -> None:
        """重置数据统计"""
        self._data_stats = {
            'cache_hits': 0,
            'cache_misses': 0,
            'data_errors': 0
        }

    def _get_name(self) -> str:
        """获取组件名称"""
        return getattr(self, 'name', self.__class__.__name__)