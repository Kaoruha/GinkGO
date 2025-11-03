from ginkgo.trading.strategy.selectors.base_selector import BaseSelector
from ginkgo.data.containers import container
from ginkgo.libs import datetime_normalize
import pandas as pd

import datetime


class MomentumSelector(BaseSelector):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(
        self,
        name: str = "MomentumSelector",
        interval: int = 5,
        rank: int = 5,
        window: int = 20,
        *args,
        **kwargs,
    ) -> None:
        super(MomentumSelector, self).__init__(name, *args, **kwargs)
        self._interested = []
        self._interval = interval
        self._rank = rank
        self._window = window
        self._last_pick = None

    @property
    def interval(self) -> int:
        return self._interval

    @property
    def rank(self) -> int:
        return self._rank

    @property
    def window(self) -> int:
        return self._window

    def pick(self, time: any = None, *args, **kwargs) -> list[str]:
        end_date = datetime_normalize(time)
        start_date = end_date - datetime.timedelta(days=self._window)
        if self._last_pick is None:
            self._last_pick = end_date
        else:
            if end_date < self._last_pick:
                # as usual time should never be less than last_pick but just in case
                self._last_pick = end_date
            if end_date - datetime_normalize(self._last_pick) <= datetime.timedelta(days=self._interval):
                if len(self._interested) > 0:
                    return self._interested
            if end_date - datetime_normalize(self._last_pick) > datetime.timedelta(days=self._interval):
                self._last_pick = end_date

        res = pd.DataFrame(columns=["code", "name", "momentum"])
        stockinfo_crud = container.cruds.stock_info()
        df = stockinfo_crud.get_page_filtered()
        df = df[:50]
        for i, r in df.iterrows():
            code = r["code"]
            name = r["code_name"]
            self.log("DEBUG", f"Pick {code} from {start_date} to {end_date}")
            bar_crud = container.cruds.bar()
            df = bar_crud.get_page_filtered(code=code, start_date=start_date, end_date=end_date, as_dataframe=True)
            if df.shape[0] == 0:
                continue
            momentum = df["close"].iloc[-1] / df["close"].iloc[0] - 1
            new_df = pd.DataFrame([{"code": code, "name": name, "momentum": momentum}])
            res = pd.concat([res, new_df], ignore_index=True)
        res = res.sort_values(by="momentum", ascending=False).head(self._rank)
        if res.shape[0] > 0:
            self._interested = res["code"].tolist()
        return self._interested
