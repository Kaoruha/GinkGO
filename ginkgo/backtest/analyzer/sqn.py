"""
Date: 2022-03-03 15:21:49
Author: Suny
LastEditors: Suny
LastEditTime: 2022-03-03 15:21:49
FilePath: \GinkGO\ginkgo\backtest\analyzer\sqn.py
"""
"""
SQN公式有什麼意義呢？很簡單，稍微瞇著眼睛觀察一下不難理解：

1. 期望獲利越高，SQN值越大。(線性成長)

2. 標準差越小，SQN值越大。(倒數關係)

3. 交易次數(N)越多，SQN值越大。(開根號後線性)


    - 1.6 - 1.9 Below average
    - 2.0 - 2.4 Average
    - 2.5 - 2.9 Good
    - 3.0 - 5.0 Excellent
    - 5.1 - 6.9 Superb
    - 7.0 -     Holy Grail?

The formula:

    - SquareRoot(NumberTrades) * Average(TradesProfit) / StdDev(TradesProfit)

The sqn value should be deemed reliable when the number of trades >= 30
"""
