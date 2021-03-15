import time
import requests
import json
import csv


time_stamp = int(time.time())
print(f"Now timestamp: {time_stamp}")
# 1367107200
request_link = f"https://web-api.coinmarketcap.com/v1/cryptocurrency/ohlcv/historical?convert=USD&slug=ethereum&time_end={time_stamp}&time_start=1356969600"
print("Request link: " + request_link)
r = requests.get(url=request_link)
# print(r.content)
# 返回的数据是 JSON 格式，使用 json 模块解析
content = json.loads(r.content)
print(type(content))
print(content)
quoteList = content["data"]["quotes"]
new_list = []
for i in quoteList:
    item = {}
    item["time"] = i["quote"]["USD"]["timestamp"]
    item["open"] = i["quote"]["USD"]["open"]
    item["high"] = i["quote"]["USD"]["high"]
    item["low"] = i["quote"]["USD"]["low"]
    item["close"] = i["quote"]["USD"]["close"]
    new_list.append(item)
# print(quoteList)

# 将数据保存为 BTC.csv
# for windows, newline=''
# with open("BTC.csv", "w", encoding="utf8", newline="") as f:
#     csv_write = csv.writer(f)
#     csv_head = ["Date", "Price", "Volume"]
#     csv_write.writerow(csv_head)

#     for quote in quoteList:
#         quote_date = quote["time_open"][:10]
#         quote_price = "{:.2f}".format(quote["quote"]["USD"]["close"])
#         quote_volume = "{:.2f}".format(quote["quote"]["USD"]["volume"])
#         csv_write.writerow([quote_date, quote_price, quote_volume])

# print("Done")

import pandas as pd

# series = pd.DataFrame()
df = pd.DataFrame(new_list)
print(df)
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