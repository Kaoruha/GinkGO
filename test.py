from ginkgo_server.backtest.postion import Position

a = Position(code='aaa', buy_price=10, volume=100)
a.buy(10,100)
a.buy(40,200)
a.ready_to_sell(200)
a.sell(100)