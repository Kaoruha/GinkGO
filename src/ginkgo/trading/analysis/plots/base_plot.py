import matplotlib.pyplot as plt
import os
from matplotlib.font_manager import fontManager
import numpy as np


class BasePlot(object):
    def __init__(self, title: str = "", *args, **kwargs):
        self.figure = None
        self.raw = None
        self.title = "Hello."
        if title != "":
            self.set_title(title)

    def set_title(self, title: str):
        self.title = title
        if self.figure is not None:
            self.figure.suptitle(self.title, fontsize=20, x=0.5, y=0.97)

    @property
    def colors(self) -> list:
        l = ["cornflowerblue", "tomato", "lightgreen"]
        return l

    def set_default_cn_font(self, font=""):
        if font != "":
            plt.rcParams["font.sans-serif"] = ["SimHei"]
        else:
            fonts = [
                font.name
                for font in fontManager.ttflist
                if os.path.exists(font.fname) and os.stat(font.fname).st_size > 1e6
            ]
            plt.rcParams["font.sans-serif"] = [fonts[0]]

    def show(self, *args, **kwargs):
        plt.show()
