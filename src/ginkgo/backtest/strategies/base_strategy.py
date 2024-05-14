import pandas as pd
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.backtest.signal import Signal
from ginkgo.backtest.backtest_base import BacktestBase


class StrategyBase(BacktestBase):
    def __init__(self, spans: int = 20, name: str = "Strategy", *args, **kwargs):
        super(StrategyBase, self).__init__(name=name, *args, **kwargs)
        self._portfolio = None
        self._raw = {}
        self._attention_spans = 20
        self.set_attention_spans(spans)

    @property
    def raw(self):
        return self._raw

    @property
    def attention_spans(self):
        return self._attention_spans

    def set_attention_spans(self, spans: int) -> None:
        # Keep attention of raw data
        if isinstance(spans, int) and spans > 0:
            self._attention_spans = spans

        if isinstance(spans, str):
            self._attention_spans = int(spans)

    def on_price_update(self, code):
        pass

    @property
    def portfolio(self):
        return self._portfolio

    def bind_portfolio(self, portfolio, *args, **kwargs):
        self._portfolio = portfolio
        self.set_backtest_id(portfolio.backtest_id)

    def cal(self, *args, **kwargs) -> Signal:
        pass
