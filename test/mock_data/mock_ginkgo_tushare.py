"""
Mock GinkgoTushare数据源
用于测试时替代真实的Tushare数据源，所有方法都从预存的CSV文件读取数据
"""

import os
import pandas as pd
from typing import Optional, Any
from ginkgo.libs import datetime_normalize, GLOG
from rich.console import Console

console = Console()


class MockGinkgoTushare:
    """Mock Tushare数据源，模拟GinkgoTushare的所有方法，但从CSV文件读取数据"""

    def __init__(self, *args, **kwargs) -> None:
        self.pro = None  # Mock不需要真实连接
        self.mock_data_dir = "test/mock_data"
        self._data_cache = {}
        self._load_available_data()

    def _load_available_data(self):
        """预加载所有可用的Mock数据"""
        if not os.path.exists(self.mock_data_dir):
            print(f"⚠️ Mock数据目录不存在: {self.mock_data_dir}")
            return

        for filename in os.listdir(self.mock_data_dir):
            if filename.endswith('.csv'):
                print(f"📂 预加载Mock数据: {filename}")
                df = pd.read_csv(os.path.join(self.mock_data_dir, filename))
                self._data_cache[filename] = df
                print(f"   ✅ 加载了 {len(df)} 条记录")

    def connect(self, *args, **kwargs) -> None:
        """Mock连接方法"""
        print("🔌 Mock Tushare连接已建立（无需真实token）")

    def fetch_cn_stock_trade_day(self, *args, **kwargs) -> pd.DataFrame:
        """Mock获取交易日历"""
        print("📅 Mock交易日历数据")
        # 基于预存的Bar数据生成交易日历
        bar_files = [k for k in self._data_cache.keys() if 'bar_data' in k]
        if not bar_files:
            return pd.DataFrame()

        # 从第一个可用的bar数据中提取交易日
        bar_data = self._data_cache[bar_files[0]]
        if 'trade_date' in bar_data.columns:
            trade_dates = bar_data[['trade_date']].copy()
            trade_dates.columns = ['cal_date']
            # 生成cal_date对应的日期
            trade_dates['cal_date'] = pd.to_datetime(trade_dates['cal_date'], format='%Y%m%d')
            console.print(f":crab: Got {len(trade_dates)} records about trade day (mock).")
            return trade_dates

        return pd.DataFrame()

    def fetch_cn_stockinfo(self, *args, **kwargs) -> pd.DataFrame:
        """Mock获取股票基本信息"""
        print("📋 Mock股票基本信息")
        # 基于预存数据生成股票信息
        bar_files = [k for k in self._data_cache.keys() if 'bar_data' in k]
        if not bar_files:
            return pd.DataFrame()

        # 从预存数据中提取股票代码信息
        bar_data = self._data_cache[bar_files[0]]
        if 'ts_code' in bar_data.columns:
            codes = bar_data['ts_code'].unique()
            stock_info = pd.DataFrame({
                'ts_code': codes,
                'symbol': [code.split('.')[0] for code in codes],
                'name': [f'股票{code.split('.')[0]}' for code in codes],
                'area': ['深圳' if code.endswith('.SZ') else '上海' for code in codes],
                'market': ['主板' for _ in codes],
                'exchange': [code.split('.')[1] for code in codes],
                'list_status': ['L' for _ in codes],  # 上市状态
                'list_date': ['19910403' for _ in codes]  # 上市日期
            })
            console.print(f":crab: Got {len(stock_info)} records about stock info (mock).")
            return stock_info

        return pd.DataFrame()

    def fetch_cn_stock_daybar(
        self,
        code: str = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        *args,
        **kwargs
    ) -> pd.DataFrame:
        """
        Mock获取日线数据

        注意：Mock数据源只返回预存的数据，code参数被忽略
        """
        GLOG.DEBUG("Mock获取日线数据")

        # 检查是否有预存数据
        bar_files = [k for k in self._data_cache.keys() if 'bar_data' in k]
        if not bar_files:
            console.print("❌ Mock数据源没有可用的预存Bar数据")
            return pd.DataFrame()

        # 根据股票代码查找对应的数据文件
        df = pd.DataFrame()
        if code:
            # 将代码转换为文件名格式 (000001.SZ -> 000001_SZ)
            code_filename = code.replace('.', '_')
            target_file = f'bar_data_{code_filename}.csv'

            if target_file in self._data_cache:
                df = self._data_cache[target_file].copy()
                console.print(f":crab: Got {len(df)} records about {code} daybar (mock).")
            else:
                # 匹配真实TuShare的行为：对于不存在的代码返回空DataFrame
                console.print(f":crab: Got 0 records about {code} daybar (mock).")
                return pd.DataFrame()  # 返回空DataFrame，像真实TuShare一样

        # 如果没有指定代码，使用第一个可用的bar数据（保持向后兼容）
        if df.empty and code is None:
            bar_files = [k for k in self._data_cache.keys() if 'bar_data' in k]
            if not bar_files:
                console.print("❌ Mock数据源没有可用的预存Bar数据")
                return pd.DataFrame()
            df = self._data_cache[bar_files[0]].copy()
            console.print(f":crab: Got {len(df)} records about {df['ts_code'].iloc[0] if 'ts_code' in df.columns else 'unknown'} daybar (mock).")

        if df.empty:
            return df

        # 日期过滤
        if start_date is not None or end_date is not None:
            start_dt = datetime_normalize(start_date) if start_date else None
            end_dt = datetime_normalize(end_date) if end_date else None

            df['trade_date_dt'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')

            original_count = len(df)

            if start_dt is not None:
                df = df[df['trade_date_dt'] >= start_dt]

            if end_dt is not None:
                df = df[df['trade_date_dt'] <= end_dt]

            df = df.drop('trade_date_dt', axis=1)

            filtered_count = len(df)
            if filtered_count != original_count:
                print(f"📅 日期过滤: {original_count} -> {filtered_count} 条记录")

        return df

    def fetch_cn_stock_min(self, *args, **kwargs) -> pd.DataFrame:
        """Mock获取分钟线数据"""
        print("⏰ Mock分钟线数据（暂不支持）")
        return pd.DataFrame()

    def _calculate_optimal_window_size(self, total_days: int) -> int:
        """Mock计算最优窗口大小"""
        return min(500, total_days)

    def _calculate_daybar_window_size(self, total_days: int) -> int:
        """Mock计算日线数据窗口大小"""
        return min(800, total_days)

    def fetch_cn_stock_adjustfactor(
        self,
        code: str = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
        *args,
        **kwargs
    ) -> pd.DataFrame:
        """
        Mock获取复权因子数据

        注意：Mock数据源只返回预存的复权因子数据，code参数被忽略
        """
        print("🔄 Mock复权因子数据")

        # 检查是否有预存的复权因子数据
        adjustfactor_files = [k for k in self._data_cache.keys() if 'adjustfactor_data' in k]
        if not adjustfactor_files:
            print("⚠️ Mock数据源没有可用的预存复权因子数据")
            return pd.DataFrame()

        # 获取复权因子数据
        df = self._data_cache[adjustfactor_files[0]].copy()

        if df.empty:
            return df

        console.print(f":crab: Got {len(df)} records about adjustfactor (mock).")

        # 日期过滤
        if start_date is not None or end_date is not None:
            start_dt = datetime_normalize(start_date) if start_date else None
            end_dt = datetime_normalize(end_date) if end_date else None

            df['trade_date_dt'] = pd.to_datetime(df['trade_date'], format='%Y%m%d')

            original_count = len(df)

            if start_dt is not None:
                df = df[df['trade_date_dt'] >= start_dt]

            if end_dt is not None:
                df = df[df['trade_date_dt'] <= end_dt]

            df = df.drop('trade_date_dt', axis=1)

            filtered_count = len(df)
            if filtered_count != original_count:
                print(f"📅 复权因子日期过滤: {original_count} -> {filtered_count} 条记录")

        return df