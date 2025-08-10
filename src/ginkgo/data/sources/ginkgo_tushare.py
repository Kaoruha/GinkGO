import tushare as ts
import threading
import pandas as pd
from ...libs import datetime_normalize, GCONF, retry, time_logger, GLOG
from rich.console import Console
from .source_base import GinkgoSourceBase

console = Console()


class GinkgoTushare(GinkgoSourceBase):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.pro = None
        self.connect()

    def connect(self, *args, **kwargs) -> None:
        if self.pro == None:
            self.pro = ts.pro_api(GCONF.TUSHARETOKEN)

    @time_logger
    @retry(max_try=5)
    def fetch_cn_stock_trade_day(self, *args, **kwargs) -> pd.DataFrame:
        GLOG.DEBUG("Trying get cn stock trade day.")
        try:
            r = self.pro.trade_cal()
            if r.shape[0] == 0:
                return pd.DataFrame()
            console.print(f":crab: Got {r.shape[0]} records about trade day.")
            return r
        except Exception as e:
            raise e
        finally:
            pass

    @time_logger
    @retry(max_try=5)
    def fetch_cn_stockinfo(self, *args, **kwargs) -> pd.DataFrame:
        GLOG.DEBUG("Trying get cn stock info.")
        try:
            r = self.pro.stock_basic(
                fields=[
                    "ts_code",
                    "symbol",
                    "name",
                    "area",
                    "industry",
                    "list_date",
                    "curr_type",
                    "delist_date",
                ]
            )
            if r.shape[0] == 0:
                return pd.DataFrame()
            console.print(f":crab: Got {r.shape[0]} records about stockinfo.")
            return r
        except Exception as e:
            raise e
        finally:
            pass

    @time_logger
    @retry(max_try=5)
    def fetch_cn_stock_daybar(
        self, code: str, start_date: any = GCONF.DEFAULTSTART, end_date: any = GCONF.DEFAULTEND, *args, **kwargs
    ) -> pd.DataFrame:
        """
        获取日线数据，支持大日期跨度的分页获取

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            包含日线数据的DataFrame
        """
        import datetime

        start_dt = datetime_normalize(start_date)
        end_dt = datetime_normalize(end_date)

        # 计算日期跨度（天数）
        date_span = (end_dt - start_dt).days

        # 设置单次请求的最大天数（日线数据较密集，需要保守设置）
        # A股市场日线数据每个交易日都有，约250个交易日/年
        # 为避免超过API限制，设置较小的时间窗口
        max_days_per_request = self._calculate_daybar_window_size(date_span)

        all_data = []

        try:
            # 如果日期跨度较小，直接获取
            if date_span <= max_days_per_request:
                start_str = start_dt.strftime("%Y%m%d")
                end_str = end_dt.strftime("%Y%m%d")

                r = self.pro.daily(ts_code=code, start_date=start_str, end_date=end_str, limit="50000")
                if r.shape[0] > 0:
                    r.fillna(0, inplace=True)
                    all_data.append(r)
                    console.print(f":crab: Got {r.shape[0]} records about {code} daybar from {start_str} to {end_str}")
            else:
                # 分段获取
                GLOG.INFO(f"Large date span ({date_span} days) detected for {code}, using segmented fetch")

                # 预先计算总段数
                total_segments = 0
                temp_start = start_dt
                while temp_start < end_dt:
                    temp_end = min(temp_start + datetime.timedelta(days=max_days_per_request), end_dt)
                    total_segments += 1
                    temp_start = temp_end + datetime.timedelta(days=1)

                GLOG.INFO(f"Will fetch {total_segments} segments for {code}")

                current_start = start_dt
                segment_count = 0

                while current_start < end_dt:
                    # 计算当前段的结束日期
                    current_end = min(current_start + datetime.timedelta(days=max_days_per_request), end_dt)

                    start_str = current_start.strftime("%Y%m%d")
                    end_str = current_end.strftime("%Y%m%d")

                    segment_count += 1
                    GLOG.DEBUG(
                        f"Fetching segment {segment_count}/{total_segments} for {code}: {start_str} to {end_str}"
                    )

                    # 获取当前段的数据
                    r = self.pro.daily(ts_code=code, start_date=start_str, end_date=end_str, limit="50000")

                    if r.shape[0] > 0:
                        r.fillna(0, inplace=True)
                        all_data.append(r)
                        console.print(
                            f":crab: Segment {segment_count}/{total_segments}: Got {r.shape[0]} records about {code} daybar from {start_str} to {end_str}"
                        )
                    else:
                        GLOG.DEBUG(
                            f"No data for {code} in segment {segment_count}/{total_segments} {start_str} to {end_str}"
                        )

                    # 移动到下一个时间段
                    current_start = current_end + datetime.timedelta(days=1)

                    # 添加小延时，避免API调用过于频繁
                    if segment_count > 1:
                        import time

                        time.sleep(0.1)

            # 合并所有数据
            if len(all_data) == 0:
                return pd.DataFrame()
            elif len(all_data) == 1:
                result = all_data[0]
            else:
                result = pd.concat(all_data, ignore_index=True)

                # 按日期排序并去重
                if "trade_date" in result.columns:
                    result = (
                        result.sort_values("trade_date").drop_duplicates(subset=["trade_date"]).reset_index(drop=True)
                    )

                console.print(
                    f":green_circle: Merged {len(all_data)} segments, total {result.shape[0]} records for {code} daybar"
                )

            return result

        except Exception as e:
            GLOG.ERROR(f"Failed to fetch daybar for {code}: {e}")
            raise e

    def fetch_cn_stock_min(
        self, code: str, start_date: any = GCONF.DEFAULTSTART, end_date: any = GCONF.DEFAULTEND, *args, **kwargs
    ) -> pd.DataFrame:
        pass

    def _calculate_optimal_window_size(self, total_days: int) -> int:
        """
        根据总天数计算最优的窗口大小（用于复权因子数据）

        Args:
            total_days: 总的日期跨度天数

        Returns:
            最优的单次请求天数
        """
        # 基础窗口大小（约2年，复权因子数据稀疏）
        base_window = 365 * 6

        # 根据总天数调整窗口大小
        if total_days <= 730:  # 2年以内
            return total_days
        else:  # 5年以内
            return 365 * 10

        # 保守策略，确保不会超过API限制
        return min(base_window, total_days)

    def _calculate_daybar_window_size(self, total_days: int) -> int:
        """
        根据总天数计算日线数据的最优窗口大小

        Args:
            total_days: 总的日期跨度天数

        Returns:
            最优的单次请求天数
        """
        # 日线数据较密集，A股市场约250个交易日/年
        # 为确保不超过API限制，需要更保守的窗口设置

        if total_days <= 365 * 3:  # 3年以内
            return total_days
        else:  # 10年以上
            return 1095 * 3  # 10年窗口

    @time_logger
    @retry(max_try=11)
    def fetch_cn_stock_adjustfactor(
        self, code: str, start_date: any = GCONF.DEFAULTSTART, end_date: any = GCONF.DEFAULTEND, *args, **kwargs
    ) -> pd.DataFrame:
        """
        获取复权因子数据，支持大日期跨度的分页获取

        Args:
            code: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            包含复权因子数据的DataFrame
        """
        import datetime

        start_dt = datetime_normalize(start_date)
        end_dt = datetime_normalize(end_date)

        # 计算日期跨度（天数）
        date_span = (end_dt - start_dt).days

        # 设置单次请求的最大天数（保守估计，避免超过6000条限制）
        # 复权因子数据通常不是每日都有，所以可以设置较大的窗口
        # 对于A股市场，复权因子变化频率相对较低，大部分时间复权因子为1.0
        max_days_per_request = self._calculate_optimal_window_size(date_span)

        all_data = []

        try:
            # 如果日期跨度较小，直接获取
            if date_span <= max_days_per_request:
                start_str = start_dt.strftime("%Y-%m-%d")
                end_str = end_dt.strftime("%Y-%m-%d")

                r = self.pro.adj_factor(ts_code=code, start_date=start_str, end_date=end_str, limit=6000)
                if r.shape[0] > 0:
                    all_data.append(r)
                    console.print(
                        f":crab: Got {r.shape[0]} records about {code} adjustfactor from {start_str} to {end_str}"
                    )
            else:
                # 分段获取
                GLOG.INFO(f"Large date span ({date_span} days) detected for {code}, using segmented fetch")

                # 预先计算总段数
                total_segments = 0
                temp_start = start_dt
                while temp_start < end_dt:
                    temp_end = min(temp_start + datetime.timedelta(days=max_days_per_request), end_dt)
                    total_segments += 1
                    temp_start = temp_end + datetime.timedelta(days=1)

                GLOG.INFO(f"Will fetch {total_segments} segments for {code}")

                current_start = start_dt
                segment_count = 0

                while current_start < end_dt:
                    # 计算当前段的结束日期
                    current_end = min(current_start + datetime.timedelta(days=max_days_per_request), end_dt)

                    start_str = current_start.strftime("%Y-%m-%d")
                    end_str = current_end.strftime("%Y-%m-%d")

                    segment_count += 1
                    GLOG.DEBUG(
                        f"Fetching segment {segment_count}/{total_segments} for {code}: {start_str} to {end_str}"
                    )

                    # 获取当前段的数据
                    r = self.pro.adj_factor(ts_code=code, start_date=start_str, end_date=end_str, limit=6000)

                    if r.shape[0] > 0:
                        all_data.append(r)
                        console.print(
                            f":crab: Segment {segment_count}/{total_segments}: Got {r.shape[0]} records about {code} adjustfactor from {start_str} to {end_str}"
                        )
                    else:
                        GLOG.DEBUG(
                            f"No data for {code} in segment {segment_count}/{total_segments} {start_str} to {end_str}"
                        )

                    # 移动到下一个时间段
                    current_start = current_end + datetime.timedelta(days=1)

                    # 添加小延时，避免API调用过于频繁
                    if segment_count > 1:
                        import time

                        time.sleep(0.1)

            # 合并所有数据
            if len(all_data) == 0:
                return pd.DataFrame()
            elif len(all_data) == 1:
                result = all_data[0]
            else:
                result = pd.concat(all_data, ignore_index=True)

                # 按日期排序并去重
                if "trade_date" in result.columns:
                    result = (
                        result.sort_values("trade_date").drop_duplicates(subset=["trade_date"]).reset_index(drop=True)
                    )

                console.print(
                    f":green_circle: Merged {len(all_data)} segments, total {result.shape[0]} records for {code} adjustfactor"
                )

            return result

        except Exception as e:
            GLOG.ERROR(f"Failed to fetch adjustfactor for {code}: {e}")
            raise e
