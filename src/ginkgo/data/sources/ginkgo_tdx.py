# Upstream: 数据更新任务, 实时行情获取, BarService
# Downstream: GinkgoSourceBase, mootdx库, GLOG
# Role: 通达信(TDX)数据源适配器，提供实时行情快照和多周期K线数据获取






import pandas as pd
import datetime
from typing import List

from ginkgo.data.sources.source_base import GinkgoSourceBase
from ginkgo.libs import datetime_normalize
from mootdx.quotes import Quotes
from ginkgo.libs import GLOG, retry, time_logger
from rich.console import Console

console = Console()


import random


def _parse_a_share_code(code: str) -> "tuple[str, str] | None":
    """解析A股代码为 (code_num, code_market)，无后缀时按前缀推断市场。

    #5999: ``code.split(".")[1]`` 在无市场后缀（如 "000001"）时 IndexError 崩溃。
    tdx 仅支持 SH/SZ，按 A 股代码前缀规则推断：
      - 6 开头 → SH（沪市主板/科创板）
      - 0/3 开头 → SZ（深市主板/创业板）
      - 其他 → None（北交所等 tdx 不支持，交调用方友好处理）
    有后缀时原样返回（upper 归一）。
    """
    parts = code.split(".")
    code_num = parts[0]
    if len(parts) > 1:
        return code_num, parts[1].upper()
    if code_num.startswith("6"):
        return code_num, "SH"
    if code_num.startswith(("0", "3")):
        return code_num, "SZ"
    return None


