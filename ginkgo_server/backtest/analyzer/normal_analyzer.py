from ginkgo_server.backtest.analyzer.base_analyzer import BaseAnalyzer
import datetime

class NormalAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__()


    def report(self, *args, **kwargs):
        date = args[0].current_date
        self._init_date = date if self._init_date is '' else self._init_date
        if date > self._current_date:
            self._current_date = date
        d1 = datetime.datetime.strptime(str(self._init_date), '%Y-%m-%d')
        d2 = datetime.datetime.strptime(str(self._current_date), '%Y-%m-%d')
        days = (d2-d1).days if (d2-d1).days != 0 else 1
        years = days/365
        self._init_capital = args[0]._init_capital
        self._capital = args[0]._capital
        self._position = args[0].position
        self._freeze = args[0]._freeze
        self._current_price = args[0].current_price

        self._stock_value = 0
        for k,v in self._position.items():
            self._stock_value += v.volume * v.current_price

        self._profit = (self._capital + self._freeze + self._stock_value-self._init_capital)/(self._init_capital*years)
        self._max_drawdown = min(self._max_drawdown,self._profit)
        self._max_profit = max(self._max_profit,self._profit)
        print(f'{self._current_date}  收益:{round(self._profit,2)}%  最大收益:{round(self._max_profit,2)}%  最大回撤:{ round(self._max_drawdown,2)}% 评价: 待完善')

    def give_mark(self):
        pass

        