from ginkgo_server.backtest.analyzer.base_analyzer import BaseAnalyzer
import datetime
import matplotlib.pyplot as plt

plt.switch_backend("agg")


class NormalAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__()
        self.win_days = 0
        self.lose_days = 0

    def report(self, *args, **kwargs):
        date = args[0].current_date
        self._init_date = date if self._init_date == "" else self._init_date
        if date > self._current_date:
            self._current_date = date
        d1 = datetime.datetime.strptime(str(self._init_date), "%Y-%m-%d")
        d2 = datetime.datetime.strptime(str(self._current_date), "%Y-%m-%d")
        days = (d2 - d1).days if (d2 - d1).days != 0 else 1
        years = days / 365
        if years < 1:
            years = 1
        self._init_capital = args[0]._init_capital
        self._capital = args[0]._capital
        self._position = args[0].position
        self._freeze = args[0]._freeze
        self._current_price = args[0].current_price

        self._stock_value = 0
        for k, v in self._position.items():
            self._stock_value += (v.volume + v.freeze) * v.price
        self._profit = (
            self._capital + self._freeze + self._stock_value - self._init_capital
        ) / self._init_capital
        if self._profit > 0:
            self.win_days += 1
        else:
            self.lose_days += 1
        self._max_drawdown = min(self._max_drawdown, self._profit)
        self._max_profit = max(self._max_profit, self._profit)
        str1 = f"当前收益: {round((self._profit),3):<10}"
        str2 = f"最大收益: {round(self._max_profit,3):<10}"
        str3 = f"最大回撤: {round(self._max_drawdown,3):<10}"
        str4 = f"盈利比率:{self.win_days:>4}/{self.win_days+self.lose_days:<4}"
        print(
            f"{self._current_date}"
            + "  "
            + str1
            + "  "
            + str2
            + "  "
            + str3
            + "  "
            + str4
            + "  评价: 待完善"
        )
        # self.draw()

    def give_mark(self):
        pass