class GinkgoTDX(GinkgoSourceBase):
    # 连接池上限:tdxpy 内置 104 台,实测可用率 ~12%(2026-08-26 抽样 3/25)。
    # mootdx bestip 只测其窄池前几台,全废概率高(两轮实证:12 台手挑池全灭、
    # bestip 两种时段均失败)——改为 tdxpy 全量池随机起点试连,协议级验证
    # (get_security_bars 真拉数据,非仅 TCP),命中即用,上限控制启动耗时
    FAILOVER_SAMPLE = 15
    FAILOVER_TIMEOUT = 6

    def __init__(self, server=None):
        self.client = self._connect_with_failover(server)

    def _connect_with_failover(self, server=None):
        """显式 server 优先;否则从 tdxpy 内置池随机抽样试连(协议级验证)。

        Returns: 可用的 Quotes 客户端;全部失败时抛最后一次异常。
        """
        import random as _random
        last_err: Exception = RuntimeError("no TDX server attempted")

        # 1) 显式指定(配置/测试用)
        if server:
            return Quotes.factory(
                market="std", server=server, timeout=self.FAILOVER_TIMEOUT,
                quiet=True, verbose=0,
            )

        # 2) tdxpy 内置池随机抽样 + 协议级验证
        from tdxpy.hq import TdxHq_API
        from tdxpy.constants import hq_hosts

        pool = [(h[1], int(h[2])) for h in hq_hosts]
        _random.shuffle(pool)
        for ip, port in pool[: self.FAILOVER_SAMPLE]:
            probe = TdxHq_API()
            try:
                if not probe.connect(ip, port, time_out=self.FAILOVER_TIMEOUT):
                    continue
                bars = probe.get_security_bars(9, 1, "600036", 0, 5)
                if bars is not None and len(bars) > 0:
                    GLOG.INFO(f"TDX failover connected: {ip}:{port} (pool sample)")
                    return Quotes.factory(
                        market="std", server=(ip, port),
                        timeout=15, quiet=True, verbose=0,
                    )
            except Exception as e:
                last_err = e
            finally:
                try:
                    probe.disconnect()
                except Exception:
                    pass

        # 3) 兜底:mootdx bestip(维持旧行为,给窄池一次机会)
        GLOG.WARN("TDX pool sample all dead, fallback to mootdx bestip")
        return Quotes.factory(market="std", bestip=True, timeout=15, quiet=True, verbose=0)
        self.bar_type = {
            "0": "5m",
            "1": "15m",
            "2": "30m",
            "3": "1h",
            "4": "days",
            "5": "week",
            "6": "mon",
            "7": "1m",
            "8": "1m",
            "9": "day",
            "10": "3mon",
            "11": "year",
        }

    @time_logger
    def fetch_live(self, codes: List[str], *args, **kwargs) -> pd.DataFrame:
        """
          Index(['market', 'code', 'active1', 'price', 'last_close', 'open', 'high',
         'low', 'servertime', 'reversed_bytes0', 'reversed_bytes1', 'vol',
         'cur_vol', 'amount', 's_vol', 'b_vol', 'reversed_bytes2',
         'reversed_bytes3', 'bid1', 'ask1', 'bid_vol1', 'ask_vol1', 'bid2',
         'ask2', 'bid_vol2', 'ask_vol2', 'bid3', 'ask3', 'bid_vol3', 'ask_vol3',
         'bid4', 'ask4', 'bid_vol4', 'ask_vol4', 'bid5', 'ask5', 'bid_vol5',
         'ask_vol5', 'reversed_bytes4', 'reversed_bytes5', 'reversed_bytes6',
         'reversed_bytes7', 'reversed_bytes8', 'reversed_bytes9', 'active2',
         'volume'],
        dtype='object')
        """
        df = self.client.quotes(symbol=codes)
        console.print(f":crab: Got {df.shape[0]} records about live from [bold #E4C1C0]TDX[/].")
        return df

    @time_logger
    @retry
    def fetch_latest_bar(self, code: str, frequency: int = 7, count: int = 20, *args, **kwargs) -> pd.DataFrame:
        """
        frequency -> K线种类
        self.assertGreater(len(df), 0)
        0 => 5分钟K线 => 5m
        1 => 15分钟K线 => 15m
        2 => 30分钟K线 => 30m
        3 => 小时K线 => 1h
        4 => 日K线 (小数点x100) => days
        5 => 周K线 => week
        6 => 月K线 => mon
        7 => 1分钟K线(好像一样) => 1m
        8 => 1分钟K线(好像一样) => 1m
        9 => 日K线 => day
        10 => 季K线 => 3mon
        11 => 年K线 => year
        """
        code_num = code.split(".")[0]
        df = self.client.bars(symbol=code_num, frequency=frequency, offset=count)
        console.print(
            f":crab: Got {df.shape[0]} records about {code_num} {self.bar_type[str(frequency)]} bar from [bold #E4C1C0]TDX[/]."
        )
        return df

    @time_logger
    @retry
    def fetch_stock_list(self, *args, **kwargs) -> pd.DataFrame:
        from mootdx import consts

        df_sh = self.client.stocks(market=consts.MARKET_SH)
        df_sh["code"] = df_sh["code"].apply(lambda x: str(x) + ".SH")
        df_sz = self.client.stocks(market=consts.MARKET_SZ)
        df_sz["code"] = df_sz["code"].apply(lambda x: str(x) + ".SZ")
        df = pd.concat([df_sh, df_sz])
        console.print(f":crab: Got {df.shape[0]} records about stocklist from [bold #E4C1C0]TDX[/].")
        return df

    @time_logger
    @retry
    def fetch_history_transaction_summary(self, code: str, date: any, *args, **kwargs) -> pd.DataFrame:
        code_num = code.split(".")[0]
        date = datetime_normalize(date)
        date_num = date.strftime("%Y%m%d")
        date_num = int(date_num)
        df = self.client.minutes(symbol=code_num, date=date_num)
        console.print(f":crab: Got {df.shape[0]} records about {code} Tick Summary from [bold #E4C1C0]TDX[/].")
        return df

    @time_logger
    @retry
    def fetch_history_transaction_detail(self, code: str, date: any, *args, **kwargs) -> pd.DataFrame:

        def time_combine(time):
            new_date = datetime_normalize(date)
            time = datetime.datetime.strptime(time, "%H:%M").time()
            return datetime.datetime.combine(new_date, time)

        parsed = _parse_a_share_code(code)
        if parsed is None:
            console.print(f":warning: 无法解析 {code} 的市场后缀，请使用完整格式（如 000001.SZ）")
            return
        code_num, code_market = parsed
        if code_market not in ["SH", "SZ"]:
            console.print("TDX api just support SH and SZ now.")
            return
        date = datetime_normalize(date)
        date_num = date.strftime("%Y%m%d")
        date_num = int(date_num)
        start = 0
        page = 1000
        df = pd.DataFrame()
        with console.status(f":dango: Fetching {code} tick records from [bold #E4C1C0]TDX[/].") as status:
            while True:
                temp = self.client.transactions(symbol=code_num, start=start, offset=page, date=date_num)
                start += page
                df = pd.concat([df, temp])
                if temp.shape[0] < page:
                    break
        console.print(f":crab: Got {df.shape[0]} tick records about {code} from [bold #E4C1C0]TDX[/].")
        if df.shape[0] == 0:
            return pd.DataFrame()
        else:
            df["timestamp"] = df["time"].apply(lambda x: time_combine(x))
            df = df.sort_values(by="timestamp")
            df = df.reset_index(drop=True)
            return df

    @time_logger
    @retry
    def fetch_adjustfactor(self, code: str, *args, **kwargs) -> pd.DataFrame:
        code_num = code.split(".")[0]
        df = self.client.xdxr(symbol=code_num)
        console.print(f":crab: Got {df.shape[0]} records about {code} adjustfactor from [bold #E4C1C0]TDX[/].")
        return df

    @time_logger
    @retry
    def fetch_history_daybar(self, code: str, start_date: any, end_date: any, *args, **kwargs) -> pd.DataFrame:
        code_num = code.split(".")[0]
        start_date = datetime_normalize(start_date).strftime("%Y-%m-%d")
        end_date = datetime_normalize(end_date).strftime("%Y-%m-%d")
        df = self.client.k(symbol=code_num, begin=start_date, end=end_date)
        console.print(f":crab: Got {df.shape[0]} records about {code} OHLC from [bold #E4C1C0]TDX[/].")
        return df

