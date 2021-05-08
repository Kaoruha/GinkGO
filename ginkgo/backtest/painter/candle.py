"""
蜡烛图
"""
import matplotlib.pyplot as plt
import matplotlib as mpl
import pandas as pd
from ginkgo.data.ginkgo_mongo import ginkgo_mongo as gm
from ginkgo.backtest.painter.base_painter import BasePainter


class CandlePainter(BasePainter):
    def __init__(self, *args):
        super(CandlePainter, self).__init__(*args)

    def draw(self):
        # 预处理
        self.pre_treate()
        df = self.data[["open", "close", "high", "low", "volume"]]
