"""
Date: 2022-03-01 15:08:41
Author: Suny
LastEditors: Suny
LastEditTime: 2022-03-01 15:23:30
FilePath: \GinkGO\ginkgo\backtest\analyzer\omega_ratio.py
"""
"""
omega比率实际上考虑了收益的整个分布信息，因此包括了所有高阶矩的信息。在临界收益率等于均值的时候，Omega比率等于1。在相同的临界收益率下，对于不同的投资选择，Omega比率越大越好。适用范围：在收益率不服从正态分布的时候，Omega是非常好的替代。【意义】：Omega比率值越高,投资绩效也就越好
"""
