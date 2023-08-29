import matplotlib.pyplot as plt
import os
from matplotlib.font_manager import fontManager
import numpy as np


class BasePlot(object):
    def __init__(self, title: str = ""):
        if title == "":
            self.title = "Hello."

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

    def test(self):
        plt.suptitle(self.title, fontsize=30)  # 添加总标题，并设置文字大小
        agraphic = plt.subplot(2, 1, 1)
        agraphic.set_title("SubTitle1")  # 添加子标题
        agraphic.set_xlabel("x-axis", fontsize=10)  # 添加轴标签
        agraphic.set_ylabel("y-axis", fontsize=20)
        bgraphic = plt.subplot(2, 1, 2)
        bgraphic.set_title("SubTitle2")
        ax = []  # 保存图1数据
        ay = []
        bx = []  # 保存图2数据
        by = []
        num = 0  # 计数
        plt.ion()  # 开启一个画图的窗口进入交互模式，用于实时更新数据
        # plt.rcParams['savefig.dpi'] = 200 #图片像素
        # plt.rcParams['figure.dpi'] = 200 #分辨率
        plt.rcParams["figure.figsize"] = (10, 10)  # 图像显示大小
        # plt.rcParams["font.sans-serif"] = ["SimHei"]  # 防止中文标签乱码，还有通过导入字体文件的方法
        plt.rcParams["axes.unicode_minus"] = False
        plt.rcParams["lines.linewidth"] = 1  # 设置曲线线条宽度
        while num < 100:
            # plt.clf()  # 清除刷新前的图表，防止数据量过大消耗内存
            g1 = np.random.random()  # 生成随机数画图
            # 图表1
            ax.append(num)  # 追加x坐标值
            ay.append(g1)  # 追加y坐标值
            agraphic.plot(ax, ay, "g-", color=self.colors[1])  # 等于plt.plot(ax,ay,'g-')
            # 图表2
            bx.append(num)
            by.append(g1)
            bgraphic.plot(bx, by, "r^")

            plt.pause(0.5)  # 设置暂停时间，太快图表无法正常显示
            # plt.savefig("picture.png", dpi=300)  # 设置保存图片的分辨率
            # break
            num = num + 1

        plt.ioff()  # 关闭画图的窗口，即关闭交互模式
        plt.show()
