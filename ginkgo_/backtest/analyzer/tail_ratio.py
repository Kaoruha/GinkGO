"""
Date: 2022-03-01 15:23:36
Author: Suny
LastEditors: Suny
LastEditTime: 2022-03-01 15:23:37
FilePath: \GinkGO\ginkgo\backtest\analyzer\tail_ratio.py
"""
"""
日收益分布的95分位值/5分位值。【使用范围】：均值回归策略，这类型策略的最大风险在于左侧的尾部风险。单次的大额回撤需要很长的时间才能够恢复。因此 tail_ratio 很适合用来刻画这类策略面临的风险。【意义】：tail 比率越大越好，可以理解成衡量最好情况与最坏情况下的收益表现的指标。例如：tail_ratio = 0.25，5分位的亏损是95分位收益的四倍。 这样的策略在发生大额亏损的情况下很难在短时间内恢复
"""
