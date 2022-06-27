from ginkgo.backtest.painter.candle_trend import CandleTrend

code = "sh.000001"
p = CandleTrend(code=code, starttime="2019-01-01", endtime="2020-01-01")

p.get_data()
p.draw()
