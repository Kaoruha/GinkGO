import matplotlib.pyplot as plt
import numpy as np
import matplotlib.ticker as ticker
import matplotlib.gridspec as gridspec
from src.data.ginkgo_mongo import ginkgo_mongo as gm

df = gm.get_dayBar_by_mongo(code="sz.000725", start_date="2020-04-04")
x = df["date"].values
open_ = df["open"].astype(float).values
close = df["close"].astype(float).values
high = df["high"].astype(float).values
low = df["low"].astype(float).values
volume = df["volume"].astype(float).values


fig = plt.figure(figsize=(16, 9))
# 设置字体
# plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["font.sans-serif"] = ["Songti SC"]
plt.rcParams["axes.unicode_minus"] = False

# 设置标题
fig.suptitle("测试", fontsize=20, x=0.5, y=0.97)

# 划分Grid
gs = gridspec.GridSpec(40, 40)

# 生成上下两张图
ax2 = fig.add_subplot(gs[29:40, 0:40])
ax1 = fig.add_subplot(gs[0:30, 0:40], sharex=ax2)

# 判断涨跌颜色
up = close >= open_
colors = np.zeros(up.size, dtype="U5")
colors[:] = "red"
colors[up] = "green"


# 画图
# 蜡烛
ax1.bar(x=x, height=close - open_, bottom=open_, color=colors)
# 腊烛芯
ax1.vlines(x, low, high, color=colors, linewidth=0.6)
# 成交量
ax2.bar(x=x, height=volume, color=colors)
ax1.grid(color="gray", linestyle="--", linewidth=1, alpha=0.3)
ax1.xaxis.set_major_locator(ticker.NullLocator())
ax2.xaxis.set_major_locator(ticker.MultipleLocator(base=30))

plt.show()
