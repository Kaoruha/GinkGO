'''
Date: 2021-12-23 10:16:23
Author: Suny
LastEditors: Suny
LastEditTime: 2022-03-01 15:22:47
FilePath: \GinkGO\src\backtest\analyzer\sortino_ratio.py
'''
"""
索提诺比率
"""

"""
与夏普比率类似，所不同的是它区分了波动的好坏，因此在计算波动率时它所采用的不是标准差，而是下行标准差。这其中的隐含条件是投资组合的上涨（正回报率）符合投资人的需求，不应计入风险调整。具体计算方法为：(策略收益-无风险利率)/策略下行波动率。【适用范围】：因为索提诺比率使用的是下行偏差来考虑风险，那么所有的下行偏差局限性也会出现在索提诺比率中。也就是必须要有足够多的“不良”观测，才能计算一个有效的索提诺比率。sortino 比率数值越大，业绩表现越好。
"""