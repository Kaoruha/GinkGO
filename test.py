from ginkgo.backtest.plots.terminal_candle import TerminalCandle
from ginkgo.data.operations import get_bars_page_filtered, get_stockinfos_filtered

infos = get_stockinfos_filtered()

info = infos.iloc[0]

df = get_bars_page_filtered(code=info["code"], start_date="2020-01-01", end_date="2021-01-01", as_dataframe=True)

TerminalCandle(data=df, title=info["code"]).show()
