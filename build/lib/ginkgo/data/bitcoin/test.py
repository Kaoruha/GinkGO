# http://api.coincap.io/v2/assets/bitcoin/history?interval=m1

import time
import requests
import json
import csv


time_stamp = int(time.time())
print(f"Now timestamp: {time_stamp}")
# 1367107200
request_link = "http://api.coincap.io/v2/assets/bitcoin/history?interval=m1&start=1528370720000&end=1615798408000"
print("Request link: " + request_link)
r = requests.get(url=request_link)
# print(r.content)
# 返回的数据是 JSON 格式，使用 json 模块解析
content = json.loads(r.content)
# print(content["data"])
# quoteList = content["data"]["quotes"]
# new_list = []
# for i in quoteList:
#     item = {}
#     item["time"] = i["quote"]["USD"]["timestamp"]
#     item["open"] = i["quote"]["USD"]["open"]
#     item["high"] = i["quote"]["USD"]["high"]
#     item["low"] = i["quote"]["USD"]["low"]
#     item["close"] = i["quote"]["USD"]["close"]
#     new_list.append(item)

import pandas as pd

# series = pd.DataFrame()
df = pd.DataFrame.from_dict(content["data"])
print(df)
# print(df)
# series["Date"] = df["Date"].tolist()
# series["Price"] = df["Price"].tolist()
# series["Volume"] = df["Volume"].tolist()

# print(series)

# import matplotlib.pyplot as plt

# ax = plt.gca()
# series.plot(kind="line", x="Date", y="Price", ax=ax)
# plt.show()

# plt.cla()
# ax = plt.gca()
# series.plot(kind="line", x="Date", y="Volume", ax=ax)
# plt.show()