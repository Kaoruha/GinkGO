import pandas as pd
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.backtest.signal import Signal


class StrategyBase(object):
    def __init__(self, spans: int = 20, name: str = "Strategy", *args, **kwargs):
        super(StrategyBase, self).__init__(*args, **kwargs)
        self._name = ""
        self.set_name(name)
        self._portfolio = None
        self._raw = {}
        self._attention_spans = 20
        self.set_attention_spans(spans)

    @property
    def name(self) -> str:
        return self._name

    def set_name(self, name: str) -> None:
        self._name = name

    @property
    def cache(self):
        return self._raw

    @property
    def attention_spans(self):
        return self._attention_spans

    def set_attention_spans(self, spans: int) -> None:
        # Keep attention of raw data
        self._attention_spans = spans

    def on_price_update(self, data):
        df = data.to_dataframe()
        code = df.iloc[0]["code"]
        if code not in self._raw.keys():
            # init
            self._raw[code] = df
        else:
            # append
            if self._raw[code].shape[0] >= self._attention_spans:
                self._raw[code] = self._raw[code].iloc[1:]
            self._raw[code] = pd.concat([self._raw[code], df])
            self._raw[code] = self._raw[code].sort_values(
                by="timestamp", ascending=True
            )
        # print(self._raw[code])
        # print(self._raw[code].shape)

    @property
    def portfolio(self):
        return self._portfolio

    def bind_portfolio(self, portfolio, *args, **kwargs):
        self._portfolio = portfolio

    def cal(self, *args, **kwargs) -> Signal:
        GLOG.INFO(f"Under {self.name} Calculating...")
