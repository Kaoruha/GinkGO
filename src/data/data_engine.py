import pandas as pd
from src.data.ginkgo_mongo import ginkgo_mongo as gm
from src.backtest.event_engine import EventEngine
from src.backtest.events import MarketEvent
from src.backtest.price import Bar
from src.backtest.enums import *
from src.libs import GINKGOLOGGER as gl


class DataEngine(object):
    def __init__(self):
        self.codes = []
        self.data_cache = {}
        self.engine = None

        self.get_code_list()

    def set_event_engine(self, engine: EventEngine):
        self.engine = engine

    def get_code_list(self):
        self.codes = gm.get_all_stockcode_by_mongo()

    def check_code_exist(self, code: str) -> bool:
        b1 = any(self.codes.code == code)
        b2 = any(self.codes.code_name == code)
        return b1 or b2

    def get_bar_by_cache(self, code: str, start: str, end: str) -> pd.DataFrame:
        if code not in self.data_cache:
            gl.logger.warn(f"缓存中不存在 {code} 相关数据，尝试获取")
            if not self.save_to_cache(code=code):
                return None

        df = self.data_cache[code]

        condition = df["date"] >= start
        condition2 = df["date"] <= end
        result = df[condition & condition2].replace("", 0)
        if result.shape[0] == 0:
            return None
        else:
            return result

    def save_to_cache(self, code: str) -> bool:
        if not self.check_code_exist(code=code):
            gl.logger.error(f"数据库中没有 {code} 相关数据，缓存失败")
            return False
        df = gm.get_dayBar_by_mongo(code=code)
        if df.shape[0] > 0:
            self.data_cache[code] = df
            return True
        else:
            gl.logger.error(f"后台数据库中 {code} 相关数据为空")
            return False

    def get_daybar(self, code: str, date: str) -> None:
        if not self.check_code_exist(code=code):
            gl.logger.error(f"数据库中没有 {code} 相关数据")
            return
        if code not in self.data_cache:
            if not self.save_to_cache(code=code):
                gl.logger.error(f"缓存失败，无法获取 {code} 相关数据")
                return

        df = self.get_bar_by_cache(code=code, start=date, end=date)
        if df is None:
            gl.logger.warn(f"{date} {code} 没有交易数据")
            return

        code_ = df.code.values[0]
        open_ = df.open.values[0]
        high = df.high.values[0]
        low = df.low.values[0]
        close = df.close.values[0]
        volume = df.volume.values[0]
        amount = df.amount.values[0]
        turn = df.turn.values[0]
        pct = df["pct_change"].values[0]

        if self.engine:
            code = df.code.values
            b = Bar(
                code=code_,
                open_price=open_,
                close_price=close,
                high_price=high,
                low_price=low,
                volume=volume,
                turnover=turn,
                pct=pct,
                datetime=date,
            )
            e = MarketEvent(
                code=code,
                raw=b,
                markert_event_type=MarketEventType.BAR,
                source=Source.BACKTEST,
                datetime=date,
            )
            self.engine.put(event=e)
        else:
            gl.logger.warn("事件引擎未注册至数据引擎")
